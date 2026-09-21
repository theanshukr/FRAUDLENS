# FraudLens — Development Phases

> **Version:** 1.1 *(Updated: 2026-09-21 — Phase 0 progress review)*  
> **Project:** FraudLens — AI Agentic Fraud Investigation Platform  
> **Hackathon:** TigerGraph × Hacker House Goa 2026  
> **Total Estimated Duration:** 8–10 days (hackathon sprint)

---

## 📊 Current Status

| Phase | Status | Notes |
|---|---|---|
| **Phase 0** — Environment & Data Setup | 🟡 In Progress | Core structure done; TigerGraph connection pending |
| **Phase 1** — Graph Construction | ⬜ Not Started | Schema + loading jobs drafted; needs live DB |
| **Phase 2** — Agent Orchestration | ⬜ Not Started | Skeleton files exist; core logic not yet complete |
| **Phase 3** — Backend API | ⬜ Not Started | FastAPI `main.py` scaffolded |
| **Phase 4** — Frontend UI | ⬜ Not Started | — |
| **Phase 5** — Integration & Demo | ⬜ Not Started | — |

> **Last reviewed from branch:** `kanav-backend-updates` (commit `b47af67`, Kanav-prog)

---

## Overview

This document defines the complete development roadmap for FraudLens, organized into six sequential phases. Each phase has a clear goal, deliverables, acceptance criteria, and dependencies. Follow phases in order; P0 items within each phase are blockers for the next phase.

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
  Setup     Graph     Agent    Backend   Frontend   Demo
```

---

## Phase 0 — Environment & Data Setup

**Goal:** Working development environment with data loaded and TigerGraph accessible.  
**Duration:** Day 1  
**Priority:** P0 (Blocker for everything else)

### 0.1 Infrastructure Setup

- [ ] Create TigerGraph Savanna workspace at [savanna.tgcloud.io](https://savanna.tgcloud.io) (or install Community Edition)
  - Enable auto-stop and auto-start on Savanna
  - Note workspace URL, graph name, credentials
- [x] Set up Python virtual environment (`venv` or `conda`) ✅
- [x] Initialize Git repository with `.gitignore` ✅
- [x] Create project folder structure (see below) ✅
- [x] Set up `.env` file with all secrets (never committed) ✅ (`.env.example` committed, `.env` gitignored)

### 0.2 Project Folder Structure

```
fraudlens/
├── docs/                        # All documentation (this folder)
├── data/                        # Raw CSVs (gitignored)
│   ├── transactions.csv
│   ├── identity.csv
│   ├── closed_cases_history.csv
│   └── case_pack.csv
├── schema/                      # TigerGraph schema and loading jobs
│   ├── schema.gsql
│   └── loading_jobs.gsql
├── queries/                     # GSQL investigation queries
│   ├── get_transaction.gsql
│   ├── get_card_history.gsql
│   ├── get_device_neighbors.gsql
│   ├── find_shared_devices.gsql
│   ├── find_connected_cards.gsql
│   ├── search_similar_cases.gsql
│   └── ...
├── agent/                       # Agent orchestration layer
│   ├── orchestrator.py
│   ├── planner.py
│   ├── evidence_collector.py
│   ├── risk_assessor.py
│   ├── evidence_request_manager.py
│   ├── nba_engine.py
│   ├── case_manager.py
│   └── memory_retrieval.py
├── tools/                       # TigerGraph MCP tools
│   ├── graph_tools.py
│   ├── graphrag_tools.py
│   └── policy_tools.py
├── policy/                      # Policy engine
│   ├── policy_engine.py
│   └── rules.py
├── backend/                     # FastAPI backend
│   ├── main.py
│   ├── routes/
│   └── models/
├── frontend/                    # React/Next.js frontend
│   ├── src/
│   └── public/
├── cases/                       # Output answer files (20 benchmark cases)
├── scripts/                     # Data loading, utility scripts
│   ├── load_schema.py
│   ├── load_data.py
│   └── run_benchmarks.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

### 0.3 Data Acquisition & Validation

- [ ] Download dataset from Google Drive (HHGOA_IEEE folder)
  - `transactions.csv` (~708 MB, ~590,742 rows)
  - `identity.csv` (~144,432 rows)
  - `closed_cases_history.csv` (~5,565 rows)
  - `case_pack.csv` (20 benchmark cases)
- [x] **Dataset samples added** (`dataset_sample/` folder with 100-row samples of each CSV + full `case_pack.csv` with all 20 HHG-001→HHG-020 cases) ✅ — by Kanav
- [ ] Validate CSV headers match the dataset README column definitions
- [ ] Run basic row count checks on full dataset; confirm no truncation
- [ ] Profile key columns: `risk_score`, `customer_id`, `channel`, `card1`–`card6`, `DeviceInfo`, `addr1`

### 0.4 Dependencies

```
# Core
python >= 3.11
pyTigerGraph
langchain / langgraph         # Agent framework
openai                        # LLM
fastapi + uvicorn             # Backend
pydantic                      # Data validation

# Data
pandas
numpy

# Frontend
node >= 20
next.js / react               # Or Vite

# Utilities
python-dotenv
httpx
loguru
```

### Phase 0 Acceptance Criteria

- [ ] TigerGraph instance is accessible via pyTigerGraph
- [ ] All 4 CSVs downloaded and row-count validated
- [x] Git repo initialized with proper `.gitignore` ✅
- [x] `.env.example` committed; `.env` gitignored ✅

### Phase 0 — Work Completed (by branch `kanav-backend-updates`)

> The following items were completed by teammate **Kanav** in commit `b47af67`.
> ⚠️ **Pending merge review:** Two issues must be fixed before merging:
> 1. Unicode characters (`—`, `→`, `↑`, `↓`, box-drawing) were corrupted to spaces across 10+ files — needs a fix pass.
> 2. `tests/test_policy_engine.py` was accidentally emptied — tests need to be restored.

- [x] `dataset_sample/` folder added with 100-row CSVs and all 20 `case_pack.csv` benchmark cases ✅
- [x] `schema/schema.gsql` — `FraudCase` vertex enriched with `trigger_text`, `flagged_txn_id`, `card_id`, `customer_id`, `risk_score` fields ✅
- [x] `schema/loading_jobs.gsql` — column name fixes (`ts`, `channel`, `risk_score`), added `Customer` vertex + `OWNS` edge loading, added `load_case_pack` job ✅
- [x] `tools/graph_tools.py` — defensive `Optional` TigerGraph connection (no crash when DB not configured) ✅
- [x] Backend `main.py` FastAPI skeleton scaffolded ✅
- [x] All `agent/`, `policy/`, `scripts/`, `tools/` skeleton modules created ✅

---

## Phase 1 — TigerGraph Graph Construction

**Goal:** Production-ready knowledge graph with all entities, relationships, and GSQL investigation queries.  
**Duration:** Days 1–2  
**Priority:** P0

### 1.1 Schema Design

Define and install the graph schema in GSQL. Start with the suggested schema and extend as needed.

**Vertices:**

| Vertex | Key Fields | Source |
|---|---|---|
| `Customer` | `customer_id`, `email_domain`, `home_region` | Derived from transactions |
| `Card` | `card_id`, `card1`–`card6`, `network`, `type` | transactions.csv |
| `Transaction` | `TransactionID`, `ts`, `amount`, `channel`, `risk_score`, `product_cd` | transactions.csv |
| `DeviceProfile` | `profile_id` (hash of DeviceInfo+OS+browser+screen), `device_type`, `device_info`, `os`, `browser`, `screen`, `proxy_flag` | identity.csv |
| `EmailDomain` | `domain` | transactions.csv (`P_emaildomain`) |
| `BillingRegion` | `region_code`, `country_code` | transactions.csv (`addr1`, `addr2`) |
| `ClosedCase` | `case_id`, `outcome`, `pattern`, `exposure_usd`, `actions_taken`, `opened_at`, `closed_at` | closed_cases_history.csv |
| `FraudCase` | `case_id` (new cases written by agent) | Agent output |

**Edges:**

| Edge | From → To | Attributes |
|---|---|---|
| `OWNS` | Customer → Card | `since` |
| `MADE` | Card → Transaction | `ts` |
| `FROM_DEVICE` | Transaction → DeviceProfile | `is_new_device` |
| `PURCHASER_EMAIL` | Transaction → EmailDomain | — |
| `BILLED_IN` | Transaction → BillingRegion | — |
| `NEXT` | Transaction → Transaction | `gap_seconds` |
| `INVOLVES` | ClosedCase → Transaction | `role` |
| `ON_CARD` | ClosedCase → Card | — |
| `CONNECTED_TO` | ClosedCase → Card | `connection_type` |
| `SHARED_DEVICE` | Card → Card | `device_profile_id`, `first_seen` |
| `INVESTIGATED_IN` | Transaction → FraudCase | — |

### 1.2 GSQL Schema & Loading Jobs

- [ ] Write `schema/schema.gsql` — full vertex and edge definitions
- [ ] Write `schema/loading_jobs.gsql` — loading jobs for all 4 CSVs
- [ ] Run schema installation against TigerGraph instance
- [ ] Run loading jobs (expect 30–60 min for full transactions.csv load)
- [ ] Validate vertex and edge counts post-load

### 1.3 GSQL Investigation Queries

Write and install these GSQL queries. Each should return structured JSON.

**Transaction Queries:**
- [ ] `get_transaction(txn_id)` — full transaction + identity record
- [ ] `get_card_history(card_id, days)` — all transactions for a card in N days
- [ ] `get_card_window(card_id, hours)` — transactions within a time window (for card testing detection)
- [ ] `get_customer_transactions(customer_id, limit)` — full transaction history

**Relationship Queries:**
- [ ] `get_device_neighbors(device_profile_id)` — all cards/transactions using this device
- [ ] `find_shared_devices(card_id)` — devices shared between this card and others
- [ ] `find_connected_cards(card_id, hops)` — multi-hop card connections
- [ ] `get_billing_region_cards(region_code, days)` — all cards active in region during window
- [ ] `get_transaction_neighbors(txn_id, hops)` — entity neighborhood of a transaction

**Pattern Detection Queries:**
- [ ] `detect_card_testing(card_id, hours)` — micro-auth burst before larger purchase
- [ ] `detect_out_of_region(card_id, days)` — transactions in non-home billing regions
- [ ] `detect_velocity_anomaly(card_id, hours)` — unusual transaction frequency
- [ ] `detect_new_device_usage(card_id)` — transactions from devices marked `New`

**Case Memory Queries:**
- [ ] `search_similar_cases(pattern, device_profile_id, card_ids)` — retrieve similar closed cases
- [ ] `get_case(case_id)` — retrieve a case record
- [ ] `write_case(case_data)` — write a new case to the graph
- [ ] `write_evidence(case_id, evidence)` — append evidence to a case

**Graph Algorithm Queries:**
- [ ] Weakly Connected Components on Card–Device–Card subgraph (identify fraud rings)
- [ ] PageRank on Transaction nodes (identify high-centrality suspicious transactions)
- [ ] Shortest path between two suspicious cards (shared chain discovery)

### 1.4 Vector Store Setup (GraphRAG)

- [ ] Enable TigerGraph vector search on the instance
- [ ] Embed and load into vector store:
  - Fraud policy text (from dataset README)
  - 5 known fraud pattern descriptions
  - Closed case narratives (`analyst_notes` field)
  - Regulatory references (FinCEN SAR guidance, FFIEC red flags)
- [ ] Test vector similarity search: query "card testing sequence" → returns relevant policy/case chunks

### 1.5 TigerGraph MCP Setup

- [ ] Install TigerGraph MCP: `pip install tigergraph-mcp`
- [ ] Configure MCP connection to TigerGraph instance
- [ ] Expose all GSQL queries as MCP tools
- [ ] Validate: agent can call `get_transaction` via MCP and receive structured JSON

### Phase 1 Acceptance Criteria

- [ ] All vertices and edges loaded; row counts match source CSVs
- [ ] All 15+ GSQL queries installed and returning correct results
- [ ] Manual investigation of 1 benchmark case by hand using graph queries
- [ ] Vector search returns relevant policy/case chunks for test queries
- [ ] MCP bridge works: Python agent can call graph tools

---

## Phase 2 — Agent Orchestration Layer

**Goal:** Working investigation agent that can execute the full investigation loop end-to-end, including re-investigation after new evidence.  
**Duration:** Days 2–4  
**Priority:** P0

### 2.1 Agent Framework Setup

Choose and configure the agent framework. Recommended: **LangGraph** (explicit state machine, good for investigation loops).

- [ ] Install LangGraph (`pip install langgraph`)
- [ ] Configure LLM (OpenAI GPT-4o or equivalent)
- [ ] Define agent state schema (all fields from the case record JSON)
- [ ] Set up structured output parsing with Pydantic models

### 2.2 Module: Investigation Planner

**File:** `agent/planner.py`

**Inputs:** Trigger type, flagged transaction ID, card ID, customer ID, risk score  
**Output:** Ordered investigation plan with required graph queries and evidence priorities

- [ ] Implement `build_investigation_plan(trigger, txn_id, card_id, customer_id)` 
- [ ] Plan should include: which queries to run, in what order, and why
- [ ] Different plans for `risk_score` vs `customer_report` vs `analyst_request` triggers

### 2.3 Module: Evidence Collector

**File:** `agent/evidence_collector.py`

**Inputs:** Investigation plan, MCP tool registry  
**Output:** Structured evidence list with source, ref, entity_ids, claim

- [ ] Execute graph queries via TigerGraph MCP tools
- [ ] Structure each finding as an `EvidenceItem`:
  ```python
  class EvidenceItem(BaseModel):
      claim: str
      source: Literal["graph", "document", "customer", "external"]
      ref: str          # query name or document section
      entity_ids: list[str]
      confidence: float
      timestamp: datetime
  ```
- [ ] Collect: transaction history, device neighbors, connected cards, closed cases, policy chunks (via GraphRAG)

### 2.4 Module: Risk & Uncertainty Assessor

**File:** `agent/risk_assessor.py`

**Inputs:** Evidence list, fraud patterns  
**Output:** Structured risk assessment

```python
class RiskAssessment(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    fraud_probability: float          # 0.0 – 1.0
    confidence: float                 # 0.0 – 1.0 (separate from probability)
    evidence_sufficiency: Literal["LOW", "MEDIUM", "HIGH"]
    pattern: str                      # fraud pattern enum
    pattern_description: str
    supporting_evidence: list[str]    # evidence item IDs
    contradicting_evidence: list[str]
    missing_evidence: list[str]
    sufficient_to_act: bool
    key_risk_factors: list[str]
    uncertainty_reasons: list[str]
```

- [ ] Implement pattern matching logic for all 5 known patterns
- [ ] Implement stop condition check (probability ≥ 0.85 or ≤ 0.15 + 2 independent evidence pieces)
- [ ] Keep risk and confidence as separate metrics

### 2.5 Module: Evidence Request Manager

**File:** `agent/evidence_request_manager.py`

**Inputs:** Risk assessment (when `sufficient_to_act = False`), policy rules  
**Output:** Evidence request with type, reason, policy basis, assumed response

- [ ] Determine appropriate evidence request type (`customer_validation`, `step_up_auth`, `analyst_info`)
- [ ] Generate the request with policy rule citation
- [ ] Simulate customer/analyst response (record assumption in `assumed_response`)
- [ ] Return simulated evidence as new `EvidenceItem` for re-investigation

### 2.6 Module: Next-Best-Action Engine

**File:** `agent/nba_engine.py`

**Inputs:** Risk assessment, evidence, policy engine, permissions  
**Output:** Ordered list of recommended actions with approval routes

```python
class ActionRecommendation(BaseModel):
    action: str           # exact policy action identifier
    route: Literal["auto", "L1", "L2"]
    reason: str           # cite policy rule number
    priority: int
```

- [ ] Implement all 14 policy actions
- [ ] Implement all 10 policy rules (R1–R10)
- [ ] Implement approval routing logic
- [ ] Produce `initial` recommendations (before evidence request) and `final` (after)
- [ ] Generate `what_changed` explanation

### 2.7 Module: Policy Engine

**File:** `policy/policy_engine.py`

- [ ] Encode all policy rules as structured functions — NOT natural language prompt instructions
- [ ] `check_rule_R1(fraud_probability, evidence_count)` → bool
- [ ] `check_rule_R2(customer_response)` → bool
- [ ] `check_rule_R5(txn_sequence)` → bool
- [ ] `get_approval_route(action, exposure_usd)` → `"auto" | "L1" | "L2"`
- [ ] `requires_SAR(verdict, exposure, shared_device, connected_fraud)` → bool
- [ ] `requires_case(fraud_probability)` → bool (threshold: 0.30)
- [ ] Agent cannot override policy via LLM reasoning

### 2.8 Module: Case Manager

**File:** `agent/case_manager.py`

- [ ] Create new case record (full schema from dataset README)
- [ ] Progress case through state machine:
  ```
  TRIGGERED → INVESTIGATING → AWAITING_EVIDENCE → REASSESSING
  → ACTION_RECOMMENDED → AWAITING_APPROVAL → ACTION_TAKEN → RESOLVED
  ```
- [ ] Append evidence, decisions, timeline events
- [ ] Write case to TigerGraph via `write_case` query
- [ ] Generate final case JSON matching the exact answer format

### 2.9 Module: Memory Retrieval

**File:** `agent/memory_retrieval.py`

- [ ] Query `search_similar_cases` with current case context
- [ ] Rank results by: same pattern, shared device profile, same billing region, same customer
- [ ] Return top 3–5 similar closed cases with similarity reason
- [ ] Feed similar case summaries into risk assessment context

### 2.10 Agent Orchestration Loop

**File:** `agent/orchestrator.py`

Implement the full investigation loop as a LangGraph state machine:

```
START
  │
  ▼
[plan_investigation]
  │
  ▼
[collect_evidence] ◄─────────────────┐
  │                                  │
  ▼                                  │
[retrieve_similar_cases]             │
  │                                  │
  ▼                                  │
[assess_risk]                        │
  │                                  │
  ▼                                  │
[check_stop_condition]               │
  │                                  │
  ├── STOP ──► [recommend_nba]       │
  │                                  │
  └── CONTINUE ──► [request_evidence]│
                        │            │
                        ▼            │
                  [receive_evidence] │
                        │            │
                        └────────────┘ (re-investigate)
  │
  ▼
[apply_policy]
  │
  ▼
[determine_approval]
  │
  ▼
[explain_decision]
  │
  ▼
[write_case_to_graph]
  │
  ▼
END
```

- [ ] Implement max iteration guard (prevent infinite loops)
- [ ] Log every tool call, decision, and state transition
- [ ] Support streaming progress updates (for real-time UI)

### 2.11 Benchmark Runner

**File:** `scripts/run_benchmarks.py`

- [ ] Loop over all 20 cases in `case_pack.csv`
- [ ] Run each case through the full agent pipeline
- [ ] Write output to `cases/<case_id>.json`
- [ ] Validate output against required answer format schema
- [ ] Log: `tool_calls`, `tokens`, `latency_s` per case

### Phase 2 Acceptance Criteria

- [ ] Agent can investigate a single benchmark case end-to-end
- [ ] Risk assessment produces valid `fraud_probability` and pattern classification
- [ ] Re-investigation loop triggers when `sufficient_to_act = False`
- [ ] `initial` and `final` NBA differ correctly after simulated evidence
- [ ] Policy engine enforces approval routes correctly
- [ ] Case JSON written to TigerGraph
- [ ] Valid answer JSON produced for at least 5 test cases

---

## Phase 3 — Backend API

**Goal:** REST API connecting the agent to the frontend, with streaming support for real-time investigation progress.  
**Duration:** Days 4–5  
**Priority:** P0 for core endpoints, P1 for streaming

### 3.1 Framework Setup

- [ ] Initialize FastAPI project in `backend/`
- [ ] Configure CORS for frontend origin
- [ ] Set up Pydantic request/response models
- [ ] Configure logging and error handling
- [ ] Set up background task support (for async agent runs)

### 3.2 Core API Endpoints

```
POST   /api/investigations                        Create new investigation
GET    /api/investigations                        List all investigations
GET    /api/investigations/:id                    Get investigation details
POST   /api/investigations/:id/run               Start/resume agent run
GET    /api/investigations/:id/stream            SSE stream of agent progress
GET    /api/investigations/:id/evidence          Get evidence list
GET    /api/investigations/:id/timeline          Get case timeline
GET    /api/investigations/:id/graph             Get graph data for visualization
GET    /api/investigations/:id/recommendation    Get NBA recommendation
POST   /api/investigations/:id/approve           Analyst approves action
POST   /api/investigations/:id/reject            Analyst rejects action
POST   /api/investigations/:id/request-evidence  Request more evidence
POST   /api/investigations/:id/submit-evidence   Submit new evidence
GET    /api/cases                                List all cases
GET    /api/cases/:id                            Get case details
GET    /api/dashboard                            Dashboard summary stats
GET    /api/policies                             List fraud policies and rules
GET    /api/memory                               Historical cases for case memory view
GET    /api/benchmarks/run                       Run all 20 benchmark cases
```

### 3.3 Server-Sent Events (SSE) Streaming

- [ ] Implement SSE endpoint `/api/investigations/:id/stream`
- [ ] Agent emits progress events at each investigation step:
  ```json
  { "type": "step", "step": "collect_evidence", "message": "Connected accounts discovered", "status": "done" }
  { "type": "risk_update", "risk": "MEDIUM", "confidence": 0.64 }
  { "type": "evidence_request", "request_type": "customer_validation", "reason": "..." }
  { "type": "nba", "actions": [...] }
  { "type": "complete", "case_id": "HHG-001" }
  ```
- [ ] Frontend subscribes to SSE and updates UI in real-time

### 3.4 Graph Visualization Data Endpoint

`GET /api/investigations/:id/graph` returns:
```json
{
  "nodes": [
    { "id": "C01234", "type": "Customer", "label": "C01234", "suspicious": false },
    { "id": "C01234-K1", "type": "Card", "label": "Card K1", "suspicious": true }
  ],
  "edges": [
    { "source": "C01234", "target": "C01234-K1", "type": "OWNS" }
  ],
  "highlighted_paths": [["C01234-K1", "D000731", "C00877-K1"]],
  "suspicious_nodes": ["C01234-K1", "D000731"],
  "suspicious_edges": []
}
```

### 3.5 In-Memory State Store

- [ ] Use a simple in-memory dict (or Redis for persistence) to track active investigation states
- [ ] Store: case ID → { status, evidence, risk, timeline, agent_steps }
- [ ] Persist completed cases to `cases/` folder as JSON

### Phase 3 Acceptance Criteria

- [ ] `POST /api/investigations` creates a case and starts the agent
- [ ] SSE stream delivers real-time agent steps to a test client
- [ ] Graph data endpoint returns valid nodes/edges JSON
- [ ] Approval endpoint updates case status correctly
- [ ] All responses match defined Pydantic models

---

## Phase 4 — Frontend Investigation UI

**Goal:** Premium enterprise fraud investigation workspace that makes the agentic loop fully visible.  
**Duration:** Days 5–7  
**Priority:** P0 for investigation workspace, P1 for all other sections

### 4.1 Tech Stack

- **Framework:** Next.js 14 (App Router) or Vite + React
- **Styling:** Tailwind CSS or Vanilla CSS (dark, enterprise aesthetic)
- **Graph Visualization:** [Cytoscape.js](https://cytoscape.js.org/) or [React Flow](https://reactflow.dev/)
- **Icons:** Lucide React
- **Charts:** Recharts or D3.js
- **SSE:** Native `EventSource` API

### 4.2 Design System

- **Theme:** Dark mode — deep charcoal/navy background (`#0a0f1e`), accent electric blue (`#0ea5e9`), risk colors (red/amber/green)
- **Typography:** Inter (headings) + JetBrains Mono (IDs, scores, data)
- **Components:** Cards, badges, progress bars, timeline items, evidence items, action buttons
- **Micro-animations:** Step completions, risk gauge updates, node highlights

### 4.3 Page: Dashboard `/`

- [ ] Active investigations count + list (clickable)
- [ ] High-risk cases panel (risk badge + case ID + card)
- [ ] Cases awaiting approval (inline approve/reject buttons)
- [ ] Recent agent activity feed (last 10 actions across all cases)
- [ ] Fraud pattern breakdown (donut chart)
- [ ] Investigation outcomes bar chart (fraud / cleared / escalated)
- [ ] Evidence requests pending counter

### 4.4 Page: Cases List `/cases`

- [ ] Sortable/filterable table: Case ID, Trigger, Customer, Card, Risk, Confidence, Pattern, Status, Last Action, Updated
- [ ] Risk level color badges
- [ ] Quick-open investigation workspace on row click
- [ ] Filter by: risk level, status, pattern, trigger type
- [ ] Search by case ID or customer ID

### 4.5 Page: Investigation Workspace `/cases/:id` ⭐

This is the primary screen. Layout (all panels visible simultaneously):

**Top: Case Header**
- Case ID, Risk badge, Confidence %, Pattern, Status, Card, Customer, Last updated

**Left column: Investigation Graph**
- Interactive Cytoscape.js/React Flow canvas
- Node types color-coded: Customer (blue), Card (purple), Transaction (cyan), Device (orange), ClosedCase (red)
- Suspicious nodes/edges highlighted in red/amber with pulse animation
- Controls: Zoom, Pan, Fit-to-screen, Expand node, Filter by entity type
- Click node → side panel with full entity details
- Highlight suspicious path button

**Right column: Agent Activity Panel**
- Real-time SSE stream of investigation steps
- Icons: ✓ (done), ⚠ (warning/gap), → (action), ⏳ (in progress)
- Color coded: green / amber / blue
- Auto-scrolls to latest step

**Middle left: Evidence Panel**
- Each evidence item: claim, source badge (`graph` / `document` / `customer`), ref, entity ID tags
- Click entity ID → highlights node in graph
- Filter by source type

**Middle right: Risk Assessment Panel**
- Risk level with color (RED / AMBER / GREEN)
- Animated confidence gauge (circular progress)
- Fraud probability bar
- Evidence sufficiency indicator
- Key risk factors as tags
- Missing evidence list

**Full width: Similar Cases Panel**
- Cards for top similar closed cases
- Similarity reason, fraud pattern, previous action, outcome
- Click → open case detail drawer

**Full width: "Why Did My Decision Change?" Component**
- Only shown when re-investigation occurred
- Side-by-side: Initial Assessment ↔ Final Assessment
- Change reason highlighted in amber

**Full width: Next-Best-Action + Approval Panel**
- Ordered action list with priority number, action name, approval route badge (auto/L1/L2), policy rule citation
- `[ APPROVE ]` / `[ REJECT ]` / `[ REQUEST MORE EVIDENCE ]` buttons
- Auto actions show "Executed (simulated)" after approval
- L1/L2 actions show "Pending L1/L2 approval" then update on approve

**Full width: Case Timeline**
- Chronological audit trail of all events
- Trigger → Case Created → Evidence Collected → Risk Assessment → Evidence Request → Re-assessment → NBA → Approval → Action → Outcome

### 4.6 Page: Analytics `/analytics`

- [ ] Investigation funnel (triggered → investigated → evidence requested → resolved)
- [ ] Pattern distribution over time (line chart)
- [ ] Risk level distribution by trigger type
- [ ] Average time to resolution
- [ ] NBA action frequency breakdown
- [ ] Evidence request rate and types
- [ ] Cases by outcome (fraud / cleared / escalated / uncertain)

### 4.7 Page: Policies `/policies`

- [ ] All 14 policy actions with descriptions and approval routes
- [ ] All 10 policy rules (R1–R10) with conditions and triggered actions
- [ ] Which rules are active in current open cases

### 4.8 Page: Case Memory `/memory`

- [ ] All closed cases (history + agent-created)
- [ ] Filter by pattern, outcome, date range
- [ ] Recurring devices across multiple cases
- [ ] Similar case clusters (shared devices/regions/patterns)

### Phase 4 Acceptance Criteria

- [ ] Dashboard shows real data from API
- [ ] Investigation workspace renders graph, evidence, risk, agent activity, NBA simultaneously
- [ ] Agent activity updates in real-time via SSE during investigation
- [ ] Approve/reject buttons update case status
- [ ] "Why did my decision change?" renders when applicable
- [ ] Graph is interactive: zoom, pan, click nodes, highlight paths

---

## Phase 5 — Integration, Benchmark Evaluation & Demo Polish

**Goal:** End-to-end system working; all 20 benchmark cases processed; 3–5 minute demo flow optimized.  
**Duration:** Days 7–9  
**Priority:** P0

### 5.1 End-to-End Integration Testing

- [ ] Run 3 benchmark cases through full stack: UI trigger → SSE stream → graph update → approval
- [ ] Fix integration issues between backend and agent
- [ ] Fix CORS, SSE, and state sync issues
- [ ] Test re-investigation loop end-to-end: initial NBA → evidence request → final NBA

### 5.2 Benchmark Evaluation

- [ ] Run all 20 benchmark cases through the agent pipeline
- [ ] Validate all 20 output JSONs against the answer format schema
- [ ] Check: all IDs exist in the dataset (no made-up IDs)
- [ ] Check: `sar.file` matches whether `FILE_REPORT` is in final actions
- [ ] Check: approval routes match policy (no L1/L2 actions marked `auto`)
- [ ] Spot-check 5 cases for investigation quality and pattern accuracy
- [ ] Store all 20 files in `cases/` folder

### 5.3 Demo Flow Preparation

Implement and validate the 17-step hackathon demo flow:

| Step | Action | UI Component |
|---|---|---|
| 1 | Select benchmark case HHG-017 | Cases list page |
| 2 | Click "Start Investigation" | Case workspace header |
| 3 | Watch agent activity stream | Agent activity panel |
| 4 | Graph builds in real-time | Investigation graph |
| 5 | Device D17 connects two cards — highlighted | Graph highlighted path |
| 6 | Similar cases CC-0141, CC-2671 appear | Similar cases panel |
| 7 | Initial risk: MEDIUM 72% | Risk gauge animates |
| 8 | "Evidence insufficient" warning | Agent activity + risk panel |
| 9 | Customer validation request shown | Evidence request display |
| 10 | "Simulate Evidence" button: customer denies | Evidence submission button |
| 11 | "Why did my decision change?" renders | Decision change component |
| 12 | Risk updates to HIGH 89% | Risk gauge re-animates |
| 13 | NBA: BLOCK_CARD + FILE_REPORT + MONITOR | NBA panel |
| 14 | L1 / L2 approval badges shown | NBA approval routes |
| 15 | Analyst approval UI | Approve button |
| 16 | Approve → actions simulated → status updated | Status update |
| 17 | Timeline complete + case written to graph | Timeline + memory page |

- [ ] Create a "Demo Mode" that pre-loads case HHG-017 with guided walkthrough tooltips
- [ ] Ensure all animations are smooth; no loading spinners blocking the demo
- [ ] Test full demo flow timing: must complete within 5 minutes

### 5.4 Performance & Reliability

- [ ] Graph queries return in < 500ms (add query caching if needed)
- [ ] SSE stream reconnects on network hiccup
- [ ] Agent investigation completes in < 30 seconds per case
- [ ] UI handles empty/error states gracefully
- [ ] No broken links or console errors

### 5.5 Submission Preparation

- [ ] `README.md` at repo root: what it is, how to run, architecture diagram, tech stack
- [ ] `cases/` folder with all 20 `<case_id>.json` answer files
- [ ] `.env.example` with all required environment variables
- [ ] Technical blog post covering: what was built, architecture, TigerGraph usage, agentic capabilities, learnings, future improvements
- [ ] X/LinkedIn social media post draft tagging `@TigerGraphDB`
- [ ] Demo video recording (3–5 minutes, following the 17-step flow)

### Phase 5 Acceptance Criteria

- [ ] All 20 benchmark JSON files present and schema-valid in `cases/`
- [ ] Demo flow runs cleanly in < 5 minutes
- [ ] README is complete and accurate
- [ ] No P0 bugs in the main investigation workspace
- [ ] Repo is clean, organized, and submittable

---

## Judging Criteria Alignment

| Criterion | Weight | Phases That Address It |
|---|---|---|
| Investigation accuracy | 25% | Phase 1 (graph queries), Phase 2 (risk assessor, pattern matching), Phase 5 (benchmark run) |
| Next best action | 25% | Phase 2 (NBA engine, policy engine, re-investigation loop) |
| Agentic design & engineering | 15% | Phase 2 (orchestrator, state machine, MCP, memory), Phase 3 (SSE streaming) |
| Innovation | 15% | Phase 1 (graph algorithms, vector store), Phase 2 (re-investigation, memory), Phase 4 (graph explorer) |
| Case summary & explainability | 10% | Phase 2 (explain_decision, evidence references), Phase 4 (evidence traceability UI) |
| Demo quality | 10% | Phase 5 (demo flow, recording) |

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| TigerGraph loading time for 590K transactions | HIGH | Load in parallel batches; start with 10K sample for dev |
| LLM token costs for 20 benchmark cases | MEDIUM | Cache responses; use GPT-4o-mini for non-critical steps |
| SSE streaming reliability | MEDIUM | Add reconnect logic; fall back to polling if needed |
| Agent hallucinating entity IDs | HIGH | Validate all IDs against the dataset before writing answer JSON |
| Demo environment stability | HIGH | Use local TigerGraph CE for demo; pre-cache graph data |
| Time overrun on frontend polish | MEDIUM | Build Investigation Workspace first; other pages are P1 |

---

## Definition of Done

The project is **complete** when:

- [ ] Dataset loaded into TigerGraph and queryable
- [ ] All GSQL investigation queries installed and tested
- [ ] Agent can investigate a case end-to-end with re-investigation loop
- [ ] Policy engine enforces all rules and approval routes
- [ ] All 20 benchmark cases produce valid answer JSON files
- [ ] Backend API streams real-time investigation progress
- [ ] Frontend investigation workspace shows graph, evidence, risk, NBA, and approval
- [ ] "Why did my decision change?" component renders correctly
- [ ] Demo flow runs in < 5 minutes
- [ ] Repo is clean with complete README
- [ ] `cases/` folder has all 20 answer files
- [ ] Blog post and social post drafted
