# Keepwell Region & Safety Bounds (Always-On Rule)

1. **Data Residency (`asia-south1`):** All personal data is stored and processed in `asia-south1` (Mumbai). Any Gemini API or Live API call that carries household data goes through the endpoint recorded in `docs/DECISIONS_B.md`.
2. **Pseudonymous Telemetry:** Logs, traces, and BigQuery analytics hold pseudonymous IDs only. Never log raw phone numbers, full names, addresses, or OTP codes.
3. **Media Retention:** Raw media (call audio, photos, video frames) is deleted after 48 hours unless explicit household consent to keep it is recorded.
4. **Hard Safety Bounds (Non-Negotiable):**
   - Nothing involving gas, mains-voltage work, sealed-system refrigerant, or opening an unapproved panel is ever offered as a self-fix.
   - A `safety`-class case always skips both consent gates, sends the stop-use instruction immediately, rises to the top of the board with a distinct non-colour-only visual + audible/push treatment, and never offers a self-fix.
   - Self-fixes come only from the reviewed `safe_fix_catalogue` (≤ 6 steps, ≤ 12 min, reversible, no tools, manual page cited, named reviewer).
5. **Zero Invented Parts (Contract C11):** Every part shown in a visit plan, technician brief, debrief, quote, or stock request must come from `part_catalogue` and `part_compatibility`. Unmatched parts are displayed as `"needs checking"` and never appear as normal quote lines.
6. **Epistemic Honesty:** Never present a guess as a fact. Display agent uncertainty, evidence, and source citations verbatim. Never rewrite agent-emitted household copy (recording notice, Gate 1, Gate 2, safety stop).
7. **Forbidden Words:** Never use `"staff"`, `"dispatcher"`, or `"human approval"` in user-facing copy or code comments. Closure is by household OTP only.
8. **Scope & Ownership (Part B):** Five appliance categories only (`ac`, `refrigerator`, `washing_machine`, `ro_purifier`, `geyser`). Part B edits only `apps/`, `mocks/`, `infra/frontend/`, `docs/design/`, `.agents/part-b/`, `docs/NOTES_B.md`, `docs/DECISIONS_B.md`, `docs/HANDOFF_B.md`, `docs/rubric_B.md`, `apps/Makefile`, and `AGENTS.md`. Never edit `db/`, `services/`, `kb/`, `analytics/`, `evals/`, `infra/backend/`, or `contract/SHARED_CONTRACT.md`.
