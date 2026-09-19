"""
FraudLens — Policy Engine
==========================
Wraps the policy rules module with higher-level API for the agent.

The policy engine:
  1. Evaluates which policy rules fire given the current case state
  2. Returns which rules triggered and which actions are mandatory
  3. Determines approval routing for each action
  4. Cannot be overridden by LLM reasoning
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from loguru import logger
from policy.rules import (
    check_rule_R1, check_rule_R2, check_rule_R3, check_rule_R4,
    check_rule_R5, check_rule_R6, check_rule_R7, check_rule_R8,
    check_rule_R9, check_rule_R10,
    get_approval_route, requires_SAR, requires_case,
    ApprovalRoute,
)


@dataclass
class PolicyViolation:
    """A policy rule that fired, requiring a specific action."""
    rule_id: str
    rule_description: str
    mandatory_actions: list[str]


@dataclass
class PolicyDecision:
    """Complete policy evaluation result for a case."""
    triggered_rules: list[PolicyViolation] = field(default_factory=list)
    mandatory_actions: list[str] = field(default_factory=list)
    approval_routes: dict[str, ApprovalRoute] = field(default_factory=dict)
    requires_sar: bool = False
    requires_case_creation: bool = False
    escalation_level: Optional[str] = None   # None | "L1" | "L2"


class PolicyEngine:
    """
    Evaluates all policy rules against the current case state.
    Returns mandatory actions and approval routes.
    """

    def evaluate(
        self,
        fraud_probability: float,
        evidence_count: int,
        customer_response: str = "no_response",
        exposure_usd: float = 0.0,
        connected_fraud_cases: int = 0,
        shared_device_count: int = 0,
        txn_sequence: list[dict] = None,
        velocity_count: int = 0,
        is_new_device: bool = False,
        out_of_region: bool = False,
        final_verdict: str = "",
    ) -> PolicyDecision:
        """
        Evaluate all policy rules and return a complete PolicyDecision.

        All inputs must come from structured evidence — NOT from LLM reasoning.
        """
        if txn_sequence is None:
            txn_sequence = []

        decision = PolicyDecision()
        mandatory: set[str] = set()

        # R1 — Immediate block
        if check_rule_R1(fraud_probability, evidence_count):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R1",
                rule_description="High fraud probability with sufficient evidence",
                mandatory_actions=["BLOCK_CARD", "BLOCK_TRANSACTION"],
            ))
            mandatory.update(["BLOCK_CARD", "BLOCK_TRANSACTION"])

        # R2 — Customer denial
        if check_rule_R2(customer_response):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R2",
                rule_description="Customer explicitly denied transaction",
                mandatory_actions=["BLOCK_CARD", "WARN_CUSTOMER"],
            ))
            mandatory.update(["BLOCK_CARD", "WARN_CUSTOMER"])

        # R3 — Monitoring
        if check_rule_R3(fraud_probability):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R3",
                rule_description="Fraud probability above monitoring threshold (0.30)",
                mandatory_actions=["MONITOR_ACCOUNT", "CREATE_CASE"],
            ))
            mandatory.update(["MONITOR_ACCOUNT", "CREATE_CASE"])

        # R4 — Fraud ring
        if check_rule_R4(connected_fraud_cases):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R4",
                rule_description="Multiple connected accounts with fraud history",
                mandatory_actions=["FLAG_FRAUD_RING", "ESCALATE_CASE"],
            ))
            mandatory.update(["FLAG_FRAUD_RING", "ESCALATE_CASE"])

        # R5 — Card testing
        if check_rule_R5(txn_sequence):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R5",
                rule_description="Card testing pattern detected (micro-auths + large txn)",
                mandatory_actions=["BLOCK_CARD", "BLOCK_TRANSACTION"],
            ))
            mandatory.update(["BLOCK_CARD", "BLOCK_TRANSACTION"])

        # R6 — High exposure
        if check_rule_R6(exposure_usd):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R6",
                rule_description=f"High exposure: ${exposure_usd:,.0f} >= $10,000",
                mandatory_actions=["FILE_REPORT", "ESCALATE_CASE"],
            ))
            mandatory.update(["FILE_REPORT", "ESCALATE_CASE"])

        # R7 — Device ring
        if check_rule_R7(shared_device_count):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R7",
                rule_description=f"{shared_device_count} cards share same device profile",
                mandatory_actions=["FLAG_FRAUD_RING", "ESCALATE_CASE"],
            ))
            mandatory.update(["FLAG_FRAUD_RING", "ESCALATE_CASE"])

        # R8 — Velocity
        if check_rule_R8(velocity_count, 24):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R8",
                rule_description=f"Velocity anomaly: {velocity_count} transactions in 24h",
                mandatory_actions=["BLOCK_CARD"],
            ))
            mandatory.add("BLOCK_CARD")

        # R9 — Account takeover indicator
        if check_rule_R9(is_new_device, out_of_region):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R9",
                rule_description="New device + out-of-region: account takeover signal",
                mandatory_actions=["REQUEST_STEP_UP_AUTH"],
            ))
            mandatory.add("REQUEST_STEP_UP_AUTH")

        # R10 — Inconclusive with high probability
        if check_rule_R10(customer_response, fraud_probability):
            decision.triggered_rules.append(PolicyViolation(
                rule_id="R10",
                rule_description="No customer response with high fraud probability",
                mandatory_actions=["BLOCK_CARD", "WARN_CUSTOMER"],
            ))
            mandatory.update(["BLOCK_CARD", "WARN_CUSTOMER"])

        # Finalize
        decision.mandatory_actions = sorted(mandatory)
        decision.approval_routes = {
            action: get_approval_route(action, exposure_usd)
            for action in decision.mandatory_actions
        }
        decision.requires_sar = requires_SAR(
            final_verdict, exposure_usd,
            shared_device_count > 0,
            connected_fraud_cases > 0,
        )
        decision.requires_case_creation = requires_case(fraud_probability)

        # Highest escalation level needed
        routes = list(decision.approval_routes.values())
        if "L2" in routes:
            decision.escalation_level = "L2"
        elif "L1" in routes:
            decision.escalation_level = "L1"

        logger.info(
            f"Policy evaluated | rules_fired={len(decision.triggered_rules)} | "
            f"mandatory_actions={decision.mandatory_actions} | "
            f"escalation={decision.escalation_level} | sar={decision.requires_sar}"
        )
        return decision
