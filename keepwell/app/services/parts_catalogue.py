import json
import os
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.db_models import Part

class PartsCatalogueService:
    """
    Deterministic Parts Catalogue Service.
    Strict Rule: The LLM is NEVER the source of truth for part compatibility.
    A part is marked 'VERIFIED' only if listed in the verified catalogue.
    """

    @staticmethod
    def verify_compatibility(db: Session, part_code: str, model_number: Optional[str]) -> Dict[str, Any]:
        """
        Verifies if a part code is confirmed compatible with a specific appliance model.
        """
        if not model_number:
            return {
                "status": "UNKNOWN_MODEL",
                "is_verified": False,
                "part": None,
                "recommendation": "INSPECT_FIRST_ON_SITE",
                "reason": "Model number unknown. Technician must verify part physically on site."
            }

        part = db.query(Part).filter(Part.code == part_code).first()
        if not part:
            return {
                "status": "NOT_IN_CATALOGUE",
                "is_verified": False,
                "part": None,
                "recommendation": "INSPECT_FIRST_ON_SITE",
                "reason": f"Part code '{part_code}' not found in authorized parts inventory."
            }

        if part.is_compatible_with(model_number):
            return {
                "status": "VERIFIED_COMPATIBLE",
                "is_verified": True,
                "part": {
                    "id": part.id,
                    "code": part.code,
                    "name": part.name,
                    "category": part.category,
                    "price": part.price,
                    "in_stock": part.in_stock > 0
                },
                "recommendation": "DISPATCH_WITH_KIT",
                "reason": f"Part {part.name} confirmed compatible with {model_number}."
            }
        else:
            return {
                "status": "INCOMPATIBLE",
                "is_verified": False,
                "part": {
                    "code": part.code,
                    "name": part.name
                },
                "recommendation": "DO_NOT_DISPATCH",
                "reason": f"Part {part.name} is NOT compatible with {model_number}."
            }

    @staticmethod
    def get_parts_for_symptom(db: Session, category: str) -> List[Part]:
        return db.query(Part).filter(Part.category == category).all()
