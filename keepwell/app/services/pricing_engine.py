from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.db_models import Part, Quote, Job

class PricingEngine:
    """
    Deterministic Rate Card & Price Calculation Engine.
    Rules:
    - Agency rate card defines labor and visiting charges.
    - Verified parts catalogue defines component cost.
    - Statutory GST (18%) is applied mathematically.
    - NO LLM ever calculates money or taxes.
    """

    DEFAULT_RATES = {
        "VISITING_CHARGE": 250.0,
        "LABOR_GENERAL_DIAGNOSIS": 300.0,
        "LABOR_GAS_CHARGING": 850.0,
        "LABOR_COMPRESSOR_REPLACE": 1200.0,
        "LABOR_CAPACITOR_REPLACE": 350.0,
        "LABOR_FAN_MOTOR_REPLACE": 450.0,
        "GST_RATE": 0.18 # 18% GST standard in India
    }

    @classmethod
    def calculate_quote(
        cls,
        db: Session,
        job_id: int,
        visiting_charge: Optional[float] = None,
        labor_charge: Optional[float] = None,
        part_code: Optional[str] = None
    ) -> Dict[str, Any]:
        v_charge = visiting_charge if visiting_charge is not None else cls.DEFAULT_RATES["VISITING_CHARGE"]
        l_charge = labor_charge if labor_charge is not None else cls.DEFAULT_RATES["LABOR_GENERAL_DIAGNOSIS"]
        
        parts_cost = 0.0
        part_obj = None
        if part_code:
            part_obj = db.query(Part).filter(Part.code == part_code).first()
            if part_obj:
                parts_cost = float(part_obj.price)

        subtotal = round(v_charge + l_charge + parts_cost, 2)
        gst_amount = round(subtotal * cls.DEFAULT_RATES["GST_RATE"], 2)
        total_amount = round(subtotal + gst_amount, 2)

        return {
            "job_id": job_id,
            "visiting_charge": v_charge,
            "labor_charge": l_charge,
            "parts_cost": parts_cost,
            "subtotal": subtotal,
            "gst_rate_percent": 18.0,
            "gst_amount": gst_amount,
            "total_amount": total_amount,
            "part_code": part_code,
            "part_name": part_obj.name if part_obj else None
        }

    @classmethod
    def save_quote(cls, db: Session, quote_data: Dict[str, Any]) -> Quote:
        quote = Quote(
            job_id=quote_data["job_id"],
            visiting_charge=quote_data["visiting_charge"],
            labor_charge=quote_data["labor_charge"],
            parts_cost=quote_data["parts_cost"],
            gst_amount=quote_data["gst_amount"],
            total_amount=quote_data["total_amount"],
            agency_approved=False,
            customer_approved=False,
            payment_status="PENDING"
        )
        db.add(quote)
        db.commit()
        db.refresh(quote)
        return quote
