"""Deterministic visit planner engine (A2).

Builds a `VisitPlan` from diagnosis output, carrying `already_tried` so the
technician never repeats a failed safe fix, required skills, safety certs,
tools, p50/p80 duration estimates, and verified parts with availability
resolved along the source ladder: `van` -> `centre` -> `parts_centre`.
"""

from __future__ import annotations

import uuid
from typing import Literal, Optional, Sequence

from pydantic import BaseModel, Field

from services.agents.engines.parts import (
    CataloguePart,
    CompatibilityRow,
    RequestedPart,
    UnresolvedPart,
    VerifiedPart,
    resolve_parts,
)
from services.agents.engines.urgency import normalize_category

SourceLadder = Literal["van", "centre", "parts_centre"]
SOURCE_LADDER_ORDER: tuple[SourceLadder, ...] = ("van", "centre", "parts_centre")

# Default p50/p80 visit durations (minutes) by category and complexity band
_DURATION_TABLE: dict[tuple[str, str], tuple[int, int]] = {
    ("air_conditioner", "basic"): (45, 70),
    ("air_conditioner", "standard"): (60, 95),
    ("air_conditioner", "complex"): (90, 140),
    ("refrigerator", "basic"): (40, 65),
    ("refrigerator", "standard"): (60, 90),
    ("refrigerator", "complex"): (90, 135),
    ("washing_machine", "basic"): (40, 60),
    ("washing_machine", "standard"): (55, 85),
    ("washing_machine", "complex"): (85, 130),
    ("water_purifier", "basic"): (30, 50),
    ("water_purifier", "standard"): (45, 70),
    ("water_purifier", "complex"): (60, 90),
    ("water_heater", "basic"): (35, 55),
    ("water_heater", "standard"): (50, 80),
    ("water_heater", "complex"): (75, 115),
}

_DEFAULT_TOOLS_BY_CATEGORY: dict[str, list[str]] = {
    "air_conditioner": ["multimeter", "clamp_meter", "screwdriver_set", "gas_gauge"],
    "refrigerator": ["multimeter", "screwdriver_set", "clamp_meter"],
    "washing_machine": ["multimeter", "screwdriver_set", "pliers"],
    "water_purifier": ["tds_meter", "screwdriver_set", "spanner_set"],
    "water_heater": ["multimeter", "insulated_screwdriver_set", "spanner_set"],
}


class StockItem(BaseModel):
    part_no: str
    holder_type: SourceLadder
    quantity: int = Field(default=0, ge=0)


class PlannedPart(BaseModel):
    part_no: str
    name: str
    probability: float = Field(default=1.0, ge=0.0, le=1.0)
    quantity: int = Field(default=1, ge=1)
    source_ladder: SourceLadder
    ready: bool


class VisitPlan(BaseModel):
    """Matches Contract C5.1 VisitPlan (with additive `unresolved_parts`)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: int = 1
    trigger_reason: str
    already_tried: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    est_duration_p50_min: int
    est_duration_p80_min: int
    tools_needed: list[str] = Field(default_factory=list)
    requires_safety_cert: list[str] = Field(default_factory=list)
    parts: list[PlannedPart] = Field(default_factory=list)
    unresolved_parts: list[UnresolvedPart] = Field(default_factory=list)
    access_notes: str = ""
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)


def resolve_part_source(
    part_no: str,
    quantity: int,
    stock_rows: Sequence[StockItem],
) -> tuple[SourceLadder, bool]:
    """Pick the highest-priority source on the `van -> centre -> parts_centre` ladder."""
    qty_by_holder: dict[SourceLadder, int] = {
        "van": 0,
        "centre": 0,
        "parts_centre": 0,
    }
    target = part_no.strip().lower()
    for row in stock_rows:
        if row.part_no.strip().lower() == target:
            qty_by_holder[row.holder_type] += row.quantity

    for holder in SOURCE_LADDER_ORDER:
        if qty_by_holder[holder] >= quantity:
            return holder, True

    return "parts_centre", False


def build_visit_plan(
    *,
    category_code: str,
    trigger_reason: str,
    complexity_band: Literal["basic", "standard", "complex"] = "standard",
    already_tried: Optional[Sequence[str]] = None,
    required_skills: Optional[Sequence[str]] = None,
    requires_safety_cert: Optional[Sequence[str]] = None,
    tools_needed: Optional[Sequence[str]] = None,
    verified_parts: Optional[Sequence[VerifiedPart]] = None,
    requested_parts: Optional[Sequence[RequestedPart]] = None,
    brand_id: Optional[str] = None,
    model_id: Optional[str] = None,
    catalogue_rows: Optional[Sequence[CataloguePart]] = None,
    compat_rows: Optional[Sequence[CompatibilityRow]] = None,
    stock_rows: Optional[Sequence[StockItem]] = None,
    access_notes: str = "",
    confidence: float = 0.75,
    version: int = 1,
    est_duration_p50_min: Optional[int] = None,
    est_duration_p80_min: Optional[int] = None,
) -> VisitPlan:
    """Construct a VisitPlan with verified parts and source-ladder readiness."""
    norm_cat = normalize_category(category_code) or "air_conditioner"
    p50_default, p80_default = _DURATION_TABLE.get((norm_cat, complexity_band), (50, 80))
    p50 = est_duration_p50_min if est_duration_p50_min is not None else p50_default
    p80 = est_duration_p80_min if est_duration_p80_min is not None else max(p80_default, p50)

    resolved_verified: list[VerifiedPart] = list(verified_parts or [])
    unresolved: list[UnresolvedPart] = []

    if requested_parts:
        if brand_id and model_id and catalogue_rows is not None and compat_rows is not None:
            v_parts, u_parts = resolve_parts(
                requested_parts,
                brand_id=brand_id,
                model_id=model_id,
                catalogue_rows=catalogue_rows,
                compat_rows=compat_rows,
            )
            resolved_verified.extend(v_parts)
            unresolved.extend(u_parts)
        else:
            for rp in requested_parts:
                unresolved.append(
                    UnresolvedPart(
                        query=rp.part_no or rp.name or "",
                        quantity=rp.quantity,
                        reason="Catalogue or model identity missing; cannot verify part.",
                        flag="compatibility_unverified",
                    )
                )

    stocks = list(stock_rows or [])
    planned_parts: list[PlannedPart] = []
    for vp in resolved_verified:
        source, ready = resolve_part_source(vp.part_no, vp.quantity, stocks)
        planned_parts.append(
            PlannedPart(
                part_no=vp.part_no,
                name=vp.name,
                probability=vp.probability,
                quantity=vp.quantity,
                source_ladder=source,
                ready=ready,
            )
        )

    skills = list(required_skills) if required_skills is not None else [norm_cat]
    tools = (
        list(tools_needed)
        if tools_needed is not None
        else list(_DEFAULT_TOOLS_BY_CATEGORY.get(norm_cat, ["multimeter", "screwdriver_set"]))
    )

    return VisitPlan(
        version=version,
        trigger_reason=trigger_reason,
        already_tried=list(already_tried or []),
        required_skills=skills,
        est_duration_p50_min=p50,
        est_duration_p80_min=p80,
        tools_needed=tools,
        requires_safety_cert=list(requires_safety_cert or []),
        parts=planned_parts,
        unresolved_parts=unresolved,
        access_notes=access_notes,
        confidence=confidence,
    )
