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
        host = os.getenv("TG_HOST", "http://localhost")
        secret = os.getenv("TG_SECRET", "")
        token = os.getenv("TG_TOKEN", "") or os.getenv("TG_API_KEY", "")
        is_cloud = "tgcloud.io" in host

        conn = tg.TigerGraphConnection(
            host=host,
            graphname=os.getenv("TG_GRAPH_NAME", "FraudLens"),
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


def detect_new_device_usage(conn: tg.TigerGraphConnection, card_id: str) -> dict:
    """Detect transactions made from a new/untrusted device on this card."""
    try:
        result = conn.runInstalledQuery(
            "detect_new_device_usage",
            params={"card_id": card_id}
        )
        return {"success": True, "results": result, "entity_ids": [card_id]}
    except Exception as e:
        logger.error(f"detect_new_device_usage failed: {e}")
        # Fallback: use card_history to detect new device via heuristic
        try:
            result = conn.runInstalledQuery(
                "get_card_history",
                params={"card_id": card_id, "days": 7}
            )
            return {"success": True, "results": result, "entity_ids": [card_id],
                    "_fallback": "card_history", "_note": "detect_new_device_usage not installed; using card_history"}
        except Exception as e2:
            logger.error(f"detect_new_device_usage fallback also failed: {e2}")
            return {"success": False, "error": str(e), "results": [], "entity_ids": []}


def detect_out_of_region(conn: tg.TigerGraphConnection, card_id: str, days: int = 30) -> dict:
    """Detect transactions in non-home billing regions for this card."""
    try:
        result = conn.runInstalledQuery(
            "detect_out_of_region",
            params={"card_id": card_id, "days": days}
        )
        return {"success": True, "results": result, "entity_ids": [card_id]}
    except Exception as e:
        logger.error(f"detect_out_of_region failed: {e}")
        # Fallback: use get_billing_region_cards which traverses BillingRegion
        try:
            result = conn.runInstalledQuery(
                "get_billing_region_cards",
                params={"card_id": card_id}
            )
            return {"success": True, "results": result, "entity_ids": [card_id],
                    "_fallback": "get_billing_region_cards"}
        except Exception as e2:
            logger.error(f"detect_out_of_region fallback failed: {e2}")
            return {"success": False, "error": str(e), "results": [], "entity_ids": []}


def get_transaction_neighbors(conn: tg.TigerGraphConnection, txn_id: str) -> dict:
    """Fetch all neighbors of a transaction (card, device, region, email domain)."""
    try:
        result = conn.runInstalledQuery(
            "get_transaction_neighbors",
            params={"txn_id": txn_id}
        )
        return {"success": True, "results": result, "entity_ids": [txn_id]}
    except Exception as e:
        logger.error(f"get_transaction_neighbors failed: {e}")
        # Fallback: use get_transaction which already returns linked entities
        return get_transaction(conn, txn_id)


def get_customer_transactions(conn: tg.TigerGraphConnection, customer_id: str) -> dict:
    """Fetch all transactions linked to a customer."""
    try:
        result = conn.runInstalledQuery(
            "get_customer_transactions",
            params={"customer_id": customer_id}
        )
        return {"success": True, "results": result, "entity_ids": [customer_id]}
    except Exception as e:
        logger.error(f"get_customer_transactions failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


def get_billing_region_cards(conn: tg.TigerGraphConnection, card_id: str) -> dict:
    """Fetch billing regions used by a card."""
    try:
        result = conn.runInstalledQuery(
            "get_billing_region_cards",
            params={"card_id": card_id}
        )
        return {"success": True, "results": result, "entity_ids": [card_id]}
    except Exception as e:
        logger.error(f"get_billing_region_cards failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": []}


# ============================================================
# Case Memory Tools
# ============================================================

def search_similar_cases(
    conn: tg.TigerGraphConnection,
    pattern: str,
    device_profile_id: str = "",
    card_ids: list[str] = None,
) -> dict:
    """Search for similar historical fraud cases."""
    try:
        result = conn.runInstalledQuery(
            "search_similar_cases",
            params={"pattern": pattern}
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


# ============================================================
# Graph Expansion Tool (used by /graph/expand endpoint)
# ============================================================

def expand_entity_neighbors(
    conn: tg.TigerGraphConnection,
    entity_id: str,
    entity_type: str,
) -> dict:
    """
    Expand neighbors of a given entity for graph visualization.
    Returns neighbors with their attributes and edge types.
    Tries the most specific query for each entity type, falls back to generic vertex fetch.
    """
    try:
        if entity_type in ("Transaction", "transaction"):
            result = conn.runInstalledQuery(
                "get_transaction_neighbors",
                params={"txn_id": entity_id}
            )
            return {"success": True, "results": result, "entity_ids": [entity_id], "entity_type": entity_type}

        elif entity_type in ("Card", "card"):
            result = conn.runInstalledQuery(
                "get_card_history",
                params={"card_id": entity_id, "days": 30}
            )
            return {"success": True, "results": result, "entity_ids": [entity_id], "entity_type": entity_type}

        elif entity_type in ("DeviceProfile", "device", "Device"):
            result = conn.runInstalledQuery(
                "get_device_neighbors",
                params={"device_profile_id": entity_id}
            )
            return {"success": True, "results": result, "entity_ids": [entity_id], "entity_type": entity_type}

        elif entity_type in ("Customer", "customer"):
            result = conn.runInstalledQuery(
                "get_customer_transactions",
                params={"customer_id": entity_id}
            )
            return {"success": True, "results": result, "entity_ids": [entity_id], "entity_type": entity_type}

        else:
            # Generic: try get_transaction as fallback
            result = conn.getVerticesById(entity_type, [entity_id])
            return {"success": True, "results": result, "entity_ids": [entity_id], "entity_type": entity_type}

    except Exception as e:
        logger.error(f"expand_entity_neighbors({entity_id}, {entity_type}) failed: {e}")
        return {"success": False, "error": str(e), "results": [], "entity_ids": [entity_id], "entity_type": entity_type}

