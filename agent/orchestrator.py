"""
FraudLens — Agent Orchestrator
================================
LangGraph state machine implementing the full investigation loop.

Investigation Flow:
  START
    │
    ▼
  [plan_investigation]
    │
    ▼
  [collect_evidence] ◄─────────────────┐
    │                                  │
    ▼                                  │
  [retrieve_similar_cases]             │
    │                                  │
    ▼                                  │
  [assess_risk]                        │
    │                                  │
    ▼                                  │
  [check_stop_condition]               │
    │                                  │
    ├── STOP ──► [recommend_nba]       │
    │                                  │
    └── CONTINUE ──► [request_evidence]│
                          │            │
                          ▼            │
                    [receive_evidence] │
                          │            │
                          └────────────┘ (re-investigate)
    │
    ▼
  [apply_policy]
    │
    ▼
  [determine_approval]
    │
    ▼
  [explain_decision]
    │
    ▼
  [write_case_to_graph]
    │
    ▼
  END
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Optional

from loguru import logger

from agent.planner import build_investigation_plan, TriggerType
from agent.evidence_collector import EvidenceCollector, EvidenceItem
from agent.risk_assessor import RiskAssessor, RiskAssessment
from agent.evidence_request_manager import EvidenceRequestManager, EvidenceRequest
from agent.nba_engine import NBAEngine, ActionRecommendation
from agent.case_manager import CaseManager, CaseStatus, FraudCaseRecord
from agent.memory_retrieval import MemoryRetrieval


# ============================================================
# Investigation State
# ============================================================

class InvestigationState:
    """Mutable state passed through the LangGraph nodes."""

    def __init__(
        self,
        case_id: str,
        txn_id: str,
        trigger_type: str,
        card_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        trigger_risk_score: Optional[float] = None,
    ):
        self.case_id          = case_id
        self.txn_id           = txn_id
        self.trigger_type     = trigger_type
        self.card_id          = card_id
        self.customer_id      = customer_id
        self.trigger_risk_score = trigger_risk_score

        # Investigation data
        self.plan             = None
        self.evidence: list[EvidenceItem] = []
        self.similar_cases: list[dict] = []
        self.initial_assessment: Optional[RiskAssessment] = None
        self.final_assessment:   Optional[RiskAssessment] = None
        self.evidence_request:   Optional[EvidenceRequest] = None

        # NBA
        self.initial_actions: list[ActionRecommendation] = []
        self.final_actions:   list[ActionRecommendation] = []
        self.what_changed: Optional[str] = None

        # Loop control
        self.iteration        = 0
        self.max_iterations   = 3
        self.stop_investigation = False

        # Progress stream
        self.progress_events: list[dict] = []


# ============================================================
# Orchestrator
# ============================================================

class Orchestrator:
    """
    Runs the complete fraud investigation loop as an async generator.

    Emits progress events at each step for real-time SSE streaming.

    Usage:
        orch = Orchestrator()
        async for event in orch.investigate(txn_id="T_001", trigger="risk_score"):
            print(event)
    """

    def __init__(
        self,
        mcp_client: Any = None,
        vector_store: Any = None,
        cases_dir: str = "./cases",
    ):
        self.collector       = EvidenceCollector(mcp_client=mcp_client)
        self.assessor        = RiskAssessor()
        self.req_manager     = EvidenceRequestManager()
        self.nba_engine      = NBAEngine()
        self.case_manager    = CaseManager(cases_dir=cases_dir, tg_client=mcp_client)
        self.memory          = MemoryRetrieval(mcp_client=mcp_client, vector_store=vector_store)

    async def investigate(
        self,
        txn_id: str,
        trigger_type: str,
        card_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        trigger_risk_score: Optional[float] = None,
        case_id: Optional[str] = None,
    ) -> AsyncIterator[dict]:
        """
        Run the full investigation loop.

        Yields SSE-compatible progress events at each step.
        """
        # --- Create Case ---
        case = self.case_manager.create_case(
            txn_id=txn_id,
            trigger_type=trigger_type,
            card_id=card_id,
            customer_id=customer_id,
            trigger_risk_score=trigger_risk_score,
            case_id=case_id,
        )
        state = InvestigationState(
            case_id=case.case_id,
            txn_id=txn_id,
            trigger_type=trigger_type,
            card_id=card_id,
            customer_id=customer_id,
            trigger_risk_score=trigger_risk_score,
        )

        yield self._event("case_created", f"Case {case.case_id} created", case_id=case.case_id)

        # --- Plan ---
        self.case_manager.transition(case, CaseStatus.INVESTIGATING, "Building investigation plan")
        yield self._event("step", "Building investigation plan", step="plan_investigation")

        state.plan = build_investigation_plan(trigger_type, txn_id, card_id, customer_id)
        yield self._event("step", f"Plan ready — {len(state.plan.steps)} steps", step="plan_complete", status="done")

        # --- Main Investigation Loop ---
        evidence_request_count = 0
        while state.iteration < state.max_iterations and not state.stop_investigation:
            state.iteration += 1
            logger.info(f"Investigation round {state.iteration}")

            # --- Collect Evidence ---
            yield self._event("step", "Collecting evidence from TigerGraph", step="collect_evidence")
            new_evidence = await self.collector.collect(state.plan, state.evidence)
            state.evidence.extend(new_evidence)
            self.case_manager.append_evidence(case, new_evidence)
            yield self._event("step", f"{len(new_evidence)} evidence items collected", step="collect_evidence", status="done")

            # --- Similar Cases ---
            yield self._event("step", "Retrieving similar historical cases", step="retrieve_similar_cases")
            similar = await self.memory.retrieve(
                pattern=state.plan.hypothesis,
                device_profile_id=None,
                card_ids=[card_id] if card_id else [],
            )
            state.similar_cases = [
                {
                    "case_id": c.case_id,
                    "similarity_score": c.similarity_score,
                    "similarity_reasons": c.similarity_reasons,
                    "pattern": c.pattern,
                    "outcome": c.outcome,
                    "actions_taken": c.actions_taken,
                    "analyst_notes_excerpt": c.analyst_notes_excerpt,
                }
                for c in similar
            ]
            self.case_manager.set_similar_cases(case, state.similar_cases)
            yield self._event("step", f"{len(similar)} similar cases found", step="retrieve_similar_cases", status="done")

            # --- Assess Risk ---
            yield self._event("step", "Assessing risk and evidence", step="assess_risk")
            assessment = self.assessor.assess(
                evidence=state.evidence,
                trigger_type=trigger_type,
                similar_cases=state.similar_cases,
            )
            yield self._event(
                "risk_update",
                f"Risk: {assessment.risk_level} ({assessment.fraud_probability:.0%})",
                risk=assessment.risk_level,
                fraud_probability=assessment.fraud_probability,
                confidence=assessment.confidence,
            )

            # Store initial assessment on first round
            if state.initial_assessment is None:
                state.initial_assessment = assessment
                self.case_manager.set_initial_assessment(case, assessment)

            # --- Check Stop Condition ---
            if assessment.sufficient_to_act or state.iteration >= state.max_iterations:
                state.stop_investigation = True
                state.final_assessment = assessment
                self.case_manager.set_final_assessment(case, assessment)
                yield self._event("step", f"Stop condition met: {assessment.stop_reason or 'max iterations'}", step="check_stop", status="done")
                break

            # --- Request Evidence ---
            self.case_manager.transition(case, CaseStatus.AWAITING_EVIDENCE, "Requesting additional evidence")
            yield self._event("step", "Evidence insufficient — requesting more", step="request_evidence", status="warning")

            ev_request = self.req_manager.determine_request(
                assessment, state.evidence, evidence_request_count
            )
            if ev_request is None:
                state.stop_investigation = True
                state.final_assessment = assessment
                self.case_manager.set_final_assessment(case, assessment)
                break

            state.evidence_request = ev_request
            evidence_request_count += 1
            yield self._event(
                "evidence_request",
                f"Requesting {ev_request.request_type}: {ev_request.question[:80]}...",
                request_type=ev_request.request_type,
                request_id=ev_request.request_id,
            )

            # --- Receive Simulated Evidence ---
            self.case_manager.transition(case, CaseStatus.REASSESSING, "New evidence received — reassessing")
            simulated = self.req_manager.simulate_response(ev_request, scenario="deny")
            state.evidence.append(simulated)
            self.case_manager.append_evidence(case, [simulated])
            yield self._event("step", f"New evidence received: {simulated.claim[:80]}...", step="receive_evidence", status="done")

        # --- NBA ---
        self.case_manager.transition(case, CaseStatus.ACTION_RECOMMENDED, "Generating Next-Best-Action")
        yield self._event("step", "Generating Next-Best-Action", step="recommend_nba")

        final_assessment = state.final_assessment or state.initial_assessment

        state.initial_actions = self.nba_engine.recommend(
            state.initial_assessment, phase="initial"
        )
        state.final_actions = self.nba_engine.recommend(
            final_assessment, phase="final"
        )
        self.case_manager.set_nba(case, state.initial_actions, phase="initial")
        self.case_manager.set_nba(case, state.final_actions, phase="final")

        # What changed?
        if state.initial_assessment != final_assessment:
            state.what_changed = self.nba_engine.compute_what_changed(
                state.initial_actions, state.final_actions,
                state.initial_assessment, final_assessment,
                new_evidence_claim=state.evidence[-1].claim if state.evidence else "",
            )
            case.what_changed = state.what_changed

        yield self._event("nba", f"NBA ready: {[a.action for a in state.final_actions]}")

        # --- Determine Approval ---
        needs_approval = any(a.route in ("L1", "L2") for a in state.final_actions)
        if needs_approval:
            self.case_manager.transition(case, CaseStatus.AWAITING_APPROVAL, "Awaiting analyst approval")
            yield self._event("step", "Analyst approval required", step="awaiting_approval", status="warning")

        # --- Resolve ---
        fraud_verdict = "fraud" if final_assessment.fraud_probability >= 0.50 else "cleared"
        self.case_manager.resolve(
            case,
            verdict=fraud_verdict,
            exposure_usd=trigger_risk_score * 1000 if trigger_risk_score else 0.0,
            sar_required=any(a.action == "FILE_REPORT" for a in state.final_actions),
        )

        # --- Write to Graph & Disk ---
        await self.case_manager.write_to_graph(case)
        output_path = self.case_manager.save_to_disk(case)
        yield self._event("complete", f"Investigation complete | case={case.case_id}", case_id=case.case_id)

        logger.info(f"Investigation complete: {case.case_id} | verdict={fraud_verdict} | path={output_path}")

    def _event(self, event_type: str, message: str, **kwargs) -> dict:
        """Create a progress event dict for SSE streaming."""
        return {"type": event_type, "message": message, **kwargs}


# ============================================================
# CLI Entry Point
# ============================================================

async def run_single_case(
    txn_id: str,
    trigger_type: str = "risk_score",
    card_id: Optional[str] = None,
):
    """Run a single case investigation (dev helper)."""
    orch = Orchestrator()
    async for event in orch.investigate(txn_id, trigger_type, card_id=card_id):
        print(f"  [{event['type'].upper()}] {event['message']}")


if __name__ == "__main__":
    asyncio.run(run_single_case("T_MOCK_001", "risk_score", "CARD_MOCK_001"))
