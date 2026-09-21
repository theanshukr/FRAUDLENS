"""
FraudLens     TigerGraph Graph Tools
=====================================
MCP tool wrappers for all TigerGraph GSQL queries.

These tools are exposed to the agent via the TigerGraph MCP bridge.
Each function corresponds to one GSQL installed query.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import pyTigerGraph as tg
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# TigerGraph Connection
# ============================================================

def get_tg_connection() -> Optional[tg.TigerGraphConnection]:
    """Create and return an authenticated TigerGraph connection."""
    try:
        conn = tg.TigerGraphConnection(
            host=os.getenv("TG_HOST", "http://localhost"),
            graphname=os.getenv("TG_GRAPH_NAME", "FraudLens"),
            username=os.getenv("TG_USERNAME", "tigergraph"),
            password=os.getenv("TG_PASSWORD", "tigergraph"),
        )
        secret = os.getenv("TG_SECRET", "")
        if secret and secret != "your_secret_here":
            conn.getToken(secret)
        logger.info(f"Connected to TigerGraph: {conn.host}/{conn.graphname}")
        return conn
    except Exception as e:
        logger.warning(f"TigerGraph connection failed (this is expected if no DB is configured): {e}")
        return None


# ============================================================
# Transaction Tools
# ============================================================

def get_transaction(conn: tg.TigerGraphConnection, txn_id: str) -> dict:
    """Fetch full transaction + linked identity record."""
    try:
        result = conn.runInstalledQuery("get_transaction", params={"txn_id": txn_id})
        logger.debug(f"get_transaction({txn_id})     {len(result)} results")
        return {"success": True, "results": result, "entity_ids": [txn_id]}
    except Exception as e:
        logger.error(f"get_transaction failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


def get_card_history(conn: tg.TigerGraphConnection, card_id: str, days: int = 30) -> dict:
    """Fetch all card transactions within N days."""
    try:
        result = conn.runInstalledQuery("get_card_history", params={"card_id": card_id, "days": days})
        return {"success": True, "results": result, "entity_ids": [card_id]}
    except Exception as e:
        logger.error(f"get_card_history failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


def get_card_window(conn: tg.TigerGraphConnection, card_id: str, hours: int) -> dict:
    """Fetch transactions within a time window (for card testing detection)."""
    try:
        result = conn.runInstalledQuery("get_card_window", params={"card_id": card_id, "hours": hours})
        return {"success": True, "results": result, "entity_ids": [card_id]}
    except Exception as e:
        logger.error(f"get_card_window failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


# ============================================================
# Relationship Tools
# ============================================================

def get_device_neighbors(conn: tg.TigerGraphConnection, device_profile_id: str) -> dict:
    """Find all cards/transactions using this device profile."""
    try:
        result = conn.runInstalledQuery(
            "get_device_neighbors",
            params={"device_profile_id": device_profile_id}
        )
        return {"success": True, "results": result, "entity_ids": [device_profile_id]}
    except Exception as e:
        logger.error(f"get_device_neighbors failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


def find_shared_devices(conn: tg.TigerGraphConnection, card_id: str) -> dict:
    """Find devices shared between this card and others."""
    try:
        result = conn.runInstalledQuery("find_shared_devices", params={"card_id": card_id})
        return {"success": True, "results": result, "entity_ids": [card_id]}
    except Exception as e:
        logger.error(f"find_shared_devices failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


def find_connected_cards(conn: tg.TigerGraphConnection, card_id: str, hops: int = 2) -> dict:
    """Multi-hop card connection discovery."""
    try:
        result = conn.runInstalledQuery(
            "find_connected_cards",
            params={"card_id": card_id, "hops": hops}
        )
        return {"success": True, "results": result, "entity_ids": [card_id]}
    except Exception as e:
        logger.error(f"find_connected_cards failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


# ============================================================
# Pattern Detection Tools
# ============================================================

def detect_card_testing(conn: tg.TigerGraphConnection, card_id: str, hours: int = 24) -> dict:
    """Detect micro-auth burst pattern before larger purchase."""
    try:
        result = conn.runInstalledQuery(
            "detect_card_testing",
            params={"card_id": card_id, "hours": hours}
        )
        return {"success": True, "results": result, "entity_ids": [card_id]}
    except Exception as e:
        logger.error(f"detect_card_testing failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


def detect_velocity_anomaly(conn: tg.TigerGraphConnection, card_id: str, hours: int = 24) -> dict:
    """Detect unusual transaction frequency."""
    try:
        result = conn.runInstalledQuery(
            "detect_velocity_anomaly",
            params={"card_id": card_id, "hours": hours}
        )
        return {"success": True, "results": result, "entity_ids": [card_id]}
    except Exception as e:
        logger.error(f"detect_velocity_anomaly failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


# ============================================================
# Case Memory Tools
# ============================================================

def search_similar_cases(
    conn: tg.TigerGraphConnection,
    pattern: str,
    device_profile_id: str,
    card_ids: list[str],
) -> dict:
    """Search for similar historical fraud cases."""
    try:
        result = conn.runInstalledQuery(
            "search_similar_cases",
            params={
                "pattern": pattern,
                "device_profile_id": device_profile_id,
                "card_ids": card_ids,
            }
        )
        return {"success": True, "results": result, "entity_ids": []}
    except Exception as e:
        logger.error(f"search_similar_cases failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


def write_case(conn: tg.TigerGraphConnection, case_data: dict) -> dict:
    """Write a new FraudCase to TigerGraph."""
    try:
        result = conn.runInstalledQuery("write_case", params=case_data)
        return {"success": True, "results": result}
    except Exception as e:
        logger.error(f"write_case failed: {e}")
        return {"success": False, "error": str(e)}
