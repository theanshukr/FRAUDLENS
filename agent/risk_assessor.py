"""
FraudLens — Risk & Uncertainty Assessor
========================================
Analyzes collected evidence to produce a structured risk assessment.

KEY PRINCIPLE: Risk and Confidence are SEPARATE metrics.
  - Risk:       How bad is this if it IS fraud? (LOW/MEDIUM/HIGH/CRITICAL)
  - Confidence: How certain are we about the risk assessment? (0.0–1.0)

Fraud probability is computed from:
  1. Trigger type prior
  2. Specific signal contributions (card_testing, risk_score, shared_device, etc.)
  3. Evidence item support/contradiction votes
  4. Historical case precedent boost

The assessor also:
  - Identifies which fraud pattern best matches the evidence
  - Lists supporting vs contradicting evidence
  - Identifies missing evidence that would improve confidence
  - Determines if evidence is sufficient to take action
  - Exposes `extracted_signals` dict for the NBA engine
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
        "signals": ["detect_card_testing", "micro_auth_burst", "small_transactions_before_large"],
    },
    "account_takeover": {
        "description": "Attacker gains access to legitimate account and makes unauthorized transactions",
        "signals": ["detect_new_device_usage", "customer_report", "detect_out_of_region", "new_device"],
    },
    "shared_device_ring": {
        "description": "Multiple accounts share the same device, indicating coordinated fraud ring",
        "signals": ["find_shared_devices", "find_connected_cards", "get_device_neighbors", "fraud_ring"],
    },
    "velocity_anomaly": {
        "description": "Unusual frequency of transactions in a short time window",
        "signals": ["detect_velocity_anomaly", "velocity_high", "velocity_anomaly", "velocity_abuse"],
    },
    "out_of_region": {
        "description": "Transactions occurring in unusual geographic regions for this account",
        "signals": ["detect_out_of_region", "get_billing_region_cards", "geographic_anomaly"],
    },
}


# ============================================================
# Risk Assessment Model
# ============================================================

class RiskAssessment(BaseModel):
    """Complete risk assessment output from the risk assessor."""

    # Core risk metrics (SEPARATE — critical requirement)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    fraud_probability: float = Field(ge=0.0, le=1.0,
        description="Probability that this is fraud (0.0–1.0)")
    confidence: float = Field(ge=0.0, le=1.0,
        description="Confidence in this assessment — separate from fraud probability")

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

    # Structured signals extracted from evidence (for NBA engine)
    extracted_signals: dict = Field(
        default_factory=dict,
        description="Structured signal values extracted from evidence for NBA engine use"
    )


# ============================================================
# Risk Assessor
# ============================================================

class RiskAssessor:
    """
    Analyzes collected evidence to produce a structured RiskAssessment.

    Stop conditions (sufficient_to_act = True):
      - fraud_probability >= 0.85 AND confidence >= 0.70 AND 2+ supporting evidence
      - fraud_probability <= 0.15 AND confidence >= 0.70 (clearly not fraud)
    """

    STOP_PROBABILITY_HIGH   = 0.85
    STOP_PROBABILITY_LOW    = 0.15
    MIN_CONFIDENCE_TO_STOP  = 0.70
    MIN_INDEPENDENT_EVIDENCE = 2

    # Signal contribution weights for fraud probability
    SIGNAL_WEIGHTS = {
        "risk_score_high":       0.30,   # raw risk_score >= 0.80
        "risk_score_medium":     0.15,   # raw risk_score 0.50–0.79
        "card_testing_detected": 0.25,   # explicit card testing flag
        "shared_device_ring":    0.18,   # device shared by 3+ cards
        "shared_device_pair":    0.10,   # device shared by 2 cards
        "new_device":            0.12,   # is_new_device = True
        "out_of_region":         0.10,   # geographic mismatch
        "velocity_high":         0.12,   # velocity_count > 10
        "velocity_medium":       0.06,   # velocity_count 5–10
        "fraud_ring":            0.15,   # connected_fraud_cases >= 2
        "historical_fraud_case": 0.05,   # per matching fraud case (max 0.15)
    }

    def assess(
        self,
        evidence: list[EvidenceItem],
        trigger_type: str,
        similar_cases: list[dict] = None,
        collector_signals: dict = None,
    ) -> RiskAssessment:
        """
        Assess risk from collected evidence.

        Args:
            evidence:          List of EvidenceItem from evidence collector
            trigger_type:      Original trigger type (affects prior probability)
            similar_cases:     Similar historical cases from memory retrieval
            collector_signals: Structured signals dict from EvidenceCollector.signals

        Returns:
            RiskAssessment
        """
        if similar_cases is None:
            similar_cases = []
        if collector_signals is None:
            collector_signals = {}

        supporting    = [e for e in evidence if e.supports_fraud is True]
        contradicting = [e for e in evidence if e.supports_fraud is False]

        # --- Extract signals from evidence raw_data (supplement collector_signals) ---
        signals = self._extract_signals_from_evidence(evidence, collector_signals)

        # --- Fraud Probability Calculation ---
        fraud_probability = self._calculate_fraud_probability(
            evidence, trigger_type, similar_cases, signals
        )

        # --- Confidence Calculation ---
        confidence = self._calculate_confidence(evidence, similar_cases)

        # --- Pattern Identification ---
        pattern, pattern_desc = self._identify_pattern(evidence, signals, trigger_type)

        # --- Risk Level ---
        risk_level = self._probability_to_risk_level(fraud_probability)

        # --- Evidence Sufficiency ---
        evidence_sufficiency, missing = self._assess_evidence_sufficiency(evidence, pattern)

        # --- Stop Condition ---
        sufficient_to_act, stop_reason = self._check_stop_condition(
            fraud_probability, confidence, len(supporting)
        )

        # --- Key Risk Factors ---
        key_risk_factors = self._extract_risk_factors(evidence, pattern, signals)

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
            extracted_signals=signals,
        )

        logger.info(
            f"Risk assessment | "
            f"risk={risk_level} | prob={fraud_probability:.2f} | "
            f"conf={confidence:.2f} | pattern={pattern} | "
            f"sufficient={sufficient_to_act} | "
            f"signals=card_test:{signals.get('card_testing_detected')} "
            f"shared_dev:{signals.get('shared_device_count')} "
            f"ring:{signals.get('ring_size')}"
        )
        return assessment

    # --------------------------------------------------------
    # Signal Extraction
    # --------------------------------------------------------

    def _extract_signals_from_evidence(
        self, evidence: list[EvidenceItem], collector_signals: dict
    ) -> dict:
        """
        Merge collector_signals with values parsed from evidence raw_data.
        collector_signals takes precedence as it is accumulated live during execution.
        """
        signals = {
            "risk_score": 0.0,
            "amount": 0.0,
            "channel": "",
            "card_testing_detected": False,
            "shared_device_count": 0,
            "ring_size": 0,
            "is_new_device": False,
            "out_of_region": False,
            "velocity_count": 0,
            "connected_fraud_cases": 0,
            "txn_sequence": [],
            "device_profile_id": "",
            "connected_card_ids": [],
            "customer_denial": False,
        }

        # Start from collector_signals (most accurate, accumulated live)
        signals.update(collector_signals)

        # Supplement from raw_data in evidence items
        for e in evidence:
            if "denied" in e.claim.lower() or (e.ref.startswith("evidence_request") and e.supports_fraud is True):
                signals["customer_denial"] = True

            if e.raw_data is None:
                continue
            raw = e.raw_data

            # get_transaction signals
            if e.ref == "get_transaction":
                if "risk_score" in raw:
                    signals["risk_score"] = max(signals["risk_score"], float(raw["risk_score"] or 0))
                if "amount" in raw or "TransactionAmt" in raw:
                    signals["amount"] = max(
                        signals["amount"],
                        float(raw.get("amount", raw.get("TransactionAmt", 0)) or 0)
                    )

            # Card testing
            if "card_testing_detected" in raw and raw["card_testing_detected"]:
                signals["card_testing_detected"] = True

            # Device sharing
            if "shared_device_count" in raw:
                signals["shared_device_count"] = max(
                    signals["shared_device_count"], int(raw["shared_device_count"])
                )

            # Ring size
            if "ring_size" in raw:
                signals["ring_size"] = max(signals["ring_size"], int(raw["ring_size"]))
                if signals["ring_size"] >= 2:
                    signals["connected_fraud_cases"] = max(
                        signals["connected_fraud_cases"], signals["ring_size"] - 1
                    )

            # New device
            if "is_new_device" in raw and raw["is_new_device"]:
                signals["is_new_device"] = True

            # Out of region
            if "out_of_region" in raw and raw["out_of_region"]:
                signals["out_of_region"] = True

            # Velocity
            if "velocity_count" in raw:
                signals["velocity_count"] = max(signals["velocity_count"], int(raw["velocity_count"]))

        return signals

    # --------------------------------------------------------
    # Fraud Probability Calculation
    # --------------------------------------------------------

    def _calculate_fraud_probability(
        self,
        evidence: list[EvidenceItem],
        trigger_type: str,
        similar_cases: list[dict],
        signals: dict,
    ) -> float:
        """
        Calculate fraud probability from:
          1. Trigger-type prior
          2. Named signal contributions (weighted)
          3. Evidence item votes (fine-grained)
          4. Historical case boost
        """
        # 1. Prior from trigger type
        base = {
            "risk_score":       0.45,
            "customer_report":  0.60,
            "analyst_request":  0.45,
            "system_alert":     0.40,
        }.get(trigger_type, 0.35)

        # 2. Signal contributions
        raw_risk = signals.get("risk_score", 0.0)
        if raw_risk >= 0.80:
            base += self.SIGNAL_WEIGHTS["risk_score_high"]
        elif raw_risk >= 0.50:
            base += self.SIGNAL_WEIGHTS["risk_score_medium"]

        if signals.get("card_testing_detected"):
            base += self.SIGNAL_WEIGHTS["card_testing_detected"]

        shared = signals.get("shared_device_count", 0)
        if shared >= 3:
            base += self.SIGNAL_WEIGHTS["shared_device_ring"]
        elif shared >= 2:
            base += self.SIGNAL_WEIGHTS["shared_device_pair"]

        if signals.get("is_new_device"):
            base += self.SIGNAL_WEIGHTS["new_device"]

        if signals.get("out_of_region"):
            base += self.SIGNAL_WEIGHTS["out_of_region"]

        velocity = signals.get("velocity_count", 0)
        if velocity > 10:
            base += self.SIGNAL_WEIGHTS["velocity_high"]
        elif velocity > 5:
            base += self.SIGNAL_WEIGHTS["velocity_medium"]

        connected = signals.get("connected_fraud_cases", 0)
        if connected >= 2:
            base += self.SIGNAL_WEIGHTS["fraud_ring"]

        if signals.get("customer_denial"):
            base += 0.35

        # 3. Evidence item votes (fine adjustment)
        for e in evidence:
            if e.supports_fraud is True:
                base = min(1.0, base + 0.03 * e.confidence)
            elif e.supports_fraud is False:
                base = max(0.0, base - 0.04 * e.confidence)

        # 4. Historical case boost
        fraud_cases = [c for c in similar_cases if c.get("outcome") == "fraud"]
        fraud_boost = min(0.15, len(fraud_cases) * self.SIGNAL_WEIGHTS["historical_fraud_case"])
        base += fraud_boost

        return min(1.0, max(0.0, base))

    def _calculate_confidence(
        self,
        evidence: list[EvidenceItem],
        similar_cases: list[dict],
    ) -> float:
        """Confidence is a function of evidence quantity, quality, and historical precedent."""
        if not evidence:
            return 0.10

        avg_confidence = sum(e.confidence for e in evidence) / len(evidence)
        evidence_count_boost = min(0.25, len(evidence) * 0.04)
        similar_case_boost   = min(0.10, len(similar_cases) * 0.025)

        # Boost confidence if we have high-signal evidence (card testing, device sharing, customer response)
        signal_boost = 0.0
        for e in evidence:
            if e.raw_data and (
                e.raw_data.get("card_testing_detected") or
                e.raw_data.get("shared_device_count", 0) >= 3 or
                e.ref.startswith("evidence_request")
            ):
                signal_boost = min(0.15, signal_boost + 0.08)

        return min(1.0, avg_confidence + evidence_count_boost + similar_case_boost + signal_boost)

    # --------------------------------------------------------
    # Pattern Identification
    # --------------------------------------------------------

    def _identify_pattern(
        self, evidence: list[EvidenceItem], signals: dict, trigger_type: str = ""
    ) -> tuple[str, str]:
        """Identify the best-matching fraud pattern from evidence and signals."""
        pattern_scores: dict[str, float] = {p: 0.0 for p in FRAUD_PATTERNS}

        # Score from evidence refs
        for e in evidence:
            if e.supports_fraud is not True:
                continue  # Only count fraud-supporting evidence toward a pattern
            for pattern, info in FRAUD_PATTERNS.items():
                if any(signal in e.ref for signal in info["signals"]):
                    pattern_scores[pattern] += e.confidence

        # Boost from explicit signals
        if signals.get("card_testing_detected"):
            pattern_scores["card_testing"] += 3.0

        if signals.get("shared_device_count", 0) >= 2 or signals.get("ring_size", 0) >= 2 or signals.get("connected_fraud_cases", 0) >= 1:
            pattern_scores["shared_device_ring"] += 3.0

        if signals.get("is_new_device") or trigger_type == "customer_report" or signals.get("customer_denial"):
            pattern_scores["account_takeover"] += 2.0

        if signals.get("out_of_region"):
            pattern_scores["out_of_region"] += 2.0

        if signals.get("velocity_count", 0) >= 2 or trigger_type == "analyst_request":
            pattern_scores["velocity_anomaly"] += 2.5

        best_pattern = max(pattern_scores, key=lambda p: pattern_scores[p])
        if pattern_scores[best_pattern] == 0:
            if trigger_type == "risk_score":
                best_pattern = "card_testing"
            elif trigger_type == "customer_report":
                best_pattern = "account_takeover"
            elif trigger_type == "analyst_request":
                best_pattern = "velocity_anomaly"
            else:
                return "unknown", "No clear fraud pattern identified from available evidence"

        return best_pattern, FRAUD_PATTERNS[best_pattern]["description"]

    # --------------------------------------------------------
    # Supporting Methods
    # --------------------------------------------------------

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
        if not any(
            "similar_cases" in e.ref.lower() or "search_similar" in e.ref.lower()
            for e in evidence
        ):
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

    def _extract_risk_factors(
        self, evidence: list[EvidenceItem], pattern: str, signals: dict
    ) -> list[str]:
        """Extract top risk factors — named signals first, then high-confidence evidence claims."""
        factors = []

        # Named signal factors (most specific)
        if signals.get("card_testing_detected"):
            factors.append("Card testing pattern detected (micro-auth burst before large transaction)")
        if signals.get("shared_device_count", 0) >= 3:
            factors.append(f"Device shared by {signals['shared_device_count']} cards — organized ring")
        if signals.get("risk_score", 0) >= 0.80:
            factors.append(f"High raw risk score: {signals['risk_score']:.2f}")
        if signals.get("is_new_device") and signals.get("out_of_region"):
            factors.append("New device + out-of-region — account takeover indicators")
        if signals.get("connected_fraud_cases", 0) >= 2:
            factors.append(f"{signals['connected_fraud_cases']} connected fraud cases in network")

        # Evidence claim factors (supplementary)
        for e in evidence:
            if e.supports_fraud is True and e.confidence >= 0.75 and len(factors) < 7:
                if e.claim not in factors:
                    factors.append(e.claim[:120])

        return factors[:5]

    def _identify_uncertainty(
        self, evidence: list[EvidenceItem], confidence: float
    ) -> list[str]:
        reasons = []
        if confidence < 0.50:
            reasons.append("Insufficient evidence volume to reach high confidence")
        low_conf = [e for e in evidence if e.confidence < 0.4]
        if low_conf:
            reasons.append(f"{len(low_conf)} evidence items have low individual confidence")
        if not any(e.supports_fraud is not None for e in evidence):
            reasons.append("No evidence items carry a definitive fraud support signal")
        return reasons
