"""
FraudLens — Graph Tools Tests
"""
import pytest
from tools.graph_tools import (
    get_tg_connection,
    get_transaction,
    get_card_history,
    get_device_neighbors,
    get_transaction_neighbors,
    get_customer_transactions,
    get_billing_region_cards,
    search_similar_cases,
    find_shared_devices,
    find_connected_cards,
    detect_card_testing,
    detect_velocity_anomaly,
    write_case,
    verify_case_writeback,
    expand_entity_neighbors,
)


@pytest.fixture(scope="module")
def tg_conn():
    conn = get_tg_connection()
    if conn is None:
        pytest.skip("TigerGraph connection not available")
    return conn


def test_tg_connection_active(tg_conn):
    ping_res = tg_conn.ping()
    assert ping_res.get("error") is False
    assert ping_res.get("message") == "pong"


def test_get_transaction(tg_conn):
    res = get_transaction(tg_conn, "3000001")
    assert res["success"] is True
    assert len(res["results"]) > 0


def test_get_card_history(tg_conn):
    res = get_card_history(tg_conn, "22563_399.0_150.0_american express_236.0_credit", days=365)
    assert res["success"] is True


def test_search_similar_cases(tg_conn):
    res = search_similar_cases(tg_conn, pattern="card_testing")
    assert res["success"] is True


def test_get_device_neighbors_contract(tg_conn):
    res = get_device_neighbors(tg_conn, "Windows 8.1_chrome 66.0_1368x768")
    assert res["success"] is True
    assert "entity_ids" in res


def test_get_transaction_neighbors_contract(tg_conn):
    res = get_transaction_neighbors(tg_conn, "3478561", hops=1)
    assert res["success"] is True


def test_get_customer_transactions_contract(tg_conn):
    res = get_customer_transactions(tg_conn, "C12517", lim=10)
    assert res["success"] is True


def test_search_similar_cases_all_params(tg_conn):
    res = search_similar_cases(
        tg_conn,
        pattern="card_testing",
        device_profile_id="Windows 8.1_chrome 66.0_1368x768",
        card_ids=["C12382-K1"]
    )
    assert res["success"] is True


def test_write_and_verify_case_writeback(tg_conn):
    test_case_id = "HHG-TEST-WRITEBACK"
    case_data = {
        "case_id": test_case_id,
        "trigger_type": "risk_score",
        "status": "RESOLVED",
        "fraud_prob": 0.95,
        "fraud_probability": 0.95,
        "confidence": 0.99,
        "risk_level": "CRITICAL",
        "pattern": "card_testing",
        "final_verdict": "fraud",
        "case_json": '{"test": true}',
    }
    w_res = write_case(tg_conn, case_data)
    assert w_res["success"] is True

    # Read-after-write verification
    v_res = verify_case_writeback(tg_conn, test_case_id)
    assert v_res["verified"] is True
    assert v_res["source"] == "tigergraph"


def test_expand_entity_neighbors_real_ids(tg_conn):
    res = expand_entity_neighbors(tg_conn, "3478561", "Transaction")
    assert res["success"] is True
    assert res["entity_id"] == "3478561"


def test_benchmark_transaction_3478561_exists(tg_conn):
    res = get_transaction(tg_conn, "3478561")
    assert res["success"] is True
    assert len(res["results"]) > 0
    assert len(res["results"][0].get("@@results", [])) > 0
