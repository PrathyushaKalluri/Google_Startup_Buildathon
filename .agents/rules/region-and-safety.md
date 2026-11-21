# Region and Safety Bounds (Always-On)

- **Data residency:** All personal data is stored and processed in `asia-south1` (Mumbai). Any Gemini API call carrying household data uses the endpoint recorded in `docs/DECISIONS_A.md` (Gemini Developer API by default; `GOOGLE_GENAI_USE_VERTEXAI=true` switches to Agent Platform in Mumbai).
- **Pseudonymous telemetry:** Logs, OpenTelemetry traces, and BigQuery exports hold pseudonymous IDs only. Never log raw phone numbers, addresses, or PII.
- **Media retention:** Raw media (voice notes, photos, video frames) is deleted after 48 hours unless explicit `frame_retention` / `photos_voice` consent is recorded in `consent_ledger`.
- **Safety bounds (non-negotiable):**
  - Nothing involving gas, mains-voltage work, sealed-system refrigerant, or opening an unapproved panel is ever offered as a self-fix.
  - A `safety`-class case always skips Gate 1 and Gate 2 (`not_asked`, reason `safety_flag`), sends the stop-use instruction immediately, and books the earliest qualified technician.
  - The agent never diagnoses past its evidence and abstains when below confidence threshold (`0.60`).
  - **Parts are never invented:** every part number must come from `part_catalogue` and be verified in `part_compatibility` for the appliance model. Unmatched parts go to `unresolved`, never to a quote.
- **Forbidden terminology:** Never use "staff", "dispatcher", or "human approval" in user-facing copy or code comments. The agent performs the process; the centre can reassign or reclassify. Closure is by OTP only.
- **Appliance categories:** Strictly five categories only: `ac`, `refrigerator`, `washing_machine`, `ro_purifier`, `geyser`.
