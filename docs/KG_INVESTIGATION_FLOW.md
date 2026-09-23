# FraudLens — Graph Investigation & Reasoning Flow

## Investigation Lifecycle

Every investigation in FraudLens follows a deterministic, graph-first agentic workflow that leverages TigerGraph as the core source of truth.

```text
Flagged Transaction Trigger (risk_score / customer_report / analyst_request)
    │
    ▼
[Planner: Dynamic Step Generation]
    │
    ▼
[TigerGraph Query Execution: EvidenceCollector]
    ├─► get_transaction (1-hop seed traversal)
    ├─► get_card_history (30-day baseline velocity)
    ├─► get_device_neighbors (shared device fingerprints)
    ├─► find_connected_cards (2-hop syndicate ring detection)
    ├─► detect_card_testing / detect_velocity_anomaly (typology matching)
    └─► search_similar_cases (topological case memory)
    │
    ▼
[Evidence Synthesis & Signal Extraction]
    │
    ▼
[Bayesian Risk & Uncertainty Assessment]
    │
    ├─► If High Confidence & Sufficient ────► Proceed to Policy Engine
    │
    └─► If Insufficient / Human Trigger ────► [Evidence Request Manager]
                                                   │
                                                   ├─► Customer Validation / Step-Up Auth
                                                   ├─► Ingest Evidence Response
                                                   └─► Re-Assessment Loop
    │
    ▼
[Policy Engine & NBA Evaluation]
    ├─► Rule Evaluation (R1–R10)
    ├─► Action Ranking (BLOCK_CARD, MONITOR_ACCOUNT, etc.)
    ├─► Approval Route (L1 / L2 / Senior Analyst)
    └─► FinCEN SAR Determination (Exposure > $10k / Organized Ring)
    │
    ▼
[TigerGraph Closed-Loop Writeback & Verification]
    ├─► write_case (insert FraudCase vertex & edges)
    └─► verify_case_writeback (read-after-write confirmation)
    │
    ▼
[Interactive UI Visualization & Graph Expansion]
    └─► Real-time SVG/Canvas rendering + Live 1-Hop Neighbor Expansion
```
