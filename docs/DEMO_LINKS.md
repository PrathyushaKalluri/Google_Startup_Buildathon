# Keepwell Complete Button-by-Button Walkthrough (`docs/DEMO_LINKS.md`)

This guide walks you through **all 4 Keepwell apps end-to-end**, showing **which URL to open, which button to click, and what to say**, while spending **$0.00 of your Google Cloud / Gemini credits**.

---

## 0. How This Walkthrough Spends $0.00 of Your Credits
- All 4 Firebase Hosting web apps (`https://kw-{console,field,household,brand}-0527.web.app`) are already deployed on Firebase Hosting's free CDN and include built-in deterministic stage/demo replay & local PostgreSQL mode.
- Cloud SQL (`kw-pg-verify`) is currently **`STOPPED`** (`$0` compute), and Cloud Run (`kw-api`, `kw-worker`) is set to `min-instances=0` (`$0` when idle).
- **For zero-credit exploration & rehearsal:** just open the 4 URLs below directly in Chrome (or run the local backend against your local Homebrew PostgreSQL 18 with `PYTHONPATH=. .venv312/bin/uvicorn services.api.main:app --port 8000`). Neither uses any Gemini API or Cloud SQL credits unless you explicitly pass `LIVE_GOOGLE=1`.

---

## 1. The 4 App URLs at a Glance (Open Each in a Chrome Tab)

| Tab | App Name | URL to Open in Chrome | Who Uses It |
|---|---|---|---|
| **Tab 1** | **Centre Console & Live Stage View** | `https://kw-console-0527.web.app` | Service Centre Admin (`Frost and Wave Service Point, Kukatpally`) |
| **Tab 2** | **Household Companion & Simulator** | `https://kw-household-0527.web.app` | Customer / Household (Zero sign-in: WhatsApp, Voice Call, Video Link, Home Memory, Quote & Google Pay) |
| **Tab 3** | **Field App (Technician & Parts Centre)** | `https://kw-field-0527.web.app` | Field Technician (`tech1.c_fw@keepwell.demo`) & Parts Centre Operator (`parts.demo@keepwell.demo`) |
| **Tab 4** | **Brand & Retailer Portal** | `https://kw-brand-0527.web.app` | Appliance Brand (`brand.aerovane@keepwell.demo`) & Retailer |

---

## 2. Step-by-Step Script: Exact Buttons to Click & Exact Words to Say

### ACT 1 — Service Centre Console & The C03 Stage Hero (`Tab 1`: `https://kw-console-0527.web.app`)

1. **Sign In (Screen 1):**
   - **What you see:** The Keepwell Centre Console Sign-In card with a list of 9 service centres.
   - **What to click:** Click the chip **`console.c_fw@keepwell.demo`** (*Frost and Wave Service Point, Kukatpally*) — or click **Sign In** (it is pre-selected by default).
   - **What to say:** *"Keepwell is deployed by appliance service centres and brands across India. It speaks in the name of the centre—never as a consumer marketplace. We are logging into Frost and Wave Service Point in Kukatpally, Hyderabad, an authorised service centre for Wavecrest and Frostline."*

2. **Case Board (Left Navigation Rail → `Case Board`):**
   - **What you see:** A 2-pane list-detail board of tickets strictly sorted by **`safety` → `urgent` → `standard` → `planned`**, then by `needed_by`.
   - **What to click:**
     1. Click any ticket card on the left list to open its **Case Detail** on the right.
     2. Scroll through the right pane to see: **Urgency Assessment** (with rule codes), **Consent Gates 1 & 2**, **Fix Attempts**, **Diagnosis Hypotheses** (with probabilities & manual citations), **Visit Plan** (with *"Already Tried"* and part source ladder `van -> centre -> parts_centre`), and **6-Factor Technician Candidates** (`30/25/20/15/5/5`).
     3. Click **`Reclassify Urgency`** → select `Urgent` → type reason `"Customer travelling"` → click **Confirm**. Look at the bottom of the screen: a **10-second `Undo` SnackBar** appears, and the override is logged as a training signal!
     4. Click **`Reassign Technician`** → pick another technician → click **Confirm** (also shows the 10-second `Undo` SnackBar).

3. **Live Stage View (Left Navigation Rail → `Stage View`, or `https://kw-console-0527.web.app/#/stage`):**
   - **What you see:** The auditorium-sized **Live Stage View** for Scenario **C03** (Meera Rao's Hindi call about a Wavecrest washing machine showing error `E21`).
   - **What to click:**
     1. Top-right toolbar: click **`Projector`** (or theme toggle) to switch to high-contrast Projector Mode (hides side chrome so judges in the back row can read every card).
     2. Click the primary button **`Play C03 Stage Call`** (this runs the built-in zero-credit C03 time-lapse beat-by-beat!).
   - **What to watch & say as the beats animate automatically (takes ~25 seconds):**
     - **Beat 1 (Recording Notice & Identity):** *"First, Keepwell logs the mandatory Hindi recording notice (`यह कॉल आपके सर्विस सेंटर की मदद के लिए रिकॉर्ड की जा सकती है`), identifies the household (`Meera Rao · Kukatpally`), and checks authority: Frost and Wave is Authorised for Wavecrest → Proceed."*
     - **Beat 2 (Consent Gate 1 & Gate 2 → Video Switch):** *"Before suggesting any self-fix, Keepwell enforces two hard consent gates in code and at the database: Gate 1 ('Are you okay to try a quick, safe fix yourself first?') → Yes. Gate 2 ('Would you like to switch to video, or carry on here?') → Switch to video."*
     - **Beat 3 (Guided Safe Fix Fails → Re-run Diagnosis):** *"On video, the agent guides the catalogued drain-filter clean (`SF-WM-DRAINFILTER-WC`, cited to Wavecrest Manual page 2). When Meera reports the washer still shows E21, diagnosis automatically re-runs: Drain Filter probability drops to 5%, and Drain Pump Motor (`WC-PUMP-E21`) rises to 84%."*
     - **Beat 4 (6-Factor Technician Scoring & Estimate Quote):** *"Keepwell builds the visit plan with `already_tried` so the technician never repeats the filter clean, checks `WC-PUMP-E21` against the part catalogue, scores technicians using the exact 30/25/20/15/5/5 weights (price is never scored), assigns the top technician, and issues the estimate quote."*

4. **Overview, Technicians/Calendar, and Operations (Left Navigation Rail):**
   - Click **`Overview`**: Point out the **FVR-14 (First-Visit Resolution, 14-day)** gauge, First-Time Fix rate, Self-Fix Resolution rate, and Gate Funnel. Click **`Show Table`** for the accessible tabular view.
   - Click **`Technicians & Calendar`**: Shows the centre's technicians, route ETA bars, and a keyboard-accessible **`Reschedule`** button on each slot.
   - Click **`Operations`**: Click across the 4 tabs at the top: **`Stock`**, **`Price Book`** (private to this centre under PostgreSQL RLS), **`Safe-Fix Catalogue`** (showing max 6 steps / 12 min limits and review-overdue badges), and **`Overrides`** (with **`Export CSV`**).

---

### ACT 2 — Household Companion (`Tab 2`: `https://kw-household-0527.web.app`)

 households never create accounts—they interact through WhatsApp, a phone call, or a single-purpose signed magic link. Use the **top navigation chips** in Tab 2 to switch between the 5 household surfaces:

1. **Chip 1: `WhatsApp Simulator` (`/whatsapp`):**
   - **What to click:**
     - Top bar: you can switch the receiving centre (defaults to *Frost and Wave, Kukatpally*) or language (`EN` / `हिं` / `తె`).
     - Click any quick-reply / sample complaint chip or type `"My Wavecrest washing machine shows E21 and water is not draining"` in the message box and click **Send** (or click the **Voice Note** / **Photo** attachment buttons).
   - **What to say:** *"Notice there is zero WhatsApp branding or trade dress—this is a clean Material 3 simulator sharing the exact same backend pipeline as our HMAC-verified Meta webhook."*

2. **Chip 2: `Call Dialer` (`/call`):**
   - **What to click:** Click **`Start Call`** (or **`Play Scripted C03 (Hindi)`**).
   - **What you see:** The verbatim recording notice banner at the top, live bilingual captions (`household` and `agent`), waveform controls (`Mute`, `Speaker`), and when Gate 2 is answered `"Switch to video"`, an interactive **`Open Video Link (/v/...)`** card appears right in the call!

3. **Chip 3: `Video Link` (`/v/demo-token`):**
   - **What to click:** Click the **`Video Link`** chip at the top (or click the video link card from the call).
   - **What you see:** The live camera preview (`1 fps` JPEG frame counter badge so bandwidth stays tiny on Indian mobile networks) and the 4 `ui_hint` framing overlays (**`Show model sticker`**, **`Show error display`**, **`Show drain filter`**, **`Hold steady`**) plus a **`Send Still Photo`** fallback if camera permission is denied.

4. **Chip 4: `Home Memory` (`/home/demo-token`):**
   - **What to click:** Click the **`Home Memory`** chip.
   - **What you see:** The household's registered appliances (`Wavecrest WM-70FL`, `Aerovane Split AC`), warranty status badges, explainable **Appliance Care Index**, upcoming service reminders, and the technical repair timeline.

5. **Chip 5: `Quote & OTP` (`/quotes/demo-token`):**
   - **What to click (in this exact order):**
     1. Inspect the line items: Labour, Verified Catalogue Part (`WC-PUMP-E21`), **18% GST**, and the split between **Covered (`₹0`)** and **Household Payable**. Notice any unverified part is badged **`Needs checking`** and excluded from the total!
     2. Click **`Approve Quote`**.
     3. Click **`Pay with Google Pay (TEST)`** (or **`Complete Sandbox Payment`**).
     4. **Point out the amber boundary banner that appears:** *"Payment confirmed — job remains OPEN. Only your 6-digit closure OTP closes the job after the technician finishes."*
     5. Copy or note the **6-digit Closure OTP** shown on the card (or click **`Verify OTP & Close`** to test household-side OTP confirmation).

---

### ACT 3 — Field App: Technician & Parts Centre (`Tab 3`: `https://kw-field-0527.web.app`)

The Field App routes automatically to either the **Technician Shell** or the **Parts Centre Shell** based on who signs in.

#### Part 3A: Technician Flow (`tech1.c_fw@keepwell.demo`)
1. **Sign In:** On `https://kw-field-0527.web.app`, click the persona chip **`tech1.c_fw@keepwell.demo`** (Technician 1 at Frost & Wave).
2. **Offline Outbox Toggle (Top Bar):**
   - Click the **`Offline Mode`** switch in the top app bar to simulate losing mobile signal in a basement.
   - Click **`Check In`** on the first visit card — notice the action queues into the **FIFO Offline Outbox Banner** (`1 queued action`).
   - Toggle **`Offline Mode`** back to **Online** — watch the queued check-in sync automatically with an idempotency key!
3. **Visit Detail & Privacy-Gated Address:**
   - Click the visit card to open **Visit Detail**.
   - Point out:
     - **Privacy rule:** The household's full address and phone number are released **only** because the slot is confirmed (and every read writes an immutable `access_log` row in PostgreSQL).
     - **Already Tried Banner:** Lists `SF-WM-DRAINFILTER-WC (Not worked)` so the technician never wastes time repeating the household's filter clean.
     - **Parts & Source Ladder:** Shows `WC-PUMP-E21` available on the van/centre.
4. **Spoken Close-Out Debrief (`"Needs checking"` Invariant):**
   - Scroll to **Spoken Close-Out Debrief** and click **`Record / Upload Spoken Debrief`**.
   - Look at the extracted debrief card:
     - Verified catalogue part `WC-PUMP-E21` is matched.
     - Unmatched/invented code is flagged in the **`Unresolved / Needs checking`** section and blocked from quotes (`Parts are never invented`).
   - Click **`Confirm Debrief`**.
5. **OTP Closure:**
   - Scroll to **Job Closure (OTP Only)** → enter the 6-digit sandbox OTP (displayed on screen in demo mode, e.g. `482910`) → click **`Confirm OTP & Close Visit`**. The job status changes to **`Closed`**!

#### Part 3B: Parts Centre Flow (`parts.demo@keepwell.demo`)
1. Click the **Sign Out** icon (top-right of Tab 3).
2. On the Sign-In screen, click the persona chip **`parts.demo@keepwell.demo`** (*Parts Centre Operator*).
3. **What to click:**
   - In the **`Requests`** tab, use the large one-handed (`≥52dp`) action buttons on a part reservation card: click **`Accept Request`** → **`Mark Ready`** → **`Hand Over to Technician`**.
   - Switch to the **`Stock`** bottom tab and click **`+`** / **`-`** on a part quantity stepper to update live parts-centre stock.

---

### ACT 4 — Brand & Retailer Portal (`Tab 4`: `https://kw-brand-0527.web.app`)

1. **Sign In:** On `https://kw-brand-0527.web.app`, click the persona chip **`brand.aerovane@keepwell.demo`** (or click **Sign In**).
2. **Tab 1: `Forwarded Requests` (Left/Bottom Nav):**
   - **What you see:** All brand-forwarded service requests, including **Case C18** (an in-warranty Aerovane AC repair that was mistakenly forwarded to *Cool Craft Appliance Services*, an **independent** centre).
   - **What to point out:** Keepwell's deterministic Authority Engine checked `centre_authority`, saw Cool Craft is `independent` while the claim is `brand_warranty`, and automatically returned **`202 Declined — Independent centre cannot service in-warranty Aerovane claim; returned to brand`**.
3. **Tab 2: `Intake Forms` (Brand Forward & Retailer Handover):**
   - **What to click:**
     - Toggle between **`Brand Forward Request`** and **`Retailer Installation Handover`**.
     - Click **`Submit Brand Request`** (pre-filled with a demo warranty payload) → inspect the live **`HTTP 202`** response card showing `status: received` (or `declined` if routed to an unauthorized centre).
4. **Tab 3: `Analytics` (FVR-14 & Looker Studio):**
   - **What to click:** Click **`Analytics`**.
   - **What you see:** The brand-wide **FVR-14 (First-Visit Resolution, 14-day)** gauge, Repeat-Failure Rate by appliance model, Parts-Ready-at-Visit rate, and the accessible Looker Studio / native analytics table.

---

## 3. Multilingual (`EN` / `हिं` / `తె`) & Accessibility Quick Check (Any Tab)
- In the top-right app bar of **any** of the 4 apps:
  1. Click the **Language icon (`🌐`)** and switch between **English (`EN`)**, **Hindi (`हिन्दी`)**, and **Telugu (`తెలుగు`)** — every UI chrome label updates immediately using Google Fonts (`Noto Sans Devanagari` and `Noto Sans Telugu`), while agent-emitted safety and consent text is preserved verbatim.
  2. Click the **Theme icon** to cycle **`Light` → `Dark` → `High-Contrast Light` → `High-Contrast Dark`**.
