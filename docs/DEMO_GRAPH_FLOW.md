# FraudLens — Live Demo Graph Investigation Flow

Use this flow to demonstrate the live agentic investigation and TigerGraph integration to hackathon judges.

```text
1. TRIGGER
   Flagged Transaction (e.g. HHG-014, Txn 3478561 on Card C13487-K1)
       │
       ▼
2. TIGERGRAPH GRAPH TRAVERSAL
   ├── Fetch transaction seed attributes (Amount $74.96, Channel Web, Yahoo.com)
   ├── Traverse 1-hop: Card C13487-K1, Customer C13487, Device Android 7.0 Chrome
   ├── Traverse 2-hop: Connected Cards & Shared Devices
   └── Execute graph algorithms: detect_velocity_anomaly, search_similar_cases
       │
       ▼
3. HISTORICAL MEMORY RETRIEVAL
   Query 5,565 ClosedCase vertices in TigerGraph to extract precedent patterns & actions
       │
       ▼
4. UNCERTAINTY & EVIDENCE LOOP
   Low initial certainty triggers Policy R2 -> Customer validation request issued
   Customer confirms unauthorized activity -> Risk elevated to CRITICAL (85.3%)
       │
       ▼
5. POLICY & NEXT BEST ACTION (NBA)
   Policy Engine evaluates R1, R2, R5 -> Mandates BLOCK_CARD & WARN_CUSTOMER
   Assigns L1 Analyst Approval Route
       │
       ▼
6. TIGERGRAPH WRITEBACK & READ-AFTER-WRITE VERIFICATION
   Agent writes FraudCase vertex to TigerGraph with verdict, risk score, and audit record
   Executes read-after-write verification to confirm persistence
       │
       ▼
7. INTERACTIVE KNOWLEDGE GRAPH EXPLORATION
   Open Graph View -> Click any vertex -> Click "Expand 1-Hop Neighbors"
   Backend queries TigerGraph live -> Canvas dynamically renders real neighbors
```
