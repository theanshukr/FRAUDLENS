# FraudLens — Final TigerGraph Knowledge Graph Audit Report

## 1. Status Matrix

| Component | Status | Verification Details |
|---|---|---|
| **TigerGraph Connection** | **LIVE** | Connected to Cloud Graph (`FraudLens`) via `pyTigerGraph` |
| **GSQL Contracts** | **100% PASS** | Parameter names & types verified against installed queries |
| **Graph Expansion** | **REAL** | Powered by `/api/investigations/{id}/graph/expand` -> `expand_entity_neighbors` |
| **Synthetic Graph Data** | **0 Remaining** | Zero `D_FINGERPRINT_*`, `CARD_LINK_*`, or local mock nodes |
| **Historical Case Memory** | **REAL** | 5,565 `ClosedCase` vertices queried via `search_similar_cases` |
| **TigerGraph Writeback** | **VERIFIED** | Read-after-write verification confirms `FraudCase` vertices on graph |
| **Pytest Test Suite** | **68/68 PASS** | Complete unit and integration test coverage |
| **Benchmark Accuracy** | **20/20 (100%)** | All 20 benchmark cases validated against live TigerGraph |

---

## 2. Live Graph Statistics in TigerGraph Cloud

- **Vertices**:
  - `ClosedCase`: 5,565 historical records
  - `DeviceProfile`: 4,379 device fingerprints
  - `Transaction`: Real benchmark and historical transactions
  - `Card`: Real card identifiers
  - `Customer`: Real customer records
  - `FraudCase`: Live-persisted investigation cases
  - `BillingRegion`: Real geographic billing regions
  - `EmailDomain`: Real email domains
- **Edges**:
  - `MADE`, `OWNS`, `FROM_DEVICE`, `PURCHASER_EMAIL`, `BILLED_IN`, `SHARED_DEVICE`, `CONNECTED_TO`, `INVOLVES`, `ON_CARD`, `TARGETS`, `INVESTIGATED_IN`

---

## 3. Provenance & UI Integrity

All nodes, edges, amounts, timestamps, and relationship topologies presented in the UI originate directly from:
1. Live TigerGraph GSQL query outputs
2. Agent evidence items extracted from live graph queries
3. Verified read-after-write investigation records
