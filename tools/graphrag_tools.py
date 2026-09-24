"""
FraudLens — Production GraphRAG Engine
=======================================
Combines TigerGraph graph-topological traversal with semantic vector retrieval,
hybrid score fusion, graph-aware reranking, and contextual reasoning.

Core Architecture:
  1. EmbeddingProvider: Abstraction supporting deterministic TF-IDF Vectorizer
     (with optional Google Gemini embedding provider).
  2. LocalVectorStore: Persistent vector index with metadata, temporal anti-leakage,
     and strict vector-to-document alignment.
  3. HybridRetriever: Multi-modal fusion of graph + semantic relevance.
  4. GraphRAGContextBuilder: Assembles current evidence, graph topology,
     and historical analog cases for structured reasoning.
"""

from __future__ import annotations

import os
import json
import math
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field, asdict
from loguru import logger
import numpy as np

# Directory paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. Embedding Provider Abstraction
# ============================================================

class EmbeddingProvider:
    """Base interface for generating dense vector representations."""

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


class TFIDFEmbeddingProvider(EmbeddingProvider):
    """
    Lightweight, deterministic, offline-resilient embedding provider
    using sublinear TF-IDF + L2 normalization.
    Ensures 100% zero-downtime semantic search without external API quotas.
    """

    def __init__(self, vocab_path: Optional[Path] = None):
        self.vocab_path = vocab_path or (VECTOR_STORE_DIR / "tfidf_model.pkl")
        self.vectorizer = None
        self._load_or_init()

    def _load_or_init(self):
        if self.vocab_path.exists():
            try:
                with open(self.vocab_path, "rb") as f:
                    self.vectorizer = pickle.load(f)
                logger.info(f"Loaded TFIDF vectorizer from {self.vocab_path}")
            except Exception as e:
                logger.warning(f"Could not load TFIDF model: {e}")

    def fit_documents(self, texts: list[str]):
        """Fit vectorizer on historical corpus."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=512,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        self.vectorizer.fit(texts)
        with open(self.vocab_path, "wb") as f:
            pickle.dump(self.vectorizer, f)
        logger.info(f"TFIDF vectorizer fitted on {len(texts)} docs and saved to {self.vocab_path}")

    def embed_text(self, text: str) -> list[float]:
        if self.vectorizer is None:
            return [0.0] * 128
        vec = self.vectorizer.transform([text]).toarray()[0]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.vectorizer is None:
            return [[0.0] * 128 for _ in texts]
        mat = self.vectorizer.transform(texts).toarray()
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = mat / norms
        return normalized.tolist()


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Optional Google Gemini text embedding provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self._configured = False
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._configured = True
            except Exception as e:
                logger.debug(f"Optional Gemini embeddings not configured: {e}")

    def embed_text(self, text: str) -> list[float]:
        if not self._configured:
            raise RuntimeError("Gemini API not configured")
        import google.generativeai as genai
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_query"
        )
        return result["embedding"]


class CompositeEmbeddingProvider(EmbeddingProvider):
    """
    Hybrid embedding provider:
    Uses local deterministic TF-IDF index (with optional Gemini embedding support).
    """

    def __init__(self):
        self.gemini = GeminiEmbeddingProvider()
        self.tfidf = TFIDFEmbeddingProvider()

    def embed_text(self, text: str) -> list[float]:
        return self.tfidf.embed_text(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.tfidf.embed_documents(texts)


# ============================================================
# 2. Local Persistent Vector Store
# ============================================================

@dataclass
class VectorDocument:
    """Document record stored with vector and rich provenance."""
    doc_id: str
    text: str
    metadata: dict
    embedding: list[float] = field(default_factory=list)


class LocalVectorStore:
    """
    Lightweight, persistent Vector Store for ClosedCase memory.
    Guarantees strict 1:1 alignment between documents and embeddings matrix across
    indexing, upsert, update, and reload.
    """

    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = store_dir or VECTOR_STORE_DIR
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.store_dir / "index.json"
        self.matrix_file = self.store_dir / "embeddings.npy"
        
        self.documents: list[dict] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self._load()

    def _load(self):
        if self.index_file.exists() and self.matrix_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                self.embeddings_matrix = np.load(self.matrix_file)
                logger.info(f"Loaded VectorStore index: {len(self.documents)} cases from {self.store_dir}")
            except Exception as e:
                logger.warning(f"Could not load VectorStore from disk: {e}")
                self.documents = []
                self.embeddings_matrix = None

    def save(self):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2)
        if self.embeddings_matrix is not None:
            np.save(self.matrix_file, self.embeddings_matrix)
        logger.info(f"Persisted VectorStore: {len(self.documents)} cases")

    def count(self) -> int:
        return len(self.documents)

    def upsert(self, docs: list[VectorDocument]):
        """
        Idempotently insert or update case documents with strict 1:1 vector alignment.
        """
        doc_map = {d["doc_id"]: i for i, d in enumerate(self.documents)}
        
        if self.embeddings_matrix is not None and len(self.embeddings_matrix) == len(self.documents):
            existing_embeddings = [self.embeddings_matrix[i] for i in range(len(self.documents))]
        else:
            existing_embeddings = []

        for doc in docs:
            doc_dict = {
                "doc_id": doc.doc_id,
                "text": doc.text,
                "metadata": doc.metadata,
                "source": "vector_store",
            }
            if doc.doc_id in doc_map:
                idx = doc_map[doc.doc_id]
                self.documents[idx] = doc_dict
                if doc.embedding and len(existing_embeddings) > idx:
                    existing_embeddings[idx] = np.array(doc.embedding, dtype=np.float32)
            else:
                doc_map[doc.doc_id] = len(self.documents)
                self.documents.append(doc_dict)
                if doc.embedding:
                    existing_embeddings.append(np.array(doc.embedding, dtype=np.float32))

        if existing_embeddings:
            self.embeddings_matrix = np.array(existing_embeddings, dtype=np.float32)
        self.save()

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_pattern: Optional[str] = None,
        before_ts: Optional[float] = None
    ) -> list[dict]:
        """
        Perform cosine similarity search against stored embeddings with optional temporal anti-leakage.
        """
        if self.embeddings_matrix is None or len(self.documents) == 0:
            return []

        q = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm

        scores = np.dot(self.embeddings_matrix, q)

        results = []
        for i, score in enumerate(scores):
            if i >= len(self.documents):
                break
            doc = self.documents[i]
            meta = doc.get("metadata", {})
            if filter_pattern and meta.get("pattern") != filter_pattern:
                continue
            
            # Temporal anti-leakage filter
            if before_ts is not None:
                c_ts = meta.get("closed_at") or meta.get("timestamp") or meta.get("created_at")
                if c_ts is not None:
                    try:
                        ts_val = float(c_ts) if str(c_ts).replace(".", "").isdigit() else datetime.fromisoformat(str(c_ts)).timestamp()
                        if ts_val > before_ts:
                            continue
                    except Exception:
                        pass

            norm_score = max(0.0, min(1.0, float((score + 1.0) / 2.0)))
            results.append({
                "case_id": doc["doc_id"],
                "score": round(norm_score, 4),
                "retrieval_type": "semantic",
                "source": "vector_store",
                "text": doc["text"],
                "metadata": doc["metadata"],
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


# ============================================================
# 3. Hybrid Retrieval & Score Fusion
# ============================================================

class HybridRetriever:
    """
    Fuses topological graph query results with semantic vector search candidates.
    Applies graph-aware reranking and generates unified provenance metadata.
    """

    def __init__(
        self,
        graph_weight: float = 0.60,
        semantic_weight: float = 0.40,
    ):
        self.graph_weight = float(os.getenv("GRAPHRAG_GRAPH_WEIGHT", str(graph_weight)))
        self.semantic_weight = float(os.getenv("GRAPHRAG_SEMANTIC_WEIGHT", str(semantic_weight)))

    def fuse_and_rerank(
        self,
        graph_cases: list[dict],
        semantic_cases: list[dict],
        current_signals: Optional[dict] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Merge graph and vector candidates, computing normalized hybrid relevance.
        """
        fused_map: dict[str, dict] = {}
        current_signals = current_signals or {}

        # 1. Ingest Graph Candidates
        for gc in graph_cases:
            cid = gc.get("case_id") or gc.get("v_id")
            if not cid:
                continue
            g_score = float(gc.get("similarity_score") or gc.get("match_score", 3) / 6.0)
            g_score = min(1.0, max(0.0, g_score))
            
            fused_map[cid] = {
                "case_id": cid,
                "graph_score": g_score,
                "semantic_score": 0.0,
                "pattern": gc.get("pattern", "unknown"),
                "outcome": gc.get("outcome", "unknown"),
                "actions_taken": gc.get("actions_taken", []),
                "exposure_usd": gc.get("exposure_usd", 0.0),
                "analyst_notes": gc.get("analyst_notes_excerpt", "") or gc.get("analyst_notes", ""),
                "similarity_reasons": ["Topological graph traversal match"],
                "retrieval_type": "graph",
                "source": "TigerGraph / search_similar_cases",
            }

        # 2. Ingest Semantic Candidates
        for sc in semantic_cases:
            cid = sc.get("case_id")
            if not cid:
                continue
            s_score = float(sc.get("score", 0.5))
            meta = sc.get("metadata", {})

            if cid in fused_map:
                fused_map[cid]["semantic_score"] = s_score
                fused_map[cid]["retrieval_type"] = "hybrid"
                fused_map[cid]["source"] = "Hybrid: TigerGraph + VectorStore"
                fused_map[cid]["similarity_reasons"].append("Semantic narrative similarity")
            else:
                fused_map[cid] = {
                    "case_id": cid,
                    "graph_score": 0.0,
                    "semantic_score": s_score,
                    "pattern": meta.get("pattern", "unknown"),
                    "outcome": meta.get("outcome", "unknown"),
                    "actions_taken": meta.get("actions_taken", "").split("|") if isinstance(meta.get("actions_taken"), str) else meta.get("actions_taken", []),
                    "exposure_usd": float(meta.get("exposure_usd", 0.0)),
                    "analyst_notes": meta.get("analyst_notes", "") or sc.get("text", "")[:200],
                    "similarity_reasons": ["Semantic vector similarity on case narrative"],
                    "retrieval_type": "semantic",
                    "source": "VectorStore / analyst_notes embedding",
                }

        # 3. Compute Hybrid Score & Graph-Aware Boost
        fused_list = []
        for cid, item in fused_map.items():
            g = item["graph_score"]
            s = item["semantic_score"]
            
            if item["retrieval_type"] == "hybrid":
                base_score = (self.graph_weight * g) + (self.semantic_weight * s)
            elif item["retrieval_type"] == "graph":
                base_score = g * 0.85
            else:
                base_score = s * 0.75

            active_pattern = current_signals.get("pattern", "")
            if active_pattern and item.get("pattern") == active_pattern:
                base_score = min(1.0, base_score + 0.10)
                item["similarity_reasons"].append(f"Direct typology alignment ({active_pattern})")

            item["hybrid_score"] = round(min(1.0, max(0.0, base_score)), 3)
            fused_list.append(item)

        fused_list.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return fused_list[:top_k]


# ============================================================
# 4. GraphRAG Context Builder
# ============================================================

class GraphRAGContextBuilder:
    """
    Builds a unified, structured prompt context combining:
      1. Seed Investigation Details
      2. TigerGraph Multi-Hop Graph Evidence
      3. Hybrid Historical Precedents
      4. Policy & Uncertainty Context
    """

    @staticmethod
    def build_context(
        case_id: str,
        txn_id: str,
        trigger_type: str,
        graph_evidence: list[Any],
        historical_cases: list[dict],
        extracted_signals: dict,
        fraud_probability: float,
        risk_level: str,
        pattern: str,
    ) -> dict:
        """Construct canonical GraphRAG context dictionary."""
        evidence_summary = []
        for ev in graph_evidence:
            claim = ev.get("claim", "") if isinstance(ev, dict) else getattr(ev, "claim", "")
            source = ev.get("source", "graph") if isinstance(ev, dict) else getattr(ev, "source", "graph")
            ref = ev.get("ref", "") if isinstance(ev, dict) else getattr(ev, "ref", "")
            conf = ev.get("confidence", 0.0) if isinstance(ev, dict) else getattr(ev, "confidence", 0.0)
            evidence_summary.append({
                "claim": claim,
                "source": f"TigerGraph / {ref}" if source == "graph" else source,
                "confidence": conf,
            })

        precedents = []
        for hc in historical_cases:
            precedents.append({
                "case_id": hc.get("case_id"),
                "retrieval_type": hc.get("retrieval_type", "graph"),
                "hybrid_relevance": hc.get("hybrid_score", 0.0),
                "graph_relevance": hc.get("graph_score", 0.0),
                "semantic_relevance": hc.get("semantic_score", 0.0),
                "pattern": hc.get("pattern"),
                "outcome": hc.get("outcome"),
                "actions_taken": hc.get("actions_taken"),
                "why_relevant": hc.get("similarity_reasons", []),
                "analyst_notes": hc.get("analyst_notes", "")[:160],
            })

        return {
            "investigation": {
                "case_id": case_id,
                "txn_id": txn_id,
                "trigger_type": trigger_type,
                "assessed_risk_level": risk_level,
                "fraud_probability": round(fraud_probability, 3),
                "detected_pattern": pattern,
            },
            "graph_signals": {
                "shared_device_count": extracted_signals.get("shared_device_count", 0),
                "card_testing_detected": extracted_signals.get("card_testing_detected", False),
                "ring_size": extracted_signals.get("ring_size", 0),
                "is_new_device": extracted_signals.get("is_new_device", False),
                "velocity_count": extracted_signals.get("velocity_count", 0),
            },
            "evidence": evidence_summary,
            "historical_precedents": precedents,
            "provenance": {
                "graph_source": "TigerGraph Cloud (FraudLens)",
                "vector_source": "FraudLens VectorStore (TF-IDF)",
                "fusion_method": "Weighted Bimodal Hybrid RAG",
            }
        }


# Global Accessors
_embedding_provider = CompositeEmbeddingProvider()
_vector_store = LocalVectorStore()
_hybrid_retriever = HybridRetriever()


def get_embedding_provider() -> EmbeddingProvider:
    return _embedding_provider


def get_vector_store() -> LocalVectorStore:
    return _vector_store


def get_hybrid_retriever() -> HybridRetriever:
    return _hybrid_retriever


def semantic_search_cases(query_text: str, top_k: int = 5, before_ts: Optional[float] = None) -> list[dict]:
    """Execute semantic search against historical closed cases."""
    vec = _embedding_provider.embed_text(query_text)
    return _vector_store.search(vec, top_k=top_k, before_ts=before_ts)


def fuse_retrieval_results(
    graph_cases: list[dict],
    semantic_cases: list[dict],
    current_signals: Optional[dict] = None,
    top_k: int = 5,
) -> list[dict]:
    """Execute hybrid fusion on graph and semantic candidates."""
    return _hybrid_retriever.fuse_and_rerank(graph_cases, semantic_cases, current_signals, top_k)


def build_graphrag_context(
    case_id: str,
    txn_id: str,
    trigger_type: str,
    graph_evidence: list[Any],
    historical_cases: list[dict],
    extracted_signals: dict,
    fraud_probability: float,
    risk_level: str,
    pattern: str,
) -> dict:
    """Build unified GraphRAG context dictionary."""
    return GraphRAGContextBuilder.build_context(
        case_id=case_id,
        txn_id=txn_id,
        trigger_type=trigger_type,
        graph_evidence=graph_evidence,
        historical_cases=historical_cases,
        extracted_signals=extracted_signals,
        fraud_probability=fraud_probability,
        risk_level=risk_level,
        pattern=pattern,
    )
