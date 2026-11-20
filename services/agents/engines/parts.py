"""Hard parts catalogue & compatibility verification engine (A2).

Enforces Contract C11 ("Parts are never invented"):
Every part named in a visit plan, technician brief, debrief, quote, or stock
request MUST exist in `part_catalogue` for the appliance's brand AND be linked
to the appliance's model in `part_compatibility`.
Any part failing either check goes into `unresolved` and NEVER into verified
parts or quotes.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Sequence, Union

from pydantic import BaseModel, Field

_DATASET_CSV_DIR = Path(__file__).resolve().parents[3] / "input" / "dataset" / "csv"


class CataloguePart(BaseModel):
    id: str
    brand_id: str
    part_no: str
    name: str
    kind: str = "genuine"
    substitution_group: Optional[str] = None
    mrp_paise: int = 0
    warranty_months: int = 0


class CompatibilityRow(BaseModel):
    part_id: str
    model_id: str
    revision: Optional[str] = None


class RequestedPart(BaseModel):
    part_no: Optional[str] = None
    name: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    probability: float = Field(default=1.0, ge=0.0, le=1.0)


class VerifiedPart(BaseModel):
    part_id: str
    brand_id: str
    part_no: str
    name: str
    kind: str
    mrp_paise: int
    warranty_months: int
    quantity: int = 1
    probability: float = 1.0
    model_id: str
    compatibility_verified: bool = True


class UnresolvedPart(BaseModel):
    query: str
    quantity: int = 1
    reason: str
    flag: str = "compatibility_unverified"


def _norm(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


@lru_cache(maxsize=2)
def load_part_catalogue_csv(
    csv_path: Optional[str] = None,
) -> list[CataloguePart]:
    path = Path(csv_path) if csv_path else (_DATASET_CSV_DIR / "part_catalogue.csv")
    rows: list[CataloguePart] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                CataloguePart(
                    id=row["id"],
                    brand_id=row["brand_id"],
                    part_no=row["part_no"],
                    name=row["name"],
                    kind=row.get("kind", "genuine"),
                    substitution_group=row.get("substitution_group") or None,
                    mrp_paise=int(row.get("mrp_paise") or 0),
                    warranty_months=int(row.get("warranty_months") or 0),
                )
            )
    return rows


@lru_cache(maxsize=2)
def load_part_compatibility_csv(
    csv_path: Optional[str] = None,
) -> list[CompatibilityRow]:
    path = Path(csv_path) if csv_path else (_DATASET_CSV_DIR / "part_compatibility.csv")
    rows: list[CompatibilityRow] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                CompatibilityRow(
                    part_id=row["part_id"],
                    model_id=row["model_id"],
                    revision=row.get("revision") or None,
                )
            )
    return rows


def _coerce_requested(item: Union[str, dict[str, Any], RequestedPart]) -> RequestedPart:
    if isinstance(item, RequestedPart):
        return item
    if isinstance(item, str):
        return RequestedPart(part_no=item.strip(), name=item.strip(), quantity=1)
    if isinstance(item, dict):
        return RequestedPart(**item)
    raise TypeError(f"Unsupported requested part type: {type(item)!r}")


def _coerce_catalogue(item: Union[dict[str, Any], CataloguePart]) -> CataloguePart:
    return item if isinstance(item, CataloguePart) else CataloguePart(**item)


def _coerce_compat(item: Union[dict[str, Any], CompatibilityRow]) -> CompatibilityRow:
    return item if isinstance(item, CompatibilityRow) else CompatibilityRow(**item)


def resolve_parts(
    requested_parts: Sequence[Union[str, dict[str, Any], RequestedPart]],
    brand_id: str,
    model_id: str,
    catalogue_rows: Sequence[Union[dict[str, Any], CataloguePart]],
    compat_rows: Sequence[Union[dict[str, Any], CompatibilityRow]],
) -> tuple[list[VerifiedPart], list[UnresolvedPart]]:
    """Verify requested parts against brand catalogue and model compatibility.

    Returns `(verified_parts, unresolved)`.
    Any part not present in `catalogue_rows` for `brand_id`, or not linked to
    `model_id` in `compat_rows`, is placed in `unresolved` and NEVER in
    `verified_parts`.
    """
    cat = [_coerce_catalogue(r) for r in catalogue_rows]
    compat = [_coerce_compat(r) for r in compat_rows]

    brand_cat = [p for p in cat if p.brand_id == brand_id]
    by_part_no: dict[str, CataloguePart] = {_norm(p.part_no): p for p in brand_cat}
    by_name: dict[str, CataloguePart] = {_norm(p.name): p for p in brand_cat}
    compat_pairs: set[tuple[str, str]] = {(c.part_id, c.model_id) for c in compat}

    verified: list[VerifiedPart] = []
    unresolved: list[UnresolvedPart] = []

    for raw in requested_parts:
        req = _coerce_requested(raw)
        query_label = (req.part_no or req.name or "").strip()
        if not query_label:
            unresolved.append(
                UnresolvedPart(
                    query="",
                    quantity=req.quantity,
                    reason="empty_part_query",
                    flag="not_in_brand_catalogue",
                )
            )
            continue

        matched: Optional[CataloguePart] = None
        if req.part_no:
            matched = by_part_no.get(_norm(req.part_no))
        if matched is None and req.name:
            matched = by_name.get(_norm(req.name))

        if matched is None:
            unresolved.append(
                UnresolvedPart(
                    query=query_label,
                    quantity=req.quantity,
                    reason=f"Part {query_label!r} not found in part_catalogue for brand {brand_id}.",
                    flag="not_in_brand_catalogue",
                )
            )
            continue

        if (matched.id, model_id) not in compat_pairs:
            unresolved.append(
                UnresolvedPart(
                    query=query_label,
                    quantity=req.quantity,
                    reason=(
                        f"Part {matched.part_no!r} exists for brand {brand_id} but is not "
                        f"linked to model {model_id} in part_compatibility."
                    ),
                    flag="compatibility_unverified",
                )
            )
            continue

        verified.append(
            VerifiedPart(
                part_id=matched.id,
                brand_id=matched.brand_id,
                part_no=matched.part_no,
                name=matched.name,
                kind=matched.kind,
                mrp_paise=matched.mrp_paise,
                warranty_months=matched.warranty_months,
                quantity=req.quantity,
                probability=req.probability,
                model_id=model_id,
                compatibility_verified=True,
            )
        )

    return verified, unresolved
