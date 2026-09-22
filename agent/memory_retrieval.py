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
    """A retrieved similar historical case with similarity metadata."""
    case_id: str
    similarity_score: float
    similarity_reasons: list[str]
    pattern: str
    outcome: str                     # fraud | cleared | escalated
    actions_taken: list[str]
    exposure_usd: float
    shared_entities: list[str]       # Entity IDs shared with current case
    analyst_notes_excerpt: str = ""


class MemoryRetrieval:
    """
    Retrieves similar historical fraud cases using graph queries and GraphRAG.
    """

    def __init__(self, mcp_client: Any = None, vector_store: Any = None):
        """
        Args:
            mcp_client:   TigerGraph MCP client for graph-based search
            vector_store: TigerGraph vector store for semantic search
        """
        self.mcp_client   = mcp_client
        self.vector_store = vector_store

    async def retrieve(
        self,
        pattern: str,
        device_profile_id: Optional[str],
        card_ids: list[str],
        top_k: int = 5,
    ) -> list[SimilarCase]:
        """
        Retrieve similar historical cases using graph + vector similarity.

        Args:
            pattern:           Current case fraud pattern
            device_profile_id: Device profile from current transaction
            card_ids:          Card IDs involved in current case
            top_k:             Maximum number of similar cases to return

        Returns:
            List of SimilarCase ordered by similarity_score descending
        """
        # Graph-based retrieval
        graph_cases = await self._graph_retrieve(pattern, device_profile_id, card_ids)

        # Vector-based retrieval (GraphRAG)
        vector_cases = await self._vector_retrieve(pattern)

        # Merge and deduplicate
        all_cases = self._merge_results(graph_cases, vector_cases)

        # Rank by combined similarity score
        ranked = sorted(all_cases, key=lambda c: c.similarity_score, reverse=True)

        logger.info(
            f"Memory retrieval | pattern={pattern} | "
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

    async def _vector_retrieve(self, pattern: str) -> list[SimilarCase]:
        """
        Retrieve cases using TigerGraph vector similarity search (GraphRAG).
        Searches analyst_notes embeddings for semantic similarity.
        """
        if self.vector_store is None:
            return []   # Vector store not available in dev mode

        try:
            # TODO (Phase 1): Implement actual vector search
            # results = await self.vector_store.similarity_search(
            #     query=f"fraud case involving {pattern}",
            #     k=5
            # )
            return []
        except Exception as e:
            logger.warning(f"Vector retrieval failed: {e}")
            return []

    def _parse_graph_results(self, result: dict) -> list[SimilarCase]:
        """Parse GSQL query result into SimilarCase objects."""
        cases = []
        for r in result.get("results", []):
            cases.append(SimilarCase(
                case_id=r.get("case_id", ""),
                similarity_score=r.get("match_score", 0) / 6.0,  # Normalize to 0-1
                similarity_reasons=["Graph pattern match"],
                pattern=r.get("pattern", "unknown"),
                outcome=r.get("outcome", "unknown"),
                actions_taken=r.get("actions_taken", "").split(","),
                exposure_usd=r.get("exposure_usd", 0.0),
                shared_entities=[],
                analyst_notes_excerpt=r.get("analyst_notes", "")[:200],
            ))
        return cases

    def _merge_results(
        self,
        graph_cases: list[SimilarCase],
        vector_cases: list[SimilarCase],
    ) -> list[SimilarCase]:
        """Merge graph + vector results, deduplicating by case_id."""
        seen: set[str] = set()
        merged: list[SimilarCase] = []

        for case in graph_cases + vector_cases:
            if case.case_id not in seen:
                seen.add(case.case_id)
                merged.append(case)
            else:
                # Boost score for cases found by both methods
                for existing in merged:
                    if existing.case_id == case.case_id:
                        existing.similarity_score = min(1.0, existing.similarity_score + 0.2)
                        existing.similarity_reasons.append("Also matched by vector similarity")

        return merged

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
            ),
        ]
