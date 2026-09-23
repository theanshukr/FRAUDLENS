"""
FraudLens     Memory Retrieval
==============================
Retrieves similar historical fraud cases from TigerGraph to inform
the current investigation.

Memory retrieval strategy:
  1. Graph-based matching: same pattern, shared device, same card
  2. Vector similarity: semantic similarity on analyst_notes (GraphRAG)
  3. Ranking: combined score from both methods

The top 3-5 similar cases are injected into the risk assessment context
to improve fraud_probability estimation and pattern identification.
"""

from __future__ import annotations

from typing import Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class SimilarCase:
    """A retrieved similar historical case with similarity metadata and provenance."""
    case_id: str
    similarity_score: float
    similarity_reasons: list[str]
    pattern: str
    outcome: str                     # fraud | cleared | escalated
    actions_taken: list[str]
    exposure_usd: float
    shared_entities: list[str]       # Entity IDs shared with current case
    analyst_notes_excerpt: str = ""
    retrieval_type: str = "graph"    # graph | semantic | hybrid
    graph_score: float = 0.0
    semantic_score: float = 0.0
    hybrid_score: float = 0.0
    source: str = "TigerGraph / search_similar_cases"


class MemoryRetrieval:
    """
    Retrieves similar historical fraud cases using TigerGraph queries and GraphRAG.
    """

    def __init__(self, mcp_client: Any = None, vector_store: Any = None):
        """
        Args:
            mcp_client:   TigerGraph MCP client for graph-based search
            vector_store: Vector store for semantic search
        """
        self.mcp_client   = mcp_client
        self.vector_store = vector_store

    async def retrieve(
        self,
        pattern: str,
        device_profile_id: Optional[str],
        card_ids: list[str],
        top_k: int = 5,
        query_context: str = "",
    ) -> list[SimilarCase]:
        """
        Retrieve similar historical cases using hybrid graph + vector similarity.

        Args:
            pattern:           Current case fraud pattern
            device_profile_id: Device profile from current transaction
            card_ids:          Card IDs involved in current case
            top_k:             Maximum number of similar cases to return
            query_context:     Optional natural language context for vector search

        Returns:
            List of SimilarCase ordered by similarity_score descending
        """
        # Graph-based retrieval
        graph_cases = await self._graph_retrieve(pattern, device_profile_id, card_ids)

        # Vector-based retrieval (GraphRAG)
        vector_cases = await self._vector_retrieve(pattern, query_context)

        # Merge and deduplicate with hybrid weighting & graph-aware boost
        all_cases = self._merge_results(graph_cases, vector_cases, active_pattern=pattern)

        # Rank by combined similarity score
        ranked = sorted(all_cases, key=lambda c: c.similarity_score, reverse=True)

        logger.info(
            f"GraphRAG Memory retrieval | pattern={pattern} | "
            f"graph_hits={len(graph_cases)} | vector_hits={len(vector_cases)} | "
            f"top={min(top_k, len(ranked))}"
        )
        return ranked[:top_k]

    async def _graph_retrieve(
        self,
        pattern: str,
        device_profile_id: Optional[str],
        card_ids: list[str],
    ) -> list[SimilarCase]:
        """Retrieve cases using search_similar_cases GSQL query."""
        if self.mcp_client is None:
            return self._mock_similar_cases(pattern)

        try:
            from tools import graph_tools as gt
            result = gt.search_similar_cases(
                self.mcp_client,
                pattern=pattern,
                device_profile_id=device_profile_id or "",
                card_ids=card_ids,
            )
            return self._parse_graph_results(result)
        except Exception as e:
            logger.warning(f"Graph retrieval failed: {e}")
            return self._mock_similar_cases(pattern)

    async def _vector_retrieve(self, pattern: str, query_context: str = "") -> list[SimilarCase]:
        """
        Retrieve cases using Vector similarity search on historical analyst notes (GraphRAG).
        """
        try:
            from tools.graphrag_tools import semantic_search_cases
            query = query_context if query_context else f"fraud pattern {pattern} investigation evidence and outcome"
            results = semantic_search_cases(query_text=query, top_k=5)
            cases = []
            for r in results:
                meta = r.get("metadata", {})
                score = float(r.get("score", 0.5))
                cases.append(SimilarCase(
                    case_id=r.get("case_id", ""),
                    similarity_score=score,
                    similarity_reasons=["Semantic narrative similarity on analyst notes"],
                    pattern=meta.get("pattern", "unknown"),
                    outcome=meta.get("outcome", "unknown"),
                    actions_taken=meta.get("actions_taken", "").split("|") if isinstance(meta.get("actions_taken"), str) else meta.get("actions_taken", []),
                    exposure_usd=float(meta.get("exposure_usd", 0.0)),
                    shared_entities=[],
                    analyst_notes_excerpt=meta.get("analyst_notes", "")[:200] or r.get("text", "")[:200],
                    retrieval_type="semantic",
                    semantic_score=score,
                    source="VectorStore / analyst_notes embedding",
                ))
            return cases
        except Exception as e:
            logger.warning(f"Vector retrieval failed: {e}")
            return []

    def _parse_graph_results(self, result: dict) -> list[SimilarCase]:
        """Parse GSQL query result into SimilarCase objects."""
        cases = []
        for r in result.get("results", []):
            score = round(r.get("match_score", 0) / 6.0, 3)
            cases.append(SimilarCase(
                case_id=r.get("case_id", ""),
                similarity_score=score,
                similarity_reasons=["Graph pattern match"],
                pattern=r.get("pattern", "unknown"),
                outcome=r.get("outcome", "unknown"),
                actions_taken=r.get("actions_taken", "").split(",") if isinstance(r.get("actions_taken"), str) else r.get("actions_taken", []),
                exposure_usd=float(r.get("exposure_usd", 0.0)),
                shared_entities=[],
                analyst_notes_excerpt=r.get("analyst_notes", "")[:200],
                retrieval_type="graph",
                graph_score=score,
                source="TigerGraph / search_similar_cases",
            ))
        return cases

    def _merge_results(
        self,
        graph_cases: list[SimilarCase],
        vector_cases: list[SimilarCase],
        active_pattern: str = "",
    ) -> list[SimilarCase]:
        """Merge graph + vector results with weighted hybrid scoring and graph-aware boost."""
        try:
            from tools.graphrag_tools import fuse_retrieval_results
            g_dicts = [
                {
                    "case_id": c.case_id,
                    "similarity_score": c.similarity_score,
                    "pattern": c.pattern,
                    "outcome": c.outcome,
                    "actions_taken": c.actions_taken,
                    "exposure_usd": c.exposure_usd,
                    "analyst_notes_excerpt": c.analyst_notes_excerpt,
                }
                for c in graph_cases
            ]
            v_dicts = [
                {
                    "case_id": c.case_id,
                    "score": c.similarity_score,
                    "metadata": {
                        "pattern": c.pattern,
                        "outcome": c.outcome,
                        "actions_taken": c.actions_taken,
                        "exposure_usd": c.exposure_usd,
                        "analyst_notes": c.analyst_notes_excerpt,
                    }
                }
                for c in vector_cases
            ]
            fused = fuse_retrieval_results(
                graph_cases=g_dicts,
                semantic_cases=v_dicts,
                current_signals={"pattern": active_pattern},
                top_k=5,
            )
            merged = []
            for f in fused:
                merged.append(SimilarCase(
                    case_id=f["case_id"],
                    similarity_score=f["hybrid_score"],
                    similarity_reasons=f["similarity_reasons"],
                    pattern=f["pattern"],
                    outcome=f["outcome"],
                    actions_taken=f["actions_taken"],
                    exposure_usd=f["exposure_usd"],
                    shared_entities=[],
                    analyst_notes_excerpt=f["analyst_notes"],
                    retrieval_type=f["retrieval_type"],
                    graph_score=f["graph_score"],
                    semantic_score=f["semantic_score"],
                    hybrid_score=f["hybrid_score"],
                    source=f["source"],
                ))
            return merged
        except Exception as e:
            logger.warning(f"Hybrid fusion error: {e} - falling back to baseline merge")
            seen: set[str] = set()
            merged_fallback: list[SimilarCase] = []
            for case in graph_cases + vector_cases:
                if case.case_id not in seen:
                    seen.add(case.case_id)
                    merged_fallback.append(case)
                else:
                    for existing in merged_fallback:
                        if existing.case_id == case.case_id:
                            existing.similarity_score = min(1.0, existing.similarity_score + 0.2)
                            existing.similarity_reasons.append("Also matched by vector similarity")
                            existing.retrieval_type = "hybrid"
            return merged_fallback

    def _mock_similar_cases(self, pattern: str) -> list[SimilarCase]:
        """Mock similar cases for development without TigerGraph."""
        return [
            SimilarCase(
                case_id="CC-0141",
                similarity_score=0.85,
                similarity_reasons=["Same fraud pattern: card_testing", "Shared device profile"],
                pattern=pattern,
                outcome="fraud",
                actions_taken=["BLOCK_CARD", "FILE_REPORT"],
                exposure_usd=1250.0,
                shared_entities=["D_MOCK_001"],
                analyst_notes_excerpt="Card testing with micro-auths followed by large e-commerce transaction. Device shared across 3 accounts.",
                retrieval_type="graph",
                graph_score=0.85,
                source="Mock TigerGraph / search_similar_cases",
            ),
            SimilarCase(
                case_id="CC-2671",
                similarity_score=0.72,
                similarity_reasons=["Connected card via shared device"],
                pattern="shared_device_ring",
                outcome="fraud",
                actions_taken=["BLOCK_CARD", "FLAG_FRAUD_RING", "ESCALATE_CASE"],
                exposure_usd=3400.0,
                shared_entities=["D_MOCK_001", "CARD_B"],
                analyst_notes_excerpt="Device shared across organized fraud ring. 4 accounts identified.",
                retrieval_type="graph",
                graph_score=0.72,
                source="Mock TigerGraph / search_similar_cases",
            ),
        ]
