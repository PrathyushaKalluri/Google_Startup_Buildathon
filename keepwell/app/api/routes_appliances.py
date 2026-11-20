from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import Appliance, Job
from app.services.home_memory_service import HomeMemoryService

router = APIRouter(prefix="/api/appliances", tags=["Home Memory"])

@router.get("/{appliance_id}/history")
def get_appliance_history(appliance_id: int, db: Session = Depends(get_db)):
    """Returns verified Home Memory timeline for an appliance."""
    history = HomeMemoryService.get_appliance_history(db, appliance_id)
    if not history:
        raise HTTPException(status_code=404, detail="Appliance not found")
    return history

@router.get("/by-magic/{token}")
def get_magic_link_context(token: str, db: Session = Depends(get_db)):
    """Serves zero-login magic link for household customer."""
    job = db.query(Job).filter(Job.magic_token == token).first()
    if not job:
        raise HTTPException(status_code=404, detail="Invalid or expired magic link")

    appliance_history = HomeMemoryService.get_appliance_history(db, job.appliance_id) if job.appliance_id else {}
    
    quote_data = None
    if job.quotes:
        q = job.quotes[-1]
        quote_data = {
            "quote_id": q.id,
            "visiting_charge": q.visiting_charge,
            "labor_charge": q.labor_charge,
            "parts_cost": q.parts_cost,
            "gst_amount": q.gst_amount,
            "total_amount": q.total_amount,
            "agency_approved": q.agency_approved,
            "customer_approved": q.customer_approved,
            "payment_status": q.payment_status
        }

    return {
        "job_id": job.id,
        "job_state": job.state,
        "customer_name": job.customer.name,
        "appliance": appliance_history,
        "symptom": job.raw_transcript,
        "scheduled_slot": job.scheduled_slot,
        "quote": quote_data
    }
