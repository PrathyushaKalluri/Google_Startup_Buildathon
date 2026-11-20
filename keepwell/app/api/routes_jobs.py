import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import Job, Appliance, JobEvent
from app.core.state_machine import JobState, validate_transition
from app.agents.diagnostic_agent import DiagnosticAgent
from app.services.parts_catalogue import PartsCatalogueService
from app.services.home_memory_service import HomeMemoryService

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    quotes_data = []
    for q in job.quotes:
        quotes_data.append({
            "quote_id": q.id,
            "total_amount": q.total_amount,
            "agency_approved": q.agency_approved,
            "customer_approved": q.customer_approved,
            "payment_status": q.payment_status
        })

    events_data = []
    for ev in job.events:
        events_data.append({
            "from_state": ev.from_state,
            "to_state": ev.to_state,
            "actor": ev.actor,
            "comment": ev.comment,
            "timestamp": ev.timestamp.strftime("%H:%M:%S")
        })

    return {
        "id": job.id,
        "state": job.state,
        "customer": {
            "name": job.customer.name,
            "phone": job.customer.phone,
            "address": job.customer.address
        },
        "appliance": {
            "id": job.appliance.id if job.appliance else None,
            "brand": job.appliance.brand if job.appliance else "Generic",
            "model_number": job.appliance.model_number if job.appliance else None,
            "type": job.appliance.appliance_type if job.appliance else "REFRIGERATOR"
        },
        "symptom": job.raw_transcript,
        "hazard_flag": job.hazard_flag,
        "hazard_summary": job.hazard_summary,
        "diagnostic_hypotheses": json.loads(job.diagnostic_hypotheses or "[]"),
        "parts_status": job.parts_status,
        "quotes": quotes_data,
        "timeline": events_data,
        "magic_link": f"/m/{job.magic_token}"
    }

@router.post("/{job_id}/diagnose")
def run_diagnostics(job_id: int, db: Session = Depends(get_db)):
    """
    Step 4 of Flagship scenario:
    Runs Gemini 3.8 Flash Diagnostic reasoning over appliance history.
    Verifies candidate parts against Parts Catalogue service.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    appliance = job.appliance
    history = HomeMemoryService.get_appliance_history(db, appliance.id) if appliance else {}
    history_summary = f"{len(history.get('service_timeline', []))} prior services on record."

    diag_result = DiagnosticAgent.analyze_fault(
        symptom_text=job.raw_transcript or "",
        appliance_type=appliance.appliance_type if appliance else "REFRIGERATOR",
        brand=appliance.brand if appliance else "LG",
        model_number=appliance.model_number if appliance else None,
        past_repair_summary=history_summary
    )

    hypotheses = diag_result.get("hypotheses", [])
    job.diagnostic_hypotheses = json.dumps(hypotheses)
    
    # Check parts catalogue for top hypothesis
    parts_status = "UNKNOWN"
    selected_part_id = None
    if hypotheses:
        top_part_code = hypotheses[0].get("required_part_code")
        if top_part_code:
            part_check = PartsCatalogueService.verify_compatibility(
                db=db,
                part_code=top_part_code,
                model_number=appliance.model_number if appliance else None
            )
            parts_status = part_check["status"]
            if part_check["is_verified"] and part_check.get("part"):
                selected_part_id = part_check["part"]["id"]

    job.parts_status = parts_status
    job.selected_part_id = selected_part_id
    
    # Update state
    target_state = JobState.INSPECT_FIRST_RECOMMENDED.value if diag_result.get("abstain") else JobState.DIAGNOSIS_READY.value
    prev_state = job.state
    job.state = target_state
    
    event = JobEvent(
        job_id=job.id,
        from_state=prev_state,
        to_state=target_state,
        actor="SYSTEM",
        comment=f"Diagnostic reasoning executed. Parts status: {parts_status}.",
        payload=json.dumps(diag_result)
    )
    db.add(event)
    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "state": job.state,
        "parts_status": job.parts_status,
        "hypotheses": hypotheses,
        "abstain": diag_result.get("abstain", False)
    }
