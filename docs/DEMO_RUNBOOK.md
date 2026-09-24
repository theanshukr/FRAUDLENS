# FraudLens — Hackathon Demo Runbook

Step-by-step guide for presenting the end-to-end FraudLens system during hackathon evaluation.

---

## 1. Prerequisites & Services

Verify both backend and frontend servers are healthy:
- **FastAPI Backend:** `http://localhost:8000/docs`
- **Next.js Frontend:** `http://localhost:3000`
- **MCP System Status:** `http://localhost:8000/api/system/mcp`
- **Graph Connection:** Active TigerGraph Cloud connection (`FraudLens` graph)

---

## 2. End-to-End Investigation Demo Script

### Step 1: Select a Benchmark Case
1. Navigate to `http://localhost:3000/investigations`.
2. Select **HHG-001** (or any case from `HHG-001` through `HHG-020`).
3. Click **"Run Investigation"**.

### Step 2: Observe Real-Time Agent Execution & Provenance
1. Watch the live SSE timeline stream:
   - Case Created event
   - TigerGraph GSQL queries executing (`get_transaction`, `get_card_history`, `find_shared_devices`)
   - GraphRAG historical memory search across 5,565 closed cases
   - Risk & Uncertainty assessment calculation
2. Point out the **Truthful Provenance Badge**:
   - `TIGERGRAPH LIVE`
   - `ACCESS: MCP` (or `ACCESS: DIRECT`)
   - Exact count of real MCP calls executed (e.g. `MCP CALLS: 4`)

### Step 3: Interactive Multi-Hop Graph Exploration
1. Navigate to the **Graph View** (`/graph` tab or link).
2. Highlight the interactive entity topology:
   - Red: Transaction & Flagged Cards
   - Orange: Devices & Shared Device Rings
   - Blue: Customers
   - Yellow: Closed historical fraud cases
3. Click **"Expand Neighbors"** to demonstrate multi-hop real-time graph traversal.
4. Review the **"Why This Matters"** graph insight, populated purely from actual graph metrics and shared topology.

### Step 4: Uncertainty & Additional Evidence Loop
1. Show how the agent detects uncertainty when evidence is incomplete (e.g. confidence < 0.70).
2. The agent triggers an **Evidence Request** (Customer confirmation or Step-up Auth).
3. Provide the customer feedback response.
4. Observe the **GraphRAG Re-Investigation**:
   - Agent re-queries graph topology with new parameters.
   - GraphRAG re-runs semantic search.
   - Risk probability updates dynamically.
   - "Why did my decision change?" diff component clearly articulates the shift.

### Step 5: Deterministic Policy & NBA
1. Navigate to the **Decisions** tab.
2. Observe deterministic rule citations (e.g., Rule R1 `Immediate Block`, Rule R5 `Card Testing Pattern`, Rule R7 `Device Ring`).
3. Show the Next-Best-Action recommendation (`BLOCK_CARD`) and Approval Route (`L1`).
4. Click **"Approve & Resolve"**.

### Step 6: Verified TigerGraph Writeback
1. View the writeback status:
   - Agent executes `write_case` to TigerGraph.
   - Agent executes `get_case` to perform **read-after-write verification**.
   - Verified badge displays: `Writeback Verified: TRUE (TigerGraph Cloud)`.

---

## 3. Verifying Zero Synthetic Fallbacks
To prove data integrity:
1. Open browser DevTools Network tab.
2. Inspect `GET /api/investigations/{case_id}/graph`:
   - All node IDs match actual TigerGraph IDs (`3478561`, `C13487-K1`, `D28941`).
   - Zero mock IDs (`CARD_MOCK`, `D_MOCK`) appear anywhere in the payload.
