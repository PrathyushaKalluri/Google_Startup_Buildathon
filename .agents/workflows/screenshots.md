---
description: Capture browser screenshots across all Keepwell surfaces, viewports, themes, and languages into docs/design/screenshots/.
---

# /screenshots — Visual Verification Capture

1. Ensure mocks are running (`/mocks`).
2. Start or build the target Flutter web surfaces (`console`, `field`, `household`, `brand`).
3. Using the Antigravity browser subagent, visit each primary route and save PNGs to `docs/design/screenshots/<surface>/`:
   - `console`: Case Board, Case Detail, Live Stage (`/stage` + Projector Mode), Calendar, Overview (FVR-14 gauge)
   - `field`: Technician Job List, Job Brief, Firm Quote, Spoken Debrief, OTP Closure; Parts Centre queue
   - `household`: WhatsApp Simulator, Call Dialer, Video Link (`/v/<token>`), Home Memory, Quote + Pay + OTP
   - `brand`: Requests table, Forward/Handover form, Analytics
4. Capture matrix per key screen:
   - Viewports: Phone (`390x844`), Tablet (`834x1194`), Desktop (`1440x900`)
   - Themes: Light & Dark
   - Languages: `en`, `hi`, `te`
5. Attach screenshots to the milestone walkthrough artifact and verify zero layout regressions.
