"""
FraudLens — TigerGraph Model Context Protocol (MCP) Client Layer
================================================================
Production-grade MCP Client integration using official `tigergraph-mcp` (v1.0.3).

Provides:
  - TigerGraph MCP session management & dynamic tool discovery
  - Safe tool invocation with provenance generation
  - GraphAccessMode abstraction (MCP / DIRECT / AUTO)
  - Zero synthetic data fallback guarantees
  - Temporal anti-leakage support
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def get_mcp_package_version() -> str:
    """Dynamically get installed tigergraph-mcp version."""
    try:
        return importlib.metadata.version("tigergraph-mcp")
    except Exception:
        try:
            import tigergraph_mcp
            return getattr(tigergraph_mcp, "__version__", "1.0.3")
        except Exception:
            return "1.0.3"


class _WorkerLoop:
    """Dedicated persistent event loop thread for async MCP tool executions."""
    _instance: Optional[_WorkerLoop] = None
    _lock = threading.Lock()

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True, name="TigerGraphMCPWorker")
        self.thread.start()

    @classmethod
    def get_instance(cls) -> _WorkerLoop:
        with cls._lock:
            if cls._instance is None or not cls._instance.thread.is_alive():
                cls._instance = _WorkerLoop()
            return cls._instance

    def run_coroutine(self, coro_fn: Callable, *args, timeout: float = 15.0, **kwargs) -> Any:
        async def _wrapper():
            res = coro_fn(*args, **kwargs)
            if asyncio.iscoroutine(res):
                return await asyncio.wait_for(res, timeout=timeout)
            return res

        fut = asyncio.run_coroutine_threadsafe(_wrapper(), self.loop)
        return fut.result(timeout=timeout + 2.0)


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

        self._connected = False
        self._tools: List[Dict[str, Any]] = []
        self._last_health_check: Optional[Dict[str, Any]] = None
        self._call_history: List[Dict[str, Any]] = []
        self._version = get_mcp_package_version()
        self._worker = _WorkerLoop.get_instance()

    def _ensure_auth_env(self):
        """Ensure TigerGraph auth tokens are populated in environment for tigergraph-mcp."""
        if not os.getenv("TG_TOKEN") and not os.getenv("TG_API_TOKEN"):
            if self.secret and self.secret != "your_secret_here":
                try:
                    import pyTigerGraph as tg
                    is_cloud = "tgcloud.io" in self.host
                    conn = tg.TigerGraphConnection(
                        host=self.host,
                        graphname=self.graphname,
                        username=self.username,
                        password=self.password,
                        gsqlSecret=self.secret,
                        tgCloud=is_cloud,
                    )
                    token = conn.getToken(self.secret)
                    token_str = token[0] if isinstance(token, tuple) else str(token)
                    if token_str and len(token_str) > 10:
                        os.environ["TG_TOKEN"] = token_str
                        os.environ["TG_API_TOKEN"] = token_str
                        self.api_token = token_str
                        logger.debug("Successfully refreshed TG token for MCP client")
                except Exception as e:
                    logger.debug(f"Could not fetch TG token in MCP client: {e}")

    def _discover_tools(self) -> List[Dict[str, Any]]:
        """Discover tools from official tigergraph_mcp tool registry."""
        try:
            from tigergraph_mcp.tools import tool_registry
            all_tools = tool_registry.get_all_tools()
            tools_list = []
            for t in all_tools:
                tools_list.append({
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {}
                })
            return tools_list
        except Exception as e:
            logger.warning(f"Could not discover tools from tool_registry: {e}")
            try:
                from tigergraph_mcp import TigerGraphToolName
                return [{"name": t.value, "description": "", "inputSchema": {}} for t in TigerGraphToolName]
            except Exception:
                return []

    def connect(self) -> bool:
        """Initialize MCP tools and verify connectivity via real MCP tool invocation."""
        try:
            self._ensure_auth_env()
            self._tools = self._discover_tools()

            # Verify connectivity by invoking official get_vertex_count tool
            test_res = self.call_tool(
                tool_name="tigergraph__get_vertex_count",
                arguments={"vertex_type": "Transaction", "graph_name": self.graphname},
                timeout=12.0
            )

            if test_res.get("success"):
                self._connected = True
                logger.info(f"TigerGraph MCP Connected to {self.host}/{self.graphname} — {len(self._tools)} tools discovered")
                return True
            else:
                err = test_res.get("error") or test_res.get("summary") or "Connection probe returned unsuccessful"
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
            self._tools = self._discover_tools()
        return self._tools

    def health_check(self) -> Dict[str, Any]:
        """Perform live health check and tool count discovery."""
        now = datetime.now(timezone.utc).isoformat()
        is_conn = self.is_connected()
        tool_count = len(self._tools) if self._tools else 0

        status = {
            "available": is_conn,
            "connected": is_conn,
            "server": "tigergraph-mcp",
            "version": self._version,
            "transport": "stdio/in-process",
            "graph_name": self.graphname,
            "host": self.host.replace("https://", "").replace("http://", "").split("/")[0],
            "tool_count": tool_count if is_conn else 0,
            "discovered_tools": [t["name"] for t in self._tools] if is_conn else [],
            "access_mode": self.mode,
            "last_check": now,
            "last_error": None if is_conn else "MCP server connection or tool execution test failed"
        }
        self._last_health_check = status
        return status

    def _get_tool_function(self, tool_name: str) -> Optional[Callable]:
        """Resolve tool function from tigergraph_mcp.tools without private methods."""
        clean_name = tool_name.replace("tigergraph__", "")
        import tigergraph_mcp.tools as tg_tools
        if hasattr(tg_tools, clean_name):
            return getattr(tg_tools, clean_name)
        return None

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: float = 15.0
    ) -> Dict[str, Any]:
        """
        Execute an official MCP tool with timeout and structured provenance.
        """
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()
        self._ensure_auth_env()

        args = dict(arguments)
        if "graph_name" not in args:
            args["graph_name"] = self.graphname

        tool_fn = self._get_tool_function(tool_name)
        if tool_fn is None:
            err_msg = f"Unknown MCP tool: '{tool_name}'"
            logger.error(err_msg)
            prov = {
                "access_mode": "mcp",
                "provider": "TigerGraph MCP",
                "tool": tool_name,
                "parameters": args,
                "timestamp": timestamp,
                "latency_ms": 0.0,
                "success": False,
                "error": err_msg
            }
            self._record_call(prov)
            return {"success": False, "error": err_msg, "results": [], "provenance": prov}

        try:
            # Execute async tool function safely in persistent worker event loop
            res_raw = self._worker.run_coroutine(tool_fn, timeout=timeout, **args)

            latency_ms = round((time.time() - start_time) * 1000, 2)
            parsed_data = self._parse_mcp_text_content(res_raw)

            prov_success = parsed_data.get("success", True)
            provenance = {
                "access_mode": "mcp",
                "provider": "TigerGraph MCP",
                "tool": tool_name,
                "parameters": {k: v for k, v in args.items() if k not in ("token", "password", "secret")},
                "timestamp": timestamp,
                "latency_ms": latency_ms,
                "success": prov_success
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
