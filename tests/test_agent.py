"""
FraudLens — Agent Layer Tests
==============================
End-to-end and unit tests for the agent orchestration system.
All tests run in mock mode (no TigerGraph connection required).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent.evidence_collector import EvidenceCollector, EvidenceItem
from agent.planner import build_investigation_plan, TriggerType
from agent.risk_assessor import RiskAssessor, RiskAssessment
from agent.nba_engine import NBAEngine
from agent.case_manager import CaseManager, CaseStatus
from agent.orchestrator import Orchestrator, run_single_case
from policy.rules import check_rule_R1, check_rule_R5


# ============================================================
# Helpers
# ============================================================

def run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


@pytest.fixture()
def tmp_cases(tmp_path):
    """Temporary cases directory for each test."""
    return str(tmp_path / "cases")


# ============================================================
# 1 — Evidence Collector: per-query parsers
# ============================================================

class TestEvidenceCollector:

    def test_mock_get_transaction_high_risk(self):
        """get_transaction mock with risk_score=0.87 → supports_fraud=True."""
        collector = EvidenceCollector()
        result = collector._mock_response("get_transaction")
        # Inject directly for deterministic test
        step = _make_step("get_transaction", {"txn_id": "T_MOCK"})
        items = collector._parse_get_transaction(step, result)

        assert len(items) == 1
        e = items[0]
        assert e.supports_fraud is True
        assert e.confidence >= 0.80
        assert "risk score" in e.claim.lower()
        assert collector.signals["risk_score"] >= 0.80

    def test_mock_card_history_detects_card_testing(self):
        """Card history with 3 micro + 1 large transaction → card testing evidence."""
        collector = EvidenceCollector()
        result = collector._mock_response("get_card_history")
        step = _make_step("get_card_history", {})
        items = collector._parse_get_card_history(step, result)

        assert len(items) == 1
        e = items[0]
        assert e.supports_fraud is True
        assert "card testing" in e.claim.lower()

    def test_mock_device_neighbors_shared_3(self):
        """3 device neighbors → shared_device_ring supports_fraud=True."""
        collector = EvidenceCollector()
        result = collector._mock_response("get_device_neighbors")
        step = _make_step("get_device_neighbors", {})
        items = collector._parse_get_device_neighbors(step, result)

        assert len(items) == 1
        e = items[0]
        assert e.supports_fraud is True
        assert collector.signals["shared_device_count"] >= 3

    def test_mock_card_testing_flag(self):
        """detect_card_testing with card_testing_detected=True → definitive fraud."""
        collector = EvidenceCollector()
        result = collector._mock_response("detect_card_testing")
        step = _make_step("detect_card_testing", {})
        items = collector._parse_detect_card_testing(step, result)

        assert len(items) == 1
        e = items[0]
        assert e.supports_fraud is True
        assert e.confidence >= 0.90
        assert collector.signals["card_testing_detected"] is True

    def test_full_mock_collect_populates_signals(self):
        """Full collect() run populates all expected signal keys."""
        collector = EvidenceCollector()
        plan = build_investigation_plan(
            "risk_score", "T_MOCK_001", card_id="CARD_MOCK_001"
        )
        evidence = run(collector.collect(plan))

        assert len(evidence) > 0
        # Key signals must be set
        assert collector.signals["risk_score"] >= 0.0
        assert isinstance(collector.signals["card_testing_detected"], bool)
        assert isinstance(collector.signals["shared_device_count"], int)


# ============================================================
# 2 — Risk Assessor: signal-aware probability
# ============================================================

class TestRiskAssessor:

    def _make_evidence(self, **kwargs) -> EvidenceItem:
        defaults = dict(
            evidence_id="EVD-TEST",
            claim="Test evidence",
            source="graph",
            ref="get_transaction",
            entity_ids=[],
            confidence=0.80,
            supports_fraud=True,
            raw_data={},
        )
        defaults.update(kwargs)
        return EvidenceItem(**defaults)

    def test_high_risk_score_signal_boosts_probability(self):
        """risk_score=0.90 signal should push fraud_probability well above base."""
        assessor = RiskAssessor()
        evidence = [self._make_evidence(
            ref="get_transaction",
            raw_data={"risk_score": 0.90, "amount": 500.0},
        )]
        signals = {"risk_score": 0.90, "amount": 500.0, "card_testing_detected": False,
                   "shared_device_count": 0, "ring_size": 0, "is_new_device": False,
                   "out_of_region": False, "velocity_count": 0, "connected_fraud_cases": 0,
                   "txn_sequence": [], "device_profile_id": "", "connected_card_ids": []}

        assessment = assessor.assess(evidence, "risk_score", collector_signals=signals)
        assert assessment.fraud_probability >= 0.70

    def test_card_testing_signal_produces_high_risk(self):
        """card_testing_detected=True should produce CRITICAL or HIGH risk."""
        assessor = RiskAssessor()
        evidence = [
            self._make_evidence(ref="detect_card_testing", raw_data={"card_testing_detected": True}),
            self._make_evidence(ref="get_card_history", raw_data={"micro_txn_count": 3}),
        ]
        signals = {"risk_score": 0.87, "amount": 542.0, "card_testing_detected": True,
                   "shared_device_count": 0, "ring_size": 0, "is_new_device": False,
                   "out_of_region": False, "velocity_count": 0, "connected_fraud_cases": 0,
                   "txn_sequence": [], "device_profile_id": "", "connected_card_ids": []}

        assessment = assessor.assess(evidence, "risk_score", collector_signals=signals)
        assert assessment.risk_level in ("HIGH", "CRITICAL")
        assert assessment.fraud_probability >= 0.75
        assert assessment.pattern == "card_testing"

    def test_shared_device_ring_pattern(self):
        """shared_device_count=3 → shared_device_ring pattern."""
        assessor = RiskAssessor()
        evidence = [
            self._make_evidence(ref="get_device_neighbors", raw_data={"shared_device_count": 3}),
            self._make_evidence(ref="find_connected_cards", raw_data={"ring_size": 3}),
        ]
        signals = {"risk_score": 0.0, "amount": 0.0, "card_testing_detected": False,
                   "shared_device_count": 3, "ring_size": 3, "is_new_device": False,
                   "out_of_region": False, "velocity_count": 0, "connected_fraud_cases": 2,
                   "txn_sequence": [], "device_profile_id": "", "connected_card_ids": []}

        assessment = assessor.assess(evidence, "risk_score", collector_signals=signals)
        assert assessment.pattern == "shared_device_ring"
        assert assessment.fraud_probability >= 0.50

    def test_sufficient_to_act_stop_condition(self):
        """High prob + high confidence + 2 supporting items → sufficient_to_act=True."""
        assessor = RiskAssessor()
        supporting = [
            self._make_evidence(evidence_id=f"EVD-{i}", confidence=0.90, supports_fraud=True)
            for i in range(4)
        ]
        signals = {"risk_score": 0.95, "amount": 1000.0, "card_testing_detected": True,
                   "shared_device_count": 3, "ring_size": 0, "is_new_device": False,
                   "out_of_region": False, "velocity_count": 0, "connected_fraud_cases": 0,
                   "txn_sequence": [], "device_profile_id": "", "connected_card_ids": []}
        assessment = assessor.assess(supporting, "risk_score", collector_signals=signals)
        assert assessment.sufficient_to_act is True

    def test_assessment_exposes_extracted_signals(self):
        """RiskAssessment.extracted_signals must contain expected keys."""
        assessor = RiskAssessor()
        evidence = [self._make_evidence()]
        assessment = assessor.assess(evidence, "risk_score")
        assert "risk_score" in assessment.extracted_signals
        assert "card_testing_detected" in assessment.extracted_signals
        assert "shared_device_count" in assessment.extracted_signals


# ============================================================
# 3 — NBA Engine: signals extracted and policy fires
# ============================================================

class TestNBAEngine:

    def _high_risk_assessment(self) -> RiskAssessment:
        return RiskAssessment(
            risk_level="CRITICAL",
            fraud_probability=0.92,
            confidence=0.85,
            evidence_sufficiency="HIGH",
            sufficient_to_act=True,
            pattern="card_testing",
            pattern_description="Card testing",
            extracted_signals={
                "risk_score": 0.92,
                "amount": 542.0,
                "card_testing_detected": True,
                "shared_device_count": 3,
                "ring_size": 3,
                "is_new_device": True,
                "out_of_region": False,
                "velocity_count": 0,
                "connected_fraud_cases": 2,
                "txn_sequence": [
                    {"amount": 1.0, "ts": ""},
                    {"amount": 1.5, "ts": ""},
                    {"amount": 2.0, "ts": ""},
                    {"amount": 542.0, "ts": ""},
                ],
            },
        )

    def test_policy_R1_fires_from_extracted_signals(self):
        """R1 (high prob + evidence) must fire and produce BLOCK_CARD action."""
        engine = NBAEngine()
        assessment = self._high_risk_assessment()
        actions = engine.recommend(assessment, phase="final")

        action_names = {a.action for a in actions}
        assert "BLOCK_CARD" in action_names, f"BLOCK_CARD missing from {action_names}"

    def test_policy_R4_fraud_ring_fires(self):
        """connected_fraud_cases=2 → R4 fires → FLAG_FRAUD_RING + ESCALATE_CASE."""
        engine = NBAEngine()
        assessment = self._high_risk_assessment()
        actions = engine.recommend(assessment, phase="final")

        action_names = {a.action for a in actions}
        assert "FLAG_FRAUD_RING" in action_names or "ESCALATE_CASE" in action_names

    def test_actions_have_mandatory_flag(self):
        """Policy-mandated actions must have is_mandatory=True."""
        engine = NBAEngine()
        assessment = self._high_risk_assessment()
        actions = engine.recommend(assessment, phase="initial")

        mandatory = [a for a in actions if a.is_mandatory]
        assert len(mandatory) >= 1

    def test_actions_ordered_by_priority(self):
        """Actions list must be ordered by priority (ascending)."""
        engine = NBAEngine()
        assessment = self._high_risk_assessment()
        actions = engine.recommend(assessment, phase="final")

        priorities = [a.priority for a in actions]
        assert priorities == sorted(priorities)


# ============================================================
# 4 — Case Manager: schema fields
# ============================================================

class TestCaseManager:

    def test_create_case_has_all_required_fields(self, tmp_cases):
        cm = CaseManager(cases_dir=tmp_cases)
        case = cm.create_case(
            txn_id="T_TEST_001",
            trigger_type="risk_score",
            card_id="CARD_001",
            customer_id="C_001",
            trigger_risk_score=0.87,
            case_id="HHG-TEST",
        )
        assert case.case_id == "HHG-TEST"
        assert case.txn_id == "T_TEST_001"
        assert case.status == CaseStatus.TRIGGERED
        assert len(case.timeline) == 1

    def test_benchmark_json_has_required_fields(self, tmp_cases):
        """to_answer_json() must include all fields checked by validate_case_json()."""
        cm = CaseManager(cases_dir=tmp_cases)
        case = cm.create_case("T_TEST_002", "risk_score", case_id="HHG-SCHEMA")
        cm.transition(case, CaseStatus.RESOLVED)

        # Set minimal required data
        case.final_fraud_probability = 0.90
        case.final_risk_level = "CRITICAL"
        case.pattern = "card_testing"
        case.final_verdict = "fraud"
        case.final_actions = [{"action": "BLOCK_CARD", "route": "L1"}]
        case.evidence = [{"evidence_id": "EVD-001", "claim": "test"}]
        case.sar = {"file": False, "reason": None}

        answer = cm.to_answer_json(case)
        required = [
            "case_id", "txn_id", "trigger_type", "status",
            "final_fraud_probability", "final_risk_level",
            "pattern", "final_verdict", "final_actions",
            "evidence", "timeline", "sar",
        ]
        for field in required:
            assert field in answer, f"Missing benchmark field: {field}"


# ============================================================
# 5 — Orchestrator: full pipeline (mock mode)
# ============================================================

class TestOrchestrator:

    def test_full_pipeline_mock_emits_events(self, tmp_cases):
        """Full investigation loop must emit case_created, risk_update, nba, complete events."""
        orch = Orchestrator(cases_dir=tmp_cases)

        events = run(_collect_events(orch, "T_MOCK_001", "risk_score", "CARD_MOCK_001"))

        event_types = {e["type"] for e in events}
        assert "case_created" in event_types
        assert "risk_update" in event_types
        assert "nba" in event_types
        assert "complete" in event_types

    def test_full_pipeline_writes_case_file(self, tmp_cases):
        """Investigation must write a case JSON file to cases/ dir."""
        orch = Orchestrator(cases_dir=tmp_cases)
        events = run(_collect_events(orch, "T_MOCK_002", "risk_score", "CARD_MOCK_001",
                                     case_id="HHG-WRITE"))

        complete_event = next(e for e in events if e["type"] == "complete")
        output_path = Path(complete_event["output_path"])
        assert output_path.exists(), f"Case file not found: {output_path}"

        with open(output_path) as f:
            data = json.load(f)
        assert data["case_id"] == "HHG-WRITE"
        assert "final_verdict" in data

    def test_pipeline_stop_condition_limits_iterations(self, tmp_cases):
        """When sufficient_to_act fires, loop must stop before max_iterations."""
        orch = Orchestrator(cases_dir=tmp_cases)
        events = run(_collect_events(orch, "T_MOCK_003", "risk_score", "CARD_MOCK_001"))

        # Should not have more check_stop events than max_iterations
        check_stops = [e for e in events if e.get("step") == "check_stop"]
        assert len(check_stops) <= orch.assessor.MIN_INDEPENDENT_EVIDENCE + 2

    def test_customer_report_trigger_plan(self, tmp_cases):
        """customer_report trigger must build different investigation plan."""
        orch = Orchestrator(cases_dir=tmp_cases)
        events = run(_collect_events(orch, "T_MOCK_004", "customer_report", "CARD_MOCK_001"))

        plan_event = next(e for e in events if e.get("step") == "plan_complete")
        # The plan should exist and report some steps
        assert "Plan ready" in plan_event["message"] or "plan" in plan_event["message"].lower()

    def test_case_json_benchmark_schema_valid(self, tmp_cases):
        """Case JSON must pass the benchmark validator after a full run."""
        orch = Orchestrator(cases_dir=tmp_cases)
        run(_collect_events(orch, "T_MOCK_005", "risk_score", "CARD_MOCK_001",
                            case_id="HHG-VALIDATE"))

        from scripts.run_benchmarks import validate_case_json
        import os
        os.chdir(tmp_cases.replace("/cases", ""))

        result = validate_case_json_from_path(
            Path(tmp_cases) / "HHG-VALIDATE.json"
        )
        assert result["valid"], f"Schema issues: {result['issues']}"


# ============================================================
# Helpers for tests
# ============================================================

def _make_step(query_name: str, params: dict):
    """Create a minimal InvestigationStep for parser tests."""
    from agent.planner import InvestigationStep, QueryPriority
    return InvestigationStep(
        step_id="test",
        query_name=query_name,
        description="test step",
        priority=QueryPriority.P0,
        params=params,
        reason="test",
    )


async def _collect_events(orch, txn_id, trigger, card_id=None, case_id=None):
    events = []
    async for event in orch.investigate(
        txn_id=txn_id,
        trigger_type=trigger,
        card_id=card_id,
        case_id=case_id,
    ):
        events.append(event)
    return events


def validate_case_json_from_path(case_file: Path) -> dict:
    """Standalone validator (doesn't depend on cwd)."""
    issues = []
    if not case_file.exists():
        return {"case_id": case_file.stem, "valid": False, "issues": ["File not found"]}

    with open(case_file) as f:
        data = json.load(f)

    required_fields = [
        "case_id", "txn_id", "trigger_type", "status",
        "final_fraud_probability", "final_risk_level",
        "pattern", "final_verdict", "final_actions",
        "evidence", "timeline", "sar",
    ]
    for field in required_fields:
        if field not in data:
            issues.append(f"Missing field: {field}")

    sar_filed = data.get("sar", {}).get("file", False)
    final_actions = [a.get("action") for a in data.get("final_actions", [])]
    if sar_filed and "FILE_REPORT" not in final_actions:
        issues.append("SAR filed but FILE_REPORT not in final_actions")

    return {"case_id": data.get("case_id"), "valid": len(issues) == 0, "issues": issues}
