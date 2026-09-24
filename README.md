# FraudLens 🔍

> **AI-Powered Fraud Investigation & Next-Best Action**  
> Hackathon: TigerGraph × Hacker House Goa 2026

FraudLens is an **AI fraud investigator** — not a chatbot, not a classifier. It autonomously investigates suspicious transactions using TigerGraph's graph intelligence, discovers hidden entity relationships, retrieves similar historical fraud cases, assesses risk with confidence scoring, identifies evidence gaps, requests targeted additional evidence, re-investigates after new evidence arrives, and recommends a policy-aware Next Best Action with human approval when required.

---

## Architecture

```text
FraudLens Agent (Autonomous Orchestrator)
    │
    ├────────► TigerGraph MCP Client (tigergraph-mcp v1.0.3)
    │              │
    │              ▼
    │         TigerGraph Cloud (Live Graph Evidence & GSQL)
    │
    ├────────► GraphRAG Hybrid Retrieval
    │              ├── TigerGraph Case Memory (5,565 vertices)
    │              └── Semantic Vector Store (TF-IDF Cosine Similarity)
    │
    ├────────► LLM Reasoning & Synthesis Layer
    │
    ├────────► Deterministic RiskAssessor & PolicyEngine (R1–R10)
    │
    ├────────► Next-Best Action (NBA) Engine
    │
    ├────────► Human-in-the-Loop Approval Workflow (L1/L2)
    │
    └────────► TigerGraph Writeback (Read-After-Write Verified)
```

---

## Quick Start

### Prerequisites

- Python >= 3.11
- Node >= 20
- TigerGraph Savanna account (or Community Edition)
- OpenAI API key

### 1. Clone & Setup Environment

```bash
git clone https://github.com/your-repo/fraudlens.git
cd fraudlens

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your TigerGraph and OpenAI credentials
```

### 3. Load Data into TigerGraph

```bash
# Install schema
python scripts/load_schema.py

# Load CSV data (takes 30-60 min for full dataset)
python scripts/load_data.py

# Or load sample for development (10K rows)
python scripts/load_data.py --sample 10000
```

### 4. Run Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Run Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## Data

| File | Rows | Size | Description |
|------|------|------|-------------|
| `transactions.csv` | ~590,742 | 708 MB | Transaction records with risk scores |
| `identity.csv` | ~144,432 | ~145 MB | Device & identity information |
| `closed_cases_history.csv` | ~5,565 | ~2.7 MB | Historical fraud case memory |
| `case_pack.csv` | 20 | — | Benchmark investigation cases |

> **Note:** CSV files go in `data/` (gitignored). Copy from `docs/databasefiles/`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Graph DB | TigerGraph Cloud (Savanna / CE) |
| Graph Queries | GSQL (Parameterized with Temporal Anti-Leakage) |
| Graph Access | TigerGraph MCP (`tigergraph-mcp` v1.0.3) + Direct `pyTigerGraph` Fallback |
| Vector & Memory | GraphRAG (TigerGraph Case Memory + TF-IDF Semantic Retrieval + RRF) |
| Agent Engine | Autonomous Investigation Orchestrator + Evidence Collector |
| Policy & NBA | Deterministic PolicyEngine (Rules R1–R10) + NBAEngine |
| LLM | Google Gemini / OpenAI (Reasoning & Summarization) |
| Backend | FastAPI + SSE Real-Time Timeline Streaming |
| Frontend | Next.js 14 + TailwindCSS + Lucide Icons + SVG Graph Topology |

---

## Investigation Phases & Status

| Phase | Goal | Status |
|-------|------|--------|
| Phase 0 | Environment & Data Setup | ✅ Complete |
| Phase 1 | TigerGraph Graph Construction (214 txns, 5,565 closed cases) | ✅ Complete |
| Phase 2 | Agent Orchestration & Evidence Loop Layer | ✅ Complete |
| Phase 3 | FastAPI Backend API with Authoritative GraphAccessManager | ✅ Complete |
| Phase 4 | Next.js Investigation UI with Truthful Provenance | ✅ Complete |
| Phase 5 | Strict Benchmark Evaluation (20/20 cases, 100% verdict accuracy) | ✅ Complete |

---

## Benchmark Evaluation

Run strict evaluation across all 20 benchmark cases (`HHG-001` to `HHG-020`):

```bash
python scripts/audit_benchmarks.py
```

- **Exact Verdict Accuracy:** 100.0% (20/20)
- **Exact Pattern Accuracy:** 95.0% (19/20)
- **Evidence Loop Accuracy:** 100.0% (20/20)
- **Next-Best-Action (NBA) Accuracy:** 100.0% (20/20)
- **Approval Route Accuracy:** 100.0% (20/20)
- **Read-After-Write Verification:** 100.0% (20/20)

---

## License

MIT — Built for TigerGraph × Hacker House Goa 2026 Hackathon
