"""Deterministic two-gate consent state machine (A2).

Enforces Contract C0, C5.1, C11, and AGENTS.md Section 6.2 A2:
- Safety cases (`safety_flag=True` or `urgency_class='safety'`) -> both gates
  recorded as `not_asked` with `not_asked_reason='safety_flag'`.
- Non-repair jobs (`job_type != 'repair'`) -> both gates recorded as `not_asked`
  with `not_asked_reason='job_type'`.
- Gate 1 (`no` or `silence`) -> Gate 2 recorded as `not_asked` with
  `not_asked_reason='gate1_not_yes'`.
- `can_start_fix()` returns False unless Gate 1 is `yes`.
- `can_start_video()` returns False unless Gate 2 is `yes` and
  `choice == 'switch_to_video'`.
- Raises `GateViolationError` on any illegal transition.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel

GateNumber = Literal[1, 2]
GateAnswer = Literal["yes", "no", "silence", "not_asked"]
GateChoice = Literal["continue_here", "switch_to_video"]

GATE1_CANONICAL_PROMPT: str = "Are you okay to try a quick, safe fix yourself first?"
GATE2_CANONICAL_PROMPT: str = "Would you like to switch to video, or carry on here?"


class GateViolationError(ValueError):
    """Raised when an illegal consent-gate transition is attempted."""


class ConsentGateRecord(BaseModel):
    """Matches Contract C5.1 ConsentGate."""

    gate: GateNumber
    asked_at: Optional[datetime] = None
    answer: Optional[GateAnswer] = None
    choice: Optional[GateChoice] = None
    not_asked_reason: Optional[str] = None


class GateMachine:
    """State machine enforcing Keepwell's two consent gates."""

    def __init__(
        self,
        *,
        job_type: str = "repair",
        safety_flag: bool = False,
        urgency_class: str = "standard",
        silence_timeout_seconds: int = 30,
    ) -> None:
        self.job_type = (job_type or "repair").strip().lower()
        self.safety_flag = bool(safety_flag) or (urgency_class == "safety")
        self.urgency_class = urgency_class
        self.silence_timeout_seconds = silence_timeout_seconds

        self.gate1 = ConsentGateRecord(gate=1)
        self.gate2 = ConsentGateRecord(gate=2)

        if self.safety_flag:
            self.gate1.answer = "not_asked"
            self.gate1.not_asked_reason = "safety_flag"
            self.gate2.answer = "not_asked"
            self.gate2.not_asked_reason = "safety_flag"
        elif self.job_type != "repair":
            self.gate1.answer = "not_asked"
            self.gate1.not_asked_reason = "job_type"
            self.gate2.answer = "not_asked"
            self.gate2.not_asked_reason = "job_type"

    def ask_gate1(self, at: Optional[datetime] = None) -> ConsentGateRecord:
        """Mark Gate 1 as asked."""
        if self.gate1.answer == "not_asked":
            raise GateViolationError(
                f"Cannot ask gate 1: skipped due to {self.gate1.not_asked_reason}."
            )
        if self.gate1.answer is not None:
            raise GateViolationError("Gate 1 has already been answered.")
        self.gate1.asked_at = at or datetime.now(timezone.utc)
        return self.gate1

    def record_gate1(
        self,
        answer: Literal["yes", "no", "silence"],
        at: Optional[datetime] = None,
    ) -> ConsentGateRecord:
        """Record the household's answer to Gate 1."""
        if self.gate1.answer == "not_asked":
            raise GateViolationError(
                f"Cannot answer gate 1: skipped due to {self.gate1.not_asked_reason}."
            )
        if self.gate1.answer is not None:
            raise GateViolationError("Gate 1 has already been answered.")
        if answer not in ("yes", "no", "silence"):
            raise GateViolationError(f"Invalid gate 1 answer: {answer!r}")

        now = at or datetime.now(timezone.utc)
        if self.gate1.asked_at is None:
            self.gate1.asked_at = now
        self.gate1.answer = answer

        if answer in ("no", "silence"):
            self.gate2.answer = "not_asked"
            self.gate2.not_asked_reason = "gate1_not_yes"
        return self.gate1

    def ask_gate2(self, at: Optional[datetime] = None) -> ConsentGateRecord:
        """Mark Gate 2 as asked (only allowed after Gate 1 == 'yes')."""
        if self.gate1.answer != "yes":
            raise GateViolationError(
                f"Cannot ask gate 2 unless gate 1 is 'yes' (current gate 1: {self.gate1.answer!r})."
            )
        if self.gate2.answer is not None:
            raise GateViolationError("Gate 2 has already been answered.")
        self.gate2.asked_at = at or datetime.now(timezone.utc)
        return self.gate2

    def record_gate2(
        self,
        answer: Literal["yes", "no", "silence"],
        choice: Optional[GateChoice] = None,
        at: Optional[datetime] = None,
    ) -> ConsentGateRecord:
        """Record the household's answer to Gate 2."""
        if self.gate1.answer != "yes":
            raise GateViolationError(
                f"Cannot answer gate 2 unless gate 1 is 'yes' (current gate 1: {self.gate1.answer!r})."
            )
        if self.gate2.answer is not None:
            raise GateViolationError("Gate 2 has already been answered.")
        if answer not in ("yes", "no", "silence"):
            raise GateViolationError(f"Invalid gate 2 answer: {answer!r}")

        if answer == "yes":
            if choice not in ("continue_here", "switch_to_video"):
                raise GateViolationError(
                    "Gate 2 answer 'yes' requires choice in ('continue_here', 'switch_to_video')."
                )
        elif choice is not None:
            raise GateViolationError(
                f"Gate 2 choice must be None when answer is {answer!r}."
            )

        now = at or datetime.now(timezone.utc)
        if self.gate2.asked_at is None:
            self.gate2.asked_at = now
        self.gate2.answer = answer
        self.gate2.choice = choice
        return self.gate2

    def can_start_fix(self) -> bool:
        """Return True only when Gate 1 is answered 'yes'."""
        return (
            not self.safety_flag
            and self.job_type == "repair"
            and self.gate1.answer == "yes"
        )

    def can_start_video(self) -> bool:
        """Return True only when Gate 1 is 'yes' and Gate 2 is 'yes' with 'switch_to_video'."""
        return (
            self.can_start_fix()
            and self.gate2.answer == "yes"
            and self.gate2.choice == "switch_to_video"
        )

    def assert_can_start_fix(self) -> None:
        if not self.can_start_fix():
            raise GateViolationError(
                "Cannot start safe fix: gate 1 must be answered 'yes'."
            )

    def assert_can_start_video(self) -> None:
        if not self.can_start_video():
            raise GateViolationError(
                "Cannot start video: gate 2 must be answered 'yes' with choice 'switch_to_video'."
            )

    def records(self) -> list[ConsentGateRecord]:
        return [self.gate1, self.gate2]
