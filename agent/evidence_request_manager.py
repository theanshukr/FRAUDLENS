"""
FraudLens     Evidence Request Manager
======================================
When the risk assessment determines that evidence is insufficient
(sufficient_to_act = False), this module determines:

  1. What type of additional evidence to request
  2. The reason for the request (with policy citation)
  3. Simulated customer/analyst response for the hackathon demo
  4. New EvidenceItem from the simulated response

Evidence request types:
  - customer_validation       Contact customer to verify transaction
  - step_up_auth              Require additional authentication
  - analyst_info              Request analyst domain knowledge
  - external_data             Request external data source query
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
from loguru import logger

from agent.evidence_collector import EvidenceItem
from agent.risk_assessor import RiskAssessment


# ============================================================
# Evidence Request Model
# ============================================================

class EvidenceRequest(BaseModel):
    """A structured request for additional evidence."""

    request_id: str
    request_type: Literal["customer_validation", "step_up_auth", "analyst_info", "external_data"]
    target: str = Field(description="Who/what to ask     customer, analyst, system")
    question: str = Field(description="What specifically to ask")
    reason: str = Field(description="Why we need this evidence")
    policy_basis: str = Field(description="Policy rule that justifies this request (e.g., R2)")
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Simulated response (for hackathon demo)
    assumed_response: Optional[str] = None
    simulated: bool = True


# ============================================================
# Evidence Request Manager
# ============================================================

class EvidenceRequestManager:
    """
    Determines what additional evidence to request when the
    risk assessor determines that evidence is insufficient.
    """

    def determine_request(
        self,
        assessment: RiskAssessment,
        existing_evidence: list[EvidenceItem],
        request_count: int = 0,
    ) -> Optional[EvidenceRequest]:
        """
        Determine what evidence to request next.

        Args:
            assessment:       Current risk assessment
            existing_evidence: Evidence collected so far
            request_count:    Number of evidence requests already made

        Returns:
            EvidenceRequest or None if no more requests appropriate
        """
        # Don't request more than 2 rounds of evidence
        if request_count >= 2:
            logger.info("Max evidence request rounds reached     proceeding without more evidence")
            return None

        # Choose request type based on missing evidence and pattern
        request_type = self._determine_request_type(assessment, existing_evidence)
        if request_type is None:
            return None

        request = self._build_request(assessment, request_type, request_count)
        logger.info(
            f"Evidence request created | type={request_type} | reason={assessment.missing_evidence}"
        )
        return request

    def simulate_response(
        self,
        request: EvidenceRequest,
        scenario: str = "deny",
    ) -> EvidenceItem:
        """
        Simulate customer/analyst response for the demo.

        Args:
            request:  The evidence request
            scenario: "deny" | "confirm" | "partial" | "no_response"

        Returns:
            EvidenceItem representing the new evidence
        """
        responses = {
            "deny": {
                "customer_validation": (
                    "Customer explicitly denied making this transaction. "
                    "States card was in their possession.",
                    True,   # supports_fraud = True (customer says it's fraud)
                    0.90,
                ),
                "step_up_auth": (
                    "Step-up authentication failed     customer could not verify identity.",
                    True,
                    0.85,
                ),
                "analyst_info": (
                    "Analyst confirms pattern matches known fraud ring operating in region.",
                    True,
                    0.85,
                ),
            },
            "confirm": {
                "customer_validation": (
                    "Customer confirmed they made this transaction. Recognized merchant.",
                    False,  # supports_fraud = False
                    0.85,
                ),
                "step_up_auth": (
                    "Step-up authentication passed     customer verified identity successfully.",
                    False,
                    0.90,
                ),
            },
            "no_response": {
                "customer_validation": (
                    "Customer did not respond to validation request within timeout window.",
                    None,   # supports_fraud = None (neutral)
                    0.3,
                ),
            },
        }

        scenario_data = responses.get(scenario, {}).get(
            request.request_type,
            ("No response received.", None, 0.3)
        )
        claim, supports_fraud, confidence = scenario_data

        return EvidenceItem(
            evidence_id=f"EVD-SIM-{request.request_id}",
            claim=claim,
            source="customer" if "customer" in request.request_type else "external",
            ref=f"evidence_request:{request.request_id}",
            entity_ids=[],
            confidence=confidence,
            supports_fraud=supports_fraud,
            raw_data={"request_id": request.request_id, "scenario": scenario},
        )

    def _determine_request_type(
        self,
        assessment: RiskAssessment,
        evidence: list[EvidenceItem],
    ) -> Optional[str]:
        """Choose the most appropriate evidence request type."""
        has_customer_input = any("customer" in e.source for e in evidence)

        if not has_customer_input:
            if assessment.pattern == "shared_device_ring":
                return "analyst_info"
            return "customer_validation"

        if assessment.pattern == "shared_device_ring":
            return "analyst_info"

        if "Device relationship analysis not completed" in assessment.missing_evidence:
            return "analyst_info"

        return "step_up_auth"

    def _build_request(
        self,
        assessment: RiskAssessment,
        request_type: str,
        request_count: int,
    ) -> EvidenceRequest:
        """Build a structured evidence request."""
        request_id = f"REQ-{request_count + 1:03d}"

        templates = {
            "customer_validation": {
                "target": "Customer",
                "question": (
                    f"Did you authorize a transaction of approximately "
                    f"${assessment.fraud_probability * 1000:.0f} in the recent period? "
                    f"If not, please confirm the transaction was not made by you."
                ),
                "reason": (
                    f"Transaction shows {assessment.pattern} indicators. "
                    f"Customer confirmation required to distinguish fraud from legitimate use."
                ),
                "policy_basis": "R2     Customer validation required when fraud_probability > 0.40",
                "assumed_response": "Customer denies transaction (simulated for demo)",
            },
            "step_up_auth": {
                "target": "Customer     Authentication System",
                "question": "Please complete additional identity verification (OTP or biometric).",
                "reason": f"Pattern {assessment.pattern} detected. Step-up auth required per policy.",
                "policy_basis": "R5     Step-up auth required for high-velocity or new-device patterns",
                "assumed_response": "Step-up auth failed (simulated for demo)",
            },
            "analyst_info": {
                "target": "Fraud Analyst",
                "question": (
                    f"Please review this case for {assessment.pattern} pattern. "
                    f"Are there known fraud rings using this device profile?"
                ),
                "reason": "Complex shared-device ring pattern requires analyst domain knowledge.",
                "policy_basis": "R7     Analyst review required for organized fraud ring patterns",
                "assumed_response": "Analyst confirms fraud ring pattern (simulated for demo)",
            },
        }

        template = templates.get(request_type, templates["customer_validation"])
        return EvidenceRequest(
            request_id=request_id,
            request_type=request_type,
            **template,
        )
