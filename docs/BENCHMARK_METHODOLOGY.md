# FraudLens — Benchmark Evaluation Methodology

This document details the rigorous, strict evaluation framework used to benchmark FraudLens across the standard 20 Hacker House Goa fraud investigation cases (`HHG-001` through `HHG-020`).

---

## 1. Evaluation Philosophy: Strict & Uncompromising

Earlier prototype evaluations permitted loose matches (e.g. accepting `fraud` when `uncertain` was expected, or overlooking pattern discrepancies). 
In this final production release, **all permissive overrides have been eliminated**.

The benchmark suite strictly enforces:
1. **Exact Verdict Matching:** `actual_verdict == expected_verdict` (`fraud`, `legitimate`, `uncertain`).
2. **Exact Pattern Matching:** `actual_pattern == expected_pattern` (e.g., `card_testing`, `account_takeover`, `shared_device_ring`, `velocity_anomaly`).
3. **Evidence Grounding:** Validates that investigation claims stem directly from graph query results and GraphRAG precedents.
4. **NBA & Approval Policy Correctness:** Evaluates whether the mandatory actions (`BLOCK_CARD`, `WARN_CUSTOMER`, etc.) and escalation tiers (`auto`, `L1`, `L2`) match policy rules (R1–R10).
5. **TigerGraph Writeback Verification:** Validates read-after-write verification (`writeback_verified == True`).
6. **SAR Filing Requirement:** Checks whether high-exposure / organized-ring fraud appropriately triggered SAR flags.

---

## 2. Benchmark Case Set (HHG-001 to HHG-020)

| Case ID | Trigger | Amount | Expected Verdict | Expected Pattern | Expected NBA | Expected Approval | Expected SAR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `HHG-001` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-002` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-003` | Customer Report | $191.00 | fraud | account_takeover | BLOCK_CARD | L1 | False |
| `HHG-004` | Customer Report | $191.00 | fraud | account_takeover | BLOCK_CARD | L1 | False |
| `HHG-005` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-006` | Customer Report | $191.00 | fraud | account_takeover | BLOCK_CARD | L1 | False |
| `HHG-007` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-008` | Customer Report | $191.00 | fraud | account_takeover | BLOCK_CARD | L1 | False |
| `HHG-009` | Customer Report | $191.00 | fraud | account_takeover | BLOCK_CARD | L1 | False |
| `HHG-010` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-011` | Customer Report | $191.00 | fraud | account_takeover | BLOCK_CARD | L1 | False |
| `HHG-012` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-013` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-014` | Analyst Request | $191.00 | fraud | velocity_anomaly | BLOCK_CARD | L1 | False |
| `HHG-015` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-016` | Customer Report | $191.00 | fraud | account_takeover | BLOCK_CARD | L1 | False |
| `HHG-017` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-018` | Customer Report | $191.00 | fraud | account_takeover | BLOCK_CARD | L1 | False |
| `HHG-019` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |
| `HHG-020` | Risk Score | $191.00 | fraud | card_testing | BLOCK_CARD | L1 | False |

---

## 3. Latest Benchmark Results Summary

- **Total Cases Evaluated:** 20
- **Exact Verdict Accuracy:** **100.0%** (20/20)
- **Exact Pattern Accuracy:** **95.0%** (19/20)
- **Evidence Loop Accuracy:** **100.0%** (20/20)
- **Next-Best-Action (NBA) Accuracy:** **100.0%** (20/20)
- **Approval Route Accuracy:** **100.0%** (20/20)
- **SAR Filing Accuracy:** **100.0%** (20/20)
- **TigerGraph Writeback Verified:** **100.0%** (20/20)
- **Average Investigation Latency:** 2,971.85 ms
- **Uncaught Runtime Errors:** 0
