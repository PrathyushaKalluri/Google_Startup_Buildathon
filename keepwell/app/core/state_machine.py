from enum import Enum
from typing import List, Dict, Optional
import datetime

class JobState(str, Enum):
    INTAKE_PENDING = "INTAKE_PENDING"          # Customer message received, extracting facts
    HAZARD_REVIEW = "HAZARD_REVIEW"            # Emergency safety flag triggered, escalated to person
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"  # Asking 1-2 targeted follow-up questions
    DIAGNOSIS_READY = "DIAGNOSIS_READY"        # Hypotheses cited, parts catalogue checked
    INSPECT_FIRST_RECOMMENDED = "INSPECT_FIRST_RECOMMENDED" # Unidentified model or uncertain fault
    AGENCY_QUOTE_REVIEW = "AGENCY_QUOTE_REVIEW" # Agency owner approving rate-card quote
    QUOTE_SENT = "QUOTE_SENT"                  # Sent to customer on WhatsApp / Magic Link
    QUOTE_APPROVED = "QUOTE_APPROVED"          # Customer agreed to terms and estimated cost
    TECHNICIAN_DISPATCHED = "TECHNICIAN_DISPATCHED" # Slot booked, tech assigned with kit
    REPAIR_IN_PROGRESS = "REPAIR_IN_PROGRESS"  # Tech on site
    VERIFICATION_PENDING = "VERIFICATION_PENDING" # Tech voice close-out submitted, awaiting customer sign-off
    CLOSED_RESOLVED = "CLOSED_RESOLVED"        # Customer verified, payment confirmed, saved to Home Memory
    REOPENED_REPEAT_FAULT = "REOPENED_REPEAT_FAULT" # Same issue reported within 14-day window

# Strict valid state transitions
VALID_TRANSITIONS: Dict[JobState, List[JobState]] = {
    JobState.INTAKE_PENDING: [
        JobState.HAZARD_REVIEW,
        JobState.CLARIFICATION_NEEDED,
        JobState.DIAGNOSIS_READY,
        JobState.INSPECT_FIRST_RECOMMENDED
    ],
    JobState.HAZARD_REVIEW: [
        JobState.INTAKE_PENDING,
        JobState.TECHNICIAN_DISPATCHED,
        JobState.CLOSED_RESOLVED
    ],
    JobState.CLARIFICATION_NEEDED: [
        JobState.INTAKE_PENDING,
        JobState.DIAGNOSIS_READY,
        JobState.INSPECT_FIRST_RECOMMENDED
    ],
    JobState.DIAGNOSIS_READY: [
        JobState.AGENCY_QUOTE_REVIEW,
        JobState.INSPECT_FIRST_RECOMMENDED
    ],
    JobState.INSPECT_FIRST_RECOMMENDED: [
        JobState.AGENCY_QUOTE_REVIEW,
        JobState.TECHNICIAN_DISPATCHED
    ],
    JobState.AGENCY_QUOTE_REVIEW: [
        JobState.QUOTE_SENT,
        JobState.TECHNICIAN_DISPATCHED
    ],
    JobState.QUOTE_SENT: [
        JobState.QUOTE_APPROVED,
        JobState.CLOSED_RESOLVED
    ],
    JobState.QUOTE_APPROVED: [
        JobState.TECHNICIAN_DISPATCHED
    ],
    JobState.TECHNICIAN_DISPATCHED: [
        JobState.REPAIR_IN_PROGRESS
    ],
    JobState.REPAIR_IN_PROGRESS: [
        JobState.VERIFICATION_PENDING
    ],
    JobState.VERIFICATION_PENDING: [
        JobState.CLOSED_RESOLVED,
        JobState.REOPENED_REPEAT_FAULT
    ],
    JobState.CLOSED_RESOLVED: [
        JobState.REOPENED_REPEAT_FAULT
    ],
    JobState.REOPENED_REPEAT_FAULT: [
        JobState.TECHNICIAN_DISPATCHED
    ]
}

def can_transition(current: JobState, target: JobState) -> bool:
    allowed = VALID_TRANSITIONS.get(current, [])
    return target in allowed

def validate_transition(current: JobState, target: JobState):
    if not can_transition(current, target):
        raise ValueError(f"Illegal state transition from {current.value} to {target.value}")
