from typing import Dict, Any, Optional
from app.agents.gemini_client import gemini_client
from app.services.safety_engine import SafetyEngine
from app.core.untrusted_guard import UntrustedInputGuard
from app.config import settings

class IntakeAgent:
    """
    Intake Agent (Gemini 3.5 Flash-Lite).
    Transcribes and extracts complaint facts from code-switched Telugu, Hindi, and English.
    Identifies symptoms, flags missing fields, and formulates 1-2 clarifying questions.
    Safety checks run deterministically via SafetyEngine.
    """

    @classmethod
    def process_inbound_message(cls, raw_transcript: str, language_hint: str = "te") -> Dict[str, Any]:
        # 1. Deterministic safety & hazard evaluation first!
        safety_eval = SafetyEngine.evaluate_hazards(raw_transcript)
        
        # 2. Untrusted guard sanitization
        sanitized = UntrustedInputGuard.wrap_as_data_block("customer_complaint", raw_transcript)
        
        # 3. Model extraction prompt
        prompt = f"""You are the KeepWell Intake Agent for appliance repairs in Tier 2/3 Indian cities.
Task: Extract repair intent, appliance facts, and identify missing details.
Untrusted Customer Complaint:
{sanitized}

Return JSON with keys:
- detected_language: (te, hi, en)
- symptom_category: (REFRIGERANT_OR_COOLING, ELECTRICAL, MECHANICAL_NOISE, DRAINAGE)
- extracted_facts: (appliance_type, brand_hint, symptom_description)
- high_value_follow_up: 1 clear polite question asking for missing model number or photo.
"""
        extraction = gemini_client.generate_json(
            model=settings.gemini_model_fast,
            prompt=prompt
        )

        return {
            "hazard_detected": safety_eval["is_hazard"],
            "hazard_details": safety_eval,
            "detected_language": extraction.get("detected_language", language_hint),
            "symptom_category": extraction.get("symptom_category", "GENERAL_FAULT"),
            "extracted_facts": extraction.get("extracted_facts", {}),
            "follow_up_question": extraction.get("high_value_follow_up", "Please share a photo of your appliance model plate.")
        }
