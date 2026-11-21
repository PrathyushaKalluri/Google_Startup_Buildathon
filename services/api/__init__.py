"""Keepwell REST API v1 package (Work-Stream A5).

Installs lightweight, idempotent runtime compatibility shims between A2 engines
and A4 orchestrator/MCP call sites without modifying files outside `services/api/`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

_SHIMS_INSTALLED = False


def install_runtime_shims() -> None:
    global _SHIMS_INSTALLED
    if _SHIMS_INSTALLED:
        return
    _SHIMS_INSTALLED = True

    # 1. OTPService: accept provider= alias and subject_id=/phone= in issue_otp
    from services.agents.engines import otp as otp_mod

    _orig_otp_init = otp_mod.OTPService.__init__
    _orig_otp_issue = otp_mod.OTPService.issue_otp

    def _compat_otp_init(self: Any, mode: str = "sandbox", provider: Optional[str] = None) -> None:
        effective = provider or mode
        _orig_otp_init(self, mode=effective)

    def _compat_otp_issue(
        self: Any,
        *,
        visit_id: Optional[str] = None,
        household_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        phone: Optional[str] = None,
        ttl_seconds: int = 600,
        max_attempts: int = 5,
        now: Optional[datetime] = None,
    ) -> Any:
        vid = visit_id or subject_id or ""
        hid = household_id or phone or "household"
        return _orig_otp_issue(
            self,
            visit_id=vid,
            household_id=hid,
            ttl_seconds=ttl_seconds,
            max_attempts=max_attempts,
            now=now,
        )

    otp_mod.OTPService.__init__ = _compat_otp_init  # type: ignore[method-assign]
    otp_mod.OTPService.issue_otp = _compat_otp_issue  # type: ignore[method-assign]

    # 2. GateMachine: accept ticket_id=, provide record_skipped(), ensure asked_at/answered_at
    from services.agents.engines import gates as gates_mod

    _orig_gm_init = gates_mod.GateMachine.__init__

    def _compat_gm_init(
        self: Any,
        *,
        job_type: str = "repair",
        safety_flag: bool = False,
        urgency_class: str = "standard",
        silence_timeout_seconds: int = 30,
        ticket_id: Optional[str] = None,
    ) -> None:
        self.ticket_id = ticket_id
        _orig_gm_init(
            self,
            job_type=job_type,
            safety_flag=safety_flag,
            urgency_class=urgency_class,
            silence_timeout_seconds=silence_timeout_seconds,
        )

    def _record_skipped(self: Any) -> tuple[Any, Any]:
        now = datetime.now(timezone.utc)
        if self.gate1.asked_at is None:
            self.gate1.asked_at = now
        if self.gate2.asked_at is None:
            self.gate2.asked_at = now
        return self.gate1, self.gate2

    gates_mod.GateMachine.__init__ = _compat_gm_init  # type: ignore[method-assign]
    if not hasattr(gates_mod.GateMachine, "record_skipped"):
        gates_mod.GateMachine.record_skipped = _record_skipped  # type: ignore[attr-defined]
    if not hasattr(gates_mod.ConsentGateRecord, "answered_at"):
        gates_mod.ConsentGateRecord.answered_at = property(lambda self: self.asked_at)  # type: ignore[attr-defined]

    # 3. Assignment: TechnicianProfile & AssignmentRequirements accept orchestrator field aliases
    from services.agents.engines import assignment as assign_mod

    _orig_tp_init = assign_mod.TechnicianProfile.__init__

    def _compat_tp_init(self: Any, **data: Any) -> None:
        if "anchor_lat" in data and "lat" not in data:
            data["lat"] = data.pop("anchor_lat")
        if "anchor_lon" in data and "lon" not in data:
            data["lon"] = data.pop("anchor_lon")
        skills = data.pop("skills", None)
        if isinstance(skills, dict) and skills and "skill_level" not in data:
            data["skill_level"] = max(int(v) for v in skills.values())
        data.pop("centre_id", None)
        data.pop("parts_in_van", None)
        _orig_tp_init(self, **data)

    _orig_ar_init = assign_mod.AssignmentRequirements.__init__

    def _compat_ar_init(self: Any, **data: Any) -> None:
        if "visit_lat" in data and "household_lat" not in data:
            data["household_lat"] = data.pop("visit_lat")
        if "visit_lon" in data and "household_lon" not in data:
            data["household_lon"] = data.pop("visit_lon")
        data.pop("category_code", None)
        _orig_ar_init(self, **data)

    assign_mod.TechnicianProfile.__init__ = _compat_tp_init  # type: ignore[method-assign]
    assign_mod.AssignmentRequirements.__init__ = _compat_ar_init  # type: ignore[method-assign]

    # 4. Pricing: PriceBookEntry default category_code & EstimateRange price_low/high aliases
    from services.agents.engines import pricing as pricing_mod

    _orig_pb_init = pricing_mod.PriceBookEntry.__init__

    def _compat_pb_init(self: Any, **data: Any) -> None:
        data.setdefault("category_code", "ac")
        _orig_pb_init(self, **data)

    pricing_mod.PriceBookEntry.__init__ = _compat_pb_init  # type: ignore[method-assign]
    if not hasattr(pricing_mod.EstimateRange, "price_low_paise"):
        pricing_mod.EstimateRange.price_low_paise = property(lambda self: self.low_paise)  # type: ignore[attr-defined]
    if not hasattr(pricing_mod.EstimateRange, "price_high_paise"):
        pricing_mod.EstimateRange.price_high_paise = property(lambda self: self.high_paise)  # type: ignore[attr-defined]


install_runtime_shims()
