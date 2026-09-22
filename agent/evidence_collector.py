"""
FraudLens — Evidence Collector
================================
Executes investigation plan steps via TigerGraph graph tools and
structures each finding as a typed EvidenceItem with full semantic
meaning — not just a generic "query ran" placeholder.

Every piece of evidence must have:
  - A clear claim (what was found)
  - A source (graph | document | customer | external)
  - A reference to the query or document that produced it
  - The entity IDs involved
  - A confidence score
  - A timestamp
  - supports_fraud: True / False / None

The evidence list is the core input to the Risk Assessor.
The `signals` dict accumulates structured numeric/boolean signals
extracted across all steps for use by the NBA engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from loguru import logger


# ============================================================
# Evidence Data Models
# ============================================================

class EvidenceItem(BaseModel):
    """A single piece of evidence discovered during investigation."""

    evidence_id: str = Field(description="Unique ID for this evidence item")
    claim: str = Field(description="What was found — plain English statement")
    source: Literal["graph", "document", "customer", "external"] = Field(
        description="Where this evidence came from"
    )
    ref: str = Field(
        description="Query name or document section that produced this evidence"
    )
    entity_ids: list[str] = Field(
        default_factory=list,
        description="IDs of entities referenced (txn IDs, card IDs, device IDs, etc.)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in this specific evidence item (0.0-1.0)"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Optional[dict] = Field(
        default=None,
        description="Raw query response for audit purposes"
    )
    supports_fraud: Optional[bool] = Field(
        default=None,
        description="True if evidence supports fraud, False if contradicts, None if neutral"
    )


# ============================================================
# Evidence Collector
# ============================================================

class EvidenceCollector:
    """
    Executes investigation plan steps via TigerGraph graph tools
    and returns structured evidence items.

    If `tg_conn` is provided (a live pyTigerGraph connection), real
    queries are executed. Otherwise falls back to mock responses for
    dev / unit testing.

    The `signals` dict accumulates structured numeric/boolean values
    extracted from raw query results. The Orchestrator reads this dict
    to pass correct values into the NBA engine.

    Usage:
        collector = EvidenceCollector(tg_conn=conn)
        evidence  = await collector.collect(plan=plan, prior_evidence=[])
        signals   = collector.signals   # e.g. {"risk_score": 0.87, "shared_device_count": 3, ...}
    """

    def __init__(self, tg_conn: Any = None, mcp_client: Any = None):
        """
        Args:
            tg_conn:    Live pyTigerGraph connection (preferred).
            mcp_client: Legacy MCP client — kept for compatibility.
                        If both are None, falls back to mock responses.
        """
        self.tg_conn = tg_conn
        self.mcp_client = mcp_client
        self._evidence_counter = 0

        # Accumulated signals — reset each collect() call
        self.signals: dict = {
            "risk_score": 0.0,
            "amount": 0.0,
            "channel": "",
            "shared_device_count": 0,
            "ring_size": 0,
            "card_testing_detected": False,
            "is_new_device": False,
            "out_of_region": False,
            "velocity_count": 0,
            "txn_sequence": [],    # list of {"amount": float, "ts": str}
            "connected_fraud_cases": 0,
            "device_profile_id": "",
            "connected_card_ids": [],
        }

    def _next_id(self) -> str:
        self._evidence_counter += 1
        return f"EVD-{self._evidence_counter:04d}"

    def _reset_signals(self) -> None:
        """Reset signal accumulator for a fresh collection round."""
        self.signals = {
            "risk_score": 0.0,
            "amount": 0.0,
            "channel": "",
            "shared_device_count": 0,
            "ring_size": 0,
            "card_testing_detected": False,
            "is_new_device": False,
            "out_of_region": False,
            "velocity_count": 0,
            "txn_sequence": [],
            "connected_fraud_cases": 0,
            "device_profile_id": "",
            "connected_card_ids": [],
        }

    async def collect(
        self,
        plan,           # InvestigationPlan
        prior_evidence: list[EvidenceItem] = None,
    ) -> list[EvidenceItem]:
        """
        Execute all steps in the investigation plan and return evidence.

        Args:
            plan:           InvestigationPlan from planner.py
            prior_evidence: Evidence from previous investigation rounds

        Returns:
            List of EvidenceItem objects
        """
        if prior_evidence is None:
            prior_evidence = []

        self._reset_signals()
        evidence: list[EvidenceItem] = []

        for step in plan.steps:
            logger.info(f"Executing step: {step.query_name} | params={step.params}")
            try:
                result = await self._execute_step(step)
                items  = self._parse_result(step, result)
                evidence.extend(items)
                logger.info(f"    → {len(items)} evidence items from {step.query_name}")
            except Exception as e:
                logger.warning(f"Step {step.step_id} failed: {e}")
                # Add a "no data" evidence item so gap is visible in case record
                evidence.append(EvidenceItem(
                    evidence_id=self._next_id(),
                    claim=f"Query {step.query_name} returned no data or failed: {str(e)[:120]}",
                    source="graph",
                    ref=step.query_name,
                    entity_ids=[],
                    confidence=0.0,
                    supports_fraud=None,
                ))

        return evidence

    # --------------------------------------------------------
    # Step Execution
    # --------------------------------------------------------

    async def _execute_step(self, step) -> dict:
        """Execute a single investigation step via live TG or mock."""
        if self.tg_conn is not None:
            return self._live_execute(step)
        return self._mock_response(step.query_name)

    def _live_execute(self, step) -> dict:
        """Execute step via pyTigerGraph installed query."""
        from tools import graph_tools as gt

        # Map query_name → graph_tools function
        dispatch = {
            "get_transaction":         lambda: gt.get_transaction(self.tg_conn, step.params.get("txn_id", "")),
            "get_card_history":        lambda: gt.get_card_history(self.tg_conn, step.params.get("card_id", ""), step.params.get("days", 30)),
            "get_card_window":         lambda: gt.get_card_window(self.tg_conn, step.params.get("card_id", ""), step.params.get("hours", 24)),
            "get_device_neighbors":    lambda: gt.get_device_neighbors(self.tg_conn, step.params.get("device_profile_id", self.signals.get("device_profile_id", ""))),
            "find_shared_devices":     lambda: gt.find_shared_devices(self.tg_conn, step.params.get("card_id", "")),
            "find_connected_cards":    lambda: gt.find_connected_cards(self.tg_conn, step.params.get("card_id", ""), step.params.get("hops", 2)),
            "detect_card_testing":     lambda: gt.detect_card_testing(self.tg_conn, step.params.get("card_id", ""), step.params.get("hours", 24)),
            "detect_new_device_usage": lambda: gt.get_card_history(self.tg_conn, step.params.get("card_id", ""), 30),
            "detect_velocity_anomaly": lambda: gt.detect_velocity_anomaly(self.tg_conn, step.params.get("card_id", ""), step.params.get("hours", 24)),
            "detect_out_of_region":    lambda: gt.find_shared_devices(self.tg_conn, step.params.get("card_id", "")),
            "search_similar_cases":    lambda: gt.search_similar_cases(self.tg_conn, step.params.get("pattern", ""), step.params.get("device_profile_id", ""), step.params.get("card_ids", [])),
        }

        fn = dispatch.get(step.query_name)
        if fn is None:
            raise ValueError(f"No live handler for query: {step.query_name}")
        return fn()

    # --------------------------------------------------------
    # Per-Query Evidence Parsers
    # --------------------------------------------------------

    def _parse_result(self, step, result: dict) -> list[EvidenceItem]:
        """Route to per-query parser for semantic EvidenceItem generation."""
        parsers = {
            "get_transaction":         self._parse_get_transaction,
            "get_card_history":        self._parse_get_card_history,
            "get_card_window":         self._parse_get_card_history,
            "get_device_neighbors":    self._parse_get_device_neighbors,
            "find_shared_devices":     self._parse_find_shared_devices,
            "find_connected_cards":    self._parse_find_connected_cards,
            "detect_card_testing":     self._parse_detect_card_testing,
            "detect_new_device_usage": self._parse_detect_new_device,
            "detect_out_of_region":    self._parse_detect_out_of_region,
            "detect_velocity_anomaly": self._parse_detect_velocity_anomaly,
            "search_similar_cases":    self._parse_search_similar_cases,
        }
        parser = parsers.get(step.query_name, self._parse_generic)
        return parser(step, result)

    def _parse_get_transaction(self, step, result: dict) -> list[EvidenceItem]:
        """Parse get_transaction → extract risk_score, amount, device_profile_id."""
        items = []
        rows = result.get("results", [])
        entity_ids = result.get("entity_ids", [])

        # Parse nested TigerGraph result format
        txn_data = {}
        for row in rows:
            if isinstance(row, dict):
                # TG returns list of dicts; data may be nested under key names
                if "attributes" in row:
                    txn_data.update(row["attributes"])
                else:
                    txn_data.update(row)

        risk_score = float(txn_data.get("risk_score", txn_data.get("isFraud", 0.0)) or 0.0)
        amount = float(txn_data.get("amount", txn_data.get("TransactionAmt", 0.0)) or 0.0)
        channel = str(txn_data.get("channel", txn_data.get("ProductCD", "")))
        device_info = str(txn_data.get("device_info", txn_data.get("DeviceInfo", "")))

        # Update signals
        self.signals["risk_score"] = max(self.signals["risk_score"], risk_score)
        self.signals["amount"] = max(self.signals["amount"], amount)
        self.signals["channel"] = channel
        if device_info:
            self.signals["device_profile_id"] = device_info

        # Synthesize evidence claim
        if risk_score >= 0.8:
            claim = (
                f"Transaction flagged with high risk score {risk_score:.2f} — "
                f"amount ${amount:.2f} via {channel} channel. Strong fraud signal from risk model."
            )
            supports_fraud = True
            confidence = 0.85
        elif risk_score >= 0.5:
            claim = (
                f"Transaction has elevated risk score {risk_score:.2f} — "
                f"amount ${amount:.2f} via {channel} channel. Moderate concern."
            )
            supports_fraud = True
            confidence = 0.65
        elif risk_score > 0.0:
            claim = (
                f"Transaction risk score {risk_score:.2f} is below fraud threshold — "
                f"amount ${amount:.2f} via {channel} channel. Low fraud signal."
            )
            supports_fraud = False
            confidence = 0.60
        else:
            claim = f"Transaction retrieved — amount ${amount:.2f} via {channel}. Risk score unavailable."
            supports_fraud = None
            confidence = 0.4

        items.append(EvidenceItem(
            evidence_id=self._next_id(),
            claim=claim,
            source="graph",
            ref="get_transaction",
            entity_ids=entity_ids,
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data=txn_data,
        ))
        return items

    def _parse_get_card_history(self, step, result: dict) -> list[EvidenceItem]:
        """Parse card history — detect micro-auth sequences, build txn_sequence signal."""
        items = []
        rows = result.get("results", [])
        entity_ids = result.get("entity_ids", [])

        txns = []
        for row in rows:
            if isinstance(row, dict):
                data = row.get("attributes", row)
                try:
                    amount = float(data.get("amount", data.get("TransactionAmt", 0)) or 0)
                    ts = str(data.get("ts", data.get("TransactionDT", "")))
                    txns.append({"amount": amount, "ts": ts})
                except (ValueError, TypeError):
                    pass

        # If no structured rows, check if result has a flat list
        if not txns and isinstance(rows, list):
            for row in rows:
                if isinstance(row, (int, float)):
                    txns.append({"amount": float(row), "ts": ""})

        self.signals["txn_sequence"] = txns

        micro_txns = [t for t in txns if t["amount"] < 5.0]
        large_txns = [t for t in txns if t["amount"] >= 100.0]

        if len(micro_txns) >= 3 and large_txns:
            claim = (
                f"Card history shows {len(micro_txns)} micro-transactions (< $5) "
                f"followed by {len(large_txns)} large transaction(s) — "
                f"classic card testing pattern."
            )
            supports_fraud = True
            confidence = 0.85
        elif len(txns) > 10:
            claim = f"Card history shows {len(txns)} transactions — unusually high volume."
            supports_fraud = True
            confidence = 0.60
        elif txns:
            claim = f"Card history retrieved: {len(txns)} transactions. No anomalous pattern detected."
            supports_fraud = None
            confidence = 0.55
        else:
            claim = "Card history returned no transactions — card may be new or inactive."
            supports_fraud = None
            confidence = 0.40

        items.append(EvidenceItem(
            evidence_id=self._next_id(),
            claim=claim,
            source="graph",
            ref=step.query_name,
            entity_ids=entity_ids,
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data={"transaction_count": len(txns), "micro_txn_count": len(micro_txns)},
        ))
        return items

    def _parse_get_device_neighbors(self, step, result: dict) -> list[EvidenceItem]:
        """Parse device neighbor query — count cards sharing device."""
        items = []
        rows = result.get("results", [])
        entity_ids = result.get("entity_ids", [])
        shared_count = result.get("shared_device_count", len(rows))

        self.signals["shared_device_count"] = max(self.signals["shared_device_count"], shared_count)

        if shared_count >= 3:
            claim = (
                f"Device profile is shared by {shared_count} different cards — "
                f"strong organized fraud ring signal (threshold: 3)."
            )
            supports_fraud = True
            confidence = 0.85
        elif shared_count >= 2:
            claim = f"Device profile is shared by {shared_count} cards — moderate shared-device signal."
            supports_fraud = True
            confidence = 0.70
        elif shared_count == 1:
            claim = "Device profile is used by only 1 card — no device sharing detected."
            supports_fraud = False
            confidence = 0.65
        else:
            claim = "No device neighbors found — device profile is unique to this transaction."
            supports_fraud = False
            confidence = 0.55

        items.append(EvidenceItem(
            evidence_id=self._next_id(),
            claim=claim,
            source="graph",
            ref="get_device_neighbors",
            entity_ids=entity_ids,
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data={"shared_device_count": shared_count},
        ))
        return items

    def _parse_find_shared_devices(self, step, result: dict) -> list[EvidenceItem]:
        """Parse shared device query."""
        return self._parse_get_device_neighbors(step, result)

    def _parse_find_connected_cards(self, step, result: dict) -> list[EvidenceItem]:
        """Parse multi-hop card connection graph — extract ring size."""
        items = []
        rows = result.get("results", [])
        entity_ids = result.get("entity_ids", [])
        ring_size = result.get("ring_size", len(rows))

        connected_ids = []
        for row in rows:
            if isinstance(row, dict):
                cid = row.get("card_id", row.get("v_id", ""))
                if cid:
                    connected_ids.append(str(cid))

        self.signals["ring_size"] = max(self.signals["ring_size"], ring_size)
        self.signals["connected_card_ids"] = list(set(
            self.signals["connected_card_ids"] + connected_ids
        ))
        # Count how many connected cards have fraud history
        # (approximated as ring_size when fraud outcome known)
        if ring_size >= 2:
            self.signals["connected_fraud_cases"] = max(
                self.signals["connected_fraud_cases"], ring_size - 1
            )

        if ring_size >= 4:
            claim = (
                f"Multi-hop graph analysis reveals a connected fraud ring of {ring_size} cards "
                f"via shared device profiles — organized ring detected."
            )
            supports_fraud = True
            confidence = 0.90
        elif ring_size >= 2:
            claim = (
                f"{ring_size} cards are connected through shared devices — "
                f"potential coordinated fraud activity."
            )
            supports_fraud = True
            confidence = 0.75
        else:
            claim = "No connected cards found via device graph — this card appears isolated."
            supports_fraud = False
            confidence = 0.60

        items.append(EvidenceItem(
            evidence_id=self._next_id(),
            claim=claim,
            source="graph",
            ref="find_connected_cards",
            entity_ids=entity_ids + connected_ids,
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data={"ring_size": ring_size, "connected_card_ids": connected_ids},
        ))
        return items

    def _parse_detect_card_testing(self, step, result: dict) -> list[EvidenceItem]:
        """Parse card testing detection query — binary flag."""
        items = []
        entity_ids = result.get("entity_ids", [])
        detected = result.get("card_testing_detected", False)

        # Also check results list for detection signal
        if not detected and result.get("results"):
            detected = len(result["results"]) > 0

        self.signals["card_testing_detected"] = self.signals["card_testing_detected"] or detected

        if detected:
            claim = (
                "Card testing pattern DETECTED — micro-authorization burst followed by "
                "large transaction. This is a definitive fraud indicator (R5 trigger)."
            )
            supports_fraud = True
            confidence = 0.92
        else:
            claim = "No card testing pattern detected — transaction sequence does not show micro-auth burst."
            supports_fraud = False
            confidence = 0.70

        items.append(EvidenceItem(
            evidence_id=self._next_id(),
            claim=claim,
            source="graph",
            ref="detect_card_testing",
            entity_ids=entity_ids,
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data={"card_testing_detected": detected},
        ))
        return items

    def _parse_detect_new_device(self, step, result: dict) -> list[EvidenceItem]:
        """Parse new device usage detection."""
        items = []
        entity_ids = result.get("entity_ids", [])
        is_new = result.get("is_new_device", False)

        if not is_new and result.get("results"):
            # Heuristic: if card history shows < 2 prior transactions, device is effectively new
            rows = result.get("results", [])
            is_new = len(rows) < 2

        self.signals["is_new_device"] = self.signals["is_new_device"] or is_new

        if is_new:
            claim = (
                "Transaction originated from a new/unrecognized device — "
                "no prior transaction history from this device profile. Account takeover signal."
            )
            supports_fraud = True
            confidence = 0.78
        else:
            claim = "Transaction device profile matches prior usage history — familiar device."
            supports_fraud = False
            confidence = 0.65

        items.append(EvidenceItem(
            evidence_id=self._next_id(),
            claim=claim,
            source="graph",
            ref="detect_new_device_usage",
            entity_ids=entity_ids,
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data={"is_new_device": is_new},
        ))
        return items

    def _parse_detect_out_of_region(self, step, result: dict) -> list[EvidenceItem]:
        """Parse out-of-region detection."""
        items = []
        entity_ids = result.get("entity_ids", [])
        out_of_region = result.get("out_of_region", False)

        if not out_of_region and result.get("results"):
            out_of_region = len(result["results"]) > 0

        self.signals["out_of_region"] = self.signals["out_of_region"] or out_of_region

        if out_of_region:
            claim = (
                "Transaction occurred in a region inconsistent with this account's "
                "billing/home address — geographic anomaly detected."
            )
            supports_fraud = True
            confidence = 0.75
        else:
            claim = "Transaction region matches account's billing/home region — no geographic anomaly."
            supports_fraud = False
            confidence = 0.60

        items.append(EvidenceItem(
            evidence_id=self._next_id(),
            claim=claim,
            source="graph",
            ref="detect_out_of_region",
            entity_ids=entity_ids,
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data={"out_of_region": out_of_region},
        ))
        return items

    def _parse_detect_velocity_anomaly(self, step, result: dict) -> list[EvidenceItem]:
        """Parse velocity anomaly — extract transaction count."""
        items = []
        entity_ids = result.get("entity_ids", [])
        rows = result.get("results", [])
        velocity = result.get("velocity_count", len(rows))

        self.signals["velocity_count"] = max(self.signals["velocity_count"], velocity)

        if velocity > 10:
            claim = (
                f"Velocity anomaly detected: {velocity} transactions in the analysis window — "
                f"exceeds threshold of 10 (R8 trigger)."
            )
            supports_fraud = True
            confidence = 0.85
        elif velocity > 5:
            claim = f"Elevated transaction velocity: {velocity} transactions detected. Moderate anomaly."
            supports_fraud = True
            confidence = 0.65
        else:
            claim = f"Transaction velocity is normal: {velocity} transactions. No velocity anomaly."
            supports_fraud = False
            confidence = 0.65

        items.append(EvidenceItem(
            evidence_id=self._next_id(),
            claim=claim,
            source="graph",
            ref="detect_velocity_anomaly",
            entity_ids=entity_ids,
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data={"velocity_count": velocity},
        ))
        return items

    def _parse_search_similar_cases(self, step, result: dict) -> list[EvidenceItem]:
        """Parse similar case search — note: primary handling is in memory_retrieval.py."""
        items = []
        rows = result.get("results", [])
        entity_ids = result.get("entity_ids", [])
        fraud_cases = [r for r in rows if isinstance(r, dict) and r.get("outcome") == "fraud"]

        if fraud_cases:
            claim = (
                f"Historical memory: {len(fraud_cases)} similar closed cases resulted in "
                f"fraud verdicts — pattern has precedent in case history."
            )
            supports_fraud = True
            confidence = 0.80
        elif rows:
            claim = f"Historical memory: {len(rows)} similar cases found — mixed outcomes."
            supports_fraud = None
            confidence = 0.60
        else:
            claim = "No similar historical cases found — this pattern is novel or data is limited."
            supports_fraud = None
            confidence = 0.40

        items.append(EvidenceItem(
            evidence_id=self._next_id(),
            claim=claim,
            source="document",
            ref="search_similar_cases",
            entity_ids=entity_ids,
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data={"result_count": len(rows), "fraud_case_count": len(fraud_cases)},
        ))
        return items

    def _parse_generic(self, step, result: dict) -> list[EvidenceItem]:
        """Fallback parser for any unrecognized query."""
        return [EvidenceItem(
            evidence_id=self._next_id(),
            claim=f"Query {step.query_name} returned {len(result.get('results', []))} result(s).",
            source="graph",
            ref=step.query_name,
            entity_ids=result.get("entity_ids", []),
            confidence=0.50,
            raw_data=result,
            supports_fraud=None,
        )]

    # --------------------------------------------------------
    # Mock Responses (dev / unit test fallback)
    # --------------------------------------------------------

    def _mock_response(self, query_name: str) -> dict:
        """Return realistic mock responses for development without TigerGraph connection."""
        mocks = {
            "get_transaction": {
                "results": [{"risk_score": 0.87, "amount": 542.0, "channel": "W", "DeviceInfo": "MOCK_DEVICE_001"}],
                "entity_ids": ["T_MOCK_001"],
            },
            "get_card_history": {
                "results": [
                    {"amount": 1.0, "ts": "2026-09-20T10:00:00"},
                    {"amount": 1.5, "ts": "2026-09-20T10:01:00"},
                    {"amount": 2.0, "ts": "2026-09-20T10:02:00"},
                    {"amount": 542.0, "ts": "2026-09-20T10:15:00"},
                ],
                "entity_ids": ["CARD_MOCK_001"],
            },
            "get_card_window": {
                "results": [
                    {"amount": 1.0}, {"amount": 1.5}, {"amount": 2.0}, {"amount": 542.0},
                ],
                "entity_ids": ["CARD_MOCK_001"],
            },
            "get_device_neighbors": {
                "results": [{"card_id": "CARD_A"}, {"card_id": "CARD_B"}, {"card_id": "CARD_C"}],
                "entity_ids": ["MOCK_DEVICE_001"],
                "shared_device_count": 3,
            },
            "find_shared_devices": {
                "results": [{"card_id": "CARD_A"}, {"card_id": "CARD_B"}],
                "entity_ids": ["CARD_MOCK_001"],
                "shared_device_count": 2,
            },
            "find_connected_cards": {
                "results": [{"card_id": "CARD_B"}, {"card_id": "CARD_C"}],
                "entity_ids": ["CARD_B", "CARD_C"],
                "ring_size": 3,
            },
            "detect_card_testing": {
                "results": [{"micro_count": 3}],
                "card_testing_detected": True,
                "entity_ids": ["T_MOCK_000"],
            },
            "detect_new_device_usage": {
                "results": [],
                "is_new_device": True,
                "entity_ids": ["CARD_MOCK_001"],
            },
            "detect_out_of_region": {
                "results": [{"region_mismatch": True}],
                "out_of_region": True,
                "entity_ids": ["CARD_MOCK_001"],
            },
            "detect_velocity_anomaly": {
                "results": [],
                "velocity_count": 4,
                "entity_ids": ["CARD_MOCK_001"],
            },
            "search_similar_cases": {
                "results": [
                    {"case_id": "CC-0141", "pattern": "card_testing", "outcome": "fraud"},
                    {"case_id": "CC-2671", "pattern": "shared_device_ring", "outcome": "fraud"},
                ],
                "entity_ids": ["CC-0141", "CC-2671"],
            },
        }
        return mocks.get(query_name, {"results": [], "entity_ids": []})
