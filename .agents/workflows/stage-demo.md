---
description: Run the C03 Live Stage demo end-to-end in projector mode against mocks and the Firestore time-lapse script.
---

# /stage-demo — Live Stage C03 Rehearsal

1. Start the mock stack (`/mocks`) so REST, mock WS (`C03` script), and Firestore emulator are live.
2. Launch `apps/console` and navigate to `/stage` (enable **Projector Mode** from the demo control drawer).
3. Verify the calm empty state ("nothing happening" + Test Call invitation) renders cleanly.
4. Trigger the C03 time-lapse script from `mocks/firestore/` (or click **Play C03** in the demo drawer):
   - Hindi call (`c_fw`, Frost and Wave), washer `E21` error
   - Household & appliance identified, authority checked, urgency assessed
   - Gate 1 (yes) -> Gate 2 (`switch_to_video`) -> modality badge switches to video
   - Safe fix guided (drain filter) -> outcome `not_worked`
   - Diagnosis re-run (before/after probability bars visible)
   - Six-factor candidate scoring bars -> technician chip lands on day-plan slot
   - Reassignment override + Undo snackbar -> firm quote -> OTP closure
5. Confirm every live event from Contract Section 8 renders with its distinct accessible treatment.
