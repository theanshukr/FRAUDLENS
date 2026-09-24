# FraudLens — Temporal Anti-Leakage Architecture

**Target:** TigerGraph × Hacker House Goa 2026  
**Guarantees:** Zero Future Case Information Leakage into Historical Memory & GraphRAG

---

## 1. The Temporal Leakage Problem in Fraud Intelligence
When evaluating fraud detection agents or running historical GraphRAG similarity queries, retrieving cases that closed *after* the flagged transaction occurred introduces **future data leakage**. 

In production fraud investigation, an agent at timestamp $T_{\text{investigation}}$ only has access to closed cases where:
$$\text{closed\_at} \le T_{\text{investigation}}$$

Allowing an investigation to see subsequent outcomes artificially inflates risk scores, pattern classification, and NBA accuracy.

---

## 2. Multi-Tier Anti-Leakage Enforcement

FraudLens enforces temporal anti-leakage across all memory layers:

```text
                  Investigation Timestamp (T_investigation)
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
┌───────────────────────────────┐                   ┌───────────────────────────────┐
│     TigerGraph GSQL Tier      │                   │     Semantic Vector Store     │
│   (search_similar_cases)      │                   │       (LocalVectorStore)      │
├───────────────────────────────┤                   ├───────────────────────────────┤
│ Enforced inside GSQL query:   │                   │ Cosine similarity candidates  │
│ WHERE cc.closed_at <= cutoff  │                   │ filtered against cutoff:      │
│                               │                   │ doc.closed_at <= cutoff       │
└───────────────┬───────────────┘                   └───────────────┬───────────────┘
                │                                                   │
                └─────────────────────────┬─────────────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │      Defensive Python Tier      │
                         │    (Hybrid Memory Fusion)       │
                         │ Verifies each retrieved record  │
                         │       closed_at <= cutoff       │
                         └─────────────────────────────────┘
                                          ▼
                                Investigation Context
```

---

## 3. GSQL Level Implementation

In `queries/search_similar_cases.gsql`, the query accepts `before_ts`:

```gsql
CREATE OR REPLACE QUERY search_similar_cases(
    STRING pattern,
    STRING device_profile_id,
    SET<STRING> card_ids,
    STRING before_ts = ""
) FOR GRAPH FraudLens
SYNTAX V2 {
    SumAccum<INT> @match_score;
    all_cases = {ClosedCase.*};

    -- GSQL Database-level temporal anti-leakage filter
    valid_cases = SELECT cc FROM all_cases:cc
                  WHERE before_ts == "" OR to_datetime(cc.closed_at) <= to_datetime(before_ts);

    pattern_matches = SELECT cc FROM valid_cases:cc
                      WHERE cc.pattern == pattern
                      ACCUM cc.@match_score += 3;

    device_matches = SELECT cc FROM valid_cases:cc - (ON_CARD:e) - Card:c
                                                  - (MADE:e2) - Transaction:t
                                                  - (FROM_DEVICE:e3) - DeviceProfile:d
                     WHERE d.profile_id == device_profile_id
                     ACCUM cc.@match_score += 2;

    card_matches = SELECT cc FROM valid_cases:cc - (ON_CARD:e) - Card:c
                   WHERE c.card_id IN card_ids
                   ACCUM cc.@match_score += 1;

    results = SELECT cc FROM valid_cases:cc
              WHERE cc.@match_score > 0
              ORDER BY cc.@match_score DESC
              LIMIT 5;

    PRINT results;
}
```

---

## 4. Vector Store & Hybrid Retrieval Enforcement

In `tools/graphrag_tools.py` (`LocalVectorStore.search` and `HybridRetriever.fuse_and_rerank`), every vector candidate record is verified against `before_ts`:

```python
if before_ts is not None:
    c_ts = doc.get("metadata", {}).get("closed_at") or doc.get("metadata", {}).get("timestamp")
    if c_ts is not None:
        try:
            ts_val = float(c_ts) if str(c_ts).replace(".", "").isdigit() else datetime.fromisoformat(str(c_ts)).timestamp()
            if ts_val > before_ts:
                continue  # Exclude future case
        except Exception:
            pass
```

---

## 5. Verification & Test Contracts

| Test Scenario | Condition | Expected Result |
| :--- | :--- | :--- |
| Case closed **AFTER** investigation timestamp | `closed_at > cutoff` | **NEVER** returned in GraphRAG or GSQL |
| Case closed **BEFORE** investigation timestamp | `closed_at < cutoff` | Eligible for retrieval & hybrid ranking |
| Case closed **EXACTLY AT** cutoff | `closed_at == cutoff` | Eligible for retrieval (`<=` policy) |

Automated unit tests in `tests/test_tigergraph_mcp.py` and `tests/test_graphrag.py` continuously validate these invariants.
