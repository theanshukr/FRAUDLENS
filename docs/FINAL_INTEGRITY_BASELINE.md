# FraudLens — Final Production Integrity Baseline

**Date:** 2026-09-24  
**Target:** Hackathon Final Engineering Hardening Pass (TigerGraph × Hacker House Goa 2026)

---

## 1. Test Suite Baseline
- **Framework:** `pytest 9.1.1` (Python 3.10.0)
- **Total Tests Collected:** 89
- **Passed:** 89
- **Failed / Skipped:** 0 / 0
- **Execution Time:** ~147 seconds
- **Test Modules Covered:**
  - `tests/test_backend.py`: 28 tests (Health, Investigations, SSE, Graph, Approval, Dashboard, Policies, Memory)
  - `tests/test_agent.py`: 22 tests (EvidenceCollector, RiskAssessor, NBAEngine, CaseManager, Orchestrator)
  - `tests/test_graph_tools.py`: 12 tests (Connection, Transactions, Cards, Similarity, Writeback, Expansion)
  - `tests/test_graphrag.py`: 8 tests (TF-IDF Embeddings, VectorStore, Hybrid Fusion, Context Builder, Reasoning)
  - `tests/test_policy_engine.py`: 7 tests (Rules R1–R6, Approval Routes, SAR Filing)
  - `tests/test_tigergraph_mcp.py`: 12 tests (MCP Client, Tool Discovery, Provenance, Fallback, Anti-leakage, Writeback)

---

## 2. Benchmark Baseline
- **Cases Tested:** 20 benchmark cases (`HHG-001` through `HHG-020` in `case_pack.csv`)
- **Verdict Accuracy:** 20/20 (100.0%)
- **Pattern Accuracy:** 19/20 (95.0%) — Note: `HHG-014` exhibited velocity anomaly pattern gap
- **Evidence Loop Execution:** 20/20 (100.0%)
- **TigerGraph Writeback Success:** 20/20 (100.0%)
- **Average Fraud Probability:** 0.993
- **Average Confidence:** 1.00

---

## 3. TigerGraph Connectivity
- **Status:** Connected to TigerGraph Cloud instance (`FraudLens` graph)
- **Graph Schema:** `Transaction`, `Card`, `Customer`, `DeviceProfile`, `BillingRegion`, `EmailDomain`, `ClosedCase`
- **Edges:** `OWNS`, `MADE`, `FROM_DEVICE`, `PURCHASER_EMAIL`, `BILLED_IN`, `CONNECTED_TO`, `ON_CARD`, `INVOLVES`, `SIMILAR_TO`
- **GSQL Queries Installed:** `get_transaction`, `get_card_history`, `get_device_neighbors`, `search_similar_cases`, `detect_card_testing`, `detect_velocity_anomaly`, `find_connected_cards`

---

## 4. MCP Availability
- **Installed Package:** `tigergraph-mcp` (v1.0.3)
- **Status:** Initialized via internal server wrapper
- **Issues Identified:**
  - Direct call to private `_server._handle_call_tool` emitting unawaited coroutine warnings
  - Lack of unified `GraphAccessManager` orchestrating MCP vs Direct access
  - Route handlers in FastAPI directly calling `tg_conn` while frontend reports `ACCESS: MCP`

---

## 5. GraphRAG Availability
- **Historical Cases Indexed:** 5,565 closed cases from `data/closed_cases_history.csv`
- **Vector Store:** Local TF-IDF Vector Store (`data/vector_store/tfidf_model.pkl` + `vector_index.pkl`)
- **Retrieval Pipeline:** Hybrid (TigerGraph structural case search + TF-IDF semantic similarity + Reciprocal Rank Fusion)
- **Issues Identified:**
  - Need vector store `upsert()` alignment verification across indexing/updates/reloads
  - Ensure temporal cutoff (`before_ts`) strictly filters both graph and semantic memory

---

## 6. Known Failures & Integrity Gaps Identified
1. **Private MCP Invocation:** Unawaited coroutine warning on `_server._handle_call_tool`; need standard client/session interface and unified `GraphAccessManager`.
2. **Provenance Discrepancies:** Graph routes (`/api/investigations/{id}/graph`, `/expand`) need strict runtime provenance tracking.
3. **Synthetic Data Fallbacks in Live Path:** 37 occurrences flagged by scanner where fallback defaults (`"US"`, mock IDs) exist in non-test paths.
4. **Temporal Anti-Leakage in GSQL:** GSQL query `search_similar_cases.gsql` must enforce `closed_at <= before_ts` at the database level.
5. **Benchmark Permissiveness:** Benchmark evaluation needs single authoritative validator with strict verdict, pattern, evidence, and NBA checks.
