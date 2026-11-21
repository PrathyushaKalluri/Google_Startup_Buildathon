"""Deterministic centre-brand authority engine (A2)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

AuthorityLevel = Literal["authorised_service", "installation_only", "independent", "none"]
AuthorityDecision = Literal[
    "proceed",
    "proceed_with_notice",
    "return_to_brand",
    "cannot_install",
    "cannot_repair",
]

_LEVEL_ALIASES: dict[str, AuthorityLevel] = {
    "authorised": "authorised_service",
    "authorized": "authorised_service",
    "authorised_service": "authorised_service",
    "authorized_service": "authorised_service",
    "installation_only": "installation_only",
    "install_only": "installation_only",
    "independent": "independent",
    "none": "none",
    "": "none",
}

_INSTALL_JOB_TYPES = frozenset({"installation", "uninstall_reinstall", "demo"})
_WARRANTY_ENTITLEMENTS = frozenset({"brand_warranty", "extended_warranty"})


class AuthorityResult(BaseModel):
    """Result of checking a service centre's authority for a brand and job."""

    level: AuthorityLevel
    decision: AuthorityDecision
    reason: str


def normalize_authority_level(level: Optional[str]) -> AuthorityLevel:
    """Normalize DB/API authority level strings to canonical values."""
    if level is None:
        return "none"
    key = level.strip().lower()
    if key not in _LEVEL_ALIASES:
        raise ValueError(f"Unknown authority level: {level!r}")
    return _LEVEL_ALIASES[key]


def check_authority(
    level: Optional[str],
    job_type: str,
    entitlement: Optional[str],
) -> AuthorityResult:
    """Determine whether the receiving centre may handle this job.

    Rules (Contract C0, C5.3 & AGENTS.md Section 6.2 A2):
    - `authorised_service`: may proceed for all job types and entitlements.
    - `installation_only`: may proceed for installation/uninstall_reinstall/demo;
      refuses repairs and coverage claims (`cannot_repair`).
    - `independent`: MUST return `return_to_brand` for `brand_warranty`,
      `extended_warranty`, or `coverage_claim`. May handle out-of-warranty / AMC
      repairs and installs with an independent-centre notice (`proceed_with_notice`).
    - `none`: returns `return_to_brand` if under brand/extended warranty,
      `cannot_install` for installation jobs, and `cannot_repair` otherwise.
    """
    norm_level = normalize_authority_level(level)
    norm_job = (job_type or "repair").strip().lower()
    norm_entitlement = (entitlement or "none").strip().lower()

    if norm_level == "authorised_service":
        return AuthorityResult(
            level=norm_level,
            decision="proceed",
            reason="Centre is an authorised service partner for this brand.",
        )

    if norm_level == "installation_only":
        if norm_job in _INSTALL_JOB_TYPES:
            return AuthorityResult(
                level=norm_level,
                decision="proceed",
                reason="Centre is authorised for installation jobs for this brand.",
            )
        return AuthorityResult(
            level=norm_level,
            decision="cannot_repair",
            reason=(
                "Centre holds installation-only authority for this brand and "
                f"cannot perform {norm_job} jobs."
            ),
        )

    if norm_level == "independent":
        if norm_entitlement in _WARRANTY_ENTITLEMENTS or norm_job == "coverage_claim":
            return AuthorityResult(
                level=norm_level,
                decision="return_to_brand",
                reason=(
                    "Appliance is covered under brand or extended warranty; an "
                    "independent centre cannot service warranty claims and must "
                    "return the request to the brand."
                ),
            )
        return AuthorityResult(
            level=norm_level,
            decision="proceed_with_notice",
            reason=(
                "Centre is an independent service centre for this brand; proceed "
                "after informing the household that service is non-OEM."
            ),
        )

    # norm_level == "none"
    if norm_entitlement in _WARRANTY_ENTITLEMENTS or norm_job == "coverage_claim":
        return AuthorityResult(
            level=norm_level,
            decision="return_to_brand",
            reason=(
                "Centre has no authority for this brand and the appliance is under "
                "warranty; return the request to the brand."
            ),
        )
    if norm_job in _INSTALL_JOB_TYPES:
        return AuthorityResult(
            level=norm_level,
            decision="cannot_install",
            reason="Centre has no installation authority for this brand.",
        )
    return AuthorityResult(
        level=norm_level,
        decision="cannot_repair",
        reason="Centre has no service authority for this brand.",
    )
