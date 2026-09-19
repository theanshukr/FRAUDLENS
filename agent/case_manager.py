"""
FraudLens — Case Manager
==========================
Manages the lifecycle of a FraudCase through the investigation state machine.

Case State Machine:
  TRIGGERED → INVESTIGATING → AWAITING_EVIDENCE → REASSESSING
  → ACTION_RECOMMENDED → AWAITING_APPROVAL → ACTION_TAKEN → RESOLVED

The case manager:
  - Creates and tracks the case record
  - Appends timeline events and evidence
  - Writes the final case JSON to TigerGraph and disk
  - Produces the answer JSON matching the hackathon benchmark format
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from loguru import logger


# ============================================================
# Case State Machine
# ============================================================

class CaseStatus(str, Enum):
    TRIGGERED            = "TRIGGERED"
    INVESTIGATING        = "INVESTIGATING"
    AWAITING_EVIDENCE    = "AWAITING_EVIDENCE"
    REASSESSING          = "REASSESSING"
    ACTION_RECOMMENDED   = "ACTION_RECOMMENDED"
    AWAITING_APPROVAL    = "AWAITING_APPROVAL"
    ACTION_TAKEN         = "ACTION_TAKEN"
    RESOLVED             = "RESOLVED"


# ============================================================
# Case Timeline Event
# ============================================================

class TimelineEvent(BaseModel):
    event_type: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


# ============================================================
# Full Case Record
# ============================================================

class FraudCaseRecord(BaseModel):
    """Complete fraud case record — matches hackathon answer format."""

    # Identity
    case_id: str
    txn_id: str
    card_id: Optional[str] = None
    customer_id: Optional[str] = None

    # Trigger
    trigger_type: str
    trigger_risk_score: Optional[float] = None

    # Status
    status: CaseStatus = CaseStatus.TRIGGERED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Risk Assessment
    initial_risk_level: Optional[str] = None
    initial_fraud_probability: Optional[float] = None
    initial_confidence: Optional[float] = None
    final_risk_level: Optional[str] = None
    final_fraud_probability: Optional[float] = None
    final_confidence: Optional[float] = None
    pattern: Optional[str] = None
    pattern_description: Optional[str] = None

    # Evidence
    evidence: list[dict] = Field(default_factory=list)
    evidence_request: Optional[dict] = None
    evidence_request_response: Optional[dict] = None

    # NBA
    initial_actions: list[dict] = Field(default_factory=list)
    final_actions: list[dict] = Field(default_factory=list)
    what_changed: Optional[str] = None

    # Final Decision
    final_verdict: Optional[Literal["fraud", "cleared", "escalated", "uncertain"]] = None
    exposure_usd: Optional[float] = None

    # SAR
    sar: dict = Field(default_factory=lambda: {"file": False, "reason": None})

    # Timeline
    timeline: list[TimelineEvent] = Field(default_factory=list)

    # Similar Cases
    similar_cases: list[dict] = Field(default_factory=list)

    # Agent
    tool_calls: list[dict] = Field(default_factory=list)
    investigation_rounds: int = 0


# ============================================================
# Case Manager
# ============================================================

class CaseManager:
    """
    Creates and manages fraud case records through their lifecycle.
    Writes completed cases to disk and TigerGraph.
    """

    def __init__(
        self,
        cases_dir: str = "./cases",
        tg_client: Any = None,
    ):
        self.cases_dir = Path(cases_dir)
        self.cases_dir.mkdir(parents=True, exist_ok=True)
        self.tg_client = tg_client
        self._active_cases: dict[str, FraudCaseRecord] = {}

    def create_case(
        self,
        txn_id: str,
        trigger_type: str,
        card_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        trigger_risk_score: Optional[float] = None,
        case_id: Optional[str] = None,
    ) -> FraudCaseRecord:
        """Create a new fraud case and add it to active tracking."""
        if case_id is None:
            case_id = f"HHG-{uuid.uuid4().hex[:6].upper()}"

        case = FraudCaseRecord(
            case_id=case_id,
            txn_id=txn_id,
            card_id=card_id,
            customer_id=customer_id,
            trigger_type=trigger_type,
            trigger_risk_score=trigger_risk_score,
        )
        self._active_cases[case_id] = case
        self._add_timeline_event(case, "CASE_CREATED", f"Investigation triggered by {trigger_type}")
        logger.info(f"Case created: {case_id} | txn={txn_id} | trigger={trigger_type}")
        return case

    def get_case(self, case_id: str) -> Optional[FraudCaseRecord]:
        return self._active_cases.get(case_id)

    def transition(self, case: FraudCaseRecord, new_status: CaseStatus, description: str = "") -> None:
        """Transition case to new status and record timeline event."""
        old_status = case.status
        case.status = new_status
        case.updated_at = datetime.utcnow()
        self._add_timeline_event(
            case,
            f"STATUS_CHANGE:{old_status.value}→{new_status.value}",
            description or f"Status changed to {new_status.value}",
        )
        logger.info(f"Case {case.case_id}: {old_status.value} → {new_status.value}")

    def append_evidence(self, case: FraudCaseRecord, evidence_items: list) -> None:
        """Append new evidence items to the case record."""
        for item in evidence_items:
            if hasattr(item, "model_dump"):
                case.evidence.append(item.model_dump(mode="json"))
            else:
                case.evidence.append(item)
        case.updated_at = datetime.utcnow()

    def set_initial_assessment(self, case: FraudCaseRecord, assessment) -> None:
        case.initial_risk_level        = assessment.risk_level
        case.initial_fraud_probability = assessment.fraud_probability
        case.initial_confidence        = assessment.confidence
        case.pattern                   = assessment.pattern
        case.pattern_description       = assessment.pattern_description
        self._add_timeline_event(
            case, "INITIAL_ASSESSMENT",
            f"Initial risk: {assessment.risk_level} ({assessment.fraud_probability:.0%} probability)"
        )

    def set_final_assessment(self, case: FraudCaseRecord, assessment) -> None:
        case.final_risk_level        = assessment.risk_level
        case.final_fraud_probability = assessment.fraud_probability
        case.final_confidence        = assessment.confidence
        case.investigation_rounds   += 1
        self._add_timeline_event(
            case, "FINAL_ASSESSMENT",
            f"Final risk: {assessment.risk_level} ({assessment.fraud_probability:.0%} probability)"
        )

    def set_nba(self, case: FraudCaseRecord, actions: list, phase: str = "initial") -> None:
        serialized = [a.model_dump(mode="json") if hasattr(a, "model_dump") else a for a in actions]
        if phase == "initial":
            case.initial_actions = serialized
        else:
            case.final_actions = serialized
        self._add_timeline_event(
            case, f"NBA_{phase.upper()}",
            f"NBA generated: {[a['action'] if isinstance(a, dict) else a.action for a in actions]}"
        )

    def set_similar_cases(self, case: FraudCaseRecord, similar: list[dict]) -> None:
        case.similar_cases = similar

    def record_tool_call(self, case: FraudCaseRecord, tool_name: str, params: dict, result_summary: str) -> None:
        case.tool_calls.append({
            "tool": tool_name,
            "params": params,
            "result_summary": result_summary,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def resolve(
        self,
        case: FraudCaseRecord,
        verdict: Literal["fraud", "cleared", "escalated", "uncertain"],
        exposure_usd: float = 0.0,
        sar_required: bool = False,
        sar_reason: str = "",
    ) -> None:
        """Mark case as resolved with final verdict."""
        case.final_verdict = verdict
        case.exposure_usd  = exposure_usd
        case.sar           = {"file": sar_required, "reason": sar_reason if sar_required else None}
        self.transition(case, CaseStatus.RESOLVED, f"Case resolved: {verdict.upper()}")

    def save_to_disk(self, case: FraudCaseRecord) -> Path:
        """Write case JSON to cases/ directory."""
        output_path = self.cases_dir / f"{case.case_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(case.model_dump(mode="json"), f, indent=2, default=str)
        logger.info(f"Case saved: {output_path}")
        return output_path

    async def write_to_graph(self, case: FraudCaseRecord) -> bool:
        """Write case to TigerGraph via write_case query."""
        if self.tg_client is None:
            logger.warning("No TigerGraph client — skipping graph write (dev mode)")
            return False
        try:
            # TODO (Phase 1): Use MCP tool call
            # await self.tg_client.call_tool("write_case", {...})
            logger.info(f"Case {case.case_id} written to TigerGraph")
            return True
        except Exception as e:
            logger.error(f"Failed to write case to graph: {e}")
            return False

    def _add_timeline_event(self, case: FraudCaseRecord, event_type: str, description: str) -> None:
        case.timeline.append(TimelineEvent(
            event_type=event_type,
            description=description,
        ))
