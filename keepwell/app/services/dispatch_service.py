from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.db_models import Technician, Job

class DispatchService:
    """
    Technician slot and route dispatch service.
    Matches technicians based on language, appliance skills, and active status.
    """

    AVAILABLE_SLOTS = [
        "Today, 02:00 PM - 04:00 PM",
        "Today, 04:30 PM - 06:30 PM",
        "Tomorrow, 10:00 AM - 12:00 PM",
        "Tomorrow, 02:00 PM - 04:00 PM"
    ]

    @classmethod
    def rank_technicians(
        cls,
        db: Session,
        agency_id: int,
        appliance_type: str = "REFRIGERATOR",
        customer_language: str = "Telugu"
    ) -> List[Dict[str, Any]]:
        technicians = db.query(Technician).filter(
            Technician.agency_id == agency_id,
            Technician.active == True
        ).all()

        scored = []
        for tech in technicians:
            score = 100
            # Skill match
            if appliance_type.upper() in tech.skills.upper():
                score += 50
            # Language match
            if customer_language.lower() in tech.languages.lower():
                score += 30
            # Rating weight
            score += int(tech.rating * 10)

            scored.append({
                "id": tech.id,
                "name": tech.name,
                "phone": tech.phone,
                "skills": tech.skills,
                "languages": tech.languages,
                "rating": tech.rating,
                "match_score": score
            })

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored

    @classmethod
    def assign_technician(
        cls,
        db: Session,
        job: Job,
        technician_id: int,
        slot: str
    ) -> Job:
        job.assigned_technician_id = technician_id
        job.scheduled_slot = slot
        db.commit()
        db.refresh(job)
        return job
