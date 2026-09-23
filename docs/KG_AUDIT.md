# FraudLens — TigerGraph Knowledge Graph Audit Report

## 1. Schema & Graph Topology Overview

- **Graph Name**: `FraudLens`
- **Host**: `https://tg-27bac7ce-36bf-4eef-98fe-34ccaecaf703.tg-2635877100.i.tgcloud.io/`
- **Driver**: `pyTigerGraph` (v1.6+)

### Vertices:
| Vertex Type | Primary ID | Key Attributes |
|---|---|---|
| `Transaction` | `transaction_id` (STRING) | `ts`, `amount`, `channel`, `product_cd`, `risk_score`, `is_fraud`, `p_emaildomain` |
| `Card` | `card_id` (STRING) | `card1`..`card6`, `network`, `card_type` |
| `Customer` | `customer_id` (STRING) | `email_domain`, `home_region`, `first_seen`, `last_seen` |
| `DeviceProfile` | `profile_id` (STRING) | `device_type`, `device_info`, `os`, `browser`, `screen`, `proxy_flag` |
| `EmailDomain` | `domain` (STRING) | — |
| `BillingRegion` | `region_code` (STRING) | `country_code` |
| `ClosedCase` | `case_id` (STRING) | `outcome`, `pattern`, `exposure_usd`, `actions_taken`, `analyst_notes`, `opened_at`, `closed_at` |
| `FraudCase` | `case_id` (STRING) | `trigger_type`, `status`, `fraud_probability`, `confidence`, `risk_level`, `pattern`, `final_verdict`, `case_json` |

### Edges:
| Edge Type | Source | Target | Directed | Attributes |
|---|---|---|---|---|
| `OWNS` | `Customer` | `Card` | Yes | `since` |
| `MADE` | `Card` | `Transaction` | Yes | `ts` |
| `FROM_DEVICE` | `Transaction` | `DeviceProfile` | Yes | `is_new_device` |
| `PURCHASER_EMAIL` | `Transaction` | `EmailDomain` | Yes | — |
| `BILLED_IN` | `Transaction` | `BillingRegion` | Yes | — |
| `NEXT` | `Transaction` | `Transaction` | Yes | `gap_seconds` |
| `INVOLVES` | `ClosedCase` | `Transaction` | Yes | `role` |
| `ON_CARD` | `ClosedCase` | `Card` | Yes | — |
| `CONNECTED_TO` | `ClosedCase` | `Card` | Yes | `connection_type` |
| `SHARED_DEVICE` | `Card` | `Card` | No | `device_profile_id`, `first_seen` |
| `INVESTIGATED_IN` | `Transaction` | `FraudCase` | Yes | — |
| `TARGETS` | `FraudCase` | `Card` | Yes | — |
| `CASE_INVOLVES_CUSTOMER` | `FraudCase` | `Customer` | Yes | — |

---

## 2. GSQL Queries & Python Contract Mapping

| GSQL Query | GSQL Signature | Python Function (`tools/graph_tools.py`) | Parameter Mapping |
|---|---|---|---|
| `get_transaction` | `(STRING txn_id)` | `get_transaction(conn, txn_id)` | `txn_id` |
| `get_card_history` | `(STRING card_id, INT days)` | `get_card_history(conn, card_id, days)` | `card_id`, `days` |
| `get_card_window` | `(STRING card_id, INT hours)` | `get_card_window(conn, card_id, hours)` | `card_id`, `hours` |
| `get_device_neighbors` | `(STRING profile_id)` | `get_device_neighbors(conn, device_profile_id)` | `profile_id: device_profile_id` |
| `find_shared_devices` | `(STRING card_id)` | `find_shared_devices(conn, card_id)` | `card_id` |
| `find_connected_cards` | `(STRING card_id, INT hops)` | `find_connected_cards(conn, card_id, hops)` | `card_id`, `hops` |
| `detect_card_testing` | `(STRING card_id, INT hours)` | `detect_card_testing(conn, card_id, hours)` | `card_id`, `hours` |
| `detect_velocity_anomaly` | `(STRING card_id, INT hours)` | `detect_velocity_anomaly(conn, card_id, hours)` | `card_id`, `hours` |
| `detect_new_device_usage` | `(STRING card_id)` | `detect_new_device_usage(conn, card_id)` | `card_id` |
| `detect_out_of_region` | `(STRING card_id, INT days)` | `detect_out_of_region(conn, card_id, days)` | `card_id`, `days` |
| `get_transaction_neighbors`| `(STRING txn_id, INT hops)` | `get_transaction_neighbors(conn, txn_id, hops)` | `txn_id`, `hops` |
| `get_customer_transactions`| `(STRING customer_id, INT lim)` | `get_customer_transactions(conn, customer_id, lim)` | `customer_id`, `lim`, `max_limit` |
| `get_billing_region_cards` | `(STRING region_code, INT days)` | `get_billing_region_cards(conn, region_code, days)`| `region_code`, `days` |
| `search_similar_cases` | `(STRING pattern, STRING device_profile_id, SET<STRING> card_ids)` | `search_similar_cases(conn, pattern, device_profile_id, card_ids)` | `pattern`, `device_profile_id`, `card_ids` |
| `get_case` | `(STRING case_id)` | `get_case(conn, case_id)` | `case_id` |
| `write_case` | `(STRING case_id, ..., DOUBLE fraud_prob, ...)` | `write_case(conn, case_data)` | All case fields + `fraud_prob` |

---

## 3. Defects Identified & Systematically Resolved

1. **Parameter Name Mismatch on `get_device_neighbors`**: GSQL expected `profile_id` while Python passed `device_profile_id`, causing runtime errors. Fixed to pass `profile_id`.
2. **Missing `hops` on `get_transaction_neighbors`**: GSQL required `(STRING txn_id, INT hops)`. Fixed to pass `hops=1`.
3. **Parameter Mismatch on `get_customer_transactions`**: GSQL required limit parameter (`max_limit`/`lim`). Fixed to pass `lim=50, max_limit=50`.
4. **Synthetic Node Generation in Frontend Graph (`D_FINGERPRINT_*`, `CARD_LINK_*`)**: The UI previously generated simulated nodes on neighbor expansion. Replaced entirely with a live API call to `/api/investigations/{case_id}/graph/expand` backed by TigerGraph.
5. **Read-After-Write Verification**: Implemented `verify_case_writeback(conn, case_id)` using direct vertex reads (`conn.getVerticesById("FraudCase", [case_id])`) to ensure real persistence before setting `written_to_graph = True`.
6. **Benchmark Data Ingestion**: Loaded all 20 benchmark transactions, cards, customers, devices, and relational edges into TigerGraph cloud.
