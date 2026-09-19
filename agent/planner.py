"""
FraudLens — Investigation Planner
==================================
Builds a structured investigation plan based on the trigger type,
transaction ID, card ID, and customer ID.

The planner determines:
- Which graph queries to run
- In what order
- With what priority
- Why each step is needed

Different trigger types result in different investigation plans:
  - risk_score      → Focus on transaction patterns + device sharing
  - customer_report → Focus on account takeover signals
  - analyst_request → Comprehensive investigation across all dimensions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from loguru import logger


class TriggerType(str, Enum):
    RISK_SCORE = "risk_score"
    CUSTOMER_REPORT = "customer_report"
    ANALYST_REQUEST = "analyst_request"
    SYSTEM_ALERT = "system_alert"


class QueryPriority(str, Enum):
    P0 = "P0"   # Must run — critical path
    P1 = "P1"   # Should run — important signal
    P2 = "P2"   # Nice to have — supplementary


@dataclass
class InvestigationStep:
    """A single step in the investigation plan."""
    step_id: str
    query_name: str
    description: str
    priority: QueryPriority
    params: dict
    reason: str
    depends_on: list[str] = field(default_factory=list)


@dataclass
class InvestigationPlan:
    """Complete ordered investigation plan for a case."""
    trigger_type: TriggerType
    txn_id: str
    card_id: Optional[str]
    customer_id: Optional[str]
    steps: list[InvestigationStep] = field(default_factory=list)
    hypothesis: str = ""


def build_investigation_plan(
    trigger: str,
    txn_id: str,
    card_id: Optional[str] = None,
    customer_id: Optional[str] = None,
) -> InvestigationPlan:
    """
    Build a structured investigation plan based on the trigger type.

    Args:
        trigger:     Trigger type string (risk_score | customer_report | analyst_request)
        txn_id:      Flagged transaction ID
        card_id:     Associated card ID (if known)
        customer_id: Associated customer ID (if known)

    Returns:
        InvestigationPlan with ordered steps
    """
    trigger_type = TriggerType(trigger)
    plan = InvestigationPlan(
        trigger_type=trigger_type,
        txn_id=txn_id,
        card_id=card_id,
        customer_id=customer_id,
    )

    # --- Step 1: Always get the full transaction record first ---
    plan.steps.append(InvestigationStep(
        step_id="step_01",
        query_name="get_transaction",
        description="Retrieve full transaction + identity record",
        priority=QueryPriority.P0,
        params={"txn_id": txn_id},
        reason="Baseline: understand what happened in this transaction",
    ))

    # --- Step 2: Card history ---
    if card_id:
        plan.steps.append(InvestigationStep(
            step_id="step_02",
            query_name="get_card_history",
            description="Retrieve card transaction history (last 30 days)",
            priority=QueryPriority.P0,
            params={"card_id": card_id, "days": 30},
            reason="Establish behavioral baseline; detect velocity anomalies",
            depends_on=["step_01"],
        ))

    # --- Step 3: Device neighbors ---
    plan.steps.append(InvestigationStep(
        step_id="step_03",
        query_name="get_device_neighbors",
        description="Find all accounts that used the same device",
        priority=QueryPriority.P0,
        params={"device_profile_id": "__from_step_01__"},
        reason="Shared device is a strong fraud ring signal",
        depends_on=["step_01"],
    ))

    # --- Step 4: Connected cards (fraud ring) ---
    if card_id:
        plan.steps.append(InvestigationStep(
            step_id="step_04",
            query_name="find_connected_cards",
            description="Discover connected cards via device graph (2-hop)",
            priority=QueryPriority.P0,
            params={"card_id": card_id, "hops": 2},
            reason="Multi-hop connections reveal organized fraud rings",
            depends_on=["step_02"],
        ))

    # --- Step 5: Pattern detection (trigger-specific) ---
    if trigger_type == TriggerType.RISK_SCORE:
        plan.steps.append(InvestigationStep(
            step_id="step_05",
            query_name="detect_card_testing",
            description="Check for micro-auth burst pattern (card testing)",
            priority=QueryPriority.P0,
            params={"card_id": card_id, "hours": 24},
            reason="High risk score often co-occurs with card testing behavior",
            depends_on=["step_02"],
        ))
        plan.hypothesis = "Transaction flagged by risk model — check card testing and device sharing"

    elif trigger_type == TriggerType.CUSTOMER_REPORT:
        plan.steps.append(InvestigationStep(
            step_id="step_05",
            query_name="detect_new_device_usage",
            description="Check for transactions from new/unknown devices",
            priority=QueryPriority.P0,
            params={"card_id": card_id},
            reason="Customer report of unauthorized use → check device mismatch",
            depends_on=["step_01"],
        ))
        plan.hypothesis = "Customer reported unauthorized activity — check account takeover signals"

    elif trigger_type == TriggerType.ANALYST_REQUEST:
        plan.steps.append(InvestigationStep(
            step_id="step_05a",
            query_name="detect_velocity_anomaly",
            description="Check for unusual transaction velocity",
            priority=QueryPriority.P1,
            params={"card_id": card_id, "hours": 72},
            reason="Analyst-requested review — comprehensive pattern check",
            depends_on=["step_02"],
        ))
        plan.hypothesis = "Analyst flagged for review — comprehensive investigation across all patterns"

    # --- Step 6: Similar cases from memory (always) ---
    plan.steps.append(InvestigationStep(
        step_id="step_06",
        query_name="search_similar_cases",
        description="Retrieve similar historical fraud cases from memory",
        priority=QueryPriority.P1,
        params={
            "pattern": "__from_initial_assessment__",
            "device_profile_id": "__from_step_01__",
            "card_ids": "__from_step_04__",
        },
        reason="Historical case memory informs risk assessment and NBA",
        depends_on=["step_04"],
    ))

    logger.info(
        f"Investigation plan built | trigger={trigger} | txn={txn_id} | steps={len(plan.steps)}"
    )
    return plan


if __name__ == "__main__":
    # Quick smoke test
    plan = build_investigation_plan(
        trigger="risk_score",
        txn_id="T_12345",
        card_id="card1_card2_card3_credit_card5_charge",
        customer_id="C_001",
    )
    for step in plan.steps:
        print(f"  [{step.priority}] {step.step_id}: {step.query_name} — {step.description}")
