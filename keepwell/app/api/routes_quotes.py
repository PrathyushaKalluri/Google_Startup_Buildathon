import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import Job, Quote, JobEvent
from app.models.schemas import QuoteCreateRequest
from app.services.pricing_engine import PricingEngine
from app.services.payment_gateway import PaymentGatewayService
from app.core.state_machine import JobState

router = APIRouter(prefix="/api/quotes", tags=["Quotes & Billing"])

@router.post("/generate")
def generate_quote(req: QuoteCreateRequest, db: Session = Depends(get_db)):
    """
    Step 5 of Flagship scenario:
    Calculates deterministic rate card quote (Visiting + Labor + Part + 18% GST).
    Transitions Job to AGENCY_QUOTE_REVIEW.
    """
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    quote_calc = PricingEngine.calculate_quote(
        db=db,
        job_id=job.id,
        visiting_charge=req.visiting_charge,
        labor_charge=req.labor_charge,
        part_code=req.part_code
    )

    quote = PricingEngine.save_quote(db=db, quote_data=quote_calc)
    
    # State update
    prev = job.state
    job.state = JobState.AGENCY_QUOTE_REVIEW.value
    event = JobEvent(
        job_id=job.id,
        from_state=prev,
        to_state=job.state,
        actor="SYSTEM",
        comment=f"Generated deterministic quote #{quote.id} for Rs. {quote.total_amount:.2f}",
        payload=json.dumps(quote_calc)
    )
    db.add(event)
    db.commit()

    return {
        "quote_id": quote.id,
        "job_id": job.id,
        "calculation": quote_calc,
        "state": job.state
    }

@router.post("/{quote_id}/agency-approve")
def agency_approve_quote(quote_id: int, db: Session = Depends(get_db)):
    """Agency Owner signs off on quote before dispatching to customer."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    quote.agency_approved = True
    job = quote.job
    job.state = JobState.QUOTE_SENT.value

    event = JobEvent(
        job_id=job.id,
        from_state=JobState.AGENCY_QUOTE_REVIEW.value,
        to_state=JobState.QUOTE_SENT.value,
        actor="AGENCY",
        comment=f"Agency Owner approved quote #{quote.id}. Sent to household via WhatsApp."
    )
    db.add(event)
    db.commit()

    return {"status": "APPROVED", "quote_id": quote.id, "job_state": job.state}

@router.post("/{quote_id}/customer-approve")
def customer_approve_quote(quote_id: int, db: Session = Depends(get_db)):
    """Customer clicks 'Approve & Book' on WhatsApp or Magic Link."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    quote.customer_approved = True
    job = quote.job
    job.state = JobState.QUOTE_APPROVED.value

    # Generate UPI intent payment link
    upi_info = PaymentGatewayService.generate_upi_link(
        quote_id=quote.id,
        amount=quote.total_amount,
        agency_name=job.agency.name if job.agency else "KeepWell Repair"
    )

    event = JobEvent(
        job_id=job.id,
        from_state=JobState.QUOTE_SENT.value,
        to_state=JobState.QUOTE_APPROVED.value,
        actor="CUSTOMER",
        comment=f"Customer accepted quote #{quote.id}. UPI payment request issued."
    )
    db.add(event)
    db.commit()

    return {
        "status": "APPROVED_BY_CUSTOMER",
        "quote_id": quote.id,
        "job_state": job.state,
        "upi_payment": upi_info
    }

@router.post("/{quote_id}/upi-callback")
def upi_payment_callback(quote_id: int, db: Session = Depends(get_db)):
    """Simulates signed UPI gateway webhook payment success."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    quote.payment_status = "PAID"
    quote.upi_txn_id = f"UPI_REF_{quote.id}_SUCCESS"
    db.commit()

    return {"status": "PAID", "quote_id": quote.id, "txn_id": quote.upi_txn_id}
