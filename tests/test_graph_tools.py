"""
FraudLens — Graph Tools Tests
"""
import pytest
from tools.graph_tools import (
    get_tg_connection,
    get_transaction,
    get_card_history,
    search_similar_cases,
    find_shared_devices,
    find_connected_cards,
    detect_card_testing,
    detect_velocity_anomaly,
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


def test_detect_velocity_anomaly(tg_conn):
    res = detect_velocity_anomaly(tg_conn, "22563_399.0_150.0_american express_236.0_credit", hours=24)
    assert res["success"] is True
