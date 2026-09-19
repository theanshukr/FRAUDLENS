# FraudLens 🔍

> **AI-Powered Fraud Investigation & Next-Best Action**  
> Hackathon: TigerGraph × Hacker House Goa 2026

FraudLens is an **AI fraud investigator** — not a chatbot, not a classifier. It autonomously investigates suspicious transactions using TigerGraph's graph intelligence, discovers hidden entity relationships, retrieves similar historical fraud cases, assesses risk with confidence scoring, identifies evidence gaps, requests targeted additional evidence, re-investigates after new evidence arrives, and recommends a policy-aware Next Best Action with human approval when required.

---

## Architecture

```
Frontend (Next.js)
      ↕ SSE streaming
Backend (FastAPI)
      ↕
Agent Orchestrator (LangGraph)
   ├── Planner
   ├── Evidence Collector  ←─→  TigerGraph (via MCP)
   ├── Risk Assessor              ├── Graph Queries (GSQL)
   ├── Evidence Request Manager   └── Vector Store (GraphRAG)
   ├── NBA Engine ←─→ Policy Engine
   ├── Case Manager
   └── Memory Retrieval
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
| Graph DB | TigerGraph (Savanna or CE) |
| Graph Queries | GSQL |
| Graph MCP | tigergraph-mcp |
| Agent Framework | LangGraph |
| LLM | OpenAI GPT-4o |
| Backend | FastAPI + SSE |
| Frontend | Next.js 14 |
| Graph Viz | Cytoscape.js / React Flow |
| Vector Store | TigerGraph Vector Search |

---

## Project Structure

```
fraudlens/
├── docs/          # Documentation
├── data/          # CSVs (gitignored)
├── schema/        # GSQL schema & loading jobs
├── queries/       # GSQL investigation queries
├── agent/         # LangGraph agent modules
├── tools/         # TigerGraph MCP tools
├── policy/        # Policy engine & rules
├── backend/       # FastAPI backend
├── frontend/      # Next.js frontend
├── cases/         # Benchmark answer JSONs (20 cases)
├── scripts/       # Data loading & utility scripts
└── tests/         # Test suite
```

---

## Investigation Phases

| Phase | Goal | Status |
|-------|------|--------|
| Phase 0 | Environment & Data Setup | 🚧 In Progress |
| Phase 1 | TigerGraph Graph Construction | ⏳ Pending |
| Phase 2 | Agent Orchestration Layer | ⏳ Pending |
| Phase 3 | Backend API | ⏳ Pending |
| Phase 4 | Frontend Investigation UI | ⏳ Pending |
| Phase 5 | Integration, Benchmarks & Demo | ⏳ Pending |

---

## Benchmark Cases

All 20 benchmark cases from `case_pack.csv` will be processed and outputs stored in `cases/<case_id>.json`. Run all benchmarks:

```bash
python scripts/run_benchmarks.py
```

---

## License

MIT — Built for TigerGraph × Hacker House Goa 2026 Hackathon
