"""Deterministic safe-fix catalogue selector and validator (A2).

Wraps `input/dataset/csv/safe_fix_catalogue.csv` (or DB rows) and enforces
all schema CHECK constraints in code:
- status == 'active' (refuses 'review_due', 'retired', 'draft')
- 1 <= step_count <= 6 and len(steps) == step_count
- 1 <= est_minutes <= 12
- reversible is True
- needs_tools is False
- named reviewer_name and reviewed_on
- manual_doc_id and manual_page >= 1
- Never offered when safety_flag is True
"""

from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from services.agents.engines.urgency import normalize_category

_DEFAULT_CATALOGUE_CSV = (
    Path(__file__).resolve().parents[3] / "input" / "dataset" / "csv" / "safe_fix_catalogue.csv"
)


class SafeFixStep(BaseModel):
    n: int
    say: str
    check: str


class SafeFixEntry(BaseModel):
    id: str
    code: str
    category_code: str
    brand_id: Optional[str] = None
    model_series: Optional[str] = None
    fault_family: str = ""
    title: str
    symptom_terms: list[str] = Field(default_factory=list)
    steps: list[SafeFixStep] = Field(default_factory=list)
    step_count: int
    est_minutes: int
    reversible: bool
    needs_tools: bool
    opens_panel: bool = False
    manual_doc_id: Optional[str] = None
    manual_page: Optional[int] = None
    worst_case: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewer_role: Optional[str] = None
    reviewed_on: Optional[str] = None
    review_due: Optional[str] = None
    status: str


class SafeFixSelection(BaseModel):
    entry: SafeFixEntry
    brand_specific: bool
    matched_terms: list[str]
    effectiveness_rate: Optional[float] = None


def _parse_pg_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("t", "true", "1", "yes")


def _parse_pg_array(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    raw = str(value or "").strip()
    if not raw or raw == r"\N" or raw == "{}":
        return []
    if raw.startswith("{") and raw.endswith("}"):
        inner = raw[1:-1]
        # Use csv reader to properly handle quoted comma-separated elements
        row = next(csv.reader([inner]))
        return [item.strip() for item in row if item.strip()]
    return [raw]


def _clean_nullable(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s == r"\N":
        return None
    return s


def validate_safe_fix_entry(entry: SafeFixEntry) -> tuple[bool, list[str]]:
    """Enforce all DB CHECK and safety invariants on a catalogue entry."""
    errors: list[str] = []
    if entry.status != "active":
        errors.append(f"status must be 'active', got {entry.status!r}")
    if not (1 <= entry.step_count <= 6):
        errors.append(f"step_count must be between 1 and 6, got {entry.step_count}")
    if len(entry.steps) != entry.step_count:
        errors.append(f"len(steps)={len(entry.steps)} does not match step_count={entry.step_count}")
    if not (1 <= entry.est_minutes <= 12):
        errors.append(f"est_minutes must be between 1 and 12, got {entry.est_minutes}")
    if not entry.reversible:
        errors.append("entry must be reversible=True")
    if entry.needs_tools:
        errors.append("entry must have needs_tools=False")
    if not (entry.reviewer_name and entry.reviewer_name.strip()):
        errors.append("reviewer_name is required")
    if not (entry.reviewed_on and entry.reviewed_on.strip()):
        errors.append("reviewed_on is required")
    if not (entry.manual_doc_id and entry.manual_doc_id.strip()):
        errors.append("manual_doc_id is required")
    if entry.manual_page is None or entry.manual_page < 1:
        errors.append("manual_page must be >= 1")
    return (len(errors) == 0), errors


@lru_cache(maxsize=4)
def load_safe_fix_catalogue(csv_path: Optional[str] = None) -> list[SafeFixEntry]:
    """Load safe-fix catalogue entries from CSV."""
    path = Path(csv_path) if csv_path else _DEFAULT_CATALOGUE_CSV
    entries: list[SafeFixEntry] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            raw_steps = json.loads(row["steps"]) if row.get("steps") else []
            steps = [SafeFixStep(**s) for s in raw_steps]
            manual_page_raw = _clean_nullable(row.get("manual_page"))
            entries.append(
                SafeFixEntry(
                    id=row["id"],
                    code=row["code"],
                    category_code=row["category_code"],
                    brand_id=_clean_nullable(row.get("brand_id")),
                    model_series=_clean_nullable(row.get("model_series")),
                    fault_family=row.get("fault_family", ""),
                    title=row["title"],
                    symptom_terms=_parse_pg_array(row.get("symptom_terms")),
                    steps=steps,
                    step_count=int(row["step_count"]),
                    est_minutes=int(row["est_minutes"]),
                    reversible=_parse_pg_bool(row["reversible"]),
                    needs_tools=_parse_pg_bool(row["needs_tools"]),
                    opens_panel=_parse_pg_bool(row.get("opens_panel", False)),
                    manual_doc_id=_clean_nullable(row.get("manual_doc_id")),
                    manual_page=int(manual_page_raw) if manual_page_raw is not None else None,
                    worst_case=_clean_nullable(row.get("worst_case")),
                    reviewer_name=_clean_nullable(row.get("reviewer_name")),
                    reviewer_role=_clean_nullable(row.get("reviewer_role")),
                    reviewed_on=_clean_nullable(row.get("reviewed_on")),
                    review_due=_clean_nullable(row.get("review_due")),
                    status=row["status"].strip().lower(),
                )
            )
    return entries


def _match_symptoms(
    entry_terms: list[str],
    symptoms: list[str],
    error_codes: list[str],
) -> list[str]:
    """Return catalogue symptom terms matched by household symptoms or error codes."""
    query_items = [s.strip().lower() for s in (*symptoms, *error_codes) if s and s.strip()]
    if not query_items:
        return []
    combined_query = " ".join(query_items)
    matched: list[str] = []
    for term in entry_terms:
        t_low = term.strip().lower()
        if not t_low:
            continue
        if t_low in query_items or t_low in combined_query or any(
            q in t_low for q in query_items if len(q) >= 2
        ):
            matched.append(term)
    return matched


def select_safe_fix(
    *,
    category_code: str,
    symptoms: list[str],
    brand_id: Optional[str] = None,
    error_codes: Optional[list[str]] = None,
    catalogue: Optional[list[SafeFixEntry]] = None,
    safety_flag: bool = False,
    exclude_codes: Optional[set[str]] = None,
    effectiveness_by_code: Optional[dict[str, float]] = None,
) -> Optional[SafeFixSelection]:
    """Select the single best eligible active safe-fix entry, or None.

    Ranking order:
    1. Brand-specific match (`entry.brand_id == brand_id`) over generic (`entry.brand_id is None`)
    2. Higher number of matched symptom/error terms
    3. Higher historical effectiveness rate (if provided)
    4. Shorter `est_minutes`
    """
    if safety_flag:
        return None

    norm_cat = normalize_category(category_code)
    entries = catalogue if catalogue is not None else load_safe_fix_catalogue()
    excluded = exclude_codes or set()
    eff_map = effectiveness_by_code or {}
    err_codes = list(error_codes or [])

    candidates: list[SafeFixSelection] = []
    for entry in entries:
        if entry.code in excluded:
            continue
        if normalize_category(entry.category_code) != norm_cat:
            continue
        is_valid, _ = validate_safe_fix_entry(entry)
        if not is_valid:
            continue
        if entry.brand_id is not None and entry.brand_id != brand_id:
            continue

        matched = _match_symptoms(entry.symptom_terms, symptoms, err_codes)
        if not matched:
            continue

        candidates.append(
            SafeFixSelection(
                entry=entry,
                brand_specific=(brand_id is not None and entry.brand_id == brand_id),
                matched_terms=matched,
                effectiveness_rate=eff_map.get(entry.code),
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda c: (
            1 if c.brand_specific else 0,
            len(c.matched_terms),
            c.effectiveness_rate if c.effectiveness_rate is not None else -1.0,
            -c.entry.est_minutes,
        ),
        reverse=True,
    )
    return candidates[0]
