# FraudLens — Authoritative Final Benchmark Report

**Timestamp**: 2026-09-24 17:20:33
**Evaluation Framework**: Strict Deterministic Validator (Zero Permissive Overrides)
**Benchmark Dataset**: `cases/case_pack.csv` (20 Golden Cases)

---

## Summary Metrics

- **Total Cases Evaluated**: 20
- **Exact Verdict Accuracy**: 20/20 (100.0%)
- **Exact Pattern Accuracy**: 19/20 (95.0%)
- **Evidence Loop Execution**: 20/20 (100.0%)
- **TigerGraph Writeback Verified**: 20/20 (100.0%)
- **NBA Accuracy**: 20/20 (100.0%)
- **Average Fraud Probability**: 0.993
- **Average Confidence**: 1.000
- **Average Investigation Latency**: 420 ms
- **Active Synthetic Data Leaks in Live Path**: 25

---

## Detailed Case Results

| Case ID | Expected Verdict | Actual Verdict | Pattern Match | Init Prob | Final Prob | Final Conf | NBA | Route | Loop | Writeback | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `HHG-001` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-002` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-003` | fraud | ✅ fraud | ✅ account_takeover | 0.74 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-004` | fraud | ✅ fraud | ✅ account_takeover | 0.74 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-005` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-006` | fraud | ✅ fraud | ✅ account_takeover | 0.74 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-007` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-008` | fraud | ✅ fraud | ✅ account_takeover | 0.74 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-009` | fraud | ✅ fraud | ✅ account_takeover | 0.74 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-010` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-011` | fraud | ✅ fraud | ✅ account_takeover | 0.74 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-012` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-013` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-014` | fraud | ✅ fraud | ⚠️ velocity_anomaly | 0.45 | 0.85 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **REVIEW** |
| `HHG-015` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-016` | fraud | ✅ fraud | ✅ account_takeover | 0.74 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-017` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-018` | fraud | ✅ fraud | ✅ account_takeover | 0.74 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-019` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |
| `HHG-020` | fraud | ✅ fraud | ✅ card_testing | 0.73 | 1.00 | 1.00 | BLOCK_CARD, BLOCK_TRANSACTION | L1 | ✅ | ✅ | **PASS** |

---

## Evidence & Memory Provenance

- **Graph Retrieval**: Live TigerGraph Cloud GSQL queries (`get_transaction`, `get_card_history`, `get_device_neighbors`, `find_connected_cards`, `detect_card_testing`, `search_similar_cases`).
- **Graph Access Layer**: `GraphAccessManager` in MCP / Direct modes with runtime call accounting.
- **Memory Retrieval**: Hybrid GraphRAG over 5,565 closed historical cases with temporal anti-leakage cutoff.
- **Policy Engine**: Deterministic rules R1–R10 driving human approval routes (L1/L2) and SAR filing.

---

## Synthetic Data Audit Findings

⚠️ 25 synthetic occurrences found:

| File | Line | Pattern | Snippet |
| :--- | :--- | :--- | :--- |
| `agent\evidence_collector.py` | 682 | `CARD_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 688 | `CARD_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 697 | `CARD_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 713 | `CARD_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 718 | `CARD_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 723 | `CARD_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 682 | `D_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 688 | `D_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 697 | `D_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 713 | `D_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 718 | `D_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 723 | `D_MOCK` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 673 | `T_MOCK` | `"entity_ids": ["T_MOCK_001"],` |
| `agent\evidence_collector.py` | 708 | `T_MOCK` | `"entity_ids": ["T_MOCK_000"],` |
| `agent\evidence_collector.py` | 727 | `CC-0141` | `{"case_id": "CC-0141", "pattern": "card_testing", "outcome": "fraud"},` |
| `agent\evidence_collector.py` | 730 | `CC-0141` | `"entity_ids": ["CC-0141", "CC-2671"],` |
| `agent\evidence_collector.py` | 728 | `CC-2671` | `{"case_id": "CC-2671", "pattern": "shared_device_ring", "outcome": "fraud"},` |
| `agent\evidence_collector.py` | 730 | `CC-2671` | `"entity_ids": ["CC-0141", "CC-2671"],` |
| `agent\memory_retrieval.py` | 258 | `D_MOCK` | `shared_entities=["D_MOCK_001"],` |
| `agent\memory_retrieval.py` | 272 | `D_MOCK` | `shared_entities=["D_MOCK_001", "CARD_B"],` |
| `agent\memory_retrieval.py` | 251 | `CC-0141` | `case_id="CC-0141",` |
| `agent\memory_retrieval.py` | 265 | `CC-2671` | `case_id="CC-2671",` |
| `agent\orchestrator.py` | 610 | `CARD_MOCK` | `card_id="CARD_MOCK_001",` |
| `agent\orchestrator.py` | 610 | `D_MOCK` | `card_id="CARD_MOCK_001",` |
| `agent\orchestrator.py` | 608 | `T_MOCK` | `txn_id="T_MOCK_001",` |