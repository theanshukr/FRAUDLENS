"""
FraudLens - Policy Tools
=========================
MCP tool wrappers for policy engine functions.
Exposes policy rules as callable MCP tools for the agent.
"""
from policy.policy_engine import PolicyEngine

_engine = PolicyEngine()

def evaluate_policy(fraud_probability: float, evidence_count: int, **kwargs) -> dict:
    """Evaluate all policy rules for the given case state."""
    decision = _engine.evaluate(fraud_probability, evidence_count, **kwargs)
    return {
        "triggered_rules": [v.rule_id for v in decision.triggered_rules],
        "mandatory_actions": decision.mandatory_actions,
        "approval_routes": decision.approval_routes,
        "requires_sar": decision.requires_sar,
        "escalation_level": decision.escalation_level,
    }
