import json
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import Job, Customer, Appliance, JobEvent, Agency
from app.models.schemas import WhatsAppInboundMessage
from app.agents.intake_agent import IntakeAgent
from app.agents.identity_agent import IdentityAgent
from app.core.state_machine import JobState
from app.core.security import generate_magic_token
from app.config import settings

router = APIRouter(prefix="/webhook/whatsapp", tags=["WhatsApp"])

@router.get("")
async def verify_webhook(request: Request):
    """WhatsApp Cloud API Webhook Verification."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403, content="Verification failed")

@router.post("")
async def receive_inbound_message(msg: WhatsAppInboundMessage, db: Session = Depends(get_db)):
    """
    Receives incoming WhatsApp message (voice note transcript, text, or label photo).
    Orchestrates Flagship steps:
    1. Listen & Extract (IntakeAgent)
    2. Hazard check (SafetyEngine)
    3. Identify Machine (IdentityAgent & exact DB match)
    4. Transition Job state
    """
    # Find or create customer
    customer = db.query(Customer).filter(Customer.phone == msg.from_number).first()
    if not customer:
        customer = Customer(
            phone=msg.from_number,
            name="Household",
            language=msg.language_hint or "Telugu",
            address="Warangal, Telangana"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    agency = db.query(Agency).first()
    agency_id = agency.id if agency else 1

    # Step 1: Listen & Extract
    intake_result = IntakeAgent.process_inbound_message(
        raw_transcript=msg.text_body or "",
        language_hint=msg.language_hint or customer.language[:2].lower()
    )

    # Step 2: Check Hazard
    is_hazard = intake_result["hazard_detected"]
    hazard_info = intake_result["hazard_details"]

    # Step 3: Identify Appliance
    ocr_identity = IdentityAgent.extract_identity_from_ocr(msg.text_body or "")
    matched_appliance = None
    
    # Check customer's existing registered appliances
    if customer.appliances:
        if ocr_identity["model_number"]:
            for app in customer.appliances:
                if app.model_number == ocr_identity["model_number"]:
                    matched_appliance = app
                    break
        if not matched_appliance:
            matched_appliance = customer.appliances[0]

    # Create new provisional appliance if not found
    if not matched_appliance:
        matched_appliance = Appliance(
            customer_id=customer.id,
            appliance_type=intake_result["extracted_facts"].get("appliance_type", "REFRIGERATOR"),
            brand=ocr_identity["brand"] or "LG",
            model_number=ocr_identity["model_number"],
            is_verified=ocr_identity["is_verified"]
        )
        db.add(matched_appliance)
        db.commit()
        db.refresh(matched_appliance)

    # Determine initial state
    initial_state = JobState.HAZARD_REVIEW.value if is_hazard else (
        JobState.DIAGNOSIS_READY.value if matched_appliance.model_number else JobState.CLARIFICATION_NEEDED.value
    )

    # Create Job record
    magic_token = generate_magic_token()
    job = Job(
        agency_id=agency_id,
        customer_id=customer.id,
        appliance_id=matched_appliance.id,
        state=initial_state,
        raw_transcript=msg.text_body,
        language=intake_result["detected_language"],
        symptom_category=intake_result["symptom_category"],
        hazard_flag=is_hazard,
        hazard_summary=hazard_info.get("instructions") if is_hazard else None,
        inspect_first=not bool(matched_appliance.model_number),
        magic_token=magic_token
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Log State Event
    event = JobEvent(
        job_id=job.id,
        from_state="NONE",
        to_state=job.state,
        actor="CUSTOMER",
        comment=f"Customer inbound message via WhatsApp. Language: {job.language}",
        payload=json.dumps(intake_result)
    )
    db.add(event)
    db.commit()

    return {
        "job_id": job.id,
        "state": job.state,
        "hazard_flag": job.hazard_flag,
        "hazard_instructions": job.hazard_summary,
        "matched_appliance": {
            "id": matched_appliance.id,
            "brand": matched_appliance.brand,
            "model_number": matched_appliance.model_number,
            "is_verified": matched_appliance.is_verified
        },
        "follow_up_question": intake_result["follow_up_question"],
        "magic_link": f"/m/{job.magic_token}"
    }
