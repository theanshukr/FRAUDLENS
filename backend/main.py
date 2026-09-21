"""
FraudLens     FastAPI Backend
============================
Main application entry point.

Endpoints:
    POST   /api/investigations                     Create new investigation
    GET    /api/investigations                     List all investigations
    GET    /api/investigations/:id                 Get investigation details
    POST   /api/investigations/:id/run             Start agent run
    GET    /api/investigations/:id/stream          SSE progress stream
    GET    /api/investigations/:id/evidence        Evidence list
    GET    /api/investigations/:id/timeline        Case timeline
    GET    /api/investigations/:id/graph           Graph data for visualization
    GET    /api/investigations/:id/recommendation  NBA recommendation
    POST   /api/investigations/:id/approve         Approve action
    POST   /api/investigations/:id/reject          Reject action
    POST   /api/investigations/:id/request-evidence Request more evidence
    POST   /api/investigations/:id/submit-evidence  Submit new evidence
    GET    /api/cases                              List all cases
    GET    /api/cases/:id                          Get case details
    GET    /api/dashboard                          Dashboard stats
    GET    /api/policies                           Policy list
    GET    /api/memory                             Historical cases
    GET    /api/benchmarks/run                     Run all benchmarks

Run with: uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# App Setup
# ============================================================

app = FastAPI(
    title="FraudLens API",
    description="AI Agentic Fraud Investigation Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state store (replace with Redis for production)
_investigations: dict[str, dict] = {}
CASES_DIR = Path(os.getenv("CASES_DIR", "./cases"))
CASES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Request/Response Models
# ============================================================

class CreateInvestigationRequest(BaseModel):
    txn_id: str
    trigger_type: str = "risk_score"
    card_id: Optional[str] = None
    customer_id: Optional[str] = None
    trigger_risk_score: Optional[float] = None
    case_id: Optional[str] = None


class ApprovalRequest(BaseModel):
    action: str
    approved_by: str = "analyst"
    notes: Optional[str] = None


class EvidenceSubmitRequest(BaseModel):
    evidence_type: str
    claim: str
    source: str = "customer"


# ============================================================
# Investigation Routes
# ============================================================

@app.post("/api/investigations", status_code=201)
async def create_investigation(
    req: CreateInvestigationRequest,
    background_tasks: BackgroundTasks,
):
    """Create a new fraud investigation case."""
    from agent.orchestrator import Orchestrator

    orch = Orchestrator(cases_dir=str(CASES_DIR))

    # Run investigation in background and store events
    case_id = req.case_id or f"HHG-{req.txn_id[:6].upper()}"
    _investigations[case_id] = {
        "status": "CREATED",
        "events": [],
        "case_data": None,
    }

    async def run_investigation():
        async for event in orch.investigate(
            txn_id=req.txn_id,
            trigger_type=req.trigger_type,
            card_id=req.card_id,
            customer_id=req.customer_id,
            trigger_risk_score=req.trigger_risk_score,
            case_id=case_id,
        ):
            _investigations[case_id]["events"].append(event)
            _investigations[case_id]["status"] = event.get("type", "running")

    background_tasks.add_task(run_investigation)

    return {"case_id": case_id, "status": "CREATED", "message": "Investigation started"}


@app.get("/api/investigations")
async def list_investigations():
    """List all active investigations."""
    return {
        "investigations": [
            {"case_id": cid, "status": data["status"]}
            for cid, data in _investigations.items()
        ]
    }


@app.get("/api/investigations/{case_id}")
async def get_investigation(case_id: str):
    """Get full investigation details."""
    if case_id not in _investigations:
        # Try loading from disk
        case_file = CASES_DIR / f"{case_id}.json"
        if case_file.exists():
            with open(case_file) as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail=f"Investigation {case_id} not found")

    return _investigations[case_id]


@app.get("/api/investigations/{case_id}/stream")
async def stream_investigation(case_id: str):
    """SSE stream of agent progress events."""

    async def event_generator() -> AsyncIterator[str]:
        last_idx = 0
        timeout = 0

        while timeout < 60:  # 60 second timeout
            inv = _investigations.get(case_id, {})
            events = inv.get("events", [])

            # Send new events
            for event in events[last_idx:]:
                data = json.dumps(event)
                yield f"data: {data}\n\n"
                last_idx += 1

            # Check if complete
            if inv.get("status") == "complete":
                yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                break

            await asyncio.sleep(0.5)
            timeout += 0.5

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/investigations/{case_id}/evidence")
async def get_evidence(case_id: str):
    """Get evidence list for a case."""
    case_file = CASES_DIR / f"{case_id}.json"
    if not case_file.exists():
        raise HTTPException(status_code=404)
    with open(case_file) as f:
        data = json.load(f)
    return {"evidence": data.get("evidence", [])}


@app.get("/api/investigations/{case_id}/timeline")
async def get_timeline(case_id: str):
    """Get case timeline."""
    case_file = CASES_DIR / f"{case_id}.json"
    if not case_file.exists():
        raise HTTPException(status_code=404)
    with open(case_file) as f:
        data = json.load(f)
    return {"timeline": data.get("timeline", [])}


@app.get("/api/investigations/{case_id}/graph")
async def get_graph_data(case_id: str):
    """
    Get graph visualization data for this investigation.
    Returns nodes and edges for Cytoscape.js / React Flow.
    """
    # TODO (Phase 3): Build from actual TigerGraph data
    return {
        "nodes": [
            {"id": "C01234",        "type": "Customer",      "label": "Customer",   "suspicious": False},
            {"id": "CARD_MOCK_001", "type": "Card",          "label": "Card K1",    "suspicious": True},
            {"id": "T_MOCK_001",    "type": "Transaction",   "label": "Txn $542",   "suspicious": True},
            {"id": "D_MOCK_001",    "type": "DeviceProfile", "label": "Device D17", "suspicious": True},
        ],
        "edges": [
            {"source": "C01234",        "target": "CARD_MOCK_001", "type": "OWNS"},
            {"source": "CARD_MOCK_001", "target": "T_MOCK_001",    "type": "MADE"},
            {"source": "T_MOCK_001",    "target": "D_MOCK_001",    "type": "FROM_DEVICE"},
        ],
        "highlighted_paths": [["CARD_MOCK_001", "D_MOCK_001"]],
        "suspicious_nodes": ["CARD_MOCK_001", "T_MOCK_001", "D_MOCK_001"],
        "suspicious_edges": [],
    }


@app.get("/api/investigations/{case_id}/recommendation")
async def get_recommendation(case_id: str):
    """Get NBA recommendation for this case."""
    case_file = CASES_DIR / f"{case_id}.json"
    if not case_file.exists():
        raise HTTPException(status_code=404)
    with open(case_file) as f:
        data = json.load(f)
    return {
        "initial_actions": data.get("initial_actions", []),
        "final_actions": data.get("final_actions", []),
        "what_changed": data.get("what_changed"),
    }


@app.post("/api/investigations/{case_id}/approve")
async def approve_action(case_id: str, req: ApprovalRequest):
    """Analyst approves a recommended action."""
    # TODO (Phase 3): Update case state + simulate action execution
    logger.info(f"Action approved | case={case_id} | action={req.action} | by={req.approved_by}")
    return {"status": "approved", "action": req.action, "case_id": case_id}


@app.post("/api/investigations/{case_id}/reject")
async def reject_action(case_id: str, req: ApprovalRequest):
    """Analyst rejects a recommended action."""
    logger.info(f"Action rejected | case={case_id} | action={req.action} | by={req.approved_by}")
    return {"status": "rejected", "action": req.action, "case_id": case_id}


# ============================================================
# Dashboard & Supporting Routes
# ============================================================

@app.get("/api/dashboard")
async def get_dashboard():
    """Dashboard summary statistics."""
    case_files = list(CASES_DIR.glob("*.json"))
    cases = []
    for f in case_files:
        if f.name.startswith("_"):
            continue
        with open(f) as fp:
            try:
                cases.append(json.load(fp))
            except Exception:
                pass

    fraud_count   = sum(1 for c in cases if c.get("final_verdict") == "fraud")
    cleared_count = sum(1 for c in cases if c.get("final_verdict") == "cleared")
    high_risk     = sum(1 for c in cases if c.get("final_risk_level") in ("HIGH", "CRITICAL"))

    return {
        "total_cases": len(cases),
        "fraud_cases": fraud_count,
        "cleared_cases": cleared_count,
        "high_risk_cases": high_risk,
        "active_investigations": len(_investigations),
        "cases_awaiting_approval": sum(
            1 for c in cases if c.get("status") == "AWAITING_APPROVAL"
        ),
    }


@app.get("/api/cases")
async def list_cases():
    """List all completed cases from disk."""
    case_files = list(CASES_DIR.glob("*.json"))
    cases = []
    for f in case_files:
        if f.name.startswith("_"):
            continue
        with open(f) as fp:
            try:
                data = json.load(fp)
                cases.append({
                    "case_id": data.get("case_id"),
                    "status": data.get("status"),
                    "final_verdict": data.get("final_verdict"),
                    "final_risk_level": data.get("final_risk_level"),
                    "fraud_probability": data.get("final_fraud_probability"),
                    "pattern": data.get("pattern"),
                    "created_at": data.get("created_at"),
                })
            except Exception:
                pass
    return {"cases": cases}


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    """Get full case record."""
    case_file = CASES_DIR / f"{case_id}.json"
    if not case_file.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    with open(case_file) as f:
        return json.load(f)


@app.get("/api/policies")
async def get_policies():
    """List all fraud policies and rules."""
    # TODO (Phase 3): Load from policy engine
    return {
        "rules": [
            {"rule_id": "R1", "description": "Immediate block if fraud_probability >= 0.85 with 2+ evidence", "actions": ["BLOCK_CARD", "BLOCK_TRANSACTION"]},
            {"rule_id": "R2", "description": "Customer denial requires immediate block", "actions": ["BLOCK_CARD"]},
            {"rule_id": "R3", "description": "Monitor if fraud_probability >= 0.30", "actions": ["MONITOR_ACCOUNT"]},
            {"rule_id": "R4", "description": "Fraud ring: 2+ connected fraud cases     SAR", "actions": ["FLAG_FRAUD_RING", "ESCALATE_CASE"]},
            {"rule_id": "R5", "description": "Card testing pattern: block immediately", "actions": ["BLOCK_CARD"]},
            {"rule_id": "R6", "description": "High exposure (>=$10K): mandatory SAR", "actions": ["FILE_REPORT"]},
            {"rule_id": "R7", "description": "3+ cards share device: organized fraud ring", "actions": ["FLAG_FRAUD_RING"]},
            {"rule_id": "R8", "description": "Velocity: >10 transactions in 24h     block", "actions": ["BLOCK_CARD"]},
            {"rule_id": "R9", "description": "New device + out-of-region: step-up auth", "actions": ["REQUEST_STEP_UP_AUTH"]},
            {"rule_id": "R10", "description": "No customer response + high probability     precautionary block", "actions": ["BLOCK_CARD"]},
        ],
        "actions": [
            {"action": "ALLOW_TRANSACTION", "route": "auto"},
            {"action": "MONITOR_ACCOUNT", "route": "auto"},
            {"action": "WARN_CUSTOMER", "route": "auto"},
            {"action": "BLOCK_TRANSACTION", "route": "L1"},
            {"action": "REQUEST_STEP_UP_AUTH", "route": "auto"},
            {"action": "BLOCK_CARD", "route": "L1"},
            {"action": "BLOCK_ACCOUNT", "route": "L2"},
            {"action": "CREATE_CASE", "route": "auto"},
            {"action": "ESCALATE_CASE", "route": "L1"},
            {"action": "REQUEST_EVIDENCE", "route": "auto"},
            {"action": "FILE_REPORT", "route": "L2"},
            {"action": "CLOSE_CASE_CLEARED", "route": "L1"},
            {"action": "CLOSE_CASE_FRAUD", "route": "L1"},
            {"action": "FLAG_FRAUD_RING", "route": "L2"},
        ],
    }


@app.get("/api/memory")
async def get_memory():
    """Historical cases available for agent memory retrieval."""
    # TODO (Phase 3): Load from TigerGraph ClosedCase vertices
    return {"historical_cases": [], "total": 0}


@app.get("/api/benchmarks/run")
async def run_benchmarks(background_tasks: BackgroundTasks):
    """Trigger all 20 benchmark cases."""
    async def _run():
        import subprocess
        subprocess.run(["python", "scripts/run_benchmarks.py"], cwd=Path.cwd())

    background_tasks.add_task(_run)
    return {"status": "started", "message": "Benchmark run started in background"}


# ============================================================
# Health Check
# ============================================================

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "FraudLens API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("BACKEND_PORT", 8000)))
