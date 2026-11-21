"""Deterministic pricing, 18% GST, coverage split, and variance engine (A2).

All monetary amounts are exact integer paise (1 INR = 100 paise).
Implements:
- Estimate range (`build_estimate_range`)
- Firm quote (`build_firm_quote`)
- 18% GST calculation with deterministic integer rounding
- Warranty / AMC coverage split into `covered_paise` and `household_paise`
- Repeat-within-30d visit fee waiver (`visit_fee_paise = 0`)
- Variance % calculation between estimate and firm quote
"""

from __future__ import annotations

import uuid
from typing import Literal, Optional, Sequence

from pydantic import BaseModel, Field

from services.agents.engines.parts import VerifiedPart

GST_RATE_PERCENT: int = 18

PayerKind = Literal["household", "brand", "amc", "centre"]
LineKind = Literal["visit_fee", "labour", "part", "tax_gst", "waiver"]


class PriceBookEntry(BaseModel):
    category_code: str
    job_type: str = "repair"
    complexity_band: Literal["basic", "standard", "complex"] = "standard"
    visit_fee_paise: int = Field(ge=0)
    labour_paise: int = Field(ge=0)


class QuoteLine(BaseModel):
    kind: LineKind
    description: str
    amount_paise: int
    payer: PayerKind
    part_no: Optional[str] = None
    quantity: int = 1


class EstimateRange(BaseModel):
    low_paise: int
    high_paise: int
    household_low_paise: int
    household_high_paise: int
    covered_low_paise: int
    covered_high_paise: int
    visit_fee_waived: bool = False
    gst_rate_percent: int = GST_RATE_PERCENT


class FirmQuote(BaseModel):
    """Matches Contract C5.1 Quote."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: int = 1
    quote_type: Literal["estimate", "firm"] = "firm"
    lines: list[QuoteLine]
    subtotal_paise: int
    gst_paise: int
    total_paise: int
    household_paise: int
    covered_paise: int
    visit_fee_waived: bool = False
    approved_at: Optional[str] = None
    approval_method: Optional[str] = None


def compute_gst_paise(taxable_paise: int, gst_rate_percent: int = GST_RATE_PERCENT) -> int:
    """Compute GST in integer paise using half-up integer arithmetic."""
    if taxable_paise <= 0:
        return 0
    return (taxable_paise * gst_rate_percent + 50) // 100


def _payer_for_line(
    kind: Literal["visit_fee", "labour", "part"],
    entitlement: str,
    amc_covers_parts: bool = False,
) -> PayerKind:
    ent = (entitlement or "none").strip().lower()
    if ent in ("brand_warranty", "extended_warranty"):
        return "brand"
    if ent == "amc":
        if kind in ("visit_fee", "labour"):
            return "amc"
        return "amc" if amc_covers_parts else "household"
    return "household"


def build_firm_quote(
    *,
    price_book: PriceBookEntry,
    verified_parts: Optional[Sequence[VerifiedPart]] = None,
    entitlement: str = "out_of_warranty",
    is_repeat_30d: bool = False,
    amc_covers_parts: bool = False,
    quote_type: Literal["estimate", "firm"] = "firm",
    version: int = 1,
) -> FirmQuote:
    """Build an exact firm (or itemized estimate) quote in integer paise."""
    lines: list[QuoteLine] = []

    visit_fee = 0 if is_repeat_30d else price_book.visit_fee_paise
    visit_payer = _payer_for_line("visit_fee", entitlement, amc_covers_parts)
    if is_repeat_30d:
        lines.append(
            QuoteLine(
                kind="visit_fee",
                description="Visit fee (waived - repeat fault within 30 days)",
                amount_paise=0,
                payer="centre",
            )
        )
    elif visit_fee > 0:
        lines.append(
            QuoteLine(
                kind="visit_fee",
                description="Inspection / visit fee",
                amount_paise=visit_fee,
                payer=visit_payer,
            )
        )

    labour_payer = _payer_for_line("labour", entitlement, amc_covers_parts)
    if price_book.labour_paise > 0:
        lines.append(
            QuoteLine(
                kind="labour",
                description=f"Labour ({price_book.complexity_band} {price_book.job_type})",
                amount_paise=price_book.labour_paise,
                payer=labour_payer,
            )
        )

    part_payer = _payer_for_line("part", entitlement, amc_covers_parts)
    for vp in verified_parts or []:
        line_amt = vp.mrp_paise * vp.quantity
        lines.append(
            QuoteLine(
                kind="part",
                description=f"{vp.name} ({vp.part_no}) x{vp.quantity}",
                amount_paise=line_amt,
                payer=part_payer,
                part_no=vp.part_no,
                quantity=vp.quantity,
            )
        )

    household_taxable = sum(line.amount_paise for line in lines if line.payer == "household")
    covered_taxable = sum(line.amount_paise for line in lines if line.payer != "household")
    subtotal = household_taxable + covered_taxable

    household_gst = compute_gst_paise(household_taxable)
    covered_gst = compute_gst_paise(covered_taxable)
    total_gst = household_gst + covered_gst

    if household_gst > 0:
        lines.append(
            QuoteLine(
                kind="tax_gst",
                description=f"GST ({GST_RATE_PERCENT}%) - household share",
                amount_paise=household_gst,
                payer="household",
            )
        )
    if covered_gst > 0:
        covered_payer: PayerKind = (
            "amc" if (entitlement or "").strip().lower() == "amc" else "brand"
        )
        lines.append(
            QuoteLine(
                kind="tax_gst",
                description=f"GST ({GST_RATE_PERCENT}%) - covered share",
                amount_paise=covered_gst,
                payer=covered_payer,
            )
        )

    household_total = household_taxable + household_gst
    covered_total = covered_taxable + covered_gst
    grand_total = household_total + covered_total

    return FirmQuote(
        version=version,
        quote_type=quote_type,
        lines=lines,
        subtotal_paise=subtotal,
        gst_paise=total_gst,
        total_paise=grand_total,
        household_paise=household_total,
        covered_paise=covered_total,
        visit_fee_waived=is_repeat_30d,
    )


def build_estimate_range(
    *,
    price_book: PriceBookEntry,
    probable_parts: Optional[Sequence[VerifiedPart]] = None,
    entitlement: str = "out_of_warranty",
    is_repeat_30d: bool = False,
    amc_covers_parts: bool = False,
) -> EstimateRange:
    """Compute low (visit + labour only) and high (visit + labour + probable parts) estimates."""
    low_q = build_firm_quote(
        price_book=price_book,
        verified_parts=[],
        entitlement=entitlement,
        is_repeat_30d=is_repeat_30d,
        amc_covers_parts=amc_covers_parts,
        quote_type="estimate",
    )
    high_q = build_firm_quote(
        price_book=price_book,
        verified_parts=probable_parts or [],
        entitlement=entitlement,
        is_repeat_30d=is_repeat_30d,
        amc_covers_parts=amc_covers_parts,
        quote_type="estimate",
    )
    return EstimateRange(
        low_paise=low_q.total_paise,
        high_paise=high_q.total_paise,
        household_low_paise=low_q.household_paise,
        household_high_paise=high_q.household_paise,
        covered_low_paise=low_q.covered_paise,
        covered_high_paise=high_q.covered_paise,
        visit_fee_waived=is_repeat_30d,
    )


def compute_variance_pct(estimate_paise: int, firm_paise: int) -> float:
    """Percentage variance between estimate and firm quote."""
    if estimate_paise == 0:
        return 0.0 if firm_paise == 0 else 100.0
    return round(((firm_paise - estimate_paise) / estimate_paise) * 100.0, 2)


def exceeds_variance_threshold(
    estimate_paise: int,
    firm_paise: int,
    threshold_pct: float = 20.0,
) -> bool:
    """Return True if firm quote exceeds estimate by more than `threshold_pct`%."""
    return compute_variance_pct(estimate_paise, firm_paise) > threshold_pct
