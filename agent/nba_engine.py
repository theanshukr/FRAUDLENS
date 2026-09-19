"""
FraudLens — Next-Best-Action Engine
=====================================
Generates ordered policy-aware action recommendations.

NBA (Next-Best-Action) output contains:
  - Ordered list of recommended actions (by priority)
  - Approval route for each action (auto / L1 / L2)
  - Reason with policy rule citation
  - Initial NBA (before evidence request) vs Final NBA (after)
  - What changed explanation when re-investigation occurred

The NBA engine combines:
  1. Policy engine mandatory actions (non-negotiable)
  2. Agent-recommended actions (based on evidence + risk)
  3. Priority ordering
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field
from loguru import logger

from agent.risk_assessor import RiskAssessment
from policy.policy_engine import PolicyEngine, PolicyDecision


# ============================================================
# Action Recommendation Model
# ============================================================

class ActionRecommendation(BaseModel):
    """A single recommended action with full context."""

    action: str = Field(description="Exact policy action identifier")
    route: Literal["auto", "L1", "L2"] = Field(description="Approval route required")
    reason: str = Field(description="Why this action is recommended")
    policy_rule: str = Field(description="Policy rule number(s) that mandate or support this")
    priority: int = Field(description="Priority order (1 = highest)")
    is_mandatory: bool = Field(description="True if mandated by policy rule (non-negotiable)")
    status: Literal["pending", "approved", "rejected", "executed"] = "pending"


class NBAResult(BaseModel):
    """Complete NBA recommendation result."""

    initial_actions: list[ActionRecommendation] = Field(
        default_factory=list,
        description="Actions recommended before evidence request"
    )
    final_actions: list[ActionRecommendation] = Field(
        default_factory=list,
        description="Actions recommended after re-investigation"
    )
    what_changed: Optional[str] = Field(
        default=None,
        description="Explanation of why initial vs final differ"
    )
    requires_sar: bool = False
    escalation_level: Optional[str] = None


# ============================================================
# NBA Engine
# ============================================================

class NBAEngine:
    """
    Generates ordered, policy-aware Next-Best-Action recommendations.
    """

    def __init__(self):
        self.policy_engine = PolicyEngine()

    def recommend(
        self,
        assessment: RiskAssessment,
        exposure_usd: float = 0.0,
        customer_response: str = "no_response",
        connected_fraud_cases: int = 0,
        shared_device_count: int = 0,
        txn_sequence: list[dict] = None,
        velocity_count: int = 0,
        is_new_device: bool = False,
        out_of_region: bool = False,
        phase: Literal["initial", "final"] = "initial",
    ) -> list[ActionRecommendation]:
        """
        Generate ordered action recommendations for a given assessment.

        Args:
            assessment:           Current risk assessment
            exposure_usd:         Transaction amount / exposure
            customer_response:    "denied" | "confirmed" | "no_response"
            connected_fraud_cases: Count of connected fraud cases
            shared_device_count:  Count of cards sharing device
            txn_sequence:         Transaction sequence for card testing detection
            velocity_count:       Transactions in last 24h
            is_new_device:        Whether transaction used new/unknown device
            out_of_region:        Whether transaction is out of home region
            phase:                "initial" or "final" (after re-investigation)

        Returns:
            Ordered list of ActionRecommendation
        """
        if txn_sequence is None:
            txn_sequence = []

        # 1. Get policy decisions (mandatory actions)
        policy: PolicyDecision = self.policy_engine.evaluate(
            fraud_probability=assessment.fraud_probability,
            evidence_count=len(assessment.supporting_evidence),
            customer_response=customer_response,
            exposure_usd=exposure_usd,
            connected_fraud_cases=connected_fraud_cases,
            shared_device_count=shared_device_count,
            txn_sequence=txn_sequence,
            velocity_count=velocity_count,
            is_new_device=is_new_device,
            out_of_region=out_of_region,
            final_verdict="fraud" if assessment.fraud_probability >= 0.85 else "",
        )

        actions: list[ActionRecommendation] = []
        priority = 1

        # 2. Mandatory policy actions first
        for rule_violation in policy.triggered_rules:
            for action in rule_violation.mandatory_actions:
                if not any(a.action == action for a in actions):
                    actions.append(ActionRecommendation(
                        action=action,
                        route=policy.approval_routes.get(action, "L1"),
                        reason=rule_violation.rule_description,
                        policy_rule=rule_violation.rule_id,
                        priority=priority,
                        is_mandatory=True,
                    ))
                    priority += 1

        # 3. Agent-recommended supplementary actions
        agent_actions = self._recommend_supplementary(assessment, policy, phase)
        for action_name, reason, rule in agent_actions:
            if not any(a.action == action_name for a in actions):
                actions.append(ActionRecommendation(
                    action=action_name,
                    route=policy.approval_routes.get(action_name, "auto"),
                    reason=reason,
                    policy_rule=rule,
                    priority=priority,
                    is_mandatory=False,
                ))
                priority += 1

        # 4. SAR filing
        if policy.requires_sar:
            if not any(a.action == "FILE_REPORT" for a in actions):
                actions.append(ActionRecommendation(
                    action="FILE_REPORT",
                    route="L2",
                    reason="Suspicious Activity Report required by policy",
                    policy_rule="R6/R4",
                    priority=priority,
                    is_mandatory=True,
                ))

        logger.info(
            f"NBA complete [{phase}] | actions={[a.action for a in actions]} | "
            f"escalation={policy.escalation_level}"
        )
        return actions

    def _recommend_supplementary(
        self,
        assessment: RiskAssessment,
        policy: PolicyDecision,
        phase: str,
    ) -> list[tuple[str, str, str]]:
        """Generate agent-recommended (non-mandatory) supplementary actions."""
        supplementary = []

        if assessment.fraud_probability >= 0.30 and policy.requires_case_creation:
            supplementary.append((
                "CREATE_CASE",
                f"Fraud probability {assessment.fraud_probability:.0%} exceeds case creation threshold",
                "R_CASE",
            ))

        if assessment.risk_level in ("HIGH", "CRITICAL"):
            supplementary.append((
                "MONITOR_ACCOUNT",
                "High risk level warrants enhanced account monitoring",
                "R3",
            ))

        if assessment.fraud_probability < 0.15:
            supplementary.append((
                "ALLOW_TRANSACTION",
                "Low fraud probability — transaction appears legitimate",
                "R_CLEAR",
            ))

        return supplementary

    def compute_what_changed(
        self,
        initial: list[ActionRecommendation],
        final: list[ActionRecommendation],
        initial_assessment: RiskAssessment,
        final_assessment: RiskAssessment,
        new_evidence_claim: str,
    ) -> str:
        """
        Generate a plain-English explanation of why the NBA changed.
        Used for the 'Why did my decision change?' component.
        """
        initial_actions = {a.action for a in initial}
        final_actions   = {a.action for a in final}

        added   = final_actions - initial_actions
        removed = initial_actions - final_actions

        prob_delta = final_assessment.fraud_probability - initial_assessment.fraud_probability
        conf_delta = final_assessment.confidence - initial_assessment.confidence

        lines = [
            f"New evidence: '{new_evidence_claim}'",
            f"",
            f"Risk changed: {initial_assessment.risk_level} → {final_assessment.risk_level}",
            f"Fraud probability: {initial_assessment.fraud_probability:.0%} → {final_assessment.fraud_probability:.0%} "
            f"({'↑' if prob_delta > 0 else '↓'}{abs(prob_delta):.0%})",
            f"Confidence: {initial_assessment.confidence:.0%} → {final_assessment.confidence:.0%} "
            f"({'↑' if conf_delta > 0 else '↓'}{abs(conf_delta):.0%})",
        ]

        if added:
            lines.append(f"")
            lines.append(f"New actions required: {', '.join(sorted(added))}")
        if removed:
            lines.append(f"Actions no longer needed: {', '.join(sorted(removed))}")

        return "\n".join(lines)
