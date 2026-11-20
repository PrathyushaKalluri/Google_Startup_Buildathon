# Circuit — Round 3 team plan: run, record, submit

Live, editable version: https://claude.ai/code/artifact/30fedb33-76d2-4c17-b8e8-e7bc400fc44a

## Deadline and who does what

Round 3 closes **Sunday 4 October, 11:59 PM IST**. Aim to submit by **9 PM** so an upload failure doesn't sink us.

This zip is the working app, plus Part 1 (draft: `Circuit_Round3_Part1_DRAFT.docx`) and Part 2 (finished: `Circuit_Round3_Part2.docx`). It runs on one laptop: Gnani and Claude/Gemini calls are real, the four human roles click and type in one browser console, and Pine Labs and Delhivery responses are pasted from their docs.

| Role | What they do | Who |
| --- | --- | --- |
| Operator | Sets up the laptop, runs the app, plays the Wizard (pastes Pine Labs and Delhivery responses), records the screen | |
| Household voice | Records one 15–30 second Telugu voice note describing the AC problem, with consent | |
| Agency, technician, payer | Click their buttons and type replies in the console during the take | |
| Writer | Fills Part 1 and Part 2 answers from the exported decision log | |
| Business lead | Decides which company builds Circuit, drafts Part 2 | |

Keep this zip private (team WhatsApp group or private Drive only). Never put it in a public GitHub repo.

## Do first (10 minutes)

- [ ] **Revoke the Gnani key `simulation_key1`.** It was pasted into a chat. In the Gnani dashboard, delete it and generate a new key. The new key goes only in the laptop's `.env` file.
- [ ] **Make the GitHub repo private.** `PrathyushaKalluri/ken-case-competition-2026` is public and holds raw interview audio and transcripts (one recording has no consent captured) plus pirated textbooks. Settings → Danger Zone → Change visibility → Private, then add teammates as collaborators.
- [ ] **Message every interviewee** that their words may be published by The Ken (age band and city only, never their name), and log their age band and city.

## Laptop setup (operator, about 15 minutes)

You need Python 3.11 or newer, the new Gnani key, and a Claude or Gemini API key.

1. Unzip this file and open a terminal in the `circuit_app` folder.
2. Install:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env             # Windows: copy .env.example .env
   ```
3. Open `.env` in a text editor. Set `LLM_PROVIDER` (`claude` or `gemini`), the matching API key, and `GNANI_STT_API_KEY`.
4. Run `python check_setup.py`. It lists the models your key can use; copy one exactly into `LLM_MODEL`, then run it again until it prints ALL GOOD.
5. Test Gnani once with any short clip: `python check_setup.py test.ogg`. You should see HTTP 200 and a transcript. This uses one Gnani credit.
6. Run the offline tests: `python -m pytest -q` should show 11 passed.
7. Start the app: `python run.py`, then open http://localhost:8000.

If any step errors, paste the exact message into the Claude chat.

## Prepare before recording

Everything here is made before Record is pressed, but nothing is fed to Circuit until the take starts.

- [ ] **Voice note.** A consenting person records 15–30 seconds in Telugu as "Meera" in Ramagundam: the AC runs but doesn't cool, it's very hot, please send someone. Save it as `.ogg`, `.m4a` or `.mp3` on the laptop.
- [ ] **Model number to say later.** When Circuit asks for the label, the household answers `DEMO-AC-MODEL-A` and says the warranty is over. It's the only model with compatible fixture stock; any other model ends at an inspection-visit verdict.
- [ ] **Real knowledge excerpts.** Add one or two short AC troubleshooting excerpts as `.md` files in `knowledge/`, each starting with `source_id:`, `url:` and `provenance: SECONDARY_SOURCE` lines (LG India or Daikin support pages work). Restart the app after adding.
- [ ] **Pine Labs response JSON.** From the Pine Labs UPI Reserve Pay docs, copy a sample mandate status response into a notes file, with `"status": "ACTIVE"`. Note the exact doc section or URL.
- [ ] **Delhivery response JSON.** From the Delhivery Maps API Reference (Distance Matrix), copy a sample response into the same notes file, with its section or URL.
- [ ] **Screen recorder.** OBS, QuickTime or the Windows Game Bar. Test that it captures the whole browser.

## Rehearse, then record one take (5 minutes max)

Rehearse once with a different test clip, then click **New case** so the real take starts clean. Gnani credits are capped at 8 calls by default (`GNANI_DEMO_MAX_STT_CALLS` in `.env`).

Put the console (http://localhost:8000) and the **live trace** (link in the console header) side by side. Then, with recording running:

1. **Household:** choose the voice note → *Send voice note*. The trace shows Gnani's request and raw response, then Circuit's question arrives.
2. **Household:** type the answer: model `DEMO-AC-MODEL-A`, warranty over, a landmark.
3. **Agency:** click *Assign* on the technician Circuit ranked first. **Technician:** click *Accept job*.
4. **Household:** pick a slot, then *Grant home access*.
5. **Payer:** click *Approve*. **Wizard:** paste the Pine Labs JSON (`"status": "ACTIVE"`) and its doc section → *Feed response*.
6. **Technician:** click *Confirm kit in my bag*. **Wizard:** paste the Delhivery JSON → *Feed response*.
7. **Agency owner:** click *Sign off READY*. The trace shows the S5 gate, every condition ticked, and `READY_IN_ROLEPLAY`.
8. Click **Export decision log** and scroll it briefly on camera. Stop recording.

Wait for each Circuit reply before the next click; the header says "Circuit is working" while it thinks. Speed up those waits in editing (the rules allow it). Nobody tells Circuit what to do next: humans only click their own role's buttons or type as their role.

Upload the video to YouTube as **Unlisted** or Google Drive with "anyone with the link can view".

## Write the answers

| Brief asks for | Where it comes from | Owner |
| --- | --- | --- |
| Recording link, system prompt, model name | YouTube/Drive link; `data/04_RUNTIME_SYSTEM_PROMPT.md`; `LLM_MODEL` in `.env` | Operator |
| Story of one person, 100 words max | Meera's run, in order, plain words, real date | Writer |
| Every decision: when, input, source, decision, rule, message, recipient, channel | Export decision log table (one row per decision) | Writer |
| What Circuit knows on day one, who gives it, how | Agency fixture (technicians, slots, prices, stock), Machine Kundli, Mistri Gyan, runtime prompt: all set up by the agency owner at onboarding | Writer |
| Each Gnani, Pine Labs, Delhivery call: endpoint, request, response | "Partner calls" section of the export | Writer |
| Up to 3 imagined capabilities: partner, endpoint, data they already hold | Our Round 2 asks: Gnani confidence score; Pine Labs capture on a real-world event; Delhivery delivery to a named person | Writer |
| Mockup of every screen or conversation | Screenshots of each role's inbox in the console | Writer |
| Each rail scored out of 10, one reason each | Round 2 failure analysis plus what broke in the run | Writer |
| Where Circuit lives, who builds it and why, who pays, first 1,000 users, 3-week retention, year-one risks | Business lead's draft | Business lead |
| Landing page with sign-up call to action | Claude can build and publish it once the company is decided | Business lead |

Stay honest: the run ends at the S5 readiness verdict (no real repair, no real payment), and live WhatsApp is not connected, so call the console a role-play inbox. Both match the Round 3 rules.

## Submit (by 9 PM IST)

- [ ] Recording link (unlisted, viewable without sign-in), 5 minutes or less
- [ ] System prompt text and the exact model name
- [ ] Part 1 answers, with the decision table from the export
- [ ] Part 2 answers and the landing page link
- [ ] AI chat logs: the ChatGPT archive and a share link to the Claude chat
- [ ] One teammate re-reads everything against the brief before submitting

| If this happens during the take | Fix |
| --- | --- |
| Header shows "Last error: … API key missing" | Key not in `.env`, or app not restarted after editing it |
| Gnani BLOCKED: 403 | Gnani credits or key permission; check the dashboard |
| Gnani BLOCKED: clip too long | Re-record under 60 seconds (aim for 30) |
| Gnani BLOCKED: internal budget reached | Raise `GNANI_DEMO_MAX_STT_CALLS` in `.env`, restart |
| Circuit stops replying | Check the header error; paste it into the Claude chat |
| Gate stays WAIT | The trace lists which condition failed; usually a missed button or `CREATED` instead of `ACTIVE` |
