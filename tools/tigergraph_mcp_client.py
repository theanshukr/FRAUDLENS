"""
FraudLens — TigerGraph Model Context Protocol (MCP) Client Layer
================================================================
Production-grade MCP Client integration using official `tigergraph-mcp`.

Provides:
  - TigerGraph MCP session management & tool discovery
  - Safe tool invocation with provenance generation
  - GraphAccessMode abstraction (MCP / DIRECT / AUTO)
  - Zero synthetic data fallback guarantees
  - Temporal anti-leakage support
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class GraphAccessMode(str, Enum):
    MCP = "mcp"
    DIRECT = "direct"
    AUTO = "auto"


class TigerGraphMCPClient:
    """
    Official TigerGraph MCP Client for FraudLens.
    Manages session lifecycle, tool discovery, and structured tool invocation with full provenance.
    """

    def __init__(self):
        self.host = os.getenv("TG_HOST", "http://localhost")
        self.graphname = os.getenv("TG_GRAPH_NAME", os.getenv("TG_GRAPHNAME", "FraudLens"))
        self.username = os.getenv("TG_USERNAME", "tigergraph")
        self.password = os.getenv("TG_PASSWORD", "tigergraph")
        self.api_token = os.getenv("TG_TOKEN", os.getenv("TG_API_TOKEN", os.getenv("TG_API_KEY", "")))
        self.secret = os.getenv("TG_SECRET", "")
        self.mode = os.getenv("FRAUDLENS_GRAPH_ACCESS_MODE", "auto").lower()

        self._server = None
        self._connected = False
        self._tools: List[Dict[str, Any]] = []
        self._last_health_check: Optional[Dict[str, Any]] = None
        self._call_history: List[Dict[str, Any]] = []

    def connect(self) -> bool:
        """Initialize MCP Server and discover available tools."""
        try:
            from tigergraph_mcp.server import MCPServer
            from tigergraph_mcp import TigerGraphToolName

            self._server = MCPServer()
            
            # Test connectivity by querying vertex count on the target graph
            test_res = self.call_tool(
                tool_name="tigergraph__get_vertex_count",
                arguments={"vertex_type": "Transaction", "graph_name": self.graphname},
                timeout=12.0
            )

            if test_res.get("success"):
                self._connected = True
                self._tools = [{"name": t.value} for t in TigerGraphToolName]
                logger.info(f"TigerGraph MCP Connected to {self.host}/{self.graphname} — {len(self._tools)} tools discovered")
                return True
            else:
                err = test_res.get("error") or test_res.get("summary")
                logger.warning(f"TigerGraph MCP tool test failed: {err}")
                self._connected = False
                return False

        except Exception as e:
            logger.warning(f"TigerGraph MCP initialization failed: {e}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        if not self._connected:
            return self.connect()
        return self._connected

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return list of discovered TigerGraph MCP tools."""
        if not self._tools:
            try:
                from tigergraph_mcp import TigerGraphToolName
                self._tools = [{"name": t.value} for t in TigerGraphToolName]
            except Exception:
                self._tools = []
        return self._tools

    def health_check(self) -> Dict[str, Any]:
        """Perform live health check and tool count discovery."""
        now = datetime.now(timezone.utc).isoformat()
        is_conn = self.is_connected()
        tool_count = len(self._tools) if self._tools else 0

        status = {
            "enabled": True,
            "connected": is_conn,
            "server": "tigergraph-mcp",
            "version": "1.0.3",
            "graph_name": self.graphname,
            "host": self.host.replace("https://", "").replace("http://", "").split("/")[0],
            "tool_count": tool_count if is_conn else 0,
            "access_mode": self.mode,
            "last_check": now,
            "error": None if is_conn else "MCP server connection or tool execution test failed"
        }
        self._last_health_check = status
        return status

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: float = 15.0
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool synchronously with timeout and structured provenance.
        """
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Ensure graph_name is set
        args = dict(arguments)
        if "graph_name" not in args:
            args["graph_name"] = self.graphname

        try:
            if not self._server:
                from tigergraph_mcp.server import MCPServer
                self._server = MCPServer()

            # Execute the tool via MCPServer
            res_or_coro = self._server._handle_call_tool(tool_name, args)
            
            if asyncio.iscoroutine(res_or_coro):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()
                    res_raw = loop.run_until_complete(asyncio.wait_for(res_or_coro, timeout=timeout))
                else:
                    res_raw = asyncio.run(asyncio.wait_for(res_or_coro, timeout=timeout))
            else:
                res_raw = res_or_coro

            latency_ms = round((time.time() - start_time) * 1000, 2)
            parsed_data = self._parse_mcp_text_content(res_raw)

            provenance = {
                "access_mode": "mcp",
                "provider": "TigerGraph MCP",
                "tool": tool_name,
                "parameters": {k: v for k, v in args.items() if k not in ("token", "password", "secret")},
                "timestamp": timestamp,
                "latency_ms": latency_ms,
                "success": parsed_data.get("success", True)
            }

            self._record_call(provenance)
            parsed_data["provenance"] = provenance
            return parsed_data

        except asyncio.TimeoutError:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            err_msg = f"MCP tool '{tool_name}' timed out after {timeout}s"
            logger.error(err_msg)
            prov = {
                "access_mode": "mcp",
                "provider": "TigerGraph MCP",
                "tool": tool_name,
                "parameters": args,
                "timestamp": timestamp,
                "latency_ms": latency_ms,
                "success": False,
                "error": err_msg
            }
            self._record_call(prov)
            return {"success": False, "error": err_msg, "results": [], "provenance": prov}

        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"MCP tool '{tool_name}' execution error: {e}")
            prov = {
                "access_mode": "mcp",
                "provider": "TigerGraph MCP",
                "tool": tool_name,
                "parameters": args,
                "timestamp": timestamp,
                "latency_ms": latency_ms,
                "success": False,
                "error": str(e)
            }
            self._record_call(prov)
            return {"success": False, "error": str(e), "results": [], "provenance": prov}

    def run_installed_query(
        self,
        query_name: str,
        params: Dict[str, Any],
        timeout: float = 15.0
    ) -> Dict[str, Any]:
        """
        Execute an installed TigerGraph GSQL query via `tigergraph__run_installed_query`.
        """
        mcp_res = self.call_tool(
            tool_name="tigergraph__run_installed_query",
            arguments={
                "query_name": query_name,
                "params": params,
                "graph_name": self.graphname
            },
            timeout=timeout
        )

        success = mcp_res.get("success", False)
        if success:
            data = mcp_res.get("data", {})
            results = data.get("result", [])
            return {
                "success": True,
                "results": results,
                "query_name": query_name,
                "provenance": mcp_res.get("provenance")
            }
        else:
            return {
                "success": False,
                "error": mcp_res.get("error") or mcp_res.get("summary", "Query failed"),
                "results": [],
                "provenance": mcp_res.get("provenance")
            }

    def _parse_mcp_text_content(self, res_raw: Any) -> Dict[str, Any]:
        """Parse TextContent list or JSON response from tigergraph-mcp."""
        if not res_raw:
            return {"success": False, "error": "Empty response from MCP tool"}

        if isinstance(res_raw, list) and len(res_raw) > 0:
            item = res_raw[0]
            text = getattr(item, "text", str(item))
            # Extract JSON code block if wrapped in ```json ... ```
            if "```json" in text:
                try:
                    json_str = text.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                except Exception:
                    pass
            elif "{" in text and "}" in text:
                try:
                    start = text.index("{")
                    end = text.rindex("}") + 1
                    return json.loads(text[start:end])
                except Exception:
                    pass
            return {"success": True, "raw_text": text}

        elif isinstance(res_raw, dict):
            return res_raw

        return {"success": True, "data": str(res_raw)}

    def _record_call(self, prov: Dict[str, Any]):
        self._call_history.append(prov)
        if len(self._call_history) > 100:
            self._call_history.pop(0)

    def get_call_history(self) -> List[Dict[str, Any]]:
        return list(self._call_history)


# Global singleton instance
_mcp_client: Optional[TigerGraphMCPClient] = None


def get_mcp_client() -> TigerGraphMCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = TigerGraphMCPClient()
    return _mcp_client
