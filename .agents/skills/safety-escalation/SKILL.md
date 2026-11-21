---
name: safety-escalation
description: Hazard detection, safety-path execution, and non-negotiable safe-fix bounds for Keepwell urgency and triage engines.
---

# Safety Path & Hazard Rules

## Non-Negotiable Invariants
1. **100% safety recall:** `services/agents/engines/urgency.py` loads `services/agents/lexicon/hazard_lexicon.yaml` (burning smell, smoke, sparks, electric shock, MCB tripping on contact, gas/LPG smell, water near mains wiring, bulging/swelling, hissing refrigerant leak, scalding pressure relief). Any match forces `urgency_class = 'safety'` and `safety_flag = true`.
2. **Immediate safety path (Contract C11):**
   - Skip **both** Gate 1 and Gate 2; record both in `consent_gate` as `answer = 'not_asked'`, `not_asked_reason = 'safety_flag'`.
   - Never offer any self-fix.
   - Emit `safety_stop_sent` and deliver the canonical stop-use instruction immediately: *"Please stop using it and switch it off at the wall. A technician will come as soon as possible."* (localized to `en`, `hi`, or `te`).
   - Route to the top of the centre board and assign the nearest qualified technician with required `safety_certs`.
3. **Never ask "how urgent is it?":** Urgency is computed deterministically by `urgency.py` from hazard signals and the three fact questions (food/water/health impact now, usable at all, duration). The centre may reclassify later via `POST /v1/tickets/{id}/reclassify-urgency` (`assessed_by = 'centre_console'`).
4. **Safe-fix ceiling:** Active catalogue entries must have `step_count <= 6`, `est_minutes <= 12`, `reversible = true`, `needs_tools = false`, a cited manual page, and a named reviewer. Gas, mains-voltage, sealed-system refrigerant, and unapproved panel removal are forbidden.
5. **Release gate:** `make eval` fails the build if safety recall < 100% or gate-skip correctness < 100%.
