from typing import Dict, Any, List

class PreparationAgent:
    """
    Preparation Agent.
    Drafts actionable technician briefs and customer-facing briefings in colloquial language.
    """

    @classmethod
    def generate_technician_brief(
        cls,
        customer_name: str,
        customer_phone: str,
        customer_address: str,
        appliance_brand: str,
        appliance_type: str,
        model_number: str,
        symptom: str,
        hypotheses: List[Dict[str, Any]],
        recommended_part: Dict[str, Any],
        scheduled_slot: str
    ) -> Dict[str, Any]:
        kit_items = []
        if recommended_part and recommended_part.get("part"):
            kit_items.append(f"Part: {recommended_part['part']['name']} ({recommended_part['part']['code']})")
        else:
            kit_items.append("General diagnostic toolkit (Multimeter, Manifold gauge, clamp meter)")

        brief_text = f"""--- KEEPWELL TECHNICIAN BRIEF ---
Job Slot: {scheduled_slot}
Customer: {customer_name} ({customer_phone})
Address: {customer_address}
Appliance: {appliance_brand} {appliance_type} [{model_number or 'Model Unconfirmed'}]
Reported Problem: {symptom}

Diagnostic Hypotheses:
"""
        for h in hypotheses[:2]:
            brief_text += f"- #{h.get('rank', 1)}: {h.get('fault_name')} (Manual: {h.get('service_manual_citation')})\n"

        brief_text += f"\nRecommended Kit in Bag: {', '.join(kit_items)}"

        return {
            "summary_text": brief_text,
            "kit_checklist": kit_items,
            "model_confirmed": bool(model_number)
        }

    @classmethod
    def generate_customer_message(
        cls,
        language: str,
        quote_amount: float,
        magic_link: str,
        scheduled_slot: str
    ) -> str:
        if language == "te":
            return f"నమస్కారం! మీ రిపేర్ కోసం ఎస్టిమేట్ రూ. {quote_amount:.2f}. టెక్నీషియన్ విజిట్ సమయం: {scheduled_slot}. పూర్తి వివరాలు & అప్రూవల్ కొరకు క్లిక్ చేయండి: {magic_link}"
        elif language == "hi":
            return f"नमस्ते! आपके रिपेयर का कोटेशन रु. {quote_amount:.2f} है। तकनीशियन विज़िट स्लॉट: {scheduled_slot}। पूरा विवरण और स्वीकृति के लिए यहाँ क्लिक करें: {magic_link}"
        else:
            return f"Hello! Your estimated repair quote is Rs. {quote_amount:.2f}. Scheduled visit: {scheduled_slot}. Review details and approve here: {magic_link}"
