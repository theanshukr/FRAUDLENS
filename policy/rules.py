"""
FraudLens — Policy Rules Engine
=================================
All fraud policy rules are encoded as deterministic Python functions.

CRITICAL PRINCIPLE: The agent CANNOT override policy via LLM reasoning.
Policy rules are hard constraints — if a rule fires, its action is mandatory.

Rules R1–R10 correspond to the FraudLens policy document.
Actions A1–A14 correspond to the 14 policy actions.
"""

from __future__ import annotations

from typing import Literal

ApprovalRoute = Literal["auto", "L1", "L2"]

# ============================================================
# Policy Rules (R1–R10)
# ============================================================

def check_rule_R1(fraud_probability: float, evidence_count: int) -> bool:
    """
    R1 — Immediate Block Rule
    If fraud_probability >= 0.85 AND at least 2 independent evidence items,
    BLOCK_CARD is mandatory without L2 approval delay.
    """
    return fraud_probability >= 0.85 and evidence_count >= 2


def check_rule_R2(customer_response: str) -> bool:
    """
    R2 — Customer Denial Rule
    If customer explicitly denies a transaction, immediate block required.
    customer_response: "denied" | "confirmed" | "no_response"
    """
    return customer_response == "denied"


def check_rule_R3(fraud_probability: float) -> bool:
    """
    R3 — Monitoring Threshold
    If fraud_probability >= 0.30, add account to enhanced monitoring.
    """
    return fraud_probability >= 0.30


def check_rule_R4(connected_fraud_cases: int) -> bool:
    """
    R4 — Fraud Ring Rule
    If 2+ connected accounts previously involved in fraud cases,
    escalate to L2 and flag for SAR filing.
    """
    return connected_fraud_cases >= 2


def check_rule_R5(txn_sequence: list[dict]) -> bool:
    """
    R5 — Card Testing Rule
    If sequence has 3+ micro-transactions (< $5) followed by large transaction,
    immediately block card.
    txn_sequence: list of {"amount": float, "ts": datetime}
    """
    micro_txns = [t for t in txn_sequence if t.get("amount", 0) < 5.0]
    large_txns = [t for t in txn_sequence if t.get("amount", 0) >= 100.0]
    return len(micro_txns) >= 3 and len(large_txns) >= 1


def check_rule_R6(exposure_usd: float) -> bool:
    """
    R6 — High Exposure Rule
    If fraud exposure >= $10,000, mandatory SAR filing and L2 approval.
    """
    return exposure_usd >= 10_000.0


def check_rule_R7(shared_device_count: int) -> bool:
    """
    R7 — Device Ring Rule
    If 3+ cards share the same device profile, flag as organized fraud ring.
    Requires L2 approval and analyst review.
    """
    return shared_device_count >= 3


def check_rule_R8(velocity_count: int, hours: int) -> bool:
    """
    R8 — Velocity Rule
    If more than 10 transactions in 24 hours, block card immediately.
    """
    return velocity_count > 10 and hours <= 24


def check_rule_R9(is_new_device: bool, out_of_region: bool) -> bool:
    """
    R9 — Account Takeover Indicator
    If transaction from new device AND out-of-home-region, require step-up auth.
    """
    return is_new_device and out_of_region


def check_rule_R10(customer_response: str, fraud_probability: float) -> bool:
    """
    R10 — Inconclusive Rule
    If customer does not respond AND fraud_probability > 0.50,
    treat as confirmed fraud for precautionary blocking.
    """
    return customer_response == "no_response" and fraud_probability > 0.50


# ============================================================
# Approval Routes
# ============================================================

# Action → (min_approval_route, exposure_threshold_for_upgrade)
_ACTION_ROUTES: dict[str, tuple[ApprovalRoute, float]] = {
    "ALLOW_TRANSACTION":      ("auto", float("inf")),
    "MONITOR_ACCOUNT":        ("auto", float("inf")),
    "WARN_CUSTOMER":          ("auto", float("inf")),
    "BLOCK_TRANSACTION":      ("L1",  5_000.0),
    "REQUEST_STEP_UP_AUTH":   ("auto", float("inf")),
    "BLOCK_CARD":             ("L1",  10_000.0),
    "BLOCK_ACCOUNT":          ("L2",  float("inf")),
    "CREATE_CASE":            ("auto", float("inf")),
    "ESCALATE_CASE":          ("L1",  float("inf")),
    "REQUEST_EVIDENCE":       ("auto", float("inf")),
    "FILE_REPORT":            ("L2",  float("inf")),
    "CLOSE_CASE_CLEARED":     ("L1",  float("inf")),
    "CLOSE_CASE_FRAUD":       ("L1",  float("inf")),
    "FLAG_FRAUD_RING":        ("L2",  float("inf")),
}


def get_approval_route(action: str, exposure_usd: float = 0.0) -> ApprovalRoute:
    """
    Determine approval route for a given action + exposure amount.

    Rules:
      - auto:   System executes automatically
      - L1:     Level-1 analyst approval required
      - L2:     Level-2 supervisor approval required
      - High exposure always upgrades to L2

    Args:
        action:       Action identifier (see _ACTION_ROUTES)
        exposure_usd: Transaction exposure in USD

    Returns:
        "auto" | "L1" | "L2"
    """
    base_route, threshold = _ACTION_ROUTES.get(action, ("L2", 0.0))

    # High exposure always upgrades
    if exposure_usd >= threshold:
        return "L2"
    if exposure_usd >= 10_000.0 and base_route == "L1":
        return "L2"

    return base_route


# ============================================================
# SAR & Case Filing Requirements
# ============================================================

def requires_SAR(
    verdict: str,
    exposure_usd: float,
    shared_device: bool,
    connected_fraud: bool,
) -> bool:
    """
    Determine if a Suspicious Activity Report (SAR) must be filed.

    SAR required if:
      - Final verdict is fraud AND exposure >= $10,000
      - Shared device with connected fraud cases (organized ring)
      - Both connected_fraud AND shared_device regardless of amount
    """
    if verdict == "fraud" and exposure_usd >= 10_000.0:
        return True
    if shared_device and connected_fraud:
        return True
    return False


def requires_case(fraud_probability: float) -> bool:
    """
    R_CASE — Case Creation Rule
    A fraud case must be created if fraud_probability >= 0.30.
    """
    return fraud_probability >= 0.30
