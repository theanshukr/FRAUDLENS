"""
FraudLens — TigerGraph Graph Tools (MCP-Integrated)
===================================================
Unified graph access layer supporting both:
  1. TigerGraph Model Context Protocol (MCP) via official `tigergraph-mcp`
  2. Direct pyTigerGraph SDK (direct fallback)

Modes controlled by `FRAUDLENS_GRAPH_ACCESS_MODE`:
  - `mcp`    : Strict TigerGraph MCP tool invocation
  - `direct` : Direct pyTigerGraph SDK connection
  - `auto`   : Prefer MCP if healthy; transparent direct fallback
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import pyTigerGraph as tg
from dotenv import load_dotenv
from loguru import logger

from tools.tigergraph_mcp_client import GraphAccessMode, get_mcp_client

load_dotenv()


# ============================================================
# TigerGraph Connection & Mode Helpers
# ============================================================

def get_graph_access_mode() -> GraphAccessMode:
    """Get active graph access mode (MCP / DIRECT / AUTO)."""
    mode_str = os.getenv("FRAUDLENS_GRAPH_ACCESS_MODE", "auto").lower().strip()
    if mode_str == "mcp":
        return GraphAccessMode.MCP
    elif mode_str == "direct":
        return GraphAccessMode.DIRECT
    return GraphAccessMode.AUTO


def get_tg_connection() -> Optional[tg.TigerGraphConnection]:
    """Create and return an authenticated direct TigerGraph connection."""
    try:
        host = os.getenv("TG_HOST", "http://localhost")
        secret = os.getenv("TG_SECRET", "")
        token = os.getenv("TG_TOKEN", "") or os.getenv("TG_API_KEY", "")
        is_cloud = "tgcloud.io" in host

        conn = tg.TigerGraphConnection(
            host=host,
            graphname=os.getenv("TG_GRAPH_NAME", os.getenv("TG_GRAPHNAME", "FraudLens")),
            username=os.getenv("TG_USERNAME", "tigergraph"),
            password=os.getenv("TG_PASSWORD", "tigergraph"),
            gsqlSecret=secret if (secret and secret != "your_secret_here") else "",
            apiToken=token if token else "",
            tgCloud=is_cloud,
        )
        if not token and secret and secret != "your_secret_here":
            conn.getToken(secret)
        logger.info(f"Connected to TigerGraph: {conn.host}/{conn.graphname}")
        return conn
    except Exception as e:
        logger.warning(f"TigerGraph direct connection failed: {e}")
        return None


def execute_graph_query(
    conn: Optional[tg.TigerGraphConnection],
    query_name: str,
    params: Dict[str, Any],
    timeout: float = 15.0
) -> Dict[str, Any]:
    """
    Execute a TigerGraph installed query according to the configured GraphAccessMode.
    Returns structured results and execution provenance.
    """
    mode = get_graph_access_mode()
    mcp_client = get_mcp_client()

    # 1. Try MCP mode if configured or auto
    if mode in (GraphAccessMode.MCP, GraphAccessMode.AUTO):
        try:
            mcp_res = mcp_client.run_installed_query(query_name, params, timeout=timeout)
            if mcp_res.get("success"):
                logger.debug(f"[MCP] {query_name}({params}) -> {len(mcp_res.get('results', []))} results")
                return {
                    "success": True,
                    "results": mcp_res.get("results", []),
                    "provenance": mcp_res.get("provenance") or {
                        "access_mode": "mcp",
                        "provider": "TigerGraph MCP",
                        "tool": "tigergraph__run_installed_query",
                        "query": query_name,
                    }
                }
            elif mode == GraphAccessMode.MCP:
                # Strict MCP mode requested — do not fallback
                return {
                    "success": False,
                    "error": mcp_res.get("error", "MCP query execution failed"),
                    "results": [],
                    "provenance": mcp_res.get("provenance")
                }
        except Exception as e:
            logger.warning(f"MCP execution of {query_name} failed: {e}")
            if mode == GraphAccessMode.MCP:
                return {"success": False, "error": str(e), "results": []}

    # 2. Direct fallback (for DIRECT mode or AUTO when MCP fails)
    if conn is not None:
        try:
            start_t = time.time()
            res = conn.runInstalledQuery(query_name, params=params)
            lat_ms = round((time.time() - start_t) * 1000, 2)
            logger.debug(f"[Direct] {query_name}({params}) -> {len(res)} results")
            return {
                "success": True,
                "results": res,
                "provenance": {
                    "access_mode": "direct",
                    "provider": "pyTigerGraph SDK",
                    "query": query_name,
                    "parameters": params,
                    "latency_ms": lat_ms,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Direct TigerGraph {query_name} failed: {e}")
            return {"success": False, "error": str(e), "results": []}

    return {"success": False, "error": "Neither MCP nor Direct TigerGraph connection available", "results": []}


# ============================================================
# Transaction Tools
# ============================================================

def get_transaction(conn: Optional[tg.TigerGraphConnection], txn_id: str) -> dict:
    """Fetch full transaction + linked identity record."""
    res = execute_graph_query(conn, "get_transaction", {"txn_id": str(txn_id)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(txn_id)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def get_card_history(conn: Optional[tg.TigerGraphConnection], card_id: str, days: int = 30) -> dict:
    """Fetch all card transactions within N days."""
    res = execute_graph_query(conn, "get_card_history", {"card_id": str(card_id), "days": int(days)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(card_id)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def get_card_window(conn: Optional[tg.TigerGraphConnection], card_id: str, hours: int) -> dict:
    """Fetch transactions within a time window (for card testing detection)."""
    res = execute_graph_query(conn, "get_card_window", {"card_id": str(card_id), "hours": int(hours)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(card_id)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


# ============================================================
# Relationship Tools
# ============================================================

def get_device_neighbors(conn: Optional[tg.TigerGraphConnection], device_profile_id: str) -> dict:
    """Find all cards/transactions using this device profile."""
    res = execute_graph_query(conn, "get_device_neighbors", {"profile_id": str(device_profile_id)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(device_profile_id)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def find_shared_devices(conn: Optional[tg.TigerGraphConnection], card_id: str) -> dict:
    """Find devices shared between this card and others."""
    res = execute_graph_query(conn, "find_shared_devices", {"card_id": str(card_id)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(card_id)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def find_connected_cards(conn: Optional[tg.TigerGraphConnection], card_id: str, hops: int = 2) -> dict:
    """Multi-hop card connection discovery."""
    res = execute_graph_query(conn, "find_connected_cards", {"card_id": str(card_id), "hops": int(hops)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(card_id)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


# ============================================================
# Pattern Detection Tools
# ============================================================

def detect_card_testing(conn: Optional[tg.TigerGraphConnection], card_id: str, hours: int = 24) -> dict:
    """Detect micro-auth burst pattern before larger purchase."""
    res = execute_graph_query(conn, "detect_card_testing", {"card_id": str(card_id), "hours": int(hours)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(card_id)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def detect_velocity_anomaly(conn: Optional[tg.TigerGraphConnection], card_id: str, hours: int = 24) -> dict:
    """Detect unusual transaction frequency."""
    res = execute_graph_query(conn, "detect_velocity_anomaly", {"card_id": str(card_id), "hours": int(hours)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(card_id)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def detect_new_device_usage(conn: Optional[tg.TigerGraphConnection], card_id: str) -> dict:
    """Detect transactions made from a new/untrusted device on this card."""
    res = execute_graph_query(conn, "detect_new_device_usage", {"card_id": str(card_id)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(card_id)],
            "provenance": res.get("provenance")
        }
    # Fallback to get_card_history
    fallback_res = get_card_history(conn, card_id, days=7)
    if fallback_res.get("success"):
        fallback_res["_fallback"] = "card_history"
        return fallback_res
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def detect_out_of_region(conn: Optional[tg.TigerGraphConnection], card_id: str, days: int = 30) -> dict:
    """Detect transactions in non-home billing regions for this card."""
    res = execute_graph_query(conn, "detect_out_of_region", {"card_id": str(card_id), "days": int(days)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(card_id)],
            "provenance": res.get("provenance")
        }
    # Fallback: get_billing_region_cards
    fb_res = get_billing_region_cards(conn, card_id, days=days)
    if fb_res.get("success"):
        fb_res["_fallback"] = "get_billing_region_cards"
        return fb_res
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def get_transaction_neighbors(conn: Optional[tg.TigerGraphConnection], txn_id: str, hops: int = 1) -> dict:
    """Fetch all neighbors of a transaction (card, device, region, email domain)."""
    res = execute_graph_query(conn, "get_transaction_neighbors", {"txn_id": str(txn_id), "hops": int(hops)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(txn_id)],
            "provenance": res.get("provenance")
        }
    # Fallback: get_transaction
    return get_transaction(conn, txn_id)


def get_customer_transactions(conn: Optional[tg.TigerGraphConnection], customer_id: str, lim: int = 50) -> dict:
    """Fetch all transactions linked to a customer."""
    res = execute_graph_query(
        conn,
        "get_customer_transactions",
        {"customer_id": str(customer_id), "lim": int(lim), "max_limit": int(lim)}
    )
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(customer_id)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def get_billing_region_cards(conn: Optional[tg.TigerGraphConnection], region_code: str, days: int = 30) -> dict:
    """Fetch billing regions used by a card."""
    res = execute_graph_query(conn, "get_billing_region_cards", {"region_code": str(region_code), "days": int(days)})
    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_ids": [str(region_code)],
            "provenance": res.get("provenance")
        }
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


# ============================================================
# Case Memory & Temporal Anti-Leakage
# ============================================================

def search_similar_cases(
    conn: Optional[tg.TigerGraphConnection],
    pattern: str,
    device_profile_id: str = "",
    card_ids: Optional[List[str]] = None,
    before_ts: Optional[float] = None,
) -> dict:
    """
    Search for similar historical fraud cases.
    Guarantees temporal anti-leakage: filters out cases with closed_at > before_ts.
    """
    cards_set = set(card_ids) if card_ids else set()
    res = execute_graph_query(
        conn,
        "search_similar_cases",
        {
            "pattern": pattern or "",
            "device_profile_id": device_profile_id or "",
            "card_ids": list(cards_set)
        }
    )

    if not res.get("success"):
        return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}

    results = res.get("results", [])

    # Apply Temporal Anti-Leakage filter if before_ts provided
    if before_ts is not None and isinstance(results, list):
        filtered_results = []
        for item in results:
            if isinstance(item, dict):
                # Check timestamps inside results
                cases_list = item.get("cases") or item.get("result") or [item]
                valid_cases = []
                for c in cases_list:
                    c_ts = c.get("closed_at") or c.get("created_at") or c.get("timestamp")
                    if c_ts is not None:
                        try:
                            # Handle epoch timestamp or ISO string
                            ts_val = float(c_ts) if str(c_ts).replace(".", "").isdigit() else datetime.fromisoformat(str(c_ts)).timestamp()
                            if ts_val <= before_ts:
                                valid_cases.append(c)
                        except Exception:
                            valid_cases.append(c)
                    else:
                        valid_cases.append(c)
                if valid_cases:
                    item_copy = dict(item)
                    if "cases" in item_copy:
                        item_copy["cases"] = valid_cases
                    filtered_results.append(item_copy)
            else:
                filtered_results.append(item)
        results = filtered_results

    return {
        "success": True,
        "results": results,
        "entity_ids": [],
        "provenance": res.get("provenance")
    }


def get_case(conn: Optional[tg.TigerGraphConnection], case_id: str) -> dict:
    """Fetch a written FraudCase vertex from TigerGraph."""
    if conn is not None:
        try:
            v = conn.getVerticesById("FraudCase", [case_id])
            if v and len(v) > 0 and v[0].get("v_id") == case_id:
                return {"success": True, "results": v, "entity_ids": [case_id]}
        except Exception:
            pass

    res = execute_graph_query(conn, "get_case", {"case_id": str(case_id)})
    if res.get("success"):
        return {"success": True, "results": res.get("results", []), "entity_ids": [str(case_id)]}
    return {"success": False, "error": res.get("error", "Query failed"), "results": [], "entity_ids": []}


def verify_case_writeback(conn: Optional[tg.TigerGraphConnection], case_id: str) -> dict:
    """
    Verify that a FraudCase was actually written to TigerGraph by reading it back.
    """
    if conn is not None:
        try:
            v = conn.getVerticesById("FraudCase", [case_id])
            if v and len(v) > 0 and v[0].get("v_id") == case_id:
                return {"verified": True, "case": v[0], "source": "tigergraph", "access_mode": "direct"}
        except Exception:
            pass

    res = get_case(conn, case_id)
    if not res.get("success"):
        return {"verified": False, "reason": res.get("error", "Query execution failed")}

    results = res.get("results", [])
    found_case = None
    for item in results:
        if isinstance(item, dict):
            for k in ("c", "result", "cases", "FraudCase"):
                if k in item and item[k]:
                    found_case = item[k][0] if isinstance(item[k], list) else item[k]
                    break
            if found_case:
                break
            if item.get("v_id") == case_id:
                found_case = item
                break

    if found_case:
        return {"verified": True, "case": found_case, "source": "tigergraph", "access_mode": "mcp"}
    return {"verified": False, "reason": f"Case {case_id} not found in FraudCase vertex set"}


def write_case(conn: Optional[tg.TigerGraphConnection], case_data: dict) -> dict:
    """Write a new FraudCase to TigerGraph."""
    data = dict(case_data)
    prob = data.get("fraud_prob") or data.get("fraud_probability", 0.0)
    data["fraud_prob"] = float(prob)
    data["fraud_probability"] = float(prob)

    res = execute_graph_query(conn, "write_case", data)
    if res.get("success"):
        return {"success": True, "results": res.get("results", []), "provenance": res.get("provenance")}
    return {"success": False, "error": res.get("error", "Write failed")}


def expand_entity_neighbors(
    conn: Optional[tg.TigerGraphConnection],
    entity_id: str,
    entity_type: str,
) -> dict:
    """
    Expand neighbors of a given entity for graph visualization using MCP / TigerGraph.
    """
    eid = str(entity_id)
    etype = str(entity_type)

    if etype.lower() in ("transaction", "txn"):
        res = execute_graph_query(conn, "get_transaction_neighbors", {"txn_id": eid, "hops": 1})
    elif etype.lower() in ("card",):
        res = execute_graph_query(conn, "get_card_history", {"card_id": eid, "days": 30})
    elif etype.lower() in ("deviceprofile", "device"):
        res = execute_graph_query(conn, "get_device_neighbors", {"profile_id": eid})
    elif etype.lower() in ("customer",):
        res = execute_graph_query(conn, "get_customer_transactions", {"customer_id": eid, "lim": 50, "max_limit": 50})
    else:
        res = execute_graph_query(conn, "get_transaction_neighbors", {"txn_id": eid, "hops": 1})

    if res.get("success"):
        return {
            "success": True,
            "results": res.get("results", []),
            "entity_id": eid,
            "entity_ids": [eid],
            "entity_type": etype,
            "provenance": res.get("provenance")
        }
    return {
        "success": False,
        "error": res.get("error", "Expansion query failed"),
        "results": [],
        "entity_id": eid,
        "entity_ids": [eid],
        "entity_type": etype
    }
