"""Deterministic technician assignment & 6-factor scoring engine (A2).

Exact weights from `input/dataset/csv/scoring_config.csv` (`assignment_v1`):
- fix_confidence:  30
- parts_readiness: 25
- time_to_visit:   20
- route_cost:      15
- reliability:      5
- household_fit:    5
Total:            100  (price is NOT scored: `PRICE_SCORED = False`)
"""

from __future__ import annotations

import math
from typing import Literal, Optional, Sequence

from pydantic import BaseModel, Field

ASSIGNMENT_WEIGHTS: dict[str, int] = {
    "fix_confidence": 30,
    "parts_readiness": 25,
    "time_to_visit": 20,
    "route_cost": 15,
    "reliability": 5,
    "household_fit": 5,
}
PRICE_SCORED: bool = False

assert sum(ASSIGNMENT_WEIGHTS.values()) == 100


class TechnicianProfile(BaseModel):
    technician_id: str
    name: str
    active: bool = True
    identity_verified: bool = True
    skill_level: int = Field(default=3, ge=0, le=5)
    safety_certs: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    lat: float
    lon: float
    # Pre-computed or raw metrics (0.0..1.0)
    first_time_fix_rate: float = Field(default=0.80, ge=0.0, le=1.0)
    on_time_rate: float = Field(default=0.85, ge=0.0, le=1.0)
    repeat_visit_rate_30d: float = Field(default=0.05, ge=0.0, le=1.0)
    parts_ready_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    earliest_slot_hours: float = Field(default=4.0, ge=0.0)
    slot_start: Optional[str] = None
    slot_end: Optional[str] = None
    drive_minutes: Optional[float] = None  # Routes API value; haversine fallback if None


class AssignmentRequirements(BaseModel):
    household_lat: float
    household_lon: float
    household_language: str = "en"
    min_skill_level: int = Field(default=2, ge=1, le=5)
    required_safety_certs: list[str] = Field(default_factory=list)
    max_km: float = Field(default=25.0, gt=0.0)
    max_wait_hours: float = Field(default=48.0, gt=0.0)
    max_drive_minutes: float = Field(default=90.0, gt=0.0)


class ScoreBreakdown(BaseModel):
    fix_confidence: float
    parts_readiness: float
    time_to_visit: float
    route_cost: float
    reliability: float
    household_fit: float


class AssignmentCandidate(BaseModel):
    """Matches Contract C5.1 AssignmentCandidate."""

    technician_id: str
    name: str
    rank: int
    score: float
    score_breakdown: ScoreBreakdown
    distance_km: float
    drive_minutes: float
    slot_start: Optional[str] = None
    slot_end: Optional[str] = None
    outcome: Literal["proposed", "chosen", "not_chosen"] = "proposed"
    chosen_by: Literal["agent", "centre_console"] = "agent"
    override_reason: Optional[str] = None
    why: str


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two WGS-84 coordinates."""
    r_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(dlam / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r_km * c


def estimate_drive_minutes(distance_km: float, avg_speed_kmh: float = 24.0) -> float:
    """Fallback drive-time estimate (Hyderabad urban traffic default 24 km/h)."""
    if distance_km <= 0.0:
        return 0.0
    return round((distance_km / avg_speed_kmh) * 60.0, 1)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_technicians(
    technicians: Sequence[TechnicianProfile],
    requirements: AssignmentRequirements,
    *,
    top_k: int = 3,
) -> list[AssignmentCandidate]:
    """Filter eligible technicians and rank them with the exact 6-factor weights."""
    req_certs = set(requirements.required_safety_certs)
    scored: list[AssignmentCandidate] = []

    for tech in technicians:
        # Hard filters
        if not tech.active or not tech.identity_verified:
            continue
        if tech.skill_level < requirements.min_skill_level:
            continue
        if not req_certs.issubset(set(tech.safety_certs)):
            continue

        dist_km = round(
            haversine_km(
                tech.lat,
                tech.lon,
                requirements.household_lat,
                requirements.household_lon,
            ),
            2,
        )
        if dist_km > requirements.max_km:
            continue

        drive_min = (
            float(tech.drive_minutes)
            if tech.drive_minutes is not None
            else estimate_drive_minutes(dist_km)
        )

        # Normalized 0..1 sub-scores
        skill_norm = _clamp01(tech.skill_level / 5.0)
        fix_conf_norm = _clamp01(0.5 * skill_norm + 0.5 * tech.first_time_fix_rate)
        parts_norm = _clamp01(tech.parts_ready_ratio)
        time_norm = _clamp01(1.0 - (tech.earliest_slot_hours / requirements.max_wait_hours))
        route_norm = _clamp01(1.0 - (drive_min / requirements.max_drive_minutes))
        reliability_norm = _clamp01(
            0.6 * tech.on_time_rate + 0.4 * (1.0 - tech.repeat_visit_rate_30d)
        )
        lang_match = requirements.household_language.lower() in {
            lang.lower() for lang in tech.languages
        }
        household_fit_norm = 1.0 if lang_match else 0.3

        breakdown = ScoreBreakdown(
            fix_confidence=round(fix_conf_norm * ASSIGNMENT_WEIGHTS["fix_confidence"], 2),
            parts_readiness=round(parts_norm * ASSIGNMENT_WEIGHTS["parts_readiness"], 2),
            time_to_visit=round(time_norm * ASSIGNMENT_WEIGHTS["time_to_visit"], 2),
            route_cost=round(route_norm * ASSIGNMENT_WEIGHTS["route_cost"], 2),
            reliability=round(reliability_norm * ASSIGNMENT_WEIGHTS["reliability"], 2),
            household_fit=round(household_fit_norm * ASSIGNMENT_WEIGHTS["household_fit"], 2),
        )
        total_score = round(
            breakdown.fix_confidence
            + breakdown.parts_readiness
            + breakdown.time_to_visit
            + breakdown.route_cost
            + breakdown.reliability
            + breakdown.household_fit,
            2,
        )

        lang_note = (
            f"speaks {requirements.household_language}"
            if lang_match
            else "language fallback"
        )
        why = (
            f"Skill L{tech.skill_level} (FTF {int(round(tech.first_time_fix_rate * 100))}%), "
            f"parts {int(round(parts_norm * 100))}% ready, "
            f"{dist_km:.1f} km / {int(round(drive_min))} min away, {lang_note}."
        )

        scored.append(
            AssignmentCandidate(
                technician_id=tech.technician_id,
                name=tech.name,
                rank=0,
                score=total_score,
                score_breakdown=breakdown,
                distance_km=dist_km,
                drive_minutes=drive_min,
                slot_start=tech.slot_start,
                slot_end=tech.slot_end,
                why=why,
            )
        )

    scored.sort(
        key=lambda c: (
            c.score,
            c.score_breakdown.fix_confidence,
            c.score_breakdown.time_to_visit,
            -c.distance_km,
        ),
        reverse=True,
    )

    top = scored[:top_k] if top_k > 0 else scored
    for idx, cand in enumerate(top, start=1):
        cand.rank = idx
    return top
