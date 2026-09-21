"""
FraudLens     Risk Assessor
==========================
Analyzes collected evidence to produce a structured risk assessment.

KEY PRINCIPLE: Risk and Confidence are SEPARATE metrics.
  - Risk:       How bad is this if it IS fraud? (LOW/MEDIUM/HIGH/CRITICAL)
  - Confidence: How certain are we about the risk assessment? (0.0-1.0)

The assessor also:
  - Identifies which fraud pattern best matches the evidence
  - Lists supporting vs contradicting evidence
  - Identifies missing evidence that would improve confidence
  - Determines if evidence is sufficient to take action
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field
from loguru import logger

from agent.evidence_collector import EvidenceItem


# ============================================================
# Fraud Pattern Definitions
# ============================================================

FRAUD_PATTERNS = {
    "card_testing": {
        "description": "Attacker makes micro-auth transactions to test card validity before committing larger fraud",
        "signals": ["detect_card_testing", "small_transactions_before_large"],
    },
    "account_takeover": {
        "description": "Attacker gains access to legitimate account and makes unauthorized transactions",
        "signals": ["detect_new_device_usage", "customer_report", "unusual_location"],
    },
    "shared_device_ring": {
        "description": "Multiple accounts share the same device, indicating coordinated fraud ring",
        "signals": ["find_shared_devices", "find_connected_cards", "get_device_neighbors"],
    },
    "velocity_abuse": {
        "description": "Unusual frequency of transactions in a short time window",
        "signals": ["detect_velocity_anomaly", "get_card_window"],
    },
    "out_of_region": {
        "description": "Transactions occurring in unusual geographic regions for this account",
        "signals": ["detect_out_of_region", "get_billing_region_cards"],
    },
}


# ============================================================
# Risk Assessment Model
# ============================================================

class RiskAssessment(BaseModel):
    """Complete risk assessment output from the risk assessor."""

    # Core risk metrics (SEPARATE     critical requirement)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    fraud_probability: float = Field(ge=0.0, le=1.0,
        description="Probability that this is fraud (0.0-1.0)")
    confidence: float = Field(ge=0.0, le=1.0,
        description="Confidence in this assessment     separate from fraud probability")

    # Evidence quality
    evidence_sufficiency: Literal["LOW", "MEDIUM", "HIGH"]
    sufficient_to_act: bool = Field(
        description="True if we have enough evidence to make a final decision")

    # Pattern identification
    pattern: str = Field(description="Best-matching fraud pattern enum")
    pattern_description: str

    # Evidence breakdown
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence item IDs that support fraud hypothesis")
    contradicting_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence item IDs that contradict fraud hypothesis")
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="What additional evidence would improve this assessment")

    # Risk factors and uncertainty
    key_risk_factors: list[str] = Field(default_factory=list)
    uncertainty_reasons: list[str] = Field(default_factory=list)

    # Stop condition
    stop_reason: Optional[str] = None


# ============================================================
# Risk Assessor
# ============================================================

class RiskAssessor:
    """
    Analyzes collected evidence to produce a structured RiskAssessment.

    Stop conditions (sufficient_to_act = True):
      - fraud_probability >= 0.85 AND confidence >= 0.7 AND 2+ independent evidence pieces
      - fraud_probability <= 0.15 AND confidence >= 0.7 (clearly not fraud)
    """

    STOP_PROBABILITY_HIGH = 0.85
    STOP_PROBABILITY_LOW  = 0.15
    MIN_CONFIDENCE_TO_STOP = 0.70
    MIN_INDEPENDENT_EVIDENCE = 2

    def assess(
        self,
        evidence: list[EvidenceItem],
        trigger_type: str,
        similar_cases: list[dict] = None,
    ) -> RiskAssessment:
        """
        Assess risk from collected evidence.

        Args:
            evidence:      List of EvidenceItem from evidence collector
            trigger_type:  Original trigger type (affects weighting)
            similar_cases: Similar historical cases from memory retrieval

        Returns:
            RiskAssessment
        """
        if similar_cases is None:
            similar_cases = []

        supporting    = [e for e in evidence if e.supports_fraud is True]
        contradicting = [e for e in evidence if e.supports_fraud is False]

        # --- Fraud Probability Calculation ---
        fraud_probability = self._calculate_fraud_probability(
            evidence, trigger_type, similar_cases
        )

        # --- Confidence Calculation ---
        confidence = self._calculate_confidence(evidence, similar_cases)

        # --- Pattern Identification ---
        pattern, pattern_desc = self._identify_pattern(evidence)

        # --- Risk Level ---
        risk_level = self._probability_to_risk_level(fraud_probability)

        # --- Evidence Sufficiency ---
        evidence_sufficiency, missing = self._assess_evidence_sufficiency(evidence, pattern)

        # --- Stop Condition ---
        sufficient_to_act, stop_reason = self._check_stop_condition(
            fraud_probability, confidence, len(supporting)
        )

        # --- Key Risk Factors ---
        key_risk_factors = self._extract_risk_factors(evidence, pattern)

        # --- Uncertainty Reasons ---
        uncertainty_reasons = self._identify_uncertainty(evidence, confidence)

        assessment = RiskAssessment(
            risk_level=risk_level,
            fraud_probability=round(fraud_probability, 3),
            confidence=round(confidence, 3),
            evidence_sufficiency=evidence_sufficiency,
            sufficient_to_act=sufficient_to_act,
            pattern=pattern,
            pattern_description=pattern_desc,
            supporting_evidence=[e.evidence_id for e in supporting],
            contradicting_evidence=[e.evidence_id for e in contradicting],
            missing_evidence=missing,
            key_risk_factors=key_risk_factors,
            uncertainty_reasons=uncertainty_reasons,
            stop_reason=stop_reason,
        )

        logger.info(
            f"Risk assessment complete | "
            f"risk={risk_level} | prob={fraud_probability:.2f} | "
            f"conf={confidence:.2f} | pattern={pattern} | "
            f"sufficient={sufficient_to_act}"
        )
        return assessment

    def _calculate_fraud_probability(
        self,
        evidence: list[EvidenceItem],
        trigger_type: str,
        similar_cases: list[dict],
    ) -> float:
        """
        Calculate fraud probability from evidence signals.
        TODO (Phase 2): Replace with LLM-structured reasoning on evidence.
        """
        base = 0.3  # Prior based on trigger type

        if trigger_type == "risk_score":
            base = 0.5
        elif trigger_type == "customer_report":
            base = 0.6

        # Evidence contributions
        for e in evidence:
            if e.supports_fraud is True:
                base = min(1.0, base + 0.1 * e.confidence)
            elif e.supports_fraud is False:
                base = max(0.0, base - 0.08 * e.confidence)

        # Historical case boost
        if similar_cases:
            fraud_cases = [c for c in similar_cases if c.get("outcome") == "fraud"]
            base += 0.05 * len(fraud_cases)

        return min(1.0, base)

    def _calculate_confidence(
        self,
        evidence: list[EvidenceItem],
        similar_cases: list[dict],
    ) -> float:
        """Confidence is a function of evidence quantity and quality."""
        if not evidence:
            return 0.1

        avg_confidence = sum(e.confidence for e in evidence) / len(evidence)
        evidence_count_boost = min(0.3, len(evidence) * 0.05)
        similar_case_boost   = min(0.1, len(similar_cases) * 0.02)

        return min(1.0, avg_confidence + evidence_count_boost + similar_case_boost)

    def _identify_pattern(self, evidence: list[EvidenceItem]) -> tuple[str, str]:
        """Identify the best-matching fraud pattern from evidence."""
        pattern_scores: dict[str, int] = {p: 0 for p in FRAUD_PATTERNS}

        for e in evidence:
            for pattern, info in FRAUD_PATTERNS.items():
                if any(signal in e.ref for signal in info["signals"]):
                    pattern_scores[pattern] += 1

        best_pattern = max(pattern_scores, key=lambda p: pattern_scores[p])
        if pattern_scores[best_pattern] == 0:
            return "unknown", "No clear fraud pattern identified from available evidence"

        return best_pattern, FRAUD_PATTERNS[best_pattern]["description"]

    def _probability_to_risk_level(self, prob: float) -> str:
        if prob >= 0.80:
            return "CRITICAL"
        elif prob >= 0.60:
            return "HIGH"
        elif prob >= 0.35:
            return "MEDIUM"
        else:
            return "LOW"

    def _assess_evidence_sufficiency(
        self, evidence: list[EvidenceItem], pattern: str
    ) -> tuple[str, list[str]]:
        """Assess if we have enough evidence and identify gaps."""
        missing = []

        if len(evidence) < 3:
            missing.append("More graph queries needed to build complete picture")
        if not any("device" in e.ref.lower() for e in evidence):
            missing.append("Device relationship analysis not completed")
        if not any("similar_cases" in e.ref.lower() or "search_similar" in e.ref.lower() for e in evidence):
            missing.append("Historical case comparison not performed")

        if len(missing) == 0:
            return "HIGH", []
        elif len(missing) == 1:
            return "MEDIUM", missing
        else:
            return "LOW", missing

    def _check_stop_condition(
        self, prob: float, confidence: float, supporting_count: int
    ) -> tuple[bool, Optional[str]]:
        """Determine if we have enough to make a final decision."""
        if (prob >= self.STOP_PROBABILITY_HIGH
                and confidence >= self.MIN_CONFIDENCE_TO_STOP
                and supporting_count >= self.MIN_INDEPENDENT_EVIDENCE):
            return True, f"High confidence fraud signal: prob={prob:.2f}, conf={confidence:.2f}"

        if prob <= self.STOP_PROBABILITY_LOW and confidence >= self.MIN_CONFIDENCE_TO_STOP:
            return True, f"High confidence low-risk: prob={prob:.2f}, conf={confidence:.2f}"

        return False, None

    def _extract_risk_factors(self, evidence: list[EvidenceItem], pattern: str) -> list[str]:
        """Extract key risk factors from evidence claims."""
        factors = []
        for e in evidence:
            if e.supports_fraud is True and e.confidence >= 0.6:
                factors.append(e.claim)
        return factors[:5]  # Top 5

    def _identify_uncertainty(self, evidence: list[EvidenceItem], confidence: float) -> list[str]:
        reasons = []
        if confidence < 0.5:
            reasons.append("Insufficient evidence volume to reach high confidence")
        low_conf = [e for e in evidence if e.confidence < 0.4]
        if low_conf:
            reasons.append(f"{len(low_conf)} evidence items have low individual confidence")
        return reasons
