from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class WhatsAppInboundMessage(BaseModel):
    from_number: str = Field(..., description="Customer phone number with country code")
    message_type: str = Field("text", description="text, audio, image")
    text_body: Optional[str] = None
    media_url: Optional[str] = None
    audio_base64: Optional[str] = None
    image_base64: Optional[str] = None
    language_hint: Optional[str] = "te" # te (Telugu), hi (Hindi), en (English)

class WhatsAppOutboundMessage(BaseModel):
    to_number: str
    body: str
    buttons: Optional[List[str]] = None
    magic_link_url: Optional[str] = None

class IntakeResponse(BaseModel):
    job_id: int
    customer_phone: str
    state: str
    symptom: str
    detected_language: str
    hazard_flag: bool
    hazard_details: Optional[str] = None
    follow_up_question: Optional[str] = None
    matched_appliance: Optional[Dict[str, Any]] = None

class DiagnosticHypothesis(BaseModel):
    rank: int
    fault_name: str
    confidence: float
    service_manual_citation: str
    recommended_action: str
    required_part_code: Optional[str] = None
    abstain_reason: Optional[str] = None

class QuoteCreateRequest(BaseModel):
    job_id: int
    visiting_charge: float = 250.0
    labor_charge: float = 300.0
    part_code: Optional[str] = None

class QuoteResponse(BaseModel):
    quote_id: int
    job_id: int
    visiting_charge: float
    labor_charge: float
    parts_cost: float
    gst_amount: float
    total_amount: float
    agency_approved: bool
    customer_approved: bool
    payment_status: str
    upi_payment_link: str

class HomeMemoryView(BaseModel):
    appliance_id: int
    appliance_type: str
    brand: str
    model_number: Optional[str]
    is_verified: bool
    service_history: List[Dict[str, Any]]
    active_quote: Optional[Dict[str, Any]] = None
    job_status: Optional[str] = None
