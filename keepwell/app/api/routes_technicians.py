import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import Job, JobEvent, Technician
from app.services.dispatch_service import DispatchService
from app.services.home_memory_service import HomeMemoryService
from app.agents.memory_agent import MemoryAgent
from app.agents.preparation_agent import PreparationAgent
from app.core.state_machine import JobState

router = APIRouter(prefix="/api/technicians", tags=["Technicians & Field Service"])

@router.get("/recommend/{job_id}")
def recommend_technicians(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    techs = DispatchService.rank_technicians(
        db=db,
        agency_id=job.agency_id,
        appliance_type=job.appliance.appliance_type if job.appliance else "REFRIGERATOR",
        customer_language=job.customer.language
    )
    return {"job_id": job.id, "recommended_technicians": techs, "available_slots": DispatchService.AVAILABLE_SLOTS}

@router.post("/dispatch/{job_id}")
def dispatch_technician(
    job_id: int,
    technician_id: int = Body(..., embed=True),
    slot: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    DispatchService.assign_technician(db, job, technician_id, slot)
    prev = job.state
    job.state = JobState.TECHNICIAN_DISPATCHED.value

    event = JobEvent(
        job_id=job.id,
        from_state=prev,
        to_state=job.state,
        actor="AGENCY",
        comment=f"Dispatched technician #{technician_id} for slot {slot}."
    )
    db.add(event)
    db.commit()

    return {"status": "DISPATCHED", "job_id": job.id, "state": job.state}

@router.post("/close-out/{job_id}")
def close_out_repair(
    job_id: int,
    technician_audio_transcript: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Step 6 of Flagship scenario:
    Technician records voice close-out. MemoryAgent processes findings.
    Verified event saved permanently to Home Memory.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Memory agent creates structured close-out
    record = MemoryAgent.process_technician_closeout(technician_audio_transcript)

    # Save to Home Memory
    event = HomeMemoryService.record_service_event(
        db=db,
        job=job,
        technician_findings=record["fault_identified"],
        action_taken=record["action_taken"],
        customer_confirmed=True
    )

    prev = job.state
    job.state = JobState.CLOSED_RESOLVED.value
    
    log_event = JobEvent(
        job_id=job.id,
        from_state=prev,
        to_state=job.state,
        actor="TECHNICIAN",
        comment=f"Repair completed and verified. Saved to Home Memory (Event #{event.id}).",
        payload=json.dumps(record)
    )
    db.add(log_event)
    db.commit()

    return {
        "status": "CLOSED_RESOLVED",
        "job_id": job.id,
        "home_memory_event_id": event.id,
        "first_visit_resolved": event.first_visit_resolved,
        "service_summary": record
    }
