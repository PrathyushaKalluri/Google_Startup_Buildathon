# Keepwell Deployed Demo Links, Logins & Click-by-Click Walkthrough (`docs/DEMO_LINKS.md`)

**GCP & Firebase Project:** `gen-lang-client-0527907563` (`asia-south1`, Mumbai)

---

## 1. Deployed Public URLs

| Surface | URL | Purpose |
|---|---|---|
| **Centre Console & Live Stage View** | `https://kw-console-0527.web.app` (Stage View: `https://kw-console-0527.web.app/#/stage`) | Case board (`safety -> urgent -> standard -> planned`), Live Stage View with Projector Mode, technicians & calendar, stock, prices, overrides, FVR-14 overview |
| **Technician & Parts Centre Field App** | `https://kw-field-0527.web.app` | Role-based shell: Technician job brief, check-in, firm quote, spoken debrief (`"Needs checking"` part flag), OTP closure; Parts Centre accept/ready/handover & stock |
| **Household Companion & Simulator** | `https://kw-household-0527.web.app` | Zero-sign-in magic links (`/home/:token`, `/quotes/:token`, `/v/:token`, `/otp/:token`), WhatsApp Simulator (`/whatsapp`), Live Call Dialer (`/call`), Google Pay TEST checkout |
| **Brand & Retailer Portal** | `https://kw-brand-0527.web.app` | Brand-forwarded requests (including C18 authority decline), Brand Forward & Retailer Handover forms (`202` response), FVR-14 analytics & Looker Studio view |
| **Backend REST API (`kw-api`)** | `https://kw-api-vbeco674uq-el.a.run.app` (`/v1`, `/openapi.json`, `/healthz`, `/readyz`, `/mcp`) | FastAPI + 24-tool MCP server + Gemini Live WebSocket bridge (`wss://kw-api-vbeco674uq-el.a.run.app/v1/live/call`) |
| **Background Worker (`kw-worker`)** | `https://kw-worker-vbeco674uq-el.a.run.app` | Outbox projection drainer, gate-silence & expiry sweeps, reminders, 48h media retention |

> **Cost Guardrail Note (`demo_up.sh` / `demo_down.sh`):** Cloud SQL (`kw-pg-verify`) is stopped after verification so idle cost is ~$0. Before starting a live demo, run `./deploy/tools/demo_up.sh` (starts Cloud SQL and warms `kw-api`). When finished, run `./deploy/tools/demo_down.sh`.

---

## 2. Demo Logins (One-Click Persona Picker or Email Sign-In)

All four web apps include a **Demo Persona Picker** on the sign-in screen (and accept Bearer token `demo:<email>` when `DEMO_MODE=true`):

| Role | Demo Email | Bound Entity | Best Surface to Use |
|---|---|---|---|
| **Centre Admin (Stage Case C03)** | `console.c_fw@keepwell.demo` | **Frost and Wave Service Point, Kukatpally (`c_fw`)** — Authorised for Wavecrest & Frostline | `https://kw-console-0527.web.app` |
| **Centre Admin (Aerovane Auth)** | `console.c_av@keepwell.demo` | Aerovane Authorised Service, Gachibowli (`c_av`) | `https://kw-console-0527.web.app` |
| **Centre Admin (Zenith Auth)** | `console.c_zn@keepwell.demo` | Zenith Care Hub, Kondapur (`c_zn`) | `https://kw-console-0527.web.app` |
| **Centre Admin (Independent)** | `console.c_cc@keepwell.demo` | Cool Craft Appliance Services, Madhapur (`c_cc`) | `https://kw-console-0527.web.app` |
| **Centre Admin (RO & Geyser)** | `console.c_aq@keepwell.demo` | AquaCare RO and Geyser Services, Manikonda (`c_aq`) | `https://kw-console-0527.web.app` |
| **Centre Admin (Install-Only)** | `console.c_ip@keepwell.demo` | InstallPro Mounting Services, Tolichowki (`c_ip`) | `https://kw-console-0527.web.app` |
| **Technician 1 (Frost & Wave)** | `tech1.c_fw@keepwell.demo` | First technician at Frost & Wave (`c_fw`) | `https://kw-field-0527.web.app` |
| **Technician 2 (Frost & Wave)** | `tech2.c_fw@keepwell.demo` | Second technician at Frost & Wave (`c_fw`) | `https://kw-field-0527.web.app` |
| **Parts Centre Operator** | `parts.demo@keepwell.demo` | Hyderabad Regional Parts Hub | `https://kw-field-0527.web.app` |
| **Brand Portal (Aerovane)** | `brand.aerovane@keepwell.demo` | Aerovane Appliances (`X-Keepwell-Key: kw-brand-aerovane`) | `https://kw-brand-0527.web.app` |
| **Platform Admin** | `platform@keepwell.demo` | Cross-centre platform admin & demo runner | `https://kw-console-0527.web.app` |

---

## 3. What to Click (Step-by-Step Walkthrough)

### A. Stage Scenario C03 (Hindi Washing Machine E21 at Frost & Wave)
1. Open **Centre Console** (`https://kw-console-0527.web.app`) → select **`console.c_fw@keepwell.demo`** (*Frost and Wave Service Point, Kukatpally*).
2. Click **Stage View** in the navigation rail (or go to `#/stage`) and toggle **Projector Mode** (top-right).
3. Click **Play C03 Stage Demo** (or open **Test Call** / `https://kw-household-0527.web.app/#/call`):
   - Watch the live event feed emit `conversation_started` and `recording_notice_logged` first.
   - Watch `household_identified`, `appliance_identified` (`Wavecrest WM-70FL`, evidence `confirmed`), `authority_checked` (`authorised -> proceed`), and `urgency_assessed` (`standard`).
   - Watch **Gate 1** (`yes`) and **Gate 2** (`switch_to_video`) unlock the video modality (`modality_changed`) and guide safe fix `SF-WM-DRAINFILTER-WC` (*Wavecrest Manual p.2*).
   - Watch the safe fix fail (`fix_result: not_worked`), triggering `diagnosis_updated (rerun=true)`, `visit_plan_ready` (with `already_tried`), `candidates_scored` (6-factor breakdown: 30/25/20/15/5/5), `technician_assigned`, and `quote_issued`.
4. Click any case card to open the **Case Detail Drawer**:
   - Click **Reclassify Urgency** or **Reassign Technician** → enter a reason → observe the **10-second Undo SnackBar** and confirm the override appears under **Operations → Overrides**.

### B. Household Quote Approval, Google Pay (`TEST`) & OTP-Only Closure Boundary
1. Open **Household Companion** (`https://kw-household-0527.web.app`).
2. Click **Quote & Payment** (or `/quotes/demo`):
   - Click **Approve Quote** → choose **Google Pay (TEST)** → complete sandbox payment.
   - Verify the banner explicitly confirms: **"Payment confirmed — job remains open until you share the closure OTP with your technician."**
3. Click **WhatsApp Simulator** (`/whatsapp`) to send a Telugu/Hindi/English message or voice note, or **Video Link** (`/v/demo`) to test the 1 fps camera preview with `ui_hint` framing overlays.

### C. Technician Spoken Debrief (`"Needs checking"`) & OTP Closure
1. Open **Field App** (`https://kw-field-0527.web.app`) → sign in as **`tech1.c_fw@keepwell.demo`**.
2. Open the active visit → confirm address & phone are released only for confirmed slots → click **Check In**.
3. Scroll to **Spoken Close-Out Debrief** → review extracted parts → notice any unverified part is badged **`"Needs checking"`** (never added to a quote) → resolve and click **Confirm Debrief**.
4. Enter the household's **6-digit OTP** → click **Confirm & Close Job** (ticket transitions to `closed`).
5. Switch persona to **`parts.demo@keepwell.demo`** to use the one-handed **Accept → Mark Ready → Handover** parts centre flow.

### D. Brand Authority Decline (C18) & FVR-14 Analytics
1. Open **Brand Portal** (`https://kw-brand-0527.web.app`) → sign in as **`brand.aerovane@keepwell.demo`**.
2. In **Forwarded Requests**, inspect **C18** (Aerovane warranty repair forwarded to independent centre Cool Craft `c_cc`) → verify status is **`declined`** with the authority reason.
3. Click **Analytics** to inspect the **FVR-14 (First-Visit Resolution, 14-day)** gauge and accessible breakdown table.
