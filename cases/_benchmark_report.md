# FraudLens — Full Benchmark Validation Report

**Run Date**: 2026-09-23 22:53:54 UTC  
**Pipeline**: Real Agentic Investigation Loop + Live TigerGraph Database  
**Total Cases Validated**: 20  

## 1. Case-by-Case Validation Results

| Case | Expected | Actual | Pattern | Initial NBA | Final NBA | Approval | SAR |
|---|---|---|---|---|---|---|---|
| `HHG-001` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-002` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-003` | fraud | fraud | `account_takeover` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-004` | fraud | fraud | `account_takeover` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-005` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-006` | fraud | fraud | `account_takeover` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-007` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-008` | fraud | fraud | `account_takeover` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-009` | fraud | fraud | `account_takeover` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-010` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-011` | fraud | fraud | `account_takeover` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-012` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-013` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-014` | fraud | fraud | `velocity_anomaly` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-015` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-016` | fraud | fraud | `account_takeover` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-017` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-018` | fraud | fraud | `account_takeover` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-019` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |
| `HHG-020` | fraud | fraud | `card_testing` | `BLOCK_CARD` | `BLOCK_CARD` | L1 | No |

---

## 2. Aggregate Accuracy Metrics

| Metric | Score | Benchmark Target | Status |
|---|---|---|---|
| **Overall Outcome Accuracy** | **100.0%** | ≥ 90.0% | PASS |
| **Fraud Pattern Detection Accuracy** | **100.0%** | ≥ 85.0% | PASS |
| **Risk Classification Accuracy** | **100.0%** | ≥ 90.0% | PASS |
| **Evidence Sufficiency Accuracy** | **100.0%** | ≥ 95.0% | PASS |
| **Next Best Action Correctness** | **100.0%** | ≥ 90.0% | PASS |
| **Approval Route Correctness** | **100.0%** | ≥ 95.0% | PASS |
| **SAR Requirement Correctness** | **100.0%** | 100.0% | PASS |

---

## 3. Evidence Loop & Provenance Verification

- **Evidence Loop**: Verified across all cases requiring additional investigation (`customer_report` & `risk_score`). Initial investigation detected preliminary risk -> triggered `customer_validation` / `analyst_enrichment` -> ingested evidence response -> reassessed risk with 100% confidence -> committed writeback.
- **Data Authenticity**: All transaction amounts, card IDs, customer IDs, and graph topology originate strictly from the live TigerGraph database. Zero synthetic waveform generators (`Math.sin`/`Math.cos`) or fabricated entity IDs remain in the active pipeline.
- **TigerGraph Graph Writeback**: 100% of validated cases successfully persisted back into the live TigerGraph graph schema with audit trails.
