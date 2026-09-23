# FraudLens — Benchmark Report

**Generated**: 2026-09-24 01:25:26
**Total Cases**: 20
**Verdict Accuracy**: 20/20 (100%)
**Pattern Accuracy**: 19/20 (95%)
**TigerGraph Data Availability**: 20/20 (100%)
**Evidence Loop Demonstrated**: 20/20 (100%)
**TigerGraph Writeback Success**: 20/20 (100%)

---

## Case Results Table

| Case | Trigger | Risk Score | Pattern | Verdict | Fraud Prob | Confidence | Initial NBA | Final NBA | Approval | SAR | TG Data | Loop | Writeback |
|------|---------|-----------|---------|---------|-----------|-----------|-------------|-----------|----------|-----|---------|------|-----------|
| HHG-001 | risk_score | 0.61 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-002 | risk_score | 0.79 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-003 | customer_report | nan | account_takeover | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-004 | customer_report | nan | account_takeover | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-005 | risk_score | 0.54 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-006 | customer_report | nan | account_takeover | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-007 | risk_score | 0.87 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-008 | customer_report | nan | account_takeover | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-009 | customer_report | nan | account_takeover | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-010 | risk_score | 0.90 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-011 | customer_report | nan | account_takeover | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-012 | risk_score | 0.55 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-013 | risk_score | 0.76 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-014 | analyst_request | nan | velocity_anomaly | fraud | 85% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-015 | risk_score | 0.77 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-016 | customer_report | nan | account_takeover | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-017 | risk_score | 0.57 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-018 | customer_report | nan | account_takeover | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-019 | risk_score | 0.90 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |
| HHG-020 | risk_score | 0.52 | card_testing | fraud | 100% | 100% | MONITOR_ACCOUNT, CREATE_CASE | BLOCK_CARD, BLOCK_TRANSACTION | L1 | — | ✅ | ✅ | ✅ |

---

## Aggregate Metrics

- **Verdict Accuracy**: 20/20 (100%)
- **Pattern Detection Accuracy**: 19/20 (95%)
- **Average Fraud Probability**: 0.993
- **Average Confidence**: 1.0
- **Fraud Verdicts**: 20
- **Cleared Verdicts**: 0
- **Uncertain Verdicts**: 0
- **Evidence Loop Demonstrated**: 20/20 (100%)
- **TigerGraph Writeback Success**: 20/20 (100%)
- **NBA includes BLOCK_CARD when fraud**: 20/20 fraud cases

### TigerGraph Queries Used

- `detect_card_testing`
- `detect_new_device_usage`
- `detect_velocity_anomaly`
- `find_connected_cards`
- `get_card_history`
- `get_device_neighbors`
- `get_transaction`
- `search_similar_cases`

---

## Failure Analysis

### HHG-014
- TG_DATA_GAP: 3 evidence items returned $0.00 — transaction not found in TigerGraph


---

## Synthetic Data Leak Scan

⚠️ **33 synthetic data patterns found**:

| File | Line | Pattern | Content |
|------|------|---------|---------|
| `backend\main.py` | 586 | `$482.12` | `- Hardcoded '$482.12' transaction amounts` |
| `backend\main.py` | 587 | `DEV_FP_` | `- DEV_FP_{txn_id[-4:]} generated device IDs` |
| `backend\main.py` | 589 | `REGION_` | `- REGION_{txn_id[-3:]} generated billing region IDs` |
| `backend\main.py` | 588 | `base_txn_num - 2` | `- base_txn_num - 2 / base_txn_num - 1420 arithmetic transactions` |
| `backend\main.py` | 588 | `base_txn_num - 1420` | `- base_txn_num - 2 / base_txn_num - 1420 arithmetic transactions` |
| `backend\main.py` | 590 | `CUST_` | `- CUST_{txn_id[-4:]} generated customer IDs` |
| `backend\main.py` | 619 | `CUST_` | `# Do NOT fabricate CUST_XXXX — leave blank if no real ID` |
| `frontend\src\app\page.tsx` | 70 | `Math.sin` | `// Prepare trend data from REAL cases — no Math.sin/Math.cos synthetic data` |
| `frontend\src\app\page.tsx` | 70 | `Math.cos` | `// Prepare trend data from REAL cases — no Math.sin/Math.cos synthetic data` |
| `agent\evidence_collector.py` | 210 | `REGION_` | `"get_billing_region_cards": lambda: gt.get_billing_region_cards(self.tg_conn, st` |
| `agent\evidence_collector.py` | 716 | `REGION_` | `"results": [{"region_mismatch": True}],` |
| `agent\evidence_collector.py` | 727 | `CC-0141` | `{"case_id": "CC-0141", "pattern": "card_testing", "outcome": "fraud"},` |
| `agent\evidence_collector.py` | 730 | `CC-0141` | `"entity_ids": ["CC-0141", "CC-2671"],` |
| `agent\evidence_collector.py` | 728 | `CC-2671` | `{"case_id": "CC-2671", "pattern": "shared_device_ring", "outcome": "fraud"},` |
| `agent\evidence_collector.py` | 730 | `CC-2671` | `"entity_ids": ["CC-0141", "CC-2671"],` |
| `agent\evidence_collector.py` | 682 | `D_MOCK_001` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 688 | `D_MOCK_001` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 697 | `D_MOCK_001` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 713 | `D_MOCK_001` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 718 | `D_MOCK_001` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\evidence_collector.py` | 723 | `D_MOCK_001` | `"entity_ids": ["CARD_MOCK_001"],` |
| `agent\memory_retrieval.py` | 251 | `CC-0141` | `case_id="CC-0141",` |
| `agent\memory_retrieval.py` | 265 | `CC-2671` | `case_id="CC-2671",` |
| `agent\memory_retrieval.py` | 258 | `D_MOCK_001` | `shared_entities=["D_MOCK_001"],` |
| `agent\memory_retrieval.py` | 272 | `D_MOCK_001` | `shared_entities=["D_MOCK_001", "CARD_B"],` |
| `agent\orchestrator.py` | 610 | `D_MOCK_001` | `card_id="CARD_MOCK_001",` |
| `agent\risk_assessor.py` | 56 | `REGION_` | `"signals": ["detect_out_of_region", "get_billing_region_cards", "geographic_anom` |
| `tools\graph_tools.py` | 282 | `REGION_` | `# Fallback: get_billing_region_cards` |
| `tools\graph_tools.py` | 283 | `REGION_` | `fb_res = get_billing_region_cards(conn, card_id, days=days)` |
| `tools\graph_tools.py` | 285 | `REGION_` | `fb_res["_fallback"] = "get_billing_region_cards"` |
| `tools\graph_tools.py` | 321 | `REGION_` | `def get_billing_region_cards(conn: Optional[tg.TigerGraphConnection], region_cod` |
| `tools\graph_tools.py` | 323 | `REGION_` | `res = execute_graph_query(conn, "get_billing_region_cards", {"region_code": str(` |
| `tools\graph_tools.py` | 328 | `REGION_` | `"entity_ids": [str(region_code)],` |

---

## Evidence Provenance Summary

All evidence items in produced case JSONs must originate from one of:
- `source: graph` — TigerGraph GSQL query result
- `source: document` — case memory / CSV retrieval
- `source: customer` — evidence request response
- `source: external` — external API

### Key Finding: get_transaction Returns Empty for Most Cases

Multiple cases show `'amount $0.00 via . Risk score unavailable'` — this means the
TigerGraph `get_transaction` query returned no rows for the flagged transaction IDs.

**Root Cause**: The transactions.csv loaded has ~50,000 rows out of 590,000 total.
Many benchmark txn_ids (e.g. 3514030) are from months not yet loaded.

**Impact**: Evidence quality is lower than possible. `detect_card_testing` and
`get_card_history` still return results (card vertex exists) but transaction attributes
(amount, channel, risk_score) are missing.

**Recommendation**: Load full transactions.csv (590k rows) to TigerGraph for complete evidence.

---

## Demo Case Recommendation

**Recommended Demo Case**: `HHG-001`
- Trigger: risk_score (risk score: 0.61)
- Pattern: card_testing
- Fraud Probability: 100%
- Evidence Loop: True
- Final NBA: BLOCK_CARD, BLOCK_TRANSACTION, MONITOR_ACCOUNT
- Approval Route: L1