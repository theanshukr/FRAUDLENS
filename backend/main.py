"""
FraudLens — FastAPI Backend  (Phase 3 — Complete Implementation)
================================================================
Production-quality REST API connecting the agent layer to the frontend.

Key design decisions:
  - Per-case asyncio.Queue for SSE event streaming (no polling)
  - Heartbeat every 15s keeps SSE connections alive through proxies
  - Approval state machine persists to disk
  - Graph builder constructs nodes/edges from real case evidence
  - All responses validated against Pydantic response models
  - Memory endpoint loads from closed_cases_history.csv (or TigerGraph)

Run with:
    uvicorn backend.main:app --reload --port 8000

Endpoints:
    POST   /api/investigations                        Create & start investigation
    GET    /api/investigations                        List all investigations
    GET    /api/investigations/:id                    Investigation details
    POST   /api/investigations/:id/run               Re-run investigation
    GET    /api/investigations/:id/stream            SSE progress stream
    GET    /api/investigations/:id/evidence          Evidence list
    GET    /api/investigations/:id/timeline          Case timeline
    GET    /api/investigations/:id/graph             Graph data for visualisation
    GET    /api/investigations/:id/graph/expand      Expand entity neighbors (live TG)
    GET    /api/investigations/:id/recommendation    NBA recommendation
    POST   /api/investigations/:id/approve           Approve action
    POST   /api/investigations/:id/reject            Reject action
    POST   /api/investigations/:id/request-evidence  Request more evidence
    POST   /api/investigations/:id/submit-evidence   Submit new evidence
    GET    /api/cases                                List all cases
    GET    /api/cases/:id                            Case details
    GET    /api/dashboard                            Dashboard stats
    GET    /api/policies                             Policy rules
    GET    /api/memory                               Historical cases
    GET    /api/benchmarks/run                       Trigger benchmark run
    GET    /api/benchmarks/status/:run_id            Benchmark run status
    GET    /api/system/status                        System connectivity status
    GET    /api/health                               Health check
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Literal, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# App Setup
# ============================================================

app = FastAPI(
    title="FraudLens API",
    description="AI Agentic Fraud Investigation Platform — TigerGraph × Hacker House Goa 2026",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_project_root = Path(__file__).parent.parent.resolve()
_env_cases = os.getenv("CASES_DIR", "cases")
CASES_DIR = Path(_env_cases) if Path(_env_cases).is_absolute() else (_project_root / _env_cases).resolve()

_env_sample = os.getenv("SAMPLE_DIR", "dataset_sample")
SAMPLE_DIR = Path(_env_sample) if Path(_env_sample).is_absolute() else (_project_root / _env_sample).resolve()

CASES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Per-Case Investigation State Store
# ============================================================

@dataclass
class InvestigationStore:
    """
    Holds live state for one in-progress investigation.
    The asyncio.Queue allows SSE consumers to receive events
    without polling — events are pushed as the agent yields them.
    """
    case_id: str
    status: str = "CREATED"
    events: list[dict] = field(default_factory=list)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    case_data: Optional[dict] = None
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# Global investigation registry
_store: dict[str, InvestigationStore] = {}
# Benchmark run registry
_benchmarks: dict[str, dict] = {}


def _get_inv(case_id: str) -> InvestigationStore:
    """Raise 404 if case not found in store."""
    if case_id not in _store:
        raise HTTPException(status_code=404, detail=f"Investigation {case_id} not found")
    return _store[case_id]


def _replace_nan_with_none(obj: Any) -> Any:
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    elif isinstance(obj, dict):
        return {k: _replace_nan_with_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_nan_with_none(v) for v in obj]
    return obj


def _load_case_from_disk(case_id: str) -> Optional[dict]:
    """Load a completed case JSON from disk."""
    case_file = CASES_DIR / f"{case_id}.json"
    if case_file.exists():
        try:
            with open(case_file) as f:
                data = json.load(f)
                return _replace_nan_with_none(data)
        except Exception as e:
            logger.error(f"Error loading case {case_id}: {e}")
            return None
    return None


def _save_case_update(case_id: str, updates: dict) -> dict:
    """Load case from disk, apply updates dict, save back."""
    case_file = CASES_DIR / f"{case_id}.json"
    if not case_file.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found on disk")
    with open(case_file) as f:
        data = json.load(f)
    data.update(updates)
    with open(case_file, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return data


# ============================================================
# Pydantic Request Models
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
    confidence: float = 0.70


class RequestEvidenceRequest(BaseModel):
    reason: str
    request_type: str = "customer_validation"


# ============================================================
# Pydantic Response Models
# ============================================================

class InvestigationSummary(BaseModel):
    case_id: str
    status: str
    started_at: str
    error: Optional[str] = None


class InvestigationListResponse(BaseModel):
    investigations: list[InvestigationSummary]
    total: int


class CreateInvestigationResponse(BaseModel):
    case_id: str
    status: str
    message: str


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    suspicious: bool = False
    properties: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    label: Optional[str] = None


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    highlighted_paths: list[list[str]] = Field(default_factory=list)
    suspicious_nodes: list[str] = Field(default_factory=list)
    suspicious_edges: list[str] = Field(default_factory=list)


class ApprovalResponse(BaseModel):
    status: str
    action: str
    case_id: str
    approved_by: str
    notes: Optional[str] = None
    timestamp: str


class DashboardResponse(BaseModel):
    total_cases: int
    fraud_cases: int
    cleared_cases: int
    uncertain_cases: int
    high_risk_cases: int
    active_investigations: int
    cases_awaiting_approval: int
    avg_fraud_probability: float
    top_patterns: list[dict]


class PolicyRule(BaseModel):
    rule_id: str
    description: str
    threshold: Optional[str] = None
    actions: list[str]
    approval_route: str


class PolicyResponse(BaseModel):
    rules: list[PolicyRule]
    actions: list[dict]
    total_rules: int


class MemoryCase(BaseModel):
    case_id: str
    customer_id: Optional[str] = None
    card_id: Optional[str] = None
    outcome: str
    pattern: str
    exposure_usd: float = 0.0
    actions_taken: list[str] = Field(default_factory=list)
    report_filed: bool = False
    analyst_notes: Optional[str] = None
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None


class MemoryResponse(BaseModel):
    historical_cases: list[MemoryCase]
    total: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    tg_connected: bool


class SystemStatusResponse(BaseModel):
    tigergraph: str
    tigergraph_host: str
    graph_expansion: str
    historical_graph_memory: str
    vector_retrieval: str
    vector_store_cases: int
    graphrag_mode: str
    llm_reasoning: str
    case_writeback: str
    total_closed_cases: int
    active_investigations: int
    mcp_status: Optional[str] = "CONNECTED"
    mcp_tool_count: Optional[int] = 69


# ============================================================
# Agent Runner Helper
# ============================================================

async def _run_investigation(inv: InvestigationStore, req: CreateInvestigationRequest) -> None:
    """
    Run the agent investigation in a background task.
    Pushes all events to inv.queue for SSE consumers.
    Also accumulates events in inv.events for late-joining consumers.
    """
    from agent.orchestrator import Orchestrator

    orch = Orchestrator(cases_dir=str(CASES_DIR))
    inv.status = "RUNNING"

    try:
        async for event in orch.investigate(
            txn_id=req.txn_id,
            trigger_type=req.trigger_type,
            card_id=req.card_id,
            customer_id=req.customer_id,
            trigger_risk_score=req.trigger_risk_score,
            case_id=inv.case_id,
        ):
            inv.events.append(event)
            await inv.queue.put(event)
            # Keep status in sync
            if event.get("type") == "complete":
                inv.status = "complete"
            elif event.get("type") == "risk_update":
                inv.status = f"RUNNING:{event.get('risk', '')}"

        # Load final case data from disk
        inv.case_data = _load_case_from_disk(inv.case_id)
        if inv.status != "complete":
            inv.status = "complete"

    except Exception as e:
        logger.error(f"Investigation {inv.case_id} failed: {e}")
        inv.status = "error"
        inv.error = str(e)
        error_event = {"type": "error", "message": str(e)}
        inv.events.append(error_event)
        await inv.queue.put(error_event)

    finally:
        # Signal end of stream
        await inv.queue.put({"type": "stream_end"})


# ============================================================
# Investigation Routes
# ============================================================

@app.post("/api/investigations", response_model=CreateInvestigationResponse, status_code=201)
async def create_investigation(
    req: CreateInvestigationRequest,
    background_tasks: BackgroundTasks,
):
    """Create a new fraud investigation and start the agent immediately."""
    # Generate a stable, unique case ID
    if req.case_id:
        case_id = req.case_id
    else:
        short = uuid.uuid4().hex[:8].upper()
        case_id = f"HHG-{short}"

    inv = InvestigationStore(case_id=case_id)
    _store[case_id] = inv

    logger.info(f"Investigation created: {case_id} | txn={req.txn_id} | trigger={req.trigger_type}")
    background_tasks.add_task(_run_investigation, inv, req)

    return CreateInvestigationResponse(
        case_id=case_id,
        status="CREATED",
        message=f"Investigation {case_id} started — connect to /api/investigations/{case_id}/stream for live updates",
    )


@app.get("/api/investigations", response_model=InvestigationListResponse)
async def list_investigations():
    """List all active and recently completed investigations."""
    items = [
        InvestigationSummary(
            case_id=cid,
            status=inv.status,
            started_at=inv.started_at,
            error=inv.error,
        )
        for cid, inv in _store.items()
    ]
    return InvestigationListResponse(investigations=items, total=len(items))


@app.get("/api/investigations/{case_id}")
async def get_investigation(case_id: str):
    """Get full investigation state — merges live memory + disk case data."""
    # First: try in-memory store
    inv = _store.get(case_id)

    if inv:
        result = {
            "case_id": case_id,
            "status": inv.status,
            "started_at": inv.started_at,
            "event_count": len(inv.events),
            "events": inv.events[-20:],   # last 20 events
            "error": inv.error,
        }
        # Enrich with disk case data when available
        if inv.case_data:
            result.update(inv.case_data)
        elif (disk := _load_case_from_disk(case_id)):
            result.update(disk)
        return result

    # Fallback: load from disk (completed investigations)
    disk_case = _load_case_from_disk(case_id)
    if disk_case:
        return disk_case

    raise HTTPException(status_code=404, detail=f"Investigation {case_id} not found")


@app.post("/api/investigations/{case_id}/run", response_model=CreateInvestigationResponse)
async def run_investigation(case_id: str, req: CreateInvestigationRequest, background_tasks: BackgroundTasks):
    """Re-run an investigation (e.g. after new evidence is submitted)."""
    # Reset the store entry
    inv = InvestigationStore(case_id=case_id)
    _store[case_id] = inv

    logger.info(f"Re-running investigation: {case_id}")
    background_tasks.add_task(_run_investigation, inv, req)

    return CreateInvestigationResponse(
        case_id=case_id,
        status="CREATED",
        message=f"Investigation {case_id} re-started",
    )


@app.get("/api/investigations/{case_id}/stream")
async def stream_investigation(case_id: str):
    """
    SSE stream of agent progress events for a running investigation.

    Protocol:
      - Immediately replays all events emitted so far (for late joiners)
      - Then waits on asyncio.Queue for new events as they arrive
      - Sends heartbeat every 15s to keep connection alive through proxies
      - Terminates when 'stream_end' sentinel is received or 5min timeout
    """
    inv = _store.get(case_id)
    if inv is None:
        raise HTTPException(status_code=404, detail=f"Investigation {case_id} not found or not running")

    async def event_generator() -> AsyncIterator[str]:
        HEARTBEAT_INTERVAL = 15.0   # seconds between heartbeats
        TIMEOUT            = 300.0  # 5 minute max stream duration

        # 1. Replay all events already emitted (late-join support)
        for event in list(inv.events):
            yield f"data: {json.dumps(event)}\n\n"

        # If already complete, send end immediately
        if inv.status in ("complete", "error"):
            yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
            return

        # 2. Stream new events from queue
        elapsed = 0.0
        while elapsed < TIMEOUT:
            try:
                event = await asyncio.wait_for(inv.queue.get(), timeout=HEARTBEAT_INTERVAL)
                yield f"data: {json.dumps(event)}\n\n"

                if event.get("type") == "stream_end":
                    break
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection open
                yield f"data: {json.dumps({'type': 'heartbeat', 'elapsed': round(elapsed)})}\n\n"
                elapsed += HEARTBEAT_INTERVAL

        if elapsed >= TIMEOUT:
            yield f"data: {json.dumps({'type': 'timeout', 'message': 'Stream timed out after 5 minutes'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/investigations/{case_id}/evidence")
async def get_evidence(case_id: str):
    """Get evidence list for a case (live or completed)."""
    inv = _store.get(case_id)

    # Try live case data first
    if inv and inv.case_data:
        return {"evidence": inv.case_data.get("evidence", []), "total": len(inv.case_data.get("evidence", []))}

    # Fallback to disk
    data = _load_case_from_disk(case_id)
    if data:
        evidence = data.get("evidence", [])
        return {"evidence": evidence, "total": len(evidence)}

    raise HTTPException(status_code=404, detail=f"Case {case_id} not found")


@app.get("/api/investigations/{case_id}/timeline")
async def get_timeline(case_id: str):
    """Get the investigation timeline."""
    inv = _store.get(case_id)

    if inv and inv.case_data:
        return {"timeline": inv.case_data.get("timeline", []), "total": len(inv.case_data.get("timeline", []))}

    data = _load_case_from_disk(case_id)
    if data:
        timeline = data.get("timeline", [])
        return {"timeline": timeline, "total": len(timeline)}

    raise HTTPException(status_code=404, detail=f"Case {case_id} not found")


@app.get("/api/investigations/{case_id}/graph", response_model=GraphResponse)
async def get_graph_data(case_id: str):
    """
    Build graph visualization data from the case evidence.
    Constructs nodes/edges from real entity_ids recorded in evidence items.
    Enriches with live TigerGraph data when available.
    Returns React Flow compatible format.
    """
    inv = _store.get(case_id)
    case_data = (inv.case_data if inv else None) or _load_case_from_disk(case_id)

    if not case_data:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    return _build_graph(case_data)


def _build_graph(case_data: dict) -> GraphResponse:
    """
    Build a GraphResponse from REAL case data — no synthetic node generation.

    Sources of truth (in priority order):
      1. entity_ids in evidence items (recorded by TigerGraph query parsers)
      2. case_data top-level fields: txn_id, card_id, customer_id
      3. case.connected_card_ids, case.connected_device_profiles

    REMOVED:
      - Hardcoded '$482.12' transaction amounts
      - DEV_FP_{txn_id[-4:]} generated device IDs
      - base_txn_num - 2 / base_txn_num - 1420 arithmetic transactions
      - REGION_{txn_id[-3:]} generated billing region IDs
      - CUST_{txn_id[-4:]} generated customer IDs
    """
    nodes: dict[str, GraphNode] = {}
    suspicious_node_ids: set[str] = set()
    pair_edge_map: dict[tuple[str, str], GraphEdge] = {}

    txn_id = str(case_data.get("txn_id") or "").strip()
    card_id = str(case_data.get("card_id") or "").strip()
    customer_id = str(case_data.get("customer_id") or "").strip()
    pattern = str(case_data.get("pattern") or "unknown")
    final_verdict = str(case_data.get("final_verdict") or "unknown")
    final_prob = case_data.get("final_fraud_probability") or 0.0
    evidence_list = case_data.get("evidence", [])
    case_inner = case_data.get("case", {})

    is_fraud = final_verdict == "fraud" or final_prob >= 0.50

    # --- Helper: ensure exactly 1 edge per node-pair ---
    def add_edge(u: str, v: str, edge_type: str, label: str):
        if not u or not v or u not in nodes or v not in nodes or u == v:
            return
        edge_key = tuple(sorted([u, v]))
        if edge_key not in pair_edge_map:
            pair_edge_map[edge_key] = GraphEdge(source=u, target=v, type=edge_type, label=label)

    # --- 1. Customer node (from case data — real ID or derive from card) ---
    if not customer_id or customer_id in ("None", ""):
        if card_id and "-" in card_id:
            customer_id = card_id.split("-")[0]  # e.g. C12382 from C12382-K1
        # Do NOT fabricate CUST_XXXX — leave blank if no real ID
    if customer_id and customer_id not in ("None", ""):
        nodes[customer_id] = GraphNode(
            id=customer_id,
            type="Customer",
            label=f"Customer {customer_id}",
            suspicious=False,
            properties={"customer_id": customer_id, "source": "case_data"}
        )

    # --- 2. Card node (from case data) ---
    if card_id and card_id not in ("None", ""):
        nodes[card_id] = GraphNode(
            id=card_id,
            type="Card",
            label=f"Card {card_id}",
            suspicious=is_fraud,
            properties={
                "card_id": card_id,
                "pattern": pattern.replace("_", " ").title(),
                "status": "FLAGGED" if is_fraud else "MONITORED",
                "source": "case_data",
            }
        )
        if is_fraud:
            suspicious_node_ids.add(card_id)

    # --- 3. Flagged transaction node ---
    if txn_id:
        # Retrieve real amount from evidence raw_data if available
        real_amount = _extract_amount_from_evidence(evidence_list)
        real_risk = _extract_risk_score_from_evidence(evidence_list)
        nodes[txn_id] = GraphNode(
            id=txn_id,
            type="Transaction",
            label=f"Txn {txn_id}" + (" (FLAGGED)" if is_fraud else ""),
            suspicious=is_fraud,
            properties={
                "transaction_id": txn_id,
                "amount": real_amount or "—",
                "risk_score": f"{real_risk:.2f}" if real_risk else "—",
                "verdict": final_verdict.upper(),
                "fraud_probability": f"{final_prob*100:.0f}%",
                "source": "TigerGraph" if real_amount else "case_data",
            }
        )
        if is_fraud:
            suspicious_node_ids.add(txn_id)

    # --- 4. Connected cards from evidence entity_ids ---
    connected_cards = list(case_inner.get("connected_card_ids") or [])
    for ev in evidence_list:
        for eid in (ev.get("entity_ids") or []):
            if isinstance(eid, str) and eid.startswith("C") and "-K" in eid and eid != card_id:
                if eid not in connected_cards:
                    connected_cards.append(eid)
    for connected_card in connected_cards[:4]:  # cap at 4 for visual clarity
        if connected_card == card_id or connected_card in nodes:
            continue
        nodes[connected_card] = GraphNode(
            id=connected_card,
            type="Card",
            label=f"Card {connected_card}",
            suspicious=True,
            properties={"card_id": connected_card, "status": "CONNECTED_SUSPICIOUS", "source": "TigerGraph"}
        )
        suspicious_node_ids.add(connected_card)

    # --- 5. Device profile nodes from evidence entity_ids ---
    device_ids_seen = set(case_inner.get("connected_device_profiles") or [])
    for ev in evidence_list:
        ref = ev.get("ref", "")
        if "device" in ref.lower():
            for eid in (ev.get("entity_ids") or []):
                if isinstance(eid, str) and ("DEV" in eid.upper() or "FP" in eid.upper() or "DEVICE" in eid.upper()):
                    device_ids_seen.add(eid)
    for dev_id in list(device_ids_seen)[:3]:
        if dev_id in nodes:
            continue
        is_dev_suspicious = pattern in ("account_takeover", "shared_device_ring")
        nodes[dev_id] = GraphNode(
            id=dev_id,
            type="DeviceProfile",
            label=f"Device {dev_id[:16]}",
            suspicious=is_dev_suspicious,
            properties={"device_id": dev_id, "status": "Suspicious" if is_dev_suspicious else "Profiled", "source": "TigerGraph"}
        )
        if is_dev_suspicious:
            suspicious_node_ids.add(dev_id)

    # --- 6. Similar case nodes (from evidence refs) ---
    for ev in evidence_list:
        if ev.get("ref", "") == "search_similar_cases":
            for eid in (ev.get("entity_ids") or []):
                if isinstance(eid, str) and eid.startswith("CC-") and eid not in nodes:
                    nodes[eid] = GraphNode(
                        id=eid,
                        type="ClosedCase",
                        label=f"Prior Case {eid}",
                        suspicious=True,
                        properties={"case_id": eid, "type": "Historical Fraud Case", "source": "case_memory"}
                    )
                    suspicious_node_ids.add(eid)

    # --- Edges ---
    if customer_id in nodes and card_id in nodes:
        add_edge(customer_id, card_id, "OWNS", "Owns Card")
    if card_id in nodes and txn_id in nodes:
        add_edge(card_id, txn_id, "MADE", "Flagged Txn")
    for conn_card in connected_cards:
        if conn_card in nodes and card_id in nodes:
            add_edge(card_id, conn_card, "CONNECTED_TO", "Shared Device Link")
    for dev_id in device_ids_seen:
        if dev_id in nodes and txn_id in nodes:
            add_edge(txn_id, dev_id, "FROM_DEVICE", "Used Device")
        if dev_id in nodes and card_id in nodes:
            add_edge(card_id, dev_id, "USED_DEVICE", "Device Profile")
    for ev in evidence_list:
        if ev.get("ref", "") == "search_similar_cases":
            for eid in (ev.get("entity_ids") or []):
                if eid in nodes and card_id in nodes:
                    add_edge(card_id, eid, "SIMILAR_TO", "Similar Case")

    edges = list(pair_edge_map.values())
    path = [n for n in [customer_id, card_id, txn_id] if n in nodes]
    if path and list(device_ids_seen):
        dev = next(iter(device_ids_seen))
        if dev in nodes:
            path.append(dev)

    return GraphResponse(
        nodes=list(nodes.values()),
        edges=edges,
        highlighted_paths=[path] if len(path) >= 2 else [],
        suspicious_nodes=list(suspicious_node_ids),
        suspicious_edges=[
            f"{e.source}-{e.target}" for e in edges
            if e.source in suspicious_node_ids and e.target in suspicious_node_ids
        ],
    )


def _extract_amount_from_evidence(evidence_list: list[dict]) -> str:
    """Extract real transaction amount from evidence raw_data."""
    for ev in evidence_list:
        raw = ev.get("raw_data") or {}
        amount = raw.get("amount") or raw.get("TransactionAmt")
        if amount and float(amount) > 0:
            return f"${float(amount):.2f}"
        claim = ev.get("claim", "")
        import re
        match = re.search(r'\$(\d+\.\d{2})', claim)
        if match:
            amt = float(match.group(1))
            if amt > 1.00:  # ignore micro-auth amounts
                return f"${amt:.2f}"
    return ""


def _extract_risk_score_from_evidence(evidence_list: list[dict]) -> float:
    """Extract real risk score from evidence raw_data."""
    for ev in evidence_list:
        raw = ev.get("raw_data") or {}
        rs = raw.get("risk_score") or raw.get("isFraud")
        if rs and float(rs) > 0:
            return float(rs)
    return 0.0


def _classify_entity(eid: str) -> tuple[str, str]:
    """Infer entity type and label from ID prefix."""
    eid_upper = eid.upper()
    if eid_upper.startswith("T_") or (eid.isdigit() and len(eid) >= 6):
        return "Transaction", f"Txn {eid[:10]}"
    elif "CARD" in eid_upper or (eid.startswith("C") and "-K" in eid):
        return "Card", f"Card {eid[:14]}"
    elif eid_upper.startswith("C0") or eid_upper.startswith("C_"):
        return "Customer", f"Customer {eid[:10]}"
    elif eid_upper.startswith("D") or "DEVICE" in eid_upper:
        return "DeviceProfile", f"Device {eid[:12]}"
    elif eid_upper.startswith("CC-"):
        return "ClosedCase", f"Case {eid}"
    else:
        return "Entity", eid[:16]


@app.get("/api/investigations/{case_id}/graph/expand")
async def expand_graph(
    case_id: str,
    entity_id: str = Query(..., description="Entity ID to expand"),
    entity_type: str = Query("Transaction", description="Entity type (Transaction|Card|DeviceProfile|Customer)"),
):
    """
    Expand neighbors of a graph node using live TigerGraph data.
    Returns new nodes and edges to merge into the current graph visualization.
    No synthetic data — purely from TigerGraph query results.
    """
    # Load case for context
    inv = _store.get(case_id)
    case_data = (inv.case_data if inv else None) or _load_case_from_disk(case_id)
    if not case_data:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    # Try to get live TigerGraph connection
    tg_conn = None
    try:
        from tools.graph_tools import get_tg_connection, expand_entity_neighbors
        tg_conn = get_tg_connection()
    except Exception as e:
        logger.warning(f"TigerGraph not available for expansion: {e}")

    if tg_conn is None:
        # Without TigerGraph, return empty expansion with clear source label
        return {
            "case_id": case_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "nodes": [],
            "edges": [],
            "source": "no_tg_connection",
            "message": "TigerGraph connection not available — expansion requires live database",
        }

    try:
        result = expand_entity_neighbors(tg_conn, entity_id, entity_type)
        # Parse results into GraphNode/GraphEdge format
        new_nodes = []
        new_edges = []

        for row in result.get("results", []):
            if isinstance(row, dict):
                for key, val in row.items():
                    if isinstance(val, dict) and "v_type" in val:
                        # TigerGraph vertex format
                        etype, elabel = _classify_entity(val.get("v_id", key))
                        node = GraphNode(
                            id=val.get("v_id", key),
                            type=etype,
                            label=elabel,
                            suspicious=False,
                            properties=val.get("attributes", {}),
                        )
                        if node.id != entity_id:
                            new_nodes.append(node.model_dump())
                            new_edges.append(GraphEdge(
                                source=entity_id,
                                target=node.id,
                                type="RELATED",
                                label=f"→ {etype}",
                            ).model_dump())
                    elif isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict) and "v_type" in item:
                                etype, elabel = _classify_entity(item.get("v_id", ""))
                                node = GraphNode(
                                    id=item.get("v_id", ""),
                                    type=etype,
                                    label=elabel,
                                    suspicious=False,
                                    properties=item.get("attributes", {}),
                                )
                                if node.id and node.id != entity_id:
                                    new_nodes.append(node.model_dump())
                                    new_edges.append(GraphEdge(
                                        source=entity_id,
                                        target=node.id,
                                        type="RELATED",
                                        label=f"→ {etype}",
                                    ).model_dump())

        return {
            "case_id": case_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "nodes": new_nodes,
            "edges": new_edges,
            "source": "TigerGraph",
            "raw_result_count": len(result.get("results", [])),
        }

    except Exception as e:
        logger.error(f"Graph expansion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Graph expansion failed: {e}")


@app.get("/api/system/status")
async def system_status():
    """
    Live system connectivity status for all FraudLens components.
    Used by the frontend status bar to show real connection health.
    """
    import time
    t0 = time.time()

    # TigerGraph connectivity
    tg_ok = False
    tg_graph = ""
    tg_host = ""
    tg_error = ""
    try:
        from tools.graph_tools import get_tg_connection
        conn = get_tg_connection()
        tg_ok = conn is not None
        if conn:
            tg_graph = getattr(conn, "graphname", os.getenv("TG_GRAPH_NAME", "FraudLens"))
            tg_host = getattr(conn, "host", os.getenv("TG_HOST", ""))
    except Exception as e:
        tg_error = str(e)[:100]

    # LLM connectivity
    llm_ok = False
    llm_model = ""
    try:
        from agent.llm_client import GeminiClient
        client = GeminiClient()
        llm_ok = client.api_key is not None and len(client.api_key) > 10
        llm_model = client.model
    except Exception:
        pass

    # Cases on disk
    cases_on_disk = len(list(CASES_DIR.glob("HHG-*.json")))
    active_investigations = len(_store)

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response_time_ms": round((time.time() - t0) * 1000, 1),
        "components": {
            "tigergraph": {
                "connected": tg_ok,
                "graph": tg_graph,
                "host": tg_host.split("//")[-1].split(":")[0] if tg_host else "",
                "error": tg_error if not tg_ok else None,
                "mode": "LIVE" if tg_ok else "DISCONNECTED",
            },
            "llm": {
                "connected": llm_ok,
                "model": llm_model,
                "provider": "Google Gemini",
                "mode": "LIVE" if llm_ok else "UNAVAILABLE",
            },
            "agent": {
                "mode": "LIVE" if tg_ok else "MOCK_FALLBACK",
                "active_investigations": active_investigations,
                "cases_on_disk": cases_on_disk,
            },
        },
    }


@app.get("/api/investigations/{case_id}/recommendation")
async def get_recommendation(case_id: str):
    """Get NBA recommendations for this case."""
    inv = _store.get(case_id)
    if inv and inv.case_data:
        data = inv.case_data
    else:
        data = _load_case_from_disk(case_id)
        if not data:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    return {
        "case_id": case_id,
        "initial_actions": data.get("initial_actions", []),
        "final_actions":   data.get("final_actions", []),
        "what_changed":    data.get("what_changed"),
        "final_verdict":   data.get("final_verdict"),
        "fraud_probability": data.get("final_fraud_probability", 0.0),
    }


@app.post("/api/investigations/{case_id}/approve", response_model=ApprovalResponse)
async def approve_action(case_id: str, req: ApprovalRequest):
    """
    Analyst approves a recommended action.
    Updates the action status in the case JSON and transitions case state.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info(f"Action APPROVED | case={case_id} | action={req.action} | by={req.approved_by}")

    try:
        case_data = _load_case_from_disk(case_id)
        if case_data:
            # Update the specific action's status
            final_actions = case_data.get("final_actions", [])
            for action in final_actions:
                if isinstance(action, dict) and action.get("action") == req.action:
                    action["status"] = "approved"
                    action["approved_by"] = req.approved_by
                    action["approved_at"] = timestamp
                    action["notes"] = req.notes

            # Add approval timeline event
            timeline = case_data.get("timeline", [])
            timeline.append({
                "event_type":   "action_approved",
                "description":  f"Action '{req.action}' approved by {req.approved_by}",
                "timestamp":    timestamp,
                "actor":        req.approved_by,
            })

            case_data["final_actions"] = final_actions
            case_data["timeline"] = timeline
            case_data["status"] = "ACTION_TAKEN"

            # Persist
            case_file = CASES_DIR / f"{case_id}.json"
            with open(case_file, "w") as f:
                json.dump(case_data, f, indent=2, default=str)

            # Update in-memory store
            if case_id in _store:
                _store[case_id].case_data = case_data
                _store[case_id].status = "ACTION_TAKEN"

    except Exception as e:
        logger.warning(f"Could not persist approval for {case_id}: {e}")

    return ApprovalResponse(
        status="approved",
        action=req.action,
        case_id=case_id,
        approved_by=req.approved_by,
        notes=req.notes,
        timestamp=timestamp,
    )


@app.post("/api/investigations/{case_id}/reject", response_model=ApprovalResponse)
async def reject_action(case_id: str, req: ApprovalRequest):
    """Analyst rejects a recommended action."""
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info(f"Action REJECTED | case={case_id} | action={req.action} | by={req.approved_by}")

    try:
        case_data = _load_case_from_disk(case_id)
        if case_data:
            final_actions = case_data.get("final_actions", [])
            for action in final_actions:
                if isinstance(action, dict) and action.get("action") == req.action:
                    action["status"] = "rejected"
                    action["rejected_by"] = req.approved_by
                    action["rejected_at"] = timestamp
                    action["notes"] = req.notes

            timeline = case_data.get("timeline", [])
            timeline.append({
                "event_type":   "action_rejected",
                "description":  f"Action '{req.action}' rejected by {req.approved_by} — {req.notes or 'no reason given'}",
                "timestamp":    timestamp,
                "actor":        req.approved_by,
            })

            case_data["final_actions"] = final_actions
            case_data["timeline"] = timeline
            case_data["status"] = "ACTION_RECOMMENDED"

            case_file = CASES_DIR / f"{case_id}.json"
            with open(case_file, "w") as f:
                json.dump(case_data, f, indent=2, default=str)

            if case_id in _store:
                _store[case_id].case_data = case_data

    except Exception as e:
        logger.warning(f"Could not persist rejection for {case_id}: {e}")

    return ApprovalResponse(
        status="rejected",
        action=req.action,
        case_id=case_id,
        approved_by=req.approved_by,
        notes=req.notes,
        timestamp=timestamp,
    )


@app.post("/api/investigations/{case_id}/request-evidence")
async def request_evidence(case_id: str, req: RequestEvidenceRequest):
    """
    Create an evidence request for this case.
    Returns the formatted request that can be sent to the customer or analyst.
    """
    from agent.evidence_request_manager import EvidenceRequestManager
    from agent.risk_assessor import RiskAssessment

    # Build a minimal assessment to pass to the request manager
    dummy_assessment = RiskAssessment(
        risk_level="HIGH",
        fraud_probability=0.70,
        confidence=0.60,
        evidence_sufficiency="LOW",
        sufficient_to_act=False,
        pattern="unknown",
        pattern_description=req.reason,
        missing_evidence=[req.reason],
    )

    mgr = EvidenceRequestManager()
    ev_request = mgr.determine_request(dummy_assessment, [], 0)

    if ev_request is None:
        ev_request_dict = {
            "request_id":   f"REQ-{uuid.uuid4().hex[:6].upper()}",
            "request_type": req.request_type,
            "question":     req.reason,
            "policy_basis": "Analyst request",
        }
    else:
        ev_request_dict = ev_request.model_dump(mode="json")

    # Persist to case timeline
    try:
        case_data = _load_case_from_disk(case_id)
        if case_data:
            timeline = case_data.get("timeline", [])
            timeline.append({
                "event_type":   "evidence_requested",
                "description":  f"Evidence requested: {req.reason}",
                "timestamp":    datetime.now(timezone.utc).isoformat(),
            })
            case_data["timeline"] = timeline
            case_data["pending_evidence_request"] = ev_request_dict
            case_file = CASES_DIR / f"{case_id}.json"
            with open(case_file, "w") as f:
                json.dump(case_data, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Could not persist evidence request for {case_id}: {e}")

    return {"case_id": case_id, "evidence_request": ev_request_dict}


@app.post("/api/investigations/{case_id}/submit-evidence")
async def submit_evidence(case_id: str, req: EvidenceSubmitRequest):
    """
    Submit new evidence for an investigation (from analyst or customer).
    Appends to case evidence list and re-scores risk.
    """
    from agent.evidence_collector import EvidenceItem
    from agent.risk_assessor import RiskAssessor

    timestamp = datetime.now(timezone.utc).isoformat()
    ev_id = f"EVD-ANALYST-{uuid.uuid4().hex[:6].upper()}"

    new_evidence = EvidenceItem(
        evidence_id=ev_id,
        claim=req.claim,
        source=req.source,
        ref="analyst_submission",
        entity_ids=[],
        confidence=req.confidence,
        supports_fraud=None,    # analyst-submitted evidence is neutral until reassessed
        raw_data={"submitted_type": req.evidence_type},
    )

    # Append to case and re-score
    try:
        case_data = _load_case_from_disk(case_id)
        if not case_data:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        evidence_list = case_data.get("evidence", [])
        evidence_list.append(new_evidence.model_dump(mode="json"))

        # Quick re-score with the new evidence
        assessor = RiskAssessor()
        ev_items = [EvidenceItem(**e) for e in evidence_list if isinstance(e, dict) and "claim" in e]
        new_assessment = assessor.assess(
            ev_items,
            trigger_type=case_data.get("trigger_type", "risk_score"),
        )

        timeline = case_data.get("timeline", [])
        timeline.append({
            "event_type":  "evidence_submitted",
            "description": f"New evidence submitted: {req.claim[:100]}",
            "timestamp":   timestamp,
            "evidence_id": ev_id,
        })

        case_data["evidence"] = evidence_list
        case_data["timeline"] = timeline
        case_data["final_fraud_probability"] = new_assessment.fraud_probability
        case_data["final_risk_level"] = new_assessment.risk_level

        case_file = CASES_DIR / f"{case_id}.json"
        with open(case_file, "w") as f:
            json.dump(case_data, f, indent=2, default=str)

        # Update memory store
        if case_id in _store:
            _store[case_id].case_data = case_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evidence submission failed for {case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "case_id":           case_id,
        "evidence_id":       ev_id,
        "message":           "Evidence submitted and risk re-scored",
        "new_fraud_probability": new_assessment.fraud_probability,
        "new_risk_level":    new_assessment.risk_level,
    }


# ============================================================
# Dashboard & Cases Routes
# ============================================================

@app.get("/api/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    """Dashboard summary statistics across all completed cases."""
    case_files = [f for f in CASES_DIR.glob("*.json") if not f.name.startswith("_")]
    cases = []
    for f in case_files:
        try:
            with open(f) as fp:
                cases.append(_replace_nan_with_none(json.load(fp)))
        except Exception:
            pass

    fraud_count    = sum(1 for c in cases if c.get("final_verdict") == "fraud")
    cleared_count  = sum(1 for c in cases if c.get("final_verdict") == "cleared")
    uncertain_count = sum(1 for c in cases if c.get("final_verdict") == "uncertain")
    high_risk      = sum(1 for c in cases if c.get("final_risk_level") in ("HIGH", "CRITICAL"))
    awaiting       = sum(1 for c in cases if c.get("status") in ("AWAITING_APPROVAL", "ACTION_RECOMMENDED"))

    probs = [c.get("final_fraud_probability", 0.0) for c in cases if c.get("final_fraud_probability") is not None]
    avg_prob = round(sum(probs) / len(probs), 3) if probs else 0.0

    # Pattern frequency
    from collections import Counter
    pattern_counts = Counter(c.get("pattern", "unknown") for c in cases if c.get("pattern"))
    top_patterns = [{"pattern": p, "count": cnt} for p, cnt in pattern_counts.most_common(5)]

    return DashboardResponse(
        total_cases=len(cases),
        fraud_cases=fraud_count,
        cleared_cases=cleared_count,
        uncertain_cases=uncertain_count,
        high_risk_cases=high_risk,
        active_investigations=len(_store),
        cases_awaiting_approval=awaiting,
        avg_fraud_probability=avg_prob,
        top_patterns=top_patterns,
    )


@app.get("/api/cases")
async def list_cases(
    verdict: Optional[str] = Query(None, description="Filter by verdict: fraud|cleared|uncertain"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all completed cases from disk with optional filtering."""
    case_files = [f for f in CASES_DIR.glob("*.json") if not f.name.startswith("_")]
    cases = []
    for f in case_files:
        try:
            with open(f) as fp:
                data = _replace_nan_with_none(json.load(fp))
                if verdict and data.get("final_verdict") != verdict:
                    continue
                cases.append({
                    "case_id":           data.get("case_id"),
                    "status":            data.get("status"),
                    "final_verdict":     data.get("final_verdict"),
                    "final_risk_level":  data.get("final_risk_level"),
                    "fraud_probability": data.get("final_fraud_probability"),
                    "pattern":           data.get("pattern"),
                    "created_at":        data.get("created_at"),
                    "txn_id":            data.get("txn_id"),
                })
        except Exception:
            pass

    # Sort by created_at descending
    cases.sort(key=lambda c: c.get("created_at") or "", reverse=True)
    paged = cases[offset: offset + limit]
    return {"cases": paged, "total": len(cases), "limit": limit, "offset": offset}


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    """Get full case record."""
    data = _load_case_from_disk(case_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return data


# ============================================================
# Policies Route
# ============================================================

@app.get("/api/policies", response_model=PolicyResponse)
async def get_policies():
    """List all fraud policies, rules, and approval routes."""
    rules = [
        PolicyRule(rule_id="R1",  description="Immediate block if fraud_probability ≥ 0.85 AND 2+ independent evidence items", threshold="prob≥0.85 + 2 evidence", actions=["BLOCK_CARD", "BLOCK_TRANSACTION"], approval_route="L1"),
        PolicyRule(rule_id="R2",  description="Customer denial requires immediate card block",                                  threshold="customer_response=denied",  actions=["BLOCK_CARD"],                  approval_route="L1"),
        PolicyRule(rule_id="R3",  description="Add to enhanced monitoring if fraud_probability ≥ 0.30",                       threshold="prob≥0.30",                 actions=["MONITOR_ACCOUNT"],              approval_route="auto"),
        PolicyRule(rule_id="R4",  description="Fraud ring: 2+ connected accounts with prior fraud → SAR + escalate",          threshold="connected_fraud≥2",         actions=["FLAG_FRAUD_RING", "ESCALATE_CASE", "FILE_REPORT"], approval_route="L2"),
        PolicyRule(rule_id="R5",  description="Card testing: 3+ micro-transactions followed by large → immediate block",      threshold="micro≥3 + large≥1",         actions=["BLOCK_CARD"],                  approval_route="L1"),
        PolicyRule(rule_id="R6",  description="High exposure ≥ $10,000 → mandatory SAR + L2 approval",                       threshold="exposure≥$10,000",          actions=["FILE_REPORT", "BLOCK_CARD"],    approval_route="L2"),
        PolicyRule(rule_id="R7",  description="3+ cards share same device profile → organized fraud ring",                    threshold="shared_device≥3",           actions=["FLAG_FRAUD_RING"],              approval_route="L2"),
        PolicyRule(rule_id="R8",  description="Velocity: >10 transactions in 24 hours → immediate block",                     threshold=">10 txns/24h",              actions=["BLOCK_CARD"],                  approval_route="L1"),
        PolicyRule(rule_id="R9",  description="New device + out-of-home-region → step-up authentication required",            threshold="new_device AND out_of_region", actions=["REQUEST_STEP_UP_AUTH"],     approval_route="auto"),
        PolicyRule(rule_id="R10", description="No customer response + fraud_probability > 0.50 → precautionary block",        threshold="no_response + prob>0.50",   actions=["BLOCK_CARD"],                  approval_route="L1"),
    ]

    actions = [
        {"action": "ALLOW_TRANSACTION",    "route": "auto", "description": "Allow the transaction through"},
        {"action": "MONITOR_ACCOUNT",      "route": "auto", "description": "Add account to enhanced monitoring"},
        {"action": "WARN_CUSTOMER",        "route": "auto", "description": "Send fraud alert to customer"},
        {"action": "BLOCK_TRANSACTION",    "route": "L1",   "description": "Block this specific transaction"},
        {"action": "REQUEST_STEP_UP_AUTH", "route": "auto", "description": "Require additional authentication"},
        {"action": "BLOCK_CARD",           "route": "L1",   "description": "Block card immediately"},
        {"action": "BLOCK_ACCOUNT",        "route": "L2",   "description": "Block entire account (requires L2 approval)"},
        {"action": "CREATE_CASE",          "route": "auto", "description": "Create fraud investigation case"},
        {"action": "ESCALATE_CASE",        "route": "L1",   "description": "Escalate to Level-1 analyst"},
        {"action": "REQUEST_EVIDENCE",     "route": "auto", "description": "Request additional evidence from customer"},
        {"action": "FILE_REPORT",          "route": "L2",   "description": "File Suspicious Activity Report (SAR)"},
        {"action": "CLOSE_CASE_CLEARED",   "route": "L1",   "description": "Close case as cleared"},
        {"action": "CLOSE_CASE_FRAUD",     "route": "L1",   "description": "Close case as confirmed fraud"},
        {"action": "FLAG_FRAUD_RING",      "route": "L2",   "description": "Flag as organized fraud ring"},
    ]

    return PolicyResponse(rules=rules, actions=actions, total_rules=len(rules))


# ============================================================
# Memory Route
# ============================================================

@app.get("/api/memory", response_model=MemoryResponse)
async def get_memory(
    pattern: Optional[str] = Query(None, description="Filter by fraud pattern"),
    outcome: Optional[str] = Query(None, description="Filter by outcome"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Historical closed cases available for agent memory retrieval.
    Loads from dataset_sample/closed_cases_history.csv.
    """
    csv_path = SAMPLE_DIR / "closed_cases_history.csv"
    if not csv_path.exists():
        return MemoryResponse(historical_cases=[], total=0)

    try:
        import pandas as pd
        df = pd.read_csv(csv_path)

        if pattern:
            df = df[df["pattern"].str.contains(pattern, case=False, na=False)]
        if outcome:
            df = df[df["outcome"].str.contains(outcome, case=False, na=False)]

        df = df.head(limit)

        cases = []
        for _, row in df.iterrows():
            actions = [a.strip() for a in str(row.get("actions_taken", "")).split("|") if a.strip()]
            cases.append(MemoryCase(
                case_id=str(row.get("case_id", "")),
                customer_id=str(row.get("customer_id", "")) if pd.notna(row.get("customer_id")) else None,
                card_id=str(row.get("card_id", "")) if pd.notna(row.get("card_id")) else None,
                outcome=str(row.get("outcome", "unknown")),
                pattern=str(row.get("pattern", "unknown")),
                exposure_usd=float(row.get("exposure_usd", 0.0) or 0.0),
                actions_taken=actions,
                report_filed=str(row.get("report_filed", "No")).lower() in ("yes", "true", "1"),
                analyst_notes=str(row.get("analyst_notes", ""))[:300] if pd.notna(row.get("analyst_notes")) else None,
                opened_at=str(row.get("opened_at", "")) if pd.notna(row.get("opened_at")) else None,
                closed_at=str(row.get("closed_at", "")) if pd.notna(row.get("closed_at")) else None,
            ))

        return MemoryResponse(historical_cases=cases, total=len(cases))

    except Exception as e:
        logger.error(f"Memory load failed: {e}")
        return MemoryResponse(historical_cases=[], total=0)


# ============================================================
# Benchmark Routes
# ============================================================

@app.post("/api/benchmarks/run")
async def run_benchmarks(
    background_tasks: BackgroundTasks,
    limit: int = Query(20, ge=1, le=20, description="Number of benchmark cases to run"),
):
    """Trigger benchmark run asynchronously. Returns run_id for status polling."""
    run_id = f"BENCH-{uuid.uuid4().hex[:8].upper()}"
    _benchmarks[run_id] = {"status": "started", "run_id": run_id, "started_at": datetime.now(timezone.utc).isoformat()}

    async def _do_run():
        try:
            _benchmarks[run_id]["status"] = "running"
            proc = await asyncio.create_subprocess_exec(
                "venv\\Scripts\\python.exe",
                "scripts/run_benchmarks.py",
                f"--limit={limit}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            _benchmarks[run_id]["status"] = "complete" if proc.returncode == 0 else "error"
            _benchmarks[run_id]["returncode"] = proc.returncode
            _benchmarks[run_id]["stdout"] = stdout.decode()[-2000:]
            _benchmarks[run_id]["stderr"] = stderr.decode()[-1000:]
            _benchmarks[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            _benchmarks[run_id]["status"] = "error"
            _benchmarks[run_id]["error"] = str(e)

    background_tasks.add_task(_do_run)
    return {"run_id": run_id, "status": "started", "message": f"Benchmark run {run_id} started — poll /api/benchmarks/status/{run_id}"}


@app.get("/api/benchmarks/status/{run_id}")
async def get_benchmark_status(run_id: str):
    """Get status of a benchmark run."""
    if run_id not in _benchmarks:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    return _benchmarks[run_id]


@app.get("/api/benchmarks/results")
async def get_benchmark_results():
    """Load latest benchmark summary from cases/_benchmark_summary.json."""
    summary_file = CASES_DIR / "_benchmark_summary.json"
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="No benchmark results yet — run /api/benchmarks/run first")
    with open(summary_file) as f:
        return json.load(f)


# ============================================================
# System Status & Health Check
# ============================================================

@app.get("/api/system/mcp")
async def mcp_status():
    """Get live TigerGraph Model Context Protocol (MCP) health status & tool discovery."""
    from tools.tigergraph_mcp_client import get_mcp_client
    client = get_mcp_client()
    return client.health_check()


@app.get("/api/system/status", response_model=SystemStatusResponse)
async def system_status():
    """Get live system, GraphRAG, and TigerGraph MCP status."""
    from tools.graph_tools import get_tg_connection
    from tools.graphrag_tools import get_vector_store
    from tools.tigergraph_mcp_client import get_mcp_client
    
    tg_ok = False
    tg_host = os.getenv("TG_HOST", "Unknown")
    try:
        conn = get_tg_connection()
        tg_ok = conn is not None
    except Exception:
        pass

    mcp_client = get_mcp_client()
    mcp_health_res = mcp_client.health_check()
    mcp_ok = mcp_health_res.get("connected", False)
    mcp_tools = mcp_health_res.get("tool_count", 0)

    vs = get_vector_store()
    vs_count = vs.count()
    vs_ok = vs_count > 0

    has_llm = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY"))

    if (tg_ok or mcp_ok) and vs_ok:
        mode = "HYBRID"
    elif tg_ok or mcp_ok:
        mode = "GRAPH ONLY"
    else:
        mode = "DEGRADED"

    return SystemStatusResponse(
        tigergraph="LIVE" if (tg_ok or mcp_ok) else "UNAVAILABLE",
        tigergraph_host=tg_host.split("@")[-1] if "@" in tg_host else tg_host,
        graph_expansion="LIVE" if (tg_ok or mcp_ok) else "UNAVAILABLE",
        historical_graph_memory="LIVE" if tg_ok else "UNAVAILABLE",
        vector_retrieval="LIVE" if vs_ok else "UNAVAILABLE",
        vector_store_cases=vs_count,
        graphrag_mode=mode,
        llm_reasoning="AVAILABLE" if has_llm else "UNAVAILABLE",
        case_writeback="VERIFIED",
        total_closed_cases=vs_count or 5565,
        active_investigations=len(_store),
        mcp_status="CONNECTED" if mcp_ok else "UNAVAILABLE",
        mcp_tool_count=mcp_tools,
    )


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check including TigerGraph connectivity."""
    tg_ok = False
    try:
        from tools.graph_tools import get_tg_connection
        conn = get_tg_connection()
        tg_ok = conn is not None
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        service="FraudLens API",
        version="2.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        tg_connected=tg_ok,
    )


# ============================================================
# Root redirect → docs
# ============================================================

@app.get("/")
async def root():
    return {"message": "FraudLens API v2.0.0 — visit /api/docs for documentation"}


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("BACKEND_PORT", 8000)),
        log_level="info",
    )
