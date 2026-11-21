# Keepwell Five-Minute Stage Demo Script & Submission Guide (`docs/DEMO_SCRIPT.md` & `docs/SUBMISSION.md`)

## 1. Five-Minute Stage Script (C03: Hindi Washing Machine E21 at Frost & Wave)

| Time | Surface | Action / Click | What to Say & What Judges See | Fallback if Wi-Fi / Live API Drops |
|---|---|---|---|---|
| **0:00–0:45** | **Centre Console (`#/stage`, Projector Mode)** | Open Console signed in as `console.c_fw@keepwell.demo` (`Frost and Wave Service Point, Kukatpally`). Toggle **Projector Mode**. | *"Keepwell is the service centre's own brain and voice—never a consumer marketplace. Here is Frost and Wave's live Stage board."* | Local mock/API hot-switch via `--dart-define`. |
| **0:45–1:45** | **Household Dialer + Console Stage View** | Click **Start C03 Test Call** (or speak in Hindi: *"मेरी Wavecrest वॉशिंग मशीन में पानी नहीं निकल रहा और डिस्प्ले पर E21 आ रहा है"*). | Agent speaks in Frost & Wave's name, logs the Hindi recording notice first, identifies household & Wavecrest WM-70FL (`confirmed`), verifies `c_fw` is **authorised** for Wavecrest, and classifies urgency `standard`. | Click **Replay Recorded C03 Call** (`POST /v1/admin/demo/replay-call`). |
| **1:45–2:45** | **Consent Gates 1 & 2 -> `/v/<token>` Video** | Answer **Yes** to Gate 1 (*"क्या आप पहले खुद एक आसान और सुरक्षित उपाय आज़माना चाहेंगे?"*), then **Switch to Video** on Gate 2. | Both gates enforce consent in Python + PostgreSQL triggers. Household opens `/v/<token>`, shows E21 display & drain filter (`ui_hint`), tries catalogued safe fix `SF-WM-DRAINFILTER-WC` (cited to *Wavecrest Manual p.2*), and reports it still doesn't drain. | Use `text_in` scripted C03 button in DEMO_MODE. |
| **2:45–3:45** | **Re-run Diagnosis, 6-Factor Assignment & Reassign** | Watch Stage View emit `diagnosis_updated (rerun=true)`, `visit_plan_ready` (with `already_tried`), and `candidates_scored` (30/25/20/15/5/5). Click **Reassign Technician**. | Show 6-factor score bar (price is never scored), verified part `WC-PUMP-E21` from `part_catalogue`, and 10-second Undo snackbar + training override log. | Pre-seeded C03 ticket detail drawer. |
| **3:45–5:00** | **Household Quote/GPay + Field Debrief & OTP Close** | In **Household App**, approve quote & complete **Google Pay TEST** payment (show job stays open!). In **Field App** (`tech1.c_fw@keepwell.demo`), submit spoken debrief (invented part flagged `"Needs checking"`) and enter **6-digit household OTP**. | Prove the two hard invariants live: (1) payment marks settlement paid but **never** closes the job; (2) invented parts never reach a quote; (3) OTP closes the ticket and updates Home Memory & FVR-14 gauge. | Sandbox OTP code displayed in demo banner. |

---

## 2. Judges' Evaluation Criteria Map (`docs/SUBMISSION.md`)

1. **Domain & Problem Fit:** `services/agents/engines/{authority,urgency,gates,safefix,assignment,parts,pricing,payments,otp}.py` + `db/tests/test_rls.py`.
2. **Safety & Grounding:** `evals/eval_runner.py` (`100%` safety recall, `100%` gate-skip, `0` fabricated citations, `100%` Model Armor adversarial detection).
3. **Google AI & Cloud Stack:** `services/live/bridge.py` (`gemini-3.1-flash-live-preview`), `kb/embed_experience.py` (`gemini-embedding-2` + `pgvector`), `kb/ingest_file_search.py` (21 PDFs), `services/common/untrusted_guard.py` (Model Armor `asia-south1`), `services/mcp/server.py` (24 MCP tools), `docs/RUBRIC_AUDIT.md`.
4. **Experience & Material 3 Expressive:** `apps/kw_ui/`, `apps/{console,field,household,brand}/`, 76 screenshots in `docs/design/screenshots/`, Lighthouse A11y 96–100 in `docs/design/lighthouse/`.
