from typing import Dict, Any, List, Optional
from app.agents.gemini_client import gemini_client
from app.core.untrusted_guard import UntrustedInputGuard
from app.config import settings

class DiagnosticAgent:
    """
    Diagnostic Agent (Gemini 3.8 Flash).
    Reasons over verified appliance history and service manual excerpts to rank likely faults.
    STRICT RULE: If the model number is unknown or evidence is weak, it must ABSTAIN
    and recommend 'INSPECT_FIRST' rather than hallucinating parts or causes.
    """

    @classmethod
    def analyze_fault(
        cls,
        symptom_text: str,
        appliance_type: str,
        brand: str,
        model_number: Optional[str],
        past_repair_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        # Hard Abstention Gate: If model number is missing, enforce inspect first!
        if not model_number or model_number == "Unverified Model":
            return {
                "abstain": True,
                "recommendation": "INSPECT_FIRST_RECOMMENDED",
                "reason": "Model number is not identified. Field inspection required before parts selection.",
                "hypotheses": []
            }

        sanitized_symptom = UntrustedInputGuard.wrap_as_data_block("symptom", symptom_text)
        prompt = f"""You are the KeepWell Senior Diagnostic Agent.
Task: Provide ranked fault hypotheses with explicit service manual citations.
Appliance: {brand} {appliance_type} (Model: {model_number})
Past Service History: {past_repair_summary or 'No prior records'}
Customer Reported Symptom:
{sanitized_symptom}

Rules:
1. Every hypothesis MUST cite a realistic service manual section.
2. If evidence is ambiguous, abstain rather than guessing.
3. Suggest the candidate replacement part code if verified.
"""
        result = gemini_client.generate_json(
            model=settings.gemini_model_reasoning,
            prompt=prompt
        )

        return result
