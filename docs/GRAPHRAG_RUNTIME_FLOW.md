# FraudLens — GraphRAG Runtime Flow

## Step-by-Step Investigation Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant T as Trigger / CaseManager
    participant P as Investigation Planner
    participant EC as EvidenceCollector (TigerGraph)
    participant MR as MemoryRetrieval (GraphRAG)
    participant TG as TigerGraph Cloud (GSQL)
    participant VS as VectorStore (Local Index)
    participant HF as HybridRetriever (Fusion)
    participant LLM as LLM Reasoning Layer
    participant RA as RiskAssessor
    participant PE as PolicyEngine & NBA

    T->>P: Initialize case & build investigation plan
    loop Investigation Round (1..3)
        P->>EC: Collect multi-hop graph evidence
        EC->>TG: Query card history, device neighbors, rings
        TG-->>EC: Graph nodes & edges
        EC->>MR: Retrieve historical precedents
        par Graph Retrieval
            MR->>TG: search_similar_cases(pattern, device, cards)
            TG-->>MR: Topological historical cases
        and Vector Semantic Retrieval
            MR->>VS: semantic_search_cases(query_text)
            VS-->>MR: Semantic candidate cases
        end
        MR->>HF: fuse_and_rerank(graph_cases, semantic_cases)
        HF-->>MR: Top 5 Hybrid cases with provenance
        MR-->>EC: Fused historical precedents
        EC->>LLM: Pass GraphRAG Context (evidence + precedents + graph signals)
        LLM-->>EC: Structured JSON Reasoning (findings, uncertainty)
        EC->>RA: Assess risk & evidence sufficiency
        alt Evidence Sufficient
            RA->>PE: Evaluate Policies R1-R10
            PE->>PE: Determine NBA & Approval Route
            PE->>TG: Writeback case & read-after-write verify
        else Evidence Insufficient
            RA->>P: Request targeted customer/analyst evidence
        end
    end
```

---

## Provenance Breakdown Example

| Historical Case | Retrieval Mode | Graph Relevance | Semantic Relevance | Hybrid Relevance | Source |
|---|---|---|---|---|---|
| **CC-0141** | `hybrid` | 0.850 | 0.942 | **0.887** | `Hybrid: TigerGraph + VectorStore` |
| **CC-2671** | `hybrid` | 0.720 | 0.895 | **0.790** | `Hybrid: TigerGraph + VectorStore` |
| **CC-3312** | `semantic` | 0.000 | 0.794 | **0.595** | `VectorStore / analyst_notes embedding` |
| **CC-1528** | `semantic` | 0.000 | 0.793 | **0.595** | `VectorStore / analyst_notes embedding` |
| **CC-2823** | `semantic` | 0.000 | 0.791 | **0.593** | `VectorStore / analyst_notes embedding` |
