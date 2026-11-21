---
name: adk-agent-pattern
description: Conventions for building bounded Google ADK agents in Keepwell (intake, identity, diagnostic, fix guide, planner, quote, memory, orchestrator) with deterministic engine separation.
---

# ADK Agent Pattern (`services/agents/`)

## Core Separation Principle
**Models propose; deterministic engines dispose.** Never let an LLM decide:
- Brand authority (`engines/authority.py`)
- Safety class floor or urgency rules (`engines/urgency.py`)
- Consent gate transitions (`engines/gates.py` + DB constraint)
- Safe-fix eligibility (`engines/safefix.py`)
- Part validity (`engines/parts.py` — hard catalogue + compatibility check)
- Technician scoring weights (`engines/assignment.py` — 30/25/20/15/5/5; price not scored)
- Pricing/GST/coverage split (`engines/pricing.py`) or OTP closure (`engines/otp.py`)

## Agent Structure
1. **Model selection via env vars only (Contract C1/C4):**
   - Fast classification/intake: `GEMINI_MODEL_FAST`
   - Standard reasoning/tool agents: `GEMINI_MODEL_AGENT`
   - Complex diagnosis: `GEMINI_MODEL_PRO`
2. **Structured outputs:** Every extraction and persisted decision uses a Pydantic v2 schema passed as structured output (`response_schema`).
3. **Model Armor boundary:** Every untrusted input (household text, transcript, OCR, brand/retailer payload) passes through `services/common/untrusted_guard.py` before reaching an agent, and outputs pass through it before persistence.
4. **Abstention & honesty:** The diagnostic agent must abstain (`abstained=true`) when top hypothesis confidence is below `0.60`, and must never invent citations or part numbers.
5. **Memory & Debrief:** The memory agent transcribes technician voice debriefs, extracts structured fields, validates every part through `parts.py`, and routes unmatched parts to `unresolved` for technician confirmation.
