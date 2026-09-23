"""
FraudLens — Unit Tests for Production GraphRAG Engine
======================================================
Tests:
  1. Embedding Providers (TF-IDF, Composite)
  2. Local Vector Store (upsert, search, persistence, provenance)
  3. Hybrid Retriever (score fusion, deduplication, graph-aware boost)
  4. GraphRAG Context Builder (structured synthesis, provenance)
  5. LLM Reasoning Layer (JSON schema, fallback safety)
  6. Failure & Fallback Handling (graceful degradation)
"""

import pytest
import numpy as np
from pathlib import Path
from tools.graphrag_tools import (
    TFIDFEmbeddingProvider,
    CompositeEmbeddingProvider,
    LocalVectorStore,
    VectorDocument,
    HybridRetriever,
    GraphRAGContextBuilder,
    fuse_retrieval_results,
    semantic_search_cases,
    build_graphrag_context,
)
from agent.memory_retrieval import MemoryRetrieval, SimilarCase
from agent.llm_client import GeminiClient


class TestEmbeddingProvider:
    """Test embedding abstractions and normalization."""

    def test_tfidf_embedding_deterministic_and_normalized(self, tmp_path):
        vocab_path = tmp_path / "test_tfidf.pkl"
        provider = TFIDFEmbeddingProvider(vocab_path=vocab_path)
        corpus = [
            "card testing with micro authorization sequence on web channel",
            "account takeover after credential stuffing and device switch",
            "cross-border velocity anomaly with multiple cards on single terminal",
        ]
        provider.fit_documents(corpus)
        
        vec1 = provider.embed_text("card testing micro authorization")
        assert len(vec1) > 0
        assert isinstance(vec1, list)
        
        # Check L2 normalization (norm should be ~1.0)
        norm = np.linalg.norm(np.array(vec1))
        assert abs(norm - 1.0) < 1e-4

        # Document batch embedding
        batch_vecs = provider.embed_documents(["card testing", "account takeover"])
        assert len(batch_vecs) == 2
        assert len(batch_vecs[0]) == len(vec1)

    def test_composite_provider_fallback(self):
        provider = CompositeEmbeddingProvider()
        vec = provider.embed_text("fraud ring transaction")
        assert len(vec) > 0


class TestVectorStore:
    """Test vector storage, persistence, and similarity search."""

    def test_vector_store_upsert_and_search(self, tmp_path):
        store = LocalVectorStore(store_dir=tmp_path)
        
        # Dummy normalized vectors
        v1 = [1.0, 0.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0, 0.0]
        v3 = [0.707, 0.707, 0.0, 0.0]

        docs = [
            VectorDocument(
                doc_id="CC-001",
                text="Case 001: Card testing micro auths",
                metadata={"pattern": "card_testing", "outcome": "fraud", "exposure_usd": 1200.0},
                embedding=v1,
            ),
            VectorDocument(
                doc_id="CC-002",
                text="Case 002: Account takeover credential stuff",
                metadata={"pattern": "account_takeover", "outcome": "fraud", "exposure_usd": 3500.0},
                embedding=v2,
            ),
            VectorDocument(
                doc_id="CC-003",
                text="Case 003: Hybrid card testing and takeover",
                metadata={"pattern": "card_testing", "outcome": "fraud", "exposure_usd": 2000.0},
                embedding=v3,
            ),
        ]

        store.upsert(docs)
        assert store.count() == 3

        # Search for vector close to v1
        results = store.search(query_vector=[1.0, 0.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0]["case_id"] == "CC-001"
        assert results[0]["retrieval_type"] == "semantic"
        assert results[0]["source"] == "vector_store"
        assert results[0]["score"] > results[1]["score"]

        # Search with pattern filter
        filtered = store.search(query_vector=[0.0, 1.0, 0.0, 0.0], top_k=5, filter_pattern="account_takeover")
        assert len(filtered) == 1
        assert filtered[0]["case_id"] == "CC-002"

    def test_idempotent_upsert(self, tmp_path):
        store = LocalVectorStore(store_dir=tmp_path)
        doc = VectorDocument(
            doc_id="CC-999",
            text="Duplicate test",
            metadata={"pattern": "test"},
            embedding=[0.5, 0.5],
        )
        store.upsert([doc])
        store.upsert([doc])
        assert store.count() == 1


class TestHybridRetrieval:
    """Test fusion of graph-topological and vector-semantic candidates."""

    def test_fusion_and_deduplication(self):
        retriever = HybridRetriever(graph_weight=0.60, semantic_weight=0.40)

        graph_cases = [
            {"case_id": "CC-100", "similarity_score": 0.80, "pattern": "card_testing", "outcome": "fraud"},
            {"case_id": "CC-200", "similarity_score": 0.70, "pattern": "shared_device", "outcome": "fraud"},
        ]
        semantic_cases = [
            {"case_id": "CC-100", "score": 0.90, "metadata": {"pattern": "card_testing", "outcome": "fraud"}},
            {"case_id": "CC-300", "score": 0.85, "metadata": {"pattern": "cross_border", "outcome": "cleared"}},
        ]

        fused = retriever.fuse_and_rerank(
            graph_cases=graph_cases,
            semantic_cases=semantic_cases,
            current_signals={"pattern": "card_testing"},
            top_k=5,
        )

        assert len(fused) == 3
        # CC-100 is present in both -> should be hybrid and highest ranked
        top = fused[0]
        assert top["case_id"] == "CC-100"
        assert top["retrieval_type"] == "hybrid"
        assert top["graph_score"] == 0.80
        assert top["semantic_score"] == 0.90
        assert "Hybrid" in top["source"]
        # Pattern alignment boost applied
        assert any("Direct typology alignment" in r for r in top["similarity_reasons"])

    def test_memory_retrieval_integration(self):
        memory = MemoryRetrieval(mcp_client=None, vector_store=None)
        # Mock mode with fallback vector store
        cases = memory._merge_results(
            graph_cases=memory._mock_similar_cases("card_testing"),
            vector_cases=[],
            active_pattern="card_testing",
        )
        assert len(cases) >= 2
        assert cases[0].case_id == "CC-0141"


class TestGraphRAGContextAndLLM:
    """Test GraphRAG context building and structured LLM reasoning."""

    def test_context_builder_structure(self):
        context = build_graphrag_context(
            case_id="CASE-TEST-001",
            txn_id="TXN-999",
            trigger_type="risk_score",
            graph_evidence=[
                {"claim": "Card testing detected with 3 micro-transactions", "source": "graph", "ref": "check_card_testing", "confidence": 0.95}
            ],
            historical_cases=[
                {
                    "case_id": "CC-0141",
                    "retrieval_type": "hybrid",
                    "hybrid_score": 0.88,
                    "graph_score": 0.85,
                    "semantic_score": 0.92,
                    "pattern": "card_testing",
                    "outcome": "fraud",
                    "actions_taken": ["BLOCK_CARD"],
                    "similarity_reasons": ["Topological match", "Semantic match"],
                }
            ],
            extracted_signals={"card_testing_detected": True, "ring_size": 2},
            fraud_probability=0.85,
            risk_level="HIGH",
            pattern="card_testing",
        )

        assert context["investigation"]["case_id"] == "CASE-TEST-001"
        assert context["investigation"]["detected_pattern"] == "card_testing"
        assert len(context["evidence"]) == 1
        assert "TigerGraph" in context["evidence"][0]["source"]
        assert len(context["historical_precedents"]) == 1
        assert context["historical_precedents"][0]["retrieval_type"] == "hybrid"
        assert "TigerGraph Cloud" in context["provenance"]["graph_source"]

    def test_llm_reasoning_deterministic_fallback(self):
        client = GeminiClient(api_key="invalid_or_none_key")
        dummy_context = {
            "investigation": {"case_id": "C-1", "detected_pattern": "card_testing", "assessed_risk_level": "HIGH"},
            "evidence": [{"claim": "Rapid velocity on card"}],
            "historical_precedents": [{"case_id": "CC-0141", "pattern": "card_testing", "outcome": "fraud", "hybrid_relevance": 0.89}],
            "graph_signals": {"ring_size": 1, "card_testing_detected": True},
        }

        reasoning = client.generate_investigation_reasoning(dummy_context)
        assert isinstance(reasoning, dict)
        assert "findings" in reasoning
        assert "supporting_evidence" in reasoning
        assert "historical_context" in reasoning
        assert "reasoning_summary" in reasoning
        assert len(reasoning["findings"]) > 0
