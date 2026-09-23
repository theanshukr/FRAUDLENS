# FraudLens — Production GraphRAG Architecture

## 1. Executive Summary

FraudLens implements **true, production-structured GraphRAG** combining **TigerGraph cloud graph-topological traversals** with **dense semantic vector retrieval**, **weighted bimodal score fusion**, **graph-aware reranking**, and **structured LLM reasoning**.

Unlike naive RAG (which only searches raw text chunks) or graph-only retrieval (which misses semantic nuances in unstructured analyst investigation notes), FraudLens GraphRAG unifies:
1. Multi-hop topological graph structure (devices, cards, rings, merchant velocity, card-testing sequences) from **TigerGraph**.
2. Semantic vector similarity over 5,565 historical closed case investigation narratives.
3. Graph-aware score reranking with direct typology alignment.
4. Structured LLM reasoning synthesizing evidence, precedents, and remaining uncertainties while strictly deferring policy enforcement to the deterministic **PolicyEngine**.

---

## 2. System Architecture

```text
                               ┌─────────────────────────┐
                               │   Fraud Trigger Event   │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │  Investigation Planner  │
                               └────────────┬────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    │                                               │
                    ▼                                               ▼
     ┌─────────────────────────────┐                 ┌─────────────────────────────┐
     │  TigerGraph Cloud Traversal │                 │     Semantic Vector Store   │
     │  - Multi-hop Entity Expand  │                 │  - 5,565 Closed Cases Index │
     │  - Card Testing Detection   │                 │  - Sublinear TF-IDF /       │
     │  - Ring & Velocity Analysis │                 │    Gemini Embeddings        │
     │  - search_similar_cases     │                 │  - Cosine Similarity Search │
     └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                    │                                               │
                    │ Graph Candidates                              │ Semantic Candidates
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │    HybridRetriever          │
                             │  - Score Normalization      │
                             │  - Weighted Bimodal Fusion  │
                             │    (0.60 Graph + 0.40 Sem)  │
                             │  - Graph-Aware Boost        │
                             │  - Provenance Attribution   │
                             └──────────────┬──────────────┘
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │   GraphRAG Context Builder  │
                             │  - Investigation Snapshot   │
                             │  - Multi-Hop Graph Evidence │
                             │  - Historical Analogies     │
                             │  - Topological Signals      │
                             └──────────────┬──────────────┘
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │     LLM Reasoning Layer     │
                             │  - Structured JSON Output   │
                             │  - Observed Evidence vs     │
                             │    Historical Precedents    │
                             │  - Uncertainty Analysis     │
                             └──────────────┬──────────────┘
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │  Deterministic RiskAssessor │
                             └──────────────┬──────────────┘
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │   PolicyEngine (Rules 1-10) │
                             └──────────────┬──────────────┘
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │    NBA Engine & Writeback   │
                             │  - L1/L2 Approval Routes    │
                             │  - TigerGraph Read-After-   │
                             │    Write Verification       │
                             └─────────────────────────────┘
```

---

## 3. Core Components

### 3.1 Embedding Provider (`EmbeddingProvider`)
- **`TFIDFEmbeddingProvider`**: Deterministic 512-dimension sublinear TF-IDF + L2 normalization fitted over all 5,565 closed case narratives. Guarantees 100% offline resilience and zero API quota failures.
- **`GeminiEmbeddingProvider`**: Google Gemini text embedding (`models/embedding-001`) provider when API credentials are configured.
- **`CompositeEmbeddingProvider`**: High-availability hybrid provider that prioritizes Gemini and gracefully falls back to local TF-IDF embeddings.

### 3.2 Persistent Vector Store (`LocalVectorStore`)
- **Storage**: Dense NumPy matrix (`embeddings.npy`) + rich metadata index (`index.json`) stored under `data/vector_store/`.
- **Metadata & Provenance**: Stores `case_id`, `pattern`, `outcome`, `actions_taken`, `exposure_usd`, `analyst_notes`, and provenance source.
- **Search**: Normalized cosine similarity search with optional typology filtering.
- **Idempotency**: Upsert logic prevents vector duplication on repeated indexing runs.

### 3.3 Hybrid Fusion & Graph-Aware Reranking (`HybridRetriever`)
- **Weighted Formula**:
  $$\text{Hybrid Score} = w_{\text{graph}} \cdot S_{\text{graph}} + w_{\text{semantic}} \cdot S_{\text{semantic}}$$
  Default weights: $w_{\text{graph}} = 0.60$, $w_{\text{semantic}} = 0.40$ (configurable via environment variables `GRAPHRAG_GRAPH_WEIGHT` and `GRAPHRAG_SEMANTIC_WEIGHT`).
- **Graph-Aware Boost**: Candidates whose historical pattern matches active graph typology signals receive a 10% boost with explanatory reasoning tags.
- **Provenance Classification**: Explicitly marks candidates as `hybrid`, `graph`, or `semantic`.

### 3.4 GraphRAG Context Builder (`GraphRAGContextBuilder`)
- Constructs structured multi-modal payloads incorporating:
  - Active case metadata & trigger
  - Multi-hop TigerGraph evidence (claims, confidence, query source)
  - Fused historical analog precedents with relevance scores
  - Graph topology signals (ring size, shared device count, velocity, card testing)

### 3.5 Structured LLM Reasoning Layer (`GeminiClient`)
- LLM prompt enforces reasoning strictly from supplied GraphRAG context.
- Returns schema-validated JSON:
  ```json
  {
    "findings": ["string"],
    "supporting_evidence": ["string"],
    "contradicting_evidence": ["string"],
    "historical_context": ["string"],
    "remaining_uncertainty": ["string"],
    "reasoning_summary": "string"
  }
  ```
- **Policy Authority Invariant**: Deterministic `PolicyEngine` and `NBAEngine` retain sole authority over verdicts, actions, approval routes, and SAR filings. LLM outputs provide explainability without overriding policy.

---

## 4. Benchmark & Performance Protection

- **Total Test Suite**: 76/76 unit and integration tests passing.
- **Benchmark Performance**: 20/20 benchmark cases pass with 100% verdict accuracy and verified TigerGraph writeback.
- **Retrieval Latency**:
  - Vector search: < 5ms
  - Hybrid fusion: < 2ms
  - Graph query: 150-250ms
  - End-to-end investigation round: ~2-4s
