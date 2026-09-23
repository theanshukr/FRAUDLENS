"""
FraudLens — LLM Client (Google Gemini / OpenAI)
================================================
Provides generative AI capabilities for:
  - Case Investigation Summaries & Reasoning
  - FinCEN Suspicious Activity Report (SAR) Narratives
  - Action & Policy Explainability ("Why this action", "What changed")
"""

from __future__ import annotations

import os
from typing import Any, Optional
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Check available API keys
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

class GeminiClient:
    """Wrapper for Google Gemini 3.6 Flash."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_KEY
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self._model = None

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.model_name)
                logger.info(f"Gemini client initialized with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI SDK: {e}")

    def generate(self, prompt: str, fallback: str = "") -> str:
        """Generate text using Gemini, returning fallback string on failure."""
        if not self._model:
            return fallback

        try:
            response = self._model.generate_content(prompt, request_options={"timeout": 6.0})
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini generation error: {e}")

        return fallback

    def generate_investigation_summary(
        self,
        case_id: str,
        txn_id: str,
        fraud_probability: float,
        pattern: str,
        evidence_items: list[str],
    ) -> str:
        """Generate an executive case narrative for fraud analysts."""
        evidence_bullet_str = "\n".join([f"- {item}" for item in evidence_items])
        prompt = f"""You are a Senior Fraud Analyst reviewing an automated investigation.
Synthesize the following investigation data into a concise, professional, 2-3 sentence executive case summary.

Case ID: {case_id}
Transaction ID: {txn_id}
Assessed Fraud Probability: {fraud_probability:.2f}
Detected Typology/Pattern: {pattern}
Key Evidence Points:
{evidence_bullet_str}

Summary:"""
        fallback = f"Investigation for case {case_id} (Txn: {txn_id}) detected {pattern} pattern with {fraud_probability*100:.1f}% fraud probability based on {len(evidence_items)} collected graph signals."
        return self.generate(prompt, fallback=fallback)

    def generate_sar_narrative(
        self,
        case_id: str,
        customer_id: str,
        card_id: str,
        txn_id: str,
        amount: float,
        pattern: str,
        reasoning: str,
    ) -> str:
        """Generate legal narrative for FinCEN SAR filing."""
        prompt = f"""You are a Financial Crimes Compliance Officer preparing a FinCEN Suspicious Activity Report (SAR) narrative.
Draft a formal, factual SAR narrative (1 paragraph) based on the following case:

Subject Customer: {customer_id}
Card Identifier: {card_id}
Flagged Transaction: {txn_id} (Amount: ${amount:.2f})
Detected Suspicious Activity: {pattern}
Investigative Findings: {reasoning}

Ensure the narrative clearly outlines WHO, WHAT, WHEN, WHERE, and WHY the activity is deemed suspicious under BSA/AML standards.

SAR Narrative:"""
        fallback = f"On {case_id}, the institution detected suspicious activity involving Customer {customer_id} and Card {card_id} for transaction {txn_id} (${amount:.2f}). Investigative findings indicate {pattern} activity consistent with unauthorized account exploitation."
        return self.generate(prompt, fallback=fallback)

    def generate_action_explanation(
        self,
        action: str,
        rule_id: str,
        confidence: float,
        what_changed: Optional[str] = None,
    ) -> str:
        """Generate explainability note for Next-Best Action decision."""
        prompt = f"""Explain in 1 clear sentence why action '{action}' was recommended under rule '{rule_id}' with confidence {confidence:.2f}.
Additional Context: {what_changed or 'Initial evidence assessment.'}

Explanation:"""
        fallback = f"Action '{action}' was recommended per policy rule {rule_id} with confidence {confidence:.2f}."
        return self.generate(prompt, fallback=fallback)

    def generate_investigation_reasoning(self, graphrag_context: dict) -> dict:
        """
        Generate structured LLM investigation reasoning from unified GraphRAG context.
        Returns structured dictionary with findings, evidence breakdown, and historical analogies.
        """
        import json
        inv = graphrag_context.get("investigation", {})
        evidence_list = graphrag_context.get("evidence", [])
        precedents = graphrag_context.get("historical_precedents", [])
        signals = graphrag_context.get("graph_signals", {})

        # Deterministic structured fallback
        fallback_findings = [
            f"Observed pattern: {inv.get('detected_pattern', 'unknown')} with assessed risk {inv.get('assessed_risk_level', 'UNKNOWN')}.",
            f"Graph signals indicate ring_size={signals.get('ring_size', 0)}, card_testing={signals.get('card_testing_detected', False)}.",
        ]
        fallback_supporting = [e.get("claim", "") for e in evidence_list if e.get("claim")]
        fallback_hist = [
            f"Precedent {p.get('case_id')} ({p.get('pattern')}) -> {p.get('outcome')} [Relevance: {p.get('hybrid_relevance', 0.0)}]"
            for p in precedents[:3]
        ]
        fallback_result = {
            "findings": fallback_findings,
            "supporting_evidence": fallback_supporting[:4],
            "contradicting_evidence": [],
            "historical_context": fallback_hist,
            "remaining_uncertainty": ["Transaction dispute status requires cardholder confirmation"] if inv.get("trigger_type") in ("customer_report", "analyst_request") else [],
            "reasoning_summary": f"GraphRAG synthesized {len(evidence_list)} topological evidence items and {len(precedents)} historical analog cases confirming {inv.get('detected_pattern')} pattern.",
        }

        if not self._model:
            return fallback_result

        prompt = f"""SYSTEM:
You are the investigation reasoning assistant for FraudLens.
You must reason strictly from the supplied GraphRAG context.
You must distinguish observed evidence, historical analogies, and remaining uncertainty.
Return your analysis ONLY as valid JSON conforming exactly to this structure:
{{
  "findings": ["string"],
  "supporting_evidence": ["string"],
  "contradicting_evidence": ["string"],
  "historical_context": ["string"],
  "remaining_uncertainty": ["string"],
  "reasoning_summary": "string"
}}

USER CONTEXT:
Current Investigation:
{json.dumps(inv, indent=2)}

Graph Evidence:
{json.dumps(evidence_list, indent=2)}

Historical Precedents:
{json.dumps(precedents, indent=2)}

Graph Topology Signals:
{json.dumps(signals, indent=2)}

Generate structured JSON reasoning:"""

        try:
            raw_text = self.generate(prompt, fallback="")
            if raw_text:
                # Clean markdown code blocks if returned
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                elif clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                parsed = json.loads(clean_text.strip())
                if isinstance(parsed, dict) and "findings" in parsed:
                    return parsed
        except Exception as e:
            logger.warning(f"GraphRAG LLM reasoning parse error: {e}")

        return fallback_result


# Global singleton
gemini_client = GeminiClient()

