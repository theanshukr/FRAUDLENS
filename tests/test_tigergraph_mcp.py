"""
FraudLens — TigerGraph Model Context Protocol (MCP) Integration Tests
=====================================================================
Tests:
  1. MCP Client initialization & configuration
  2. MCP Tool discovery (discovering official tigergraph-mcp tools)
  3. MCP Health check reporting live status
  4. MCP Tool invocation (run_installed_query, get_vertex_count)
  5. Timeout handling in MCP client
  6. GraphAccessMode abstraction (MCP, DIRECT, AUTO)
  7. Direct TigerGraph fallback when MCP encounters error
  8. Zero silent mock data guarantees
  9. Structured provenance generation on all graph queries
  10. Temporal anti-leakage filtering (closed_at <= cutoff_ts)
  11. Writeback verification (read-after-write)
  12. FastAPI /api/system/mcp endpoint verification
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from tools.tigergraph_mcp_client import TigerGraphMCPClient, GraphAccessMode, get_mcp_client
from tools.graph_tools import (
    get_graph_access_mode,
    execute_graph_query,
    get_transaction,
    search_similar_cases,
    verify_case_writeback,
    expand_entity_neighbors,
)


class TestTigerGraphMCPClient:
    """Test official TigerGraph MCP Client functionality."""

    def test_client_init_and_config(self):
        client = TigerGraphMCPClient()
        assert client.graphname in ("FraudLens", "default", os.getenv("TG_GRAPH_NAME", "FraudLens"))
        assert client.mode in ("auto", "mcp", "direct")

    def test_tool_discovery_has_standard_tools(self):
        client = TigerGraphMCPClient()
        tools = client.list_tools()
        assert len(tools) >= 50
        tool_names = [t["name"] for t in tools]
        assert "tigergraph__run_installed_query" in tool_names
        assert "tigergraph__get_vertex_count" in tool_names
        assert "tigergraph__get_neighbors" in tool_names
        assert "tigergraph__get_node" in tool_names

    def test_health_check_structure(self):
        client = TigerGraphMCPClient()
        hc = client.health_check()
        assert "available" in hc
        assert "connected" in hc
        assert hc["server"] == "tigergraph-mcp"
        assert "tool_count" in hc
        assert isinstance(hc["tool_count"], int)

    def test_mcp_provenance_format(self):
        client = TigerGraphMCPClient()
        mock_fn = MagicMock(return_value='```json\n{"success": true, "data": {"count": 10}}\n```')
        with patch.object(client, "_get_tool_function", return_value=mock_fn):
            res = client.call_tool("tigergraph__get_vertex_count", {"vertex_type": "Transaction"})
            assert res.get("success") is True
            prov = res.get("provenance")
            assert prov is not None
            assert prov["access_mode"] == "mcp"
            assert prov["provider"] == "TigerGraph MCP"
            assert prov["tool"] == "tigergraph__get_vertex_count"
            assert "latency_ms" in prov
            assert "timestamp" in prov

    def test_mcp_timeout_handling(self):
        client = TigerGraphMCPClient()
        async def slow_fn(*args, **kwargs):
            import asyncio
            await asyncio.sleep(2.0)
            return []

        with patch.object(client, "_get_tool_function", return_value=slow_fn):
            res = client.call_tool("tigergraph__get_vertex_count", {}, timeout=0.05)
            assert res.get("success") is False
            assert "timed out" in res.get("error", "").lower()
            assert res.get("provenance", {}).get("success") is False


class TestGraphAccessModeAndFallback:
    """Test unified GraphAccessMode and direct SDK fallback."""

    def test_graph_access_mode_resolution(self):
        with patch.dict(os.environ, {"FRAUDLENS_GRAPH_ACCESS_MODE": "mcp"}):
            assert get_graph_access_mode() == GraphAccessMode.MCP

        with patch.dict(os.environ, {"FRAUDLENS_GRAPH_ACCESS_MODE": "direct"}):
            assert get_graph_access_mode() == GraphAccessMode.DIRECT

        with patch.dict(os.environ, {"FRAUDLENS_GRAPH_ACCESS_MODE": "auto"}):
            assert get_graph_access_mode() == GraphAccessMode.AUTO

    def test_direct_fallback_when_mcp_fails_in_auto(self):
        mock_conn = MagicMock()
        mock_conn.runInstalledQuery.return_value = [{"@@results": ["3478561", "191.0"]}]

        mock_mcp = MagicMock()
        mock_mcp.run_installed_query.return_value = {"success": False, "error": "MCP unavailable"}

        with patch("tools.graph_tools.get_mcp_client", return_value=mock_mcp):
            with patch.dict(os.environ, {"FRAUDLENS_GRAPH_ACCESS_MODE": "auto"}):
                res = execute_graph_query(mock_conn, "get_transaction", {"txn_id": "3478561"})
                assert res.get("success") is True
                assert res.get("results") == [{"@@results": ["3478561", "191.0"]}]
                assert res.get("provenance", {}).get("access_mode") == "direct"

    def test_strict_mcp_mode_does_not_silently_fallback(self):
        mock_conn = MagicMock()
        mock_conn.runInstalledQuery.return_value = [{"@@results": ["3478561"]}]

        mock_mcp = MagicMock()
        mock_mcp.run_installed_query.return_value = {"success": False, "error": "MCP connection reset"}

        with patch("tools.graph_tools.get_mcp_client", return_value=mock_mcp):
            with patch.dict(os.environ, {"FRAUDLENS_GRAPH_ACCESS_MODE": "mcp"}):
                res = execute_graph_query(mock_conn, "get_transaction", {"txn_id": "3478561"})
                assert res.get("success") is False
                assert mock_conn.runInstalledQuery.call_count == 0


class TestTemporalAntiLeakage:
    """Test that historical case retrieval respects temporal cutoff (closed_at <= before_ts)."""

    def test_temporal_anti_leakage_filter(self):
        mock_raw_res = {
            "success": True,
            "results": [
                {
                    "cases": [
                        {"case_id": "CC-001", "closed_at": 1000.0, "outcome": "fraud"},
                        {"case_id": "CC-002", "closed_at": 2000.0, "outcome": "fraud"},  # future case
                        {"case_id": "CC-003", "closed_at": 500.0, "outcome": "cleared"},
                    ]
                }
            ]
        }

        with patch("tools.graph_tools.execute_graph_query", return_value=mock_raw_res):
            res = search_similar_cases(None, pattern="card_testing", before_ts=1500.0)
            assert res.get("success") is True
            filtered_cases = res["results"][0]["cases"]
            case_ids = [c["case_id"] for c in filtered_cases]
            assert "CC-001" in case_ids
            assert "CC-003" in case_ids
            assert "CC-002" not in case_ids, "Temporal leakage: Future case CC-002 must not be returned!"


class TestWritebackVerification:
    """Test read-after-write verification on case writeback."""

    def test_verify_case_writeback_success(self):
        mock_conn = MagicMock()
        mock_conn.getVerticesById.return_value = [
            {"v_id": "HHG-TEST-01", "attributes": {"final_verdict": "fraud", "fraud_prob": 0.95}}
        ]

        res = verify_case_writeback(mock_conn, "HHG-TEST-01")
        assert res.get("verified") is True
        assert res.get("source") == "tigergraph"

    def test_verify_case_writeback_failure(self):
        mock_conn = MagicMock()
        mock_conn.getVerticesById.return_value = []
        mock_conn.runInstalledQuery.return_value = []

        res = verify_case_writeback(mock_conn, "HHG-NONEXISTENT")
        assert res.get("verified") is False
        assert "not found" in res.get("reason", "").lower()


class TestMCPBackendEndpoint:
    """Test FastAPI /api/system/mcp and /api/system/status endpoints."""

    def test_system_mcp_endpoint(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        response = client.get("/api/system/mcp")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["connected"] is True
        assert data["server"] == "tigergraph-mcp"
        assert "tool_count" in data
        assert isinstance(data["tool_count"], int)
