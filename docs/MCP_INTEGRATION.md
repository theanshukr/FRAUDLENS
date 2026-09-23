# FraudLens — TigerGraph Model Context Protocol (MCP) Integration

This document describes the production-grade **TigerGraph MCP (Model Context Protocol)** integration in FraudLens.

---

## 1. Architecture Overview

FraudLens integrates the official [`tigergraph-mcp`](https://github.com/tigergraph/tigergraph-mcp) package to provide agentic, standardized access to the live TigerGraph Knowledge Graph while keeping deterministic risk and policy evaluation strictly authoritative.

```text
                        FRAUD TRIGGER
                             │
                             ▼
                   FRAUDLENS ORCHESTRATOR
                             │
                             ▼
                    AGENT PLANNER (GSQL)
                             │
                             ▼
                 TIGERGRAPH MCP CLIENT LAYER
                 (tools/tigergraph_mcp_client.py)
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   TIGERGRAPH MCP TOOLS             DIRECT TIGERGRAPH SDK
   (tigergraph-mcp v1.0.3)            (pyTigerGraph Fallback)
            │                                 │
            └────────────────┬────────────────┘
                             ▼
                    TIGERGRAPH CLOUD
             (Live Entity Graph & GSQL Queries)
                             │
                             ▼
                    GRAPH EVIDENCE + PROVENANCE
                             │
                             ▼
                 GRAPHRAG HISTORICAL MEMORY
                 (Semantic Vector Search + RRF)
                             │
                             ▼
                    RISK & UNCERTAINTY
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
             INSUFFICIENT        SUFFICIENT
                    │                 │
             ADDITIONAL               │
             EVIDENCE                 │
                    │                 │
             REASSESSMENT ────────────┘
                             │
                             ▼
                       POLICY ENGINE
                             │
                             ▼
                     NEXT BEST ACTION (NBA)
                             │
                             ▼
                    HUMAN APPROVAL (L1/L2)
                             │
                             ▼
               TIGERGRAPH WRITEBACK VERIFICATION
                   (Read-After-Write Verified)
```

---

## 2. Graph Access Modes (`FRAUDLENS_GRAPH_ACCESS_MODE`)

FraudLens supports three graph access strategies via the environment variable `FRAUDLENS_GRAPH_ACCESS_MODE`:

| Mode | Behavior | Fallback |
| :--- | :--- | :--- |
| `auto` *(default)* | Prefers official TigerGraph MCP tool execution; if MCP encounters an environmental error, transparently falls back to direct `pyTigerGraph`. | Direct SDK |
| `mcp` | Strictly routes all graph tool invocations through `tigergraph-mcp`. Raises explicit error on failure (no mock fallback). | None |
| `direct` | Uses direct `pyTigerGraph` SDK connection for ultra-low-latency high-throughput execution. | None |

---

## 3. Discovered MCP Tools & Mapping

The official `tigergraph-mcp` server exposes **69 tools** categorized into schema, query, vertex, edge, and vector operations. FraudLens maps investigation tasks to specific MCP tools:

| FraudLens Investigation Operation | TigerGraph MCP Tool | GSQL Query / Method |
| :--- | :--- | :--- |
| **Transaction Fetch** | `tigergraph__run_installed_query` | `get_transaction` |
| **Card History (30d)** | `tigergraph__run_installed_query` | `get_card_history` |
| **Card Burst Window** | `tigergraph__run_installed_query` | `get_card_window` |
| **Device Neighbors** | `tigergraph__run_installed_query` | `get_device_neighbors` |
| **Shared Devices** | `tigergraph__run_installed_query` | `find_shared_devices` |
| **Connected Cards** | `tigergraph__run_installed_query` | `find_connected_cards` |
| **Card Testing Detection** | `tigergraph__run_installed_query` | `detect_card_testing` |
| **Velocity Anomaly Detection** | `tigergraph__run_installed_query` | `detect_velocity_anomaly` |
| **Out of Region Usage** | `tigergraph__run_installed_query` | `detect_out_of_region` |
| **Customer Transactions** | `tigergraph__run_installed_query` | `get_customer_transactions` |
| **Similar Case Search** | `tigergraph__run_installed_query` | `search_similar_cases` |
| **Vertex Counts** | `tigergraph__get_vertex_count` | Built-in vertex stats |
| **Neighbor Discovery** | `tigergraph__get_neighbors` | 1-hop traversal |
| **Case Writeback Verification** | `tigergraph__run_installed_query` / `getVerticesById` | `get_case` / `write_case` |

---

## 4. Structured Provenance Tracking

Every MCP tool call produces cryptographic/auditable provenance metadata that flows directly into `case.tool_calls`, `case.evidence`, and the investigation timeline:

```json
{
  "access_mode": "mcp",
  "provider": "TigerGraph MCP",
  "tool": "tigergraph__run_installed_query",
  "query": "get_card_history",
  "parameters": {
    "card_id": "C13487-K1",
    "days": 30,
    "graph_name": "FraudLens"
  },
  "timestamp": "2026-09-24T01:15:46.880003Z",
  "latency_ms": 118.4,
  "success": true
}
```

---

## 5. Temporal Anti-Leakage Guarantees

In all historical case searches (Graph Retrieval, Semantic Vector Search, and Hybrid GraphRAG Fusion), FraudLens enforces **Temporal Anti-Leakage**:

$$\text{Historical Case Timestamp} \le \text{Investigation Cutoff Timestamp} \, (T_{\text{investigation}})$$

Cases created or closed *after* the target transaction occurred are strictly excluded from prior case memory.

---

## 6. Endpoints & Health Check

### Health & MCP Status:
- `GET /api/system/mcp`:
  ```json
  {
    "enabled": true,
    "connected": true,
    "server": "tigergraph-mcp",
    "version": "1.0.3",
    "graph_name": "FraudLens",
    "host": "tg-27bac7ce-36bf-4eef-98fe-34ccaecaf703.tg-2635877100.i.tgcloud.io",
    "tool_count": 69,
    "access_mode": "auto",
    "last_check": "2026-09-24T01:17:32.836154+00:00",
    "error": null
  }
  ```
- `GET /api/system/status`: Reports combined infrastructure state (TigerGraph, MCP, VectorStore, LLM).

---

## 7. Security Standards

1. **Zero Credential Leakage**: `TG_PASSWORD`, `TG_TOKEN`, and `TG_SECRET` are never exposed in API outputs, frontend responses, or tool call provenance.
2. **Deterministic Policy Authority**: MCP serves as a data and tool execution layer. Decision authority remains strictly governed by `RiskAssessor`, `PolicyEngine` (Rules R1–R10), and `NBAEngine`.
