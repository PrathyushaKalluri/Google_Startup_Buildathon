# GharSaathi

*Ghar ka kaam. Agent ke naam.*

A clickable prototype of an AI agent that remembers, schedules, chases and closes household maintenance for an Indian home (demo household: Sharma Home, Hyderabad).

## Run it

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # typecheck + production build
```

## The 2–3 minute demo

1. **Aaj Ka Scene**: the geyser has been stuck for 2 days, with 3 missed technician promises. The AC service is due in 4 days.
2. **See what I'm doing** opens the geyser case. Press **Run next follow-up** twice: a new promise, then a 4th miss. **Escalate to supervisor**, follow up, and confirm the offered slot from the approval card.
3. Keep following up: the technician says he's en route, reaches the gate (approve entry) and reports the fix. **Mark repair complete** asks for evidence, then saves the receipt to the geyser's history and sets the next triggers.
4. Or take the other path: **Try another provider** (Ravi quotes ₹1,350, within the ₹1,500 limit) → **Book backup**.
5. **Service Calendar** → **Run next trigger** books the AC service on its own under the rule's ₹1,200 limit, prepares the Kent AMC renewal (above the limit, so it asks), and saves the washing-machine warranty check.
6. **Ghar Ki Memory**: open any appliance. Tap a fact's source to see the document behind it. Confirm or correct the uncertain ones. **Add something to memory** walks through extraction and review.
7. The header holds approvals, the agent activity log, household rules (spend limit, escalation, home access and windows, all of which change live behaviour) and a demo reset.

## How it's built

- `src/data/seed.ts`: the demo household, generated relative to today so the story always reads as current.
- `src/logic/workflow.ts`: the state machine and deterministic follow-up scripts (primary → supervisor → visit tracks), approvals, triggers and completion.
- `src/logic/derive.ts`: every count and status shown on screen is derived from state, never hard-coded.
- `src/store.tsx`: state plus `localStorage` persistence and hash routing.

The demo runs on its own clock, which moves forward with each simulated step. All calls, WhatsApp messages and bookings are simulated and labelled as such. Phone numbers and businesses are fictional. OTPs are never read or shared by the agent, and payments go through links the resident opens.
