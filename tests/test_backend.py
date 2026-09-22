"""
FraudLens — Backend API Tests
==============================
Uses FastAPI TestClient (synchronous) and httpx AsyncClient for SSE tests.
All tests run without a live TigerGraph connection.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app, _store, CASES_DIR


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def clear_store():
    """Clear in-memory investigation store between tests."""
    _store.clear()
    yield
    _store.clear()


@pytest.fixture()
def client():
    """Synchronous TestClient."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def seed_case(tmp_path, monkeypatch):
    """
    Create a fake completed case JSON file in a temp cases dir
    and monkeypatch CASES_DIR so the backend reads from it.
    """
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()

    case_id = "HHG-TEST01"
    case_data = {
        "case_id": case_id,
        "txn_id": "T_SEED_001",
        "card_id": "CARD_SEED_001",
        "trigger_type": "risk_score",
        "status": "RESOLVED",
        "final_verdict": "fraud",
        "final_risk_level": "CRITICAL",
        "final_fraud_probability": 0.92,
        "pattern": "card_testing",
        "initial_fraud_probability": 0.45,
        "initial_risk_level": "MEDIUM",
        "created_at": "2026-09-22T10:00:00Z",
        "evidence": [
            {
                "evidence_id": "EVD-0001",
                "claim": "High risk score 0.92",
                "source": "graph",
                "ref": "get_transaction",
                "entity_ids": ["T_SEED_001", "CARD_SEED_001"],
                "confidence": 0.90,
                "supports_fraud": True,
                "raw_data": {"risk_score": 0.92, "amount": 542.0},
            },
            {
                "evidence_id": "EVD-0002",
                "claim": "Card testing detected",
                "source": "graph",
                "ref": "detect_card_testing",
                "entity_ids": ["CARD_SEED_001"],
                "confidence": 0.92,
                "supports_fraud": True,
                "raw_data": {"card_testing_detected": True},
            },
        ],
        "timeline": [
            {"event_type": "case_created", "description": "Case created", "timestamp": "2026-09-22T10:00:00Z"},
        ],
        "final_actions": [
            {"action": "BLOCK_CARD",    "route": "L1", "is_mandatory": True,  "priority": 1},
            {"action": "CREATE_CASE",   "route": "auto", "is_mandatory": False, "priority": 2},
            {"action": "MONITOR_ACCOUNT", "route": "auto", "is_mandatory": False, "priority": 3},
        ],
        "initial_actions": [
            {"action": "MONITOR_ACCOUNT", "route": "auto", "is_mandatory": False, "priority": 1},
        ],
        "what_changed": "Card testing detected → BLOCK_CARD added",
        "sar": {"file": False, "reason": None},
        "tool_calls": [],
    }

    (cases_dir / f"{case_id}.json").write_text(json.dumps(case_data, indent=2))

    import backend.main as bm
    monkeypatch.setattr(bm, "CASES_DIR", cases_dir)

    return case_id, cases_dir, case_data


# ============================================================
# 1 — Health Check
# ============================================================

class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["service"] == "FraudLens API"
        assert "timestamp" in data
        assert "tg_connected" in data

    def test_root_redirects_to_docs_hint(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "FraudLens" in r.json()["message"]


# ============================================================
# 2 — Investigation CRUD
# ============================================================

class TestInvestigations:

    def test_create_investigation_returns_case_id(self, client):
        r = client.post("/api/investigations", json={
            "txn_id": "T_TEST_001",
            "trigger_type": "risk_score",
            "card_id": "CARD_TEST_001",
        })
        assert r.status_code == 201
        data = r.json()
        assert "case_id" in data
        assert data["status"] == "CREATED"
        assert "stream" in data["message"]

    def test_create_investigation_accepts_custom_case_id(self, client):
        r = client.post("/api/investigations", json={
            "txn_id": "T_TEST_002",
            "trigger_type": "risk_score",
            "case_id": "HHG-CUSTOM-01",
        })
        assert r.status_code == 201
        assert r.json()["case_id"] == "HHG-CUSTOM-01"

    def test_list_investigations_after_create(self, client):
        client.post("/api/investigations", json={"txn_id": "T_LIST_001", "trigger_type": "risk_score"})
        client.post("/api/investigations", json={"txn_id": "T_LIST_002", "trigger_type": "risk_score"})

        r = client.get("/api/investigations")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 2
        assert len(data["investigations"]) >= 2

    def test_get_investigation_returns_state(self, client):
        create_r = client.post("/api/investigations", json={
            "txn_id": "T_GET_001",
            "trigger_type": "risk_score",
            "case_id": "HHG-GET-01",
        })
        case_id = create_r.json()["case_id"]

        r = client.get(f"/api/investigations/{case_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["case_id"] == case_id

    def test_get_investigation_404_unknown(self, client):
        r = client.get("/api/investigations/HHG-NOTEXIST")
        assert r.status_code == 404


# ============================================================
# 3 — SSE Streaming
# ============================================================

class TestSSEStream:

    def test_stream_404_for_unknown_case(self, client):
        r = client.get("/api/investigations/HHG-NOSTREAM/stream")
        assert r.status_code == 404

    def test_stream_delivers_events_for_running_case(self, client):
        """Create a case and immediately connect to stream — must get at least case_created."""
        create_r = client.post("/api/investigations", json={
            "txn_id": "T_STREAM_001",
            "trigger_type": "risk_score",
            "card_id": "CARD_MOCK_001",
            "case_id": "HHG-STREAM-01",
        })
        case_id = create_r.json()["case_id"]

        # Give agent a moment to emit some events
        time.sleep(1.0)

        # Collect up to 5 SSE lines with a short timeout
        collected = []
        with client.stream("GET", f"/api/investigations/{case_id}/stream") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    try:
                        event = json.loads(line[5:].strip())
                        collected.append(event)
                    except json.JSONDecodeError:
                        pass
                if len(collected) >= 3 or any(e.get("type") in ("complete", "stream_end") for e in collected):
                    break

        event_types = {e.get("type") for e in collected}
        assert len(collected) >= 1
        # Must have at least one meaningful event
        assert event_types & {"case_created", "step", "risk_update", "nba", "complete", "heartbeat"}


# ============================================================
# 4 — Evidence & Timeline (from disk)
# ============================================================

class TestEvidenceTimeline:

    def test_get_evidence_from_disk(self, client, seed_case):
        case_id, _, _ = seed_case
        r = client.get(f"/api/investigations/{case_id}/evidence")
        assert r.status_code == 200
        data = r.json()
        assert "evidence" in data
        assert data["total"] >= 2

    def test_get_timeline_from_disk(self, client, seed_case):
        case_id, _, _ = seed_case
        r = client.get(f"/api/investigations/{case_id}/timeline")
        assert r.status_code == 200
        data = r.json()
        assert "timeline" in data
        assert data["total"] >= 1


# ============================================================
# 5 — Graph Data
# ============================================================

class TestGraphData:

    def test_graph_returns_nodes_and_edges(self, client, seed_case):
        case_id, _, _ = seed_case
        r = client.get(f"/api/investigations/{case_id}/graph")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data
        assert "suspicious_nodes" in data
        assert "highlighted_paths" in data
        assert len(data["nodes"]) >= 2

    def test_graph_marks_suspicious_nodes(self, client, seed_case):
        case_id, _, _ = seed_case
        r = client.get(f"/api/investigations/{case_id}/graph")
        data = r.json()
        suspicious = data["suspicious_nodes"]
        # Evidence with supports_fraud=True should mark entity_ids as suspicious
        assert len(suspicious) >= 1

    def test_graph_404_unknown_case(self, client):
        r = client.get("/api/investigations/HHG-NOGRAPH/graph")
        assert r.status_code == 404


# ============================================================
# 6 — Approve / Reject
# ============================================================

class TestApprovalWorkflow:

    def test_approve_action_returns_approved(self, client, seed_case):
        case_id, _, _ = seed_case
        r = client.post(f"/api/investigations/{case_id}/approve", json={
            "action": "BLOCK_CARD",
            "approved_by": "analyst_test",
            "notes": "Confirmed card testing pattern",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "approved"
        assert data["action"] == "BLOCK_CARD"
        assert data["case_id"] == case_id
        assert "timestamp" in data

    def test_reject_action_returns_rejected(self, client, seed_case):
        case_id, _, _ = seed_case
        r = client.post(f"/api/investigations/{case_id}/reject", json={
            "action": "BLOCK_CARD",
            "approved_by": "analyst_test",
            "notes": "Insufficient evidence",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "rejected"

    def test_approve_persists_to_disk(self, client, seed_case):
        case_id, cases_dir, _ = seed_case
        client.post(f"/api/investigations/{case_id}/approve", json={
            "action": "BLOCK_CARD",
            "approved_by": "analyst_disk_test",
        })
        # Reload from disk
        with open(cases_dir / f"{case_id}.json") as f:
            data = json.load(f)
        block_action = next(
            (a for a in data.get("final_actions", []) if a.get("action") == "BLOCK_CARD"),
            None,
        )
        assert block_action is not None
        assert block_action.get("status") == "approved"


# ============================================================
# 7 — Submit Evidence + Re-scoring
# ============================================================

class TestEvidenceSubmission:

    def test_submit_evidence_appends_and_rescores(self, client, seed_case):
        case_id, _, original = seed_case
        r = client.post(f"/api/investigations/{case_id}/submit-evidence", json={
            "evidence_type": "customer_statement",
            "claim": "Customer confirmed they did not make this transaction",
            "source": "customer",
            "confidence": 0.85,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["case_id"] == case_id
        assert "evidence_id" in data
        assert "new_fraud_probability" in data
        assert "new_risk_level" in data


# ============================================================
# 8 — Dashboard & Cases
# ============================================================

class TestDashboard:

    def test_dashboard_returns_valid_structure(self, client, seed_case):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "total_cases" in data
        assert "fraud_cases" in data
        assert "cleared_cases" in data
        assert "high_risk_cases" in data
        assert "active_investigations" in data
        assert "avg_fraud_probability" in data
        assert "top_patterns" in data
        assert data["total_cases"] >= 1

    def test_list_cases_returns_array(self, client, seed_case):
        r = client.get("/api/cases")
        assert r.status_code == 200
        data = r.json()
        assert "cases" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_cases_verdict_filter(self, client, seed_case):
        r = client.get("/api/cases?verdict=fraud")
        assert r.status_code == 200
        cases = r.json()["cases"]
        assert all(c["final_verdict"] == "fraud" for c in cases)

    def test_get_case_by_id(self, client, seed_case):
        case_id, _, original = seed_case
        r = client.get(f"/api/cases/{case_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["case_id"] == case_id
        assert data["final_verdict"] == "fraud"

    def test_get_case_404(self, client):
        r = client.get("/api/cases/HHG-NOTHERE")
        assert r.status_code == 404


# ============================================================
# 9 — Policies
# ============================================================

class TestPolicies:

    def test_policies_has_10_rules(self, client):
        r = client.get("/api/policies")
        assert r.status_code == 200
        data = r.json()
        assert data["total_rules"] == 10
        assert len(data["rules"]) == 10
        rule_ids = {rule["rule_id"] for rule in data["rules"]}
        assert rule_ids == {"R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"}

    def test_policies_has_14_actions(self, client):
        r = client.get("/api/policies")
        assert len(r.json()["actions"]) == 14

    def test_policy_approval_routes(self, client):
        r = client.get("/api/policies")
        rules = {rule["rule_id"]: rule for rule in r.json()["rules"]}
        assert rules["R1"]["approval_route"] == "L1"
        assert rules["R4"]["approval_route"] == "L2"
        assert rules["R3"]["approval_route"] == "auto"


# ============================================================
# 10 — Memory
# ============================================================

class TestMemory:

    def test_memory_returns_cases(self, client):
        r = client.get("/api/memory")
        assert r.status_code == 200
        data = r.json()
        assert "historical_cases" in data
        assert "total" in data
        # dataset_sample/closed_cases_history.csv must exist
        if data["total"] > 0:
            case = data["historical_cases"][0]
            assert "case_id" in case
            assert "outcome" in case
            assert "pattern" in case

    def test_memory_pattern_filter(self, client):
        r = client.get("/api/memory?pattern=card_testing")
        assert r.status_code == 200
        data = r.json()
        for case in data["historical_cases"]:
            assert "card" in case["pattern"].lower() or "testing" in case["pattern"].lower()

    def test_memory_limit(self, client):
        r = client.get("/api/memory?limit=5")
        assert r.status_code == 200
        data = r.json()
        assert len(data["historical_cases"]) <= 5
