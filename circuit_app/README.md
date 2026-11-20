# Circuit — Round 3 simulation (runnable)

Real: **Gnani speech-to-text** (LIVE HTTPS call) and **one LLM** (Claude or Gemini) making every decision.
Played by teammates: household, agency, technician, payer (each has an inbox + buttons on one screen).
Doc-simulated: **Pine Labs** and **Delhivery Maps** — Circuit creates the request, a teammate pastes the response copied from the docs.

## 1. Install (once, ~3 min)
```bash
cd circuit_app
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # then edit .env with your keys
```

## 2. Check keys before recording
```bash
python check_setup.py                    # lists models your key can use; copy one into LLM_MODEL
python check_setup.py my_test_clip.ogg   # ALSO one real Gnani call (uses 1 credit)
```

## 3. Run
```bash
python run.py
```
Open **http://localhost:8000** (actor console). The **Open live trace** link appears after the first household event.
Put the console and trace side by side for the screen recording.

## 4. The recording flow (one take, ≤5 min)
1. **Household** chooses the real voice note file (15–30 s, Telugu/Hindi/English) → *Send voice note*. Gnani's raw request + response appear in the trace, then Circuit's question arrives in the household inbox.
2. Household answers (type or another voice note): model number from label, warranty over, landmark.
3. Circuit ranks technicians → **Agency** clicks *Assign …* → **Technician** clicks *Accept*.
4. Circuit offers slots → **Household** picks a slot, then *Grant home access*.
5. Circuit creates the **Pine Labs** request → **Payer** clicks *Approve* → **Wizard** pastes the documented response with `"status": "ACTIVE"` (a `CREATED` status does NOT pass the gate).
6. **Technician** clicks *Confirm kit in my bag*. Circuit creates the **Delhivery Maps** request → Wizard pastes the documented Distance Matrix response.
7. **Agency owner** clicks *Sign off READY*. The trace shows the S5 gate with every condition ✅/❌ and the verdict `READY_IN_ROLEPLAY`.
8. Click **Export decision log** — this is your Part 1 decision table + every partner request/response.

The demo model `DEMO-AC-MODEL-A` is the only model with compatible fixture stock and a Machine Kundli record. Any other model correctly ends at `READY_FOR_INSPECTION_VISIT_IN_ROLEPLAY`.

Buttons only appear when the step is legitimately possible (e.g. *Approve* only after Circuit asks). The model can never set approvals, assignment, kit custody or partner status itself — only those human/wizard events can.

## 5. Before recording
- Use the **new** Gnani key (revoke the one shared in chat). Keys live only in `.env`.
- Add 1–3 real AC troubleshooting excerpts to `knowledge/` (see `knowledge/README.md`) so retrieval cites a real source, not only the generic seed.
- Copy the real sample JSON responses from Pine Labs and Delhivery docs into a notes file for the wizard to paste.
- Rehearse once; click **New case** to start clean before the real take.

## Tests
`python -m pytest -q` → 11 offline tests (scripted model, fake Gnani): full path to READY, CREATED≠ACTIVE, model can't forge approvals, slots blocked before acceptance, hazard escalates, in-warranty → OEM, duplicate audio cached, >60 s rejected not clipped, missing key never fabricates, wizard rejects non-JSON.
Live WhatsApp (Meta) is **not built** — the household uses the console inbox (labelled ROLEPLAY_INBOX), which the Round 3 rules allow ("a team member feeds it in").
