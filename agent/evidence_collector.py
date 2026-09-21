"""
FraudLens     Evidence Collector
================================
Executes investigation plan steps via TigerGraph MCP tools and
structures each finding as a typed EvidenceItem.

Every piece of evidence must have:
  - A clear claim (what was found)
  - A source (graph | document | customer | external)
  - A reference to the query or document that produced it
  - The entity IDs involved
  - A confidence score
  - A timestamp

The evidence list is the core input to the Risk Assessor.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from loguru import logger


# ============================================================
# Evidence Data Models
# ============================================================

class EvidenceItem(BaseModel):
    """A single piece of evidence discovered during investigation."""

    evidence_id: str = Field(description="Unique ID for this evidence item")
    claim: str = Field(description="What was found     plain English statement")
    source: Literal["graph", "document", "customer", "external"] = Field(
        description="Where this evidence came from"
    )
    ref: str = Field(
        description="Query name or document section that produced this evidence"
    )
    entity_ids: list[str] = Field(
        default_factory=list,
        description="IDs of entities referenced (txn IDs, card IDs, device IDs, etc.)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in this specific evidence item (0.0-1.0)"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Optional[dict] = Field(
        default=None,
        description="Raw query response for audit purposes"
    )
    supports_fraud: Optional[bool] = Field(
        default=None,
        description="True if evidence supports fraud, False if contradicts, None if neutral"
    )


# ============================================================
# Evidence Collector
# ============================================================

class EvidenceCollector:
    """
    Executes investigation plan steps via TigerGraph MCP tools
    and returns structured evidence items.

    Usage:
        collector = EvidenceCollector(mcp_client=mcp_client)
        evidence  = await collector.collect(plan=plan, prior_evidence=[])
    """

    def __init__(self, mcp_client: Any = None):
        """
        Args:
            mcp_client: TigerGraph MCP client instance.
                        If None, falls back to mock responses for dev/testing.
        """
        self.mcp_client = mcp_client
        self._evidence_counter = 0

    def _next_id(self) -> str:
        self._evidence_counter += 1
        return f"EVD-{self._evidence_counter:04d}"

    async def collect(
        self,
        plan,           # InvestigationPlan
        prior_evidence: list[EvidenceItem] = None,
    ) -> list[EvidenceItem]:
        """
        Execute all steps in the investigation plan and return evidence.

        Args:
            plan:           InvestigationPlan from planner.py
            prior_evidence: Evidence from previous investigation rounds

        Returns:
            List of EvidenceItem objects
        """
        if prior_evidence is None:
            prior_evidence = []

        evidence: list[EvidenceItem] = []

        for step in plan.steps:
            logger.info(f"Executing step: {step.query_name} | params={step.params}")
            try:
                result = await self._execute_step(step)
                items  = self._parse_result(step, result)
                evidence.extend(items)
                logger.info(f"      {len(items)} evidence items from {step.query_name}")
            except Exception as e:
                logger.warning(f"Step {step.step_id} failed: {e}")
                # Add a "no data" evidence item so gap is visible
                evidence.append(EvidenceItem(
                    evidence_id=self._next_id(),
                    claim=f"Query {step.query_name} returned no data or failed: {str(e)}",
                    source="graph",
                    ref=step.query_name,
                    entity_ids=[],
                    confidence=0.0,
                    supports_fraud=None,
                ))

        return evidence

    async def _execute_step(self, step) -> dict:
        """Execute a single investigation step via MCP or mock."""
        if self.mcp_client is None:
            return self._mock_response(step.query_name)

        # TODO (Phase 1): Replace with actual MCP tool call
        # return await self.mcp_client.call_tool(step.query_name, step.params)
        return self._mock_response(step.query_name)

    def _parse_result(self, step, result: dict) -> list[EvidenceItem]:
        """
        Parse raw query result into structured EvidenceItem list.

        TODO (Phase 2): Implement per-query parsers with LLM assistance
                        for complex multi-entity results.
        """
        # Stub: return generic evidence item
        return [EvidenceItem(
            evidence_id=self._next_id(),
            claim=f"Query {step.query_name} completed     {len(result.get('results', []))} results found",
            source="graph",
            ref=step.query_name,
            entity_ids=result.get("entity_ids", []),
            confidence=0.7,
            raw_data=result,
            supports_fraud=None,
        )]

    def _mock_response(self, query_name: str) -> dict:
        """Return mock responses for development without TigerGraph connection."""
        mocks = {
            "get_transaction": {
                "results": [{"transaction_id": "T_MOCK_001", "amount": 542.0, "risk_score": 0.87}],
                "entity_ids": ["T_MOCK_001"],
            },
            "get_card_history": {
                "results": [
                    {"transaction_id": "T_MOCK_000", "amount": 1.0},    # micro-auth
                    {"transaction_id": "T_MOCK_001", "amount": 542.0},  # large fraud
                ],
                "entity_ids": ["T_MOCK_000", "T_MOCK_001"],
            },
            "get_device_neighbors": {
                "results": [
                    {"card_id": "CARD_A"},
                    {"card_id": "CARD_B"},
                ],
                "entity_ids": ["CARD_A", "CARD_B"],
                "shared_device_count": 2,
            },
            "find_connected_cards": {
                "results": [{"card_id": "CARD_B"}, {"card_id": "CARD_C"}],
                "entity_ids": ["CARD_B", "CARD_C"],
                "ring_size": 3,
            },
            "detect_card_testing": {
                "results": [],
                "card_testing_detected": True,
                "entity_ids": ["T_MOCK_000"],
            },
            "search_similar_cases": {
                "results": [
                    {"case_id": "CC-0141", "pattern": "card_testing", "outcome": "fraud"},
                    {"case_id": "CC-2671", "pattern": "shared_device", "outcome": "fraud"},
                ],
                "entity_ids": ["CC-0141", "CC-2671"],
            },
        }
        return mocks.get(query_name, {"results": [], "entity_ids": []})
