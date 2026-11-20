# Keepwell: end-to-end flow, recommendation criteria and data design

Nov 20, 2026 · @Sri Charan Peri

## Summary

Keepwell now works for service centres and brands, not in front of households: a household calls or messages a centre, a brand forwards a request, or a retailer hands over an installation, and one agent answers all four. The agent asks relevant questions, guides a fix the household can safely try, and only if that fails books the centre's own technician with everything already known. The aim is a household that can fix more on its own and a centre that arrives prepared when it cannot. Eleven decisions follow. Weights and thresholds in this doc are starting hypotheses to calibrate in a pilot, not measured values.

| # | Decision | Recommendation | Revisit if |
| --- | --- | --- | --- |
| 1 | Position | Keepwell is the agent on each service centre's line and the link between brands, retailers and centres. It does not sit between a household and its choice of centre | A brand insists on running its own agent |
| 2 | Triggers | Four: household call, household message, brand-forwarded request, retailer installation handover. All four open the same case card | A trigger carries too little data to open a case |
| 3 | Order of steps | Identify, safety and entitlement check, clarify, diagnose, guided self-fix, visit plan, technician and slot, quote, visit, OTP closure, memory | Households skip self-fix and ask for a visit at once |
| 4 | Self-fix | Offer only steps from a reviewed safe-fix catalogue; record what the household tried on the case card; a failed fix goes straight to the visit plan | A bad-advice incident, or a brand objects |
| 5 | Centre choice | None. The centre is the one contacted, or the one the brand routes to. A job the centre is not authorised for is referred to the brand's route, not ranked | A brand asks Keepwell to choose the centre |
| 6 | Technician assignment | The agent books the centre's own technician by skill, parts and route, and tells the household. The centre can reassign from its console | Centres reject agent booking |
| 7 | Parts, quote, batching | Unchanged logic inside the centre: parts anchored to the technician's route, estimate then firm quote then approval, batching in the centre's calendar | Waiting for a batch hurts satisfaction |
| 8 | Identity across centres | One Keepwell id per physical appliance, found by brand plus serial number. Each centre's own numbers are kept as aliases. Prices and notes stay per centre | Serial numbers are rarely readable in the field |
| 9 | Data | One shared Postgres with centre id on every row and row-level security; Firestore for live state; BigQuery for analytics; consent ledger from day 1 | Centres demand separate instances |
| 10 | Stage demo | A Gemini Live call, with the centre console, technician and parts screens updating from the agent's tool calls | Live API is unreliable on the venue network, then play a recorded run |
| 11 | Launch wedge | One appliance category with recurring service, one or two centres | Interviews point to another category |

Basis for row 3: field-service research attributes the leading causes of failed first visits to missing or wrong parts, missing skills and too little time allotted, all decided before dispatch ([Kognitos, citing Aberdeen](https://www.kognitos.com/blog/field-service-management/)).

## Revised end-to-end flow

The flow now starts when someone contacts a centre, not when a household opens a complaint with Keepwell. The agent diagnoses first, guides a safe fix, and only then plans the visit, so every booking carries what was learned and what was already tried.

&#91;embedded content: end-to-end flow · 12 steps, 6 human decisions\]

Read each row in the direction of the arrows, snaking down. Step 4 asks two questions: whether the household will try a safe fix and, only if it will, whether to switch to a video session. A no to the first skips steps 6 and 7. If the fix in step 6 fails, the agent adds what the household tried to the case card and runs diagnosis and the visit plan again with that evidence. Safety-flagged cases skip step 6 and batching: the agent gives a stop-use message and books the earliest qualified technician. Urgent cases book the earliest slot first and still offer the safe fix while the household waits; a fix that works cancels the visit. A brand or retailer request enters at step 1 with the details it already holds, and the agent asks the household only for what is missing.

| Before this change | Now | Why |
| --- | --- | --- |
| Household opens a complaint with Keepwell | Household contacts its own service centre; Keepwell's agent answers on the centre's line | Households already know their centre; Keepwell serves the centre and the brand |
| Household sees three centres and picks one | No centre choice; the centre contacted handles the case | Removes a step households did not ask for and a routing question brands own |
| Three slot cards, one per centre | One proposed window from the centre's own calendar, with at most two alternatives | One decision for the household instead of a comparison |
| Dispatcher confirms the technician | The agent books the centre's technician; the centre can reassign from its console | Fewer hand-offs; each reassignment is logged as a training signal |
| Diagnosis, then visit plan | Questions, diagnosis, guided self-fix, then the visit plan with what was tried | Some faults the household can fix safely; the rest arrive better described |
| Quote, then work | Estimate, firm quote, approval, price lock | Removes surprise bills (unchanged) |
| Household confirms closure | The household gives an OTP; no tap or signature | Closure by OTP only |
| Memory per household | Memory per appliance, shared across centres by brand and serial | The same appliance can reach any centre with its history |
| No intake check | Safety and coverage check before diagnosis | Stops unsafe use and routes warranty jobs correctly (unchanged) |

## How a case starts

Four triggers open the same case card, so the agent needs one intake design, not four. What differs is how much is already known and who the agent talks to.

| Trigger | Who contacts whom | What arrives | What the agent still asks | Notes |
| --- | --- | --- | --- | --- |
| Household call | Household rings the centre's number | Caller number, a spoken description in Hindi, Telugu or English, video, if the household agrees to switch to a video session | Appliance, symptom, what was tried | Live voice agent; calls need a recording notice and consent |
| Household message | Household messages the centre's WhatsApp number | Text, voice note, photos, location pin | Only the gaps, one question at a time | One WhatsApp Business number per centre |
| Brand-forwarded request | A brand sends an installation or warranty job to the centre it routes to | Brand request id, customer details, model, serial if known, request type | Access, preferred time, symptom detail | The brand decides the centre; I have not verified that any brand offers such an integration, so treat it as a partnership to test |
| Retailer handover | A retailer sends invoice and delivery details after a sale | Invoice, model, serial, address, purchase date | Installation access (floor, lift, power point) and preferred time | Installation is the first entry into appliance memory |

Keepwell does not choose the centre in any trigger. If the centre is not authorised for the brand and the job is under warranty, the agent says so, gives the brand's own contact route and records the referral.

## Scope beyond repairs

Repairs alone are too narrow: one ticket model with six job types lets Keepwell serve every stage of an appliance's life, and installation is the cheapest way to put verified data into household memory.

| Job type | Trigger | Who performs | Entitlement check | Written to memory | Difference from a repair |
| --- | --- | --- | --- | --- | --- |
| Installation and demo | Retailer handover, brand request, or the household's call after a purchase | The centre's brand-authorised installer | Brand install policy, free or paid | Model, serial, invoice, install date, warranty start, photos | No diagnosis; checklist, demo and invoice capture |
| Preventive service | Due date, season or AMC visit; the centre's reminder or the household's call | A qualified technician at the centre | AMC or plan coverage | Service date, parts checked, health reset | Fixed scope and fixed price; no diagnosis |
| Repair | Call or message to the centre | The centre's technician | Warranty, AMC or paid | Fault, root cause, part, outcome, what the household tried | Full flow, with a guided self-fix first |
| Warranty or AMC claim | Call, message or brand request while covered | Brand-authorised centre only | Purchase date and plan terms verified | Claim id, coverage used | Document check; payer split to brand or plan provider |
| Uninstall and reinstall | House move, renovation | Qualified installer | None | Location change | Two visits with a date gap |
| Inspection and repair-or-replace advice | Household doubts a quote or the appliance is old | Independent technician | None | Condition report | No parts; a recommendation, not a repair |

Brands set the rules for who may touch an appliance, so the centre's agent should work within them rather than around them. [Electrolux](https://www.electrolux.in/support/general-warranty-terms-and-conditions) states warranty repairs are provided only by its authorised service centres, and [Bosch](https://www.bosch-home.in/service/installation-service) says its installation needs specially trained teams. Two cases follow for who starts a request:

- Brand or retailer starts it: the brand pushes installation and warranty requests to the centre it already routes to, and a retailer hands over invoice and customer details after a sale. The agent receives them on the centre's line and collects what is missing from the household.
- Household starts it: the household calls or messages the centre, for any brand the centre services. Warranty jobs the centre is not authorised for are referred to the brand's own route; paid jobs proceed.

Installation is also the best onboarding moment. [Samsung](https://www.mysmartprice.com/gear/appliances/appliances-news/samsung-brings-4-hour-installation-for-refrigerators-acs-washing-machines/) offers a 4-hour installation and demo, and the coverage notes the visit can onboard buyers into its SmartThings ecosystem. Keepwell can do the same with a neutral record: the installer photographs the model sticker and invoice, and Gemini fills the appliance record, and the serial number it reads becomes the key that links the appliance across centres.

Existing offers sell visits and plans, not a household record. [Urban Company](https://urbancompany.com/ahmedabad-tv-repair-behrampura) lists a TV check-up from ₹249 with the visit fee adjusted into the final quote; [NoBroker](https://www.nobroker.in/appliance-services-in-delhi) lists washing machine installation at ₹359 and a 180-day service warranty; [Croma](https://www.croma.com/ew-knowMore) and [Vijay Sales](https://www.vijaysales.com/vswarranty) sell extended warranty with pick-up and drop; [V-Guard](https://www.vguard.in/waterpurifier/preemptive-services) sells preventive service and AMC for water purifiers. None of these pages describes a per-household appliance history that drives reminders and routing; confirm that in competitor interviews.

## Clarify, guide and self-fix

The agent's first job is to help the household fix what it can fix safely, and to ask only questions whose answers change what happens next. A visit is booked when that fails, and the case card then shows what was already tried, so the technician does not repeat it.

### Two questions before any self-fix

Every repair complaint gets the same two questions, in this order, after the safety screen and the cover check, whichever channel it came from. Silence or an unclear answer counts as no. Other job types (installation, AMC, advice) do not get them, and a safety-flagged case gets neither: the agent gives the stop-use message and books.

| Question | The agent asks | If yes | If no |
| --- | --- | --- | --- |
| 1. Self-fix | "Before we book anyone, are you okay to try a quick, safe fix yourself?" | Ask question 2 | Skip the self-fix. The agent still asks its clarifying questions in the same channel, then diagnoses and plans the visit. It does not ask again in this case |
| 2. Video | Only after a yes to question 1: "Would you like to switch to a video session so I can see it, or carry on here?" | Send the link and carry on in video | Carry on in the same channel; photos are still welcome |

### Switching to video

| Where the case started | How the switch works |
| --- | --- |
| Phone call | A phone line carries no video, so the agent sends a link by WhatsApp or SMS to the same number. The household opens it in the phone's browser and the same conversation carries on with camera and voice |
| WhatsApp or another message | The agent replies in the thread with the link |
| Brand or retailer request | The agent first reaches the household on the number in the request, then asks the same two questions |
| Stage demo | The presenter's phone or laptop joins the session directly |

The link-in-browser route is the proposed design and has not been tested. The video session resumes the conversation so far, so nothing already answered is asked again.

### What the agent does on video

- **Ask and observe first.** The agent asks the household to show things and gives no instructions. It asks to see the display and any code, the model sticker, the indicator lights, and any leak or damage on the outside, and it listens to the sound.
- **Guide a fix second.** Only if a catalogued entry applies, the agent walks through it one step at a time and checks the success condition on camera.
- **What it sees becomes evidence.** An error code read, a light pattern, visible water or frost, the serial number: each is written to the case card with a confidence. Frames are kept only with the household's consent, and their retention is set separately.
- **The camera stays on the appliance.** The agent asks the household not to show people or the rest of the home. The household can stop at any time and the agent carries on by voice.
- **A safety sign ends the self-fix at once.** Smoke, sparks, water at a socket or a swollen battery on camera gives a stop-use message.
- **Recorded for each case:** the answer to each question with its time and channel, the modality used, the video session reference, any frames kept, and the observations drawn from them.
- **Limits.** Without compression an audio-plus-video session ends at 2 minutes, so compression and session resumption stay on; video input quality is unverified and must be rehearsed.

### Principles

- One question at a time on a call; at most three short ones in a message.
- Every question must change a decision: diagnosis, safety, the self-fix, the parts or the skill. If it would not, the agent does not ask.
- Never ask what is already known from the appliance record, the brand's request or an earlier ticket.
- Ask for a photo, or for the video switch once the household has agreed to a self-fix, when it replaces several questions: the error display, the model sticker, the leak, the drain filter.
- The agent may choose and explain a step only from the safe-fix catalogue; it may not invent one.
- Safety rules run in code before any step is offered. A safety flag ends the self-fix and gives a stop-use message.
- Limit self-fix to two attempts or about ten minutes (starting values), then book the visit.

### Questions that earn their place

| Question | Why it matters | What it changes |
| --- | --- | --- |
| What sound does it make, and when? | Separates fan, compressor, drain pump and bearing faults | Ranked causes, required skill |
| Is there a code or a light on the display? Can you show it? | Error codes are brand-specific and often decisive | Diagnosis, predicted parts |
| When did it start, and did anything happen just before: a power cut, cleaning, a move, a new installation? | Sudden or gradual; installation-related faults may be covered | Cause, entitlement |
| What have you already tried? | Avoids repeating steps and shows what is ruled out | Self-fix choice, case card |
| Any burning smell, sparks, shocks or water near a socket? | Safety | Stop-use rule |
| Does it work partly: cools weakly, spins but does not drain? | Narrows the fault class | Hypotheses |
| Can you photograph the model sticker? | The serial number identifies the appliance and its parts | Appliance record, compatibility |

### Safe-fix catalogue (starting examples)

These are examples for a brand or senior technician to review; none is validated. An entry is allowed only if every one of these holds:

- **Reversible.** Undoing the step puts the appliance back where it was.
- **The worst case is no change.** Done wrongly, nothing is damaged, lost or made unsafe, and nothing erases data or settings.
- **No tools and nothing opened** except a cover the manual tells the household to open, such as a filter cover or a battery lid. No wiring, gas, ladder or opened casing.
- **Simple.** One sentence per step, about two minutes a step (starting value), six steps at most.
- **Supported** by the maker's manual, support page or a bulletin for that model, with a named reviewer.
- **Checkable.** It has a success check the household or the camera can see, and a stop condition.

Excluded for now: factory reset, firmware updates, battery removal, anything that needs a part, and anything involving mains wiring. Phones and televisions appear below because they came up as an example; whether they belong in the first category is an open question.

| Appliance | Symptom | Household step | Success check | Stop if |
| --- | --- | --- | --- | --- |
| Air conditioner | Weak cooling | Switch off, clean the washable filter, dry it, refit | Stronger airflow within 15 minutes | An error code shows after restart |
| Air conditioner | Water dripping indoors | Look at the drain hose from the floor: no kink, and the end lower than the unit | Dripping stops after 30 minutes | The hose cannot be seen without a ladder |
| Washing machine | Will not drain | Switch off at the plug, open the drain filter cover, drain into a tray, remove lint and coins, refit | Drain cycle completes | Water leaks from the cover, or the filter will not turn |
| Refrigerator | Frost or warm interior | Check the door seal, clear the vents, check the thermostat setting | Temperature recovers over the next hours | The compressor does not start, or food is at risk |
| Water purifier | Low flow | Check the inlet tap and power adaptor, then flush as the manual says | Flow returns | Water leaks at a cartridge |
| Water heater | No hot water | Check the switch and the thermostat setting | Heating light on within ten minutes | Any shock, tripping or burning smell |
| Phone | Frozen or unresponsive | Forced restart using the button combination the maker's support page gives for that exact model (on many phones, volume down plus power held for about 15 seconds) | The logo appears and the phone restarts | The phone is hot or swollen, or the restart does not complete |
| Television or set-top box | Frozen or no picture | Switch off at the plug, wait a minute, switch on; check the power and HDMI cable ends are seated | Picture returns | Burning smell, or a hot plug or socket |
| Any | Does not switch on | Try another appliance in the socket, check the plug and MCB | Powers on | The MCB trips again, or there is a burning smell |

Each catalogue entry stores: appliance category, symptom or error code, steps (six at most), success check, stop conditions, source and page, reviewer and review date. Only entries that meet the threshold above are allowed in the first version. A button combination differs by maker and model, so the catalogue stores it per model with its source.

### What the agent records and what happens when the fix fails

The case card has a "what was tried" section: the fix id, the steps the household says it did, the outcome (fixed, no change, got worse, could not do), the time, and any photo. Attempts made before the household contacted the centre are recorded the same way, from what the household says.

When the fix fails, the agent does not restart the conversation. It adds the failed attempt to the evidence, rules out the hypotheses that attempt would have cured, and re-runs diagnosis and the visit plan. The technician and the parts decision see the same record.

### How to know it works

Track the share of cases closed without a visit, visits avoided, cases closed by self-fix that reopen within seven days (false reassurance), any harm incident (target zero), the share of households who say yes to the self-fix and video questions, questions asked per case, time to resolution, and the share of visit plans that arrive with a tried list. A rising self-resolution rate with rising reopened cases means the fixes are too optimistic.

## Urgency: how a case is classed

The agent sets the class from facts. It never asks the household how urgent the problem is, because most people say very and the agent cannot check. Rules in code decide, the household answers up to three fact questions, and a household's answer can raise a class but never lower a safety one.

| Class | Set by | Triggers (examples) | What happens |
| --- | --- | --- | --- |
| Safety | Safety rules in code, at step 2 | Burning smell, sparks, shock, water at a socket, smoke, a swollen battery | Stop-use message at once, no self-fix, no batching, earliest qualified technician |
| Urgent | Rules by category, symptom and season, plus the household's answers | Water spreading, a warm fridge with food inside, no cooling in peak season, someone at home who depends on it | Booked for the earliest window and never batched; a share of each day's capacity is held back for these |
| Standard | Default | Works partly, nothing at risk | May wait for a batching window, but never past the household's needed-by date |
| Planned | Job type | Preventive service, installation, AMC | Scheduled, and batches freely |

### Questions that feed the rules

| The agent asks | What it sets |
| --- | --- |
| Is water spreading, or is food or medicine at risk? | Urgent, from the consequence |
| Does anyone at home depend on it right now? | Urgent, from the person affected |
| Do you need it by a particular day? | The needed-by date, stored apart from the class; it limits how long a standard job can wait |

### Rules around the class

- **Re-checked whenever something new arrives.** The camera shows water spreading, a self-fix "got worse", or a waiting job nears its time target: any of these moves the case up automatically. Every change is stored with its time and reason.
- **Safety cases skip the self-fix; urgent cases do not.** An urgent case books the earliest slot first and still offers the safe fix while the household waits. If the fix works, the visit is cancelled.
- **Protective steps are not self-fixes.** Closing an inlet tap or moving medicine to a cool place is a safety message from the reviewed catalogue, given whatever the household answered to the self-fix question.
- **The centre can reclassify** a case from its console with a reason. It is logged like a reassignment and becomes training data.
- **Starting values to test, none sourced:** the 3-day batching window, the share of daily capacity held for urgent jobs, and how long food can be left before it counts as at risk.

## Technician assignment inside the centre

The trigger already fixes the centre, so the question is which of its technicians takes the case, in which window, with which parts. The agent scores the centre's eligible technicians and books the best one; the centre can reassign from its console, and each reassignment is logged.

```latex
s(t) = \sum_i w_i \, s_i(t), \qquad t \in T_c^{\text{eligible}}
```

Stage 1 removes anyone who cannot do the job; stage 2 scores who is left; stage 3 books the best technician and tells the household. Standard dispatch tools already combine availability, skills, proximity and capacity ([Salesforce](https://salesforce.com/blog/what-is-dispatch-management)); the change here is adding parts readiness and fix confidence, since dispatching on availability alone sends technicians who are free but not qualified ([AEX](https://aexinc.com/blog/how-to-increase-first-time-fix-rates)).

### Stage 1: hard filters

| Filter | Rule | Data needed |
| --- | --- | --- |
| Centre authority | Warranty and AMC jobs proceed only if this centre is brand-authorised; otherwise the agent refers the household to the brand's route (checked at step 3) | Centre brand authorisations, appliance warranty |
| Skill | Technician holds the brand, category and fault-class skill at or above the level in the visit plan | Technician skill matrix |
| Travel | Technician can reach the household inside the window from their route anchor within a maximum travel time | Routes ETA |
| Availability | Window fits open capacity | Technician calendar, current route |
| Safety | Verified identity; gas or high-voltage certification when the visit plan flags it | Technician verification |

### Stage 2: scored criteria (starting weights, sum 100)

| Criterion | What it measures | Weight | Cold-start rule |
| --- | --- | --- | --- |
| Fix confidence | Predicted chance of a first-time fix for this brand, category and fault class: technician history blended with centre history | 30 | Use the category average until 10 similar jobs exist |
| Parts readiness | Share of predicted parts in van or centre stock, or deliverable before the window; stale stock counts less | 25 | Treat unconfirmed stock as 50% until a call or scan confirms it |
| Time to visit | Earliest feasible window, weighted up for urgent jobs | 20 | None needed |
| Route cost | Extra travel minutes the job adds to the technician's day; lower is better, which rewards batching | 15 | None needed |
| Reliability | On-time arrival, repeat visit within 30 days, quote variance | 5 | Neutral score for the first 5 jobs |
| Household fit | Language, same technician as a past good visit | 5 | Neutral score |

Price is not scored: the centre's rate card sets it, so it cannot rank technicians. Guardrails: reserve a share of low-risk jobs (installation, preventive service) for new technicians so they can build history; cap any one technician's daily load; never rank on distance alone.

### Stage 3: what the household is told

- One proposed window from the centre's calendar, marked Recommended, with at most two alternatives. A tap, a reply or a spoken yes books it; on a call the agent offers it aloud.
- The confirmation names the centre, the technician (name and photo, as a trust signal), the window, the estimate range and, when the data exists, one factual reason such as "fixed 18 of 20 similar cooling faults".
- It also says what to keep ready: access, a power point, clear space around the appliance, and what the technician may need to open.
- WhatsApp reply buttons are limited to three per message (general knowledge; verify), which fits one recommended window and two alternatives.

### When the centre cannot meet the window

If no eligible technician can meet the target window, the agent says so and offers the earliest one; it does not send the case to another centre. For a warranty case the brand's own route applies. The centre's console lists every case the agent could not place and lets the centre reassign, extend hours or decline. Each reassignment and decline is stored with its reason and becomes training data for the scoring.

## Parts centre recommendation and quotation

Anchor the parts decision to where the technician's visit starts, not to the household, and decide it together with the technician assignment, because parts readiness is a scored input there. The parts travel to the technician, so the household address matters only for parts the household can fit alone.

### The visit plan: output of diagnosis

The diagnosis step should end in one structured visit plan, because assignment, parts and quoting all read from it.

| Field | Example content | Used by |
| --- | --- | --- |
| Ranked hypotheses | Fault causes with probabilities and the manual or past-case evidence behind each | Technician copilot, quote estimate |
| Already tried | Fixes the household tried, the steps, the outcome and any photo | Rules out hypotheses; stops the technician repeating steps |
| Required skills | Brand, category, fault class, minimum level | Stage 1 skill filter |
| Predicted parts | Part numbers with probability of being needed | Parts ladder, readiness score |
| Estimated duration | Minutes, with a range | Window fit, batching |
| Tools and access | Special tools, floor, lift, ladder or gas kit | Technician filter, safety |
| Safety flag | Gas, shock, water near mains | Rules, not the model, decide escalation |
| Confidence | Low confidence makes the agent ask more or book a diagnostic visit first; it never books a repair on a guess | Visit type, quote range |

### Where each part comes from

For each eligible technician, take the first source on this ladder that is ready before the slot starts minus a buffer.

| Order | Source | Ready-by is measured from | Watch |
| --- | --- | --- | --- |
| 1 | Technician's van stock | Now | Van stock must be scanned in and out to stay accurate |
| 2 | Own centre stock | Technician's shift start or previous stop to centre | Counts are often stale |
| 3 | Partner parts centre | Pickup time from the technician's route anchor (Routes ETA) | Reserve before the visit is confirmed; confirm by call or scan |
| 4 | Courier to the centre or household | Courier promise | Only for parts the household can fit, or when a delay is acceptable |

Rank parts centres in two steps. Hard filters: the exact part number and a revision compatible with the model is in stock, and for warranty jobs the part is genuine. Then score:

| Criterion | Weight | Note |
| --- | --- | --- |
| Ready-by against slot | 35 | Includes the technician's travel to the centre |
| Reliability | 25 | Share of reservations honoured, stock accuracy |
| Price | 20 | Net price against catalogue MRP |
| Part warranty and returns | 20 | Aftermarket parts are labelled on the quote |

If no source delivers before the earliest slot at an acceptable cost, tell the household the honest options: a diagnosis visit now with the fee adjusted into the repair, a later slot after the part arrives, or pick-up and drop for small appliances, a service [Vijay Sales](https://www.vijaysales.com/vswarranty) and [Croma](https://www.croma.com/ew-knowMore) already offer.

### Cost quotation and split

Quote in three steps: an estimate range at diagnosis, a firm quote after the technician confirms on site, and household approval in writing (a reply, or a spoken yes on a call followed by a confirmation message) before any part is fitted. The final bill cannot exceed the approved quote without a new approval. This answers a reported pain point: consumer-rights guides describe quotes that rise sharply once the appliance is opened ([guide](https://righttoinformation.wiki/_export/xhtml/washing-machine-fridge-repair-damage-india)).

| Quote line | Basis | Who may pay |
| --- | --- | --- |
| Visit or inspection fee | Flat by category; adjusted into the repair if the household proceeds, as [Urban Company](https://urbancompany.com/ahmedabad-tv-repair-behrampura) does | Household, or waived under plan |
| Labour | Rate card by job type and complexity band | Brand warranty, plan provider or household |
| Parts | Catalogue price, part number, genuine or compatible | Brand warranty, plan provider or household |
| Travel | Waived or reduced when the job is batched on an existing route | Keepwell or household |
| Taxes and discounts | As applicable | Household |

The split column is the point of the table: each line is assigned to the brand's warranty, an extended-warranty or AMC provider, or the household. Quote variance (final against estimate) is stored per technician and feeds the Reliability score. The job closes only when the household gives an OTP.

## Job batching and visit scheduling

Yes, batch jobs by area, but do it at the moment slots are offered, not after booking, and never for urgent jobs. Batching works in two places: the slots the household sees are shaped to cluster work, and the technician's day is re-sequenced as a route.

| Batch type | How it works | Why it helps | Guard |
| --- | --- | --- | --- |
| Same household | Memory shows other appliances due soon, so offer one combined visit | One trip, one fee, one access arrangement | Only appliances the same technician is skilled for |
| Same area | Offer the slot where a skilled technician is already heading; mark it "technician already nearby" | Lower route cost, cheaper visit fee | Parts must be ready before the job joins the route |
| Apartment community | Pool requests from one gated community into a service day | Dense, predictable travel | Needs a community contact and consent per household |
| Day route | Re-sequence confirmed stops by time window and travel time | Fewer idle minutes | Buffer for overruns |

### Rules that keep batching safe

- **Urgency classes.** Safety and urgent cases, classed as set out in the urgency section, are booked at once and never batched. Standard jobs may wait up to a set batching window; start with 3 days as a hypothesis. Planned jobs (preventive service, installation) batch freely.
- **Batch key.** Same area cell, overlapping time window, compatible skills, parts ready.
- **Overrun buffer.** Plan each stop at the upper end of the duration range from the visit plan, so one long job does not break the day.
- **Share the saving.** Pass part of the route saving to the household as a waived visit fee; it is the reason to accept a batched slot.

### Tools

| Option | Fit | Notes |
| --- | --- | --- |
| Google OR-Tools on Cloud Run, with the Routes distance matrix | Prototype and early pilot | Open-source solver (general knowledge); full control over skill and parts-ready constraints; you maintain it |
| [Route Optimization API](https://developers.google.com/maps/documentation/route-optimization/usage-and-billing) | Production | Billed per shipment; one vehicle bills the Pro SKU, two or more the Enterprise Fleet Routing SKU; failed, validate-only and infeasible requests are not billed; 60 optimise requests a minute |
| Fleet Engine | Live tracking in production | The optimisation API returns planned routes, not live positions ([Google](https://developers.google.com/maps/documentation/route-optimization/quick-reference)) |

The Route Optimization API is not in your product list. Its price lists are linked from the billing page but I could not read the India rates there, so check them before budgeting.

### How to know batching works

Track jobs per technician-day, travel minutes per job, first-time fix rate, share of jobs batched, and the change in household wait time and satisfaction for batched against unbatched slots. If waits rise while travel falls, shorten the batching window.

## Appliance memory, care index and reminders

The memory belongs to the appliance, not to a centre: any centre that serves it, with the household's consent, reads the same technical history. Treat the health score as an explainable care index built from facts Keepwell can verify, and send reminders only from a centre the household has dealt with, with recorded consent, in a way that keeps WhatsApp costs low. A score that only drops when servicing is skipped is too thin to trust, and it cannot be checked against what actually breaks.

### Care index (0 to 100)

Show it as an estimate with its reasons, for example "62: last service 14 months ago, recommended every 12". Starting bands, to be tuned: 75 and above good, 50 to 74 watch, below 50 due.

| Factor | Signal | Source | Note |
| --- | --- | --- | --- |
| Service recency | Days since last service against the recommended interval for the category | Job cards, knowledge base | Strongest and most verifiable factor |
| Age | Years since purchase or install against typical life for the category | Appliance register, knowledge base | Needs the purchase date from the invoice or installer |
| Breakdown history | Repairs in the last 12 months; repeat faults on the same component | Event timeline | Repeat fault should trigger a repair-or-replace review |
| Usage load | Hours a day, family size, season | Household answers at onboarding | Self-reported; label as such |
| Environment | Hard water, coastal humidity, dust | Pincode lookup | Optional; validate before using |
| Open advice | A technician's earlier recommendation not yet done, a known issue for the model | Job cards, knowledge base | Shown as an action, not a penalty |

Warranty or plan status is a separate flag, not part of the index. Test the index in the pilot: it is useful only if low scores predict breakdowns in the following months. Train that check in BigQuery ML once there are enough closed jobs.

### Reminder types and household controls

| Reminder | Trigger | Needs consent for |
| --- | --- | --- |
| Preventive service due | Interval reached, adjusted for season | Service reminders |
| Seasonal | Before summer for air conditioners, before monsoon for washing machines | Service reminders |
| Warranty or plan ending | A set number of days before the end date | Warranty alerts |
| Consumable change | Filter or cartridge interval | Service reminders |
| After-repair check | A few days after job closure | Follow-up |
| Rating request | After closure | Follow-up |

Household settings: channel, language, quiet hours, a cap on non-urgent messages per month, per-appliance opt-out, and snooze. Start the cap at two a month as a hypothesis. Reminders come from the centre that last served the appliance; if the household moves to another centre, that centre asks for consent before sending any.

### WhatsApp cost and rules

Templates are the only message type that can be sent outside the 24-hour customer service window ([Meta](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing.md)), so every proactive reminder is a template. Meta prices by template category, and the category decides cost. Press reports put India's marketing rate at ₹0.8631 a message against ₹0.115 for authentication, a figure other reports also give for utility ([NewsBytes](https://www.newsbytesapp.com/news/science/whatsapp-business-messages-get-costlier-in-india-from-today/story)), about 7.5 times more.

- **Write reminders as utility messages:** tied to the household's own appliance and plan, with no offer in the text. Put any offer inside an open conversation instead. Meta assigns the category, so test approval early.
- **Unresolved conflict on service messages:** NewsBytes, citing Meta, reports that from 1 October 2026 each number gets 1,000 free service messages a month, then ₹0.115 each, and utility messages are billable even inside the window. Meta's pricing page, as I fetched it, still says utility templates inside an open window are free and lists no India change on that date; its INR rates sit in linked files. Check the INR rate card in your WhatsApp account before budgeting.
- **Plan for the worse case:** at ₹0.115, a ticket conversation of 15 outbound messages costs about ₹1.70, so use buttons and one structured message in place of several plain ones.

## Knowledge base parameters

Split the knowledge base into six layers, because manuals, past jobs, prices and safety rules need different storage and different levels of trust; only the document layer belongs in managed retrieval. The most valuable layer is the one Keepwell builds itself: verified root causes from closed jobs.

| Layer | Content | Store | Updated by | Trust |
| --- | --- | --- | --- | --- |
| L1 Appliance catalogue | Brand, model, series, category, year, capacity, refrigerant or water type | Postgres table | Installer scans, onboarding, ops | Structured |
| L2 Documents | Manuals, error-code tables, troubleshooting guides, installation guides, service bulletins, parts exploded views, warranty and AMC terms | Gemini File Search store | Upload by ops | Brand documents highest |
| L3 Experience | Anonymised closed jobs: symptom, error code, root cause, part, duration, cost, outcome, and whether a self-fix was tried | Postgres with pgvector | Each closed job, after technician confirms root cause | Rises with verified count |
| L4 Policy and price | Rate cards, warranty rules by brand, service intervals, typical life, parts prices | Postgres, effective-dated | Keepwell ops, centres for their own rates | Owner-approved |
| L5 Safety rules | Gas smell, burning, sparks, water near mains, swelling | Code, not model | Keepwell ops and engineers | Deterministic |
| L6 Safe-fix catalogue | Household-doable steps with a success check and stop conditions, each tied to a manual page or bulletin | Postgres, effective-dated, with reviewer and review date | Brand or senior technician review, then ops | Reviewed before use; code selects the step, the model explains it |

### Metadata on every document and chunk

File Search lets you attach string or numeric key-value metadata at import and filter on it at query time ([Google docs](https://aistudio.google.com/docs/file-search)). Use the same fields in the experience layer.

| Field | Example values | Used for |
| --- | --- | --- |
| brand | Brand name as in the catalogue | First retrieval filter |
| category | Air conditioner, washing machine, water purifier | First retrieval filter |
| model\_series | Series or model code | Narrows to the exact appliance |
| doc\_type | manual, error\_codes, bulletin, parts\_view, warranty\_terms | Choosing what to show a technician or the household |
| language | en, hi, te | Matching the user |
| version\_year, valid\_to | 2024, null | Dropping superseded documents |
| authority | oem, centre\_verified, keepwell | Ordering evidence |
| audience | technician, household | Preventing internal detail reaching the household |

### Retrieval and answer rules (starting values)

| Parameter | Rule |
| --- | --- |
| Filter order | Brand and category first, then model series when known, then semantic search |
| Chunks returned | 5 to 8; tune against the test set |
| Citation rule | Every diagnostic claim carries a citation; no citation means mark unverified and do not use it for a self-fix or a quote |
| Source mix | Manuals say what should be done; experience cases say what usually happens; show both |
| Confidence gate | Below a set confidence (start at 0.6), the agent asks more questions or books a diagnostic visit instead of a repair |
| Language | Accept Hindi, Telugu and English input; retrieve against English documents; test accuracy per language before launch |
| Safety | L5 rules run before any model call and can end the chat with a stop-use message |

File Search returns citations with file name, custom metadata and, for PDFs, page numbers ([Google docs](https://aistudio.google.com/docs/file-search)), which supports the citation rule.

### File Search facts that shape the design

- **Cost:** you pay for embeddings when indexing; storage and query-time embeddings are free; retrieved text is billed as ordinary input tokens.
- **Limits:** 100 MB per document; total store size 1 GB on the free tier, 10 GB on Tier 1, 100 GB on Tier 2, 1 TB on Tier 3; Google recommends staying under 20 GB per store for latency, and a store holds roughly three times the input size, so shard by brand or category.
- **Not supported:** audio and video files; use in the Live API; combining with Grounding with Google Search. The Live API voice agent and the technician copilot must therefore reach the knowledge base through your own tool call.
- **Retention:** uploaded raw files are deleted after 48 hours while the store persists, so keep originals in Cloud Storage.
- **Images:** PNG and JPEG are supported, so exploded part diagrams can be indexed.
- **Rights:** brand manuals are copyrighted; confirm usage rights with each brand before indexing.

### Test before trusting

Build a test set of about 100 real complaints with technician-confirmed root causes. Track retrieval hit rate, top-3 diagnosis accuracy, citation rate and the share of diagnoses a technician overrides. Do this per language. For each safe-fix entry, also check whether households' reports of success match what technicians later find.

## Database parameters

Use Postgres as the system of record, Firestore for live state and BigQuery for analytics, because assignment, reporting and cross-centre appliance history need joins and aggregates that Firestore does poorly. Cloud SQL has no meaningful always-free tier, but new Google Cloud accounts get $300 in credits (both from your Google list). For a prototype, Firestore alone is enough; AI Studio Build can wire it up. One shared database serves every centre: a centre id on each operational row and row-level security keep one centre's prices, notes and customers from another.

| Store | Holds | Why |
| --- | --- | --- |
| Cloud SQL for PostgreSQL (with PostGIS and pgvector; confirm availability on your tier) | Households, appliances, conversations, tickets, centres, technicians, parts, quotes, job cards, consent, experience cases, the safe-fix catalogue | Joins and aggregates for assignment and reporting; geo queries; vector search over past cases; row-level security per centre |
| Firestore | Live call and case state, the centre console, technician app state | Realtime updates and offline sync for technicians in basements and lifts |
| BigQuery | Closed-job history, metrics, model training | First-time fix rate, self-resolution rate, care index checks, parts demand |
| Cloud Storage | Photos, voice notes, call recordings, invoices, original manuals | Keep raw files out of the database |

Cloud Storage's always-free allowance covers only selected US regions, so budget for storage in an India region. DPDP rules allow transfers outside India subject to further requirements the government may set ([Stocktwits summary](https://stocktwits.com/news-articles/markets/equity/government-notifies-dpdp-rules-sets-18-month-roadmap-for-data-protection-regime-ws-e-19760652/cLPQ2MrREEA)), so prefer India regions.

### One appliance, many centres: how identity works

Keepwell issues the only global id. A physical appliance gets one id, whichever centre meets it first, and each centre's own numbers are stored as aliases that point at it. No centre is asked to adopt Keepwell's numbers or to know another centre's. Two natural keys do the matching: the appliance by brand plus serial number, which is printed on the sticker and the invoice, and the household by verified phone number.

| Identity | How it is found | If it fails |
| --- | --- | --- |
| Appliance | Brand plus normalised serial number, read by Gemini from the sticker, the invoice or the carton label | No readable serial: create a provisional appliance flagged unverified (model, household, purchase date) and merge when a serial appears |
| Household | Verified phone number (hashed copy for lookup), with the address as a second signal | A new number for the same home: the household adds it as a member; merges need consent and are logged |
| A centre's own customer or job number | An alias row: centre, entity, the centre's number, the Keepwell id | Never needs matching: the lookup runs centre plus local number to Keepwell id |
| A brand's request id | The same alias row, with the brand as the system | Same as above |

So what the centre calls number 1 and another centre calls number 2 are two alias rows for one Keepwell id, and neither centre sees the other's number. When the same serial turns up twice, the older id survives, the other becomes an alias and the merge is recorded as an event, so no alias breaks.

### What is shared and what stays with the centre

| Shared across centres, with the household's consent | Private to one centre |
| --- | --- |
| Appliance identity, model, serial, warranty dates | Quotes, prices, payer split and settlement |
| Event timeline: faults, root causes, parts replaced, self-fix attempts and outcomes | Technician notes and ratings |
| Care index and its reasons | Customer notes and the centre's own numbers |
| Safety notes | The centre's stock, calls, recordings and messages |

Row-level security on the centre id enforces the right column; the left column is read through views that check consent, and every cross-centre read is written to the access log. A brand request is visible to the centre it was routed to and to that brand.

### Households and appliances

| Entity | Key fields | Why it matters |
| --- | --- | --- |
| household | id, phone (encrypted, plus hashed copy for lookup), language, address, lat and lng, pincode, community id, access notes (floor, lift), preferred windows, reminder preferences | Identity shared across centres |
| household\_member | id, household id, phone, role (owner, family, tenant), may raise tickets | One home, several people, changing numbers |
| centre\_customer | centre id, household id, the centre's customer number, first contact, consent for this centre | One household's relationship with one centre |
| appliance | id, household id, category, brand, model, serial (normalised), identity status (verified, provisional, merged), purchase date, source, invoice file, install date, installer, warranty start and end, plan id, usage profile, care index with reasons, last service, next due, status | The core record; warranty and age drive entitlement and reminders |
| appliance\_event | id, appliance id, centre id, type (purchase, install, service, repair, part replaced, self-fix, advice, reminder, index change, merge), time, ticket id, details | Append-only history the care index reads |
| external\_ref | system (a centre or a brand), entity type, the system's own number, Keepwell id, valid from | Maps every party's numbers to the one global id |

### Work, from ticket to job card

| Entity | Key fields | Why it matters |
| --- | --- | --- |
| conversation | id, centre id, channel (call, message, brand, retailer), household id, started and ended, language, transcript and recording refs, recording notice given, self-fix and video answers, modality, video session and frame refs, outcome | Every trigger leaves a record, including cases closed without a visit |
| source\_request | id, centre id, source (brand or retailer), their request id, request type, payload, received at | Brand and retailer hand-offs |
| ticket | id, centre id, household id, appliance id, conversation id, job type, case card (including what was tried), urgency class (safety, urgent, standard, planned) with its change history, needed-by date, safety flag, entitlement and payer, status, SLA targets | One model for all six job types |
| self\_fix\_attempt | id, ticket or conversation id, safe-fix id, steps the household reports, outcome (fixed, no change, got worse, could not do), time, media | What was tried, and the data to test the catalogue |
| visit\_plan | ticket id, ranked hypotheses with probabilities and evidence refs, already tried, required skills, predicted parts with probabilities, duration p50 and p80, tools, access, confidence | Single input for assignment, parts and quote |
| assignment | id, ticket id, candidate technician id, window, price range, per-criterion scores, rank, chosen, reassigned by the centre with reason | Audit trail and training data for the scoring |
| job\_card | id, ticket id, technician id, planned window, check-in and out with location, checklist, before and after photos, parts used with serials, outcome (fixed, partial, needs part, not repairable), closure OTP reference and confirmation time, rating | Closes the loop into memory and the experience layer; the OTP code itself is never stored |
| route | id, technician id, date, ordered stops with planned arrival, planned and actual travel minutes, batched flag | Measures batching |

### Supply side

| Entity | Key fields | Why it matters |
| --- | --- | --- |
| service\_centre | id, name, location, service area (pincodes or polygon), phone and WhatsApp lines, brand authorisations with level and expiry, categories, daily capacity by skill, hours, contract terms, onboarding status | Authority check and capacity |
| brand\_integration | brand id, centre id, request types, endpoint or hand-off method, status | How a brand's requests reach the centre |
| technician | id, centre id, skills (brand, category, fault class, level, certified on), languages, shift hours, route anchor, vehicle, tool kit, verification (identity, safety certificate), active | Stage 1 filters |
| technician\_metrics (computed nightly) | first-time fix rate by category, on-time rate, repeat-visit rate, acceptance rate, quote variance | Stage 2 scores |
| safe\_fix | id, category, symptom or error code, steps, success check, stop conditions, source and page, risk class, reviewer, review date | The only fixes the agent may offer |
| part\_catalogue | part number, compatible models and revisions, genuine or aftermarket, substitution group, MRP, warranty | Parts ladder and quote |
| parts\_centre | id, location, brands, hours, pickup and delivery options, reliability stats | Parts ranking |
| stock | holder (van, centre, parts centre), part number, quantity, as-of time, source (scan, call, feed), confidence | Readiness score; stale stock counts less |
| reservation | part number, quantity, visit id, ready-by, status | Prevents double booking |

### Money and trust

| Entity | Key fields | Why it matters |
| --- | --- | --- |
| quote | id, ticket id, version, type (estimate or firm), lines with amount and payer, tax, valid until, approved at and channel, variance against estimate | Price lock and the payer split |
| settlement | payer shares per line, the centre's settlement, payouts to the parts centre, Keepwell fee (to the centre or the brand, as contracted) | Accounting |
| reminder | id, centre id, appliance id, type, due date, template, category, sent, delivered, read, action taken | Reminder effectiveness and WhatsApp cost |
| consent\_ledger | subject, centre (recipient), purpose (including self-fix guidance and video diagnosis, asked per case), notice version, granted at, channel, withdrawn at | Proof of consent per purpose and per centre |
| access\_log | who, which record, which centre, when, linked ticket | Shows each read, including cross-centre reads, was needed |
| feedback and dispute | ticket id, rating, reason, resolution | Reliability score and trust |

### Design rules

- Store the score breakdown for every candidate assignment, not only the chosen one.
- Keep history append-only, with effective dates on prices, authorisations and consent.
- Put the centre id on every operational row; read shared appliance history only through consent-checked views, and log each read.
- Share the minimum: a technician sees the address and phone only after the window is confirmed, and only for that ticket.
- Store a call recording only if the household was told, and set its retention separately from the transcript.
- Never store the OTP code; store the provider's reference and the confirmation time.
- Compute metrics in BigQuery nightly and write them back to Postgres.
- Set retention per purpose before the pilot, and anonymise experience cases to pincode level.

## Google architecture and the value each product adds

Use Google where it is strongest for this product (live voice and multimodal understanding, maps and routing, realtime mobile backend, serverless hosting, analytics) and keep WhatsApp, payments and spreadsheets out of the core. Each Google product below is tied to a promise a user would notice and a number that proves it.

### The promise to each user, and what delivers it

| User | Promise | Google capabilities behind it |
| --- | --- | --- |
| Household (served through the centre) | Whether they call, message, or arrive through a brand or retailer, they get questions that make sense, a safe fix to try, and a confirmed visit if it fails, without repeating what they already tried | Gemini Live API, Gemini multimodal, File Search, Cloud Run tools |
| Service centre | Every request arrives as a case card with what was tried, a technician booked by skill, parts and route, and fewer visits for things the household could fix | Gemini, File Search, Route Optimization, Firestore, BigQuery |
| Technician | More jobs a day, fewer wasted trips, a copilot that knows the manual and past cases | Maps, Gemini Live API, Firestore offline sync, FCM |
| Parts centre | Reserved orders and demand visibility instead of walk-in guesses | Cloud Run APIs, FCM, BigQuery |
| Brand | Forwarded requests picked up at once, installations scheduled, installed-base and service-quality data back | Cloud Run APIs, BigQuery, Looker Studio |

### Stage by stage

| Stage | Google product | What it does | Value | Measure |
| --- | --- | --- | --- | --- |
| Call agent | Gemini Live API (audio and video, function calling, session resumption) | Answers the centre's line, asks clarifying questions, asks consent for a self-fix and for video, offers a safe fix, reads the case card back | The line is never in a queue; the household talks to something that asks the right questions | Share of calls resolved or booked with no one picking up; questions per case |
| Message and brand intake | Gemini API (audio, image, text, structured output) | Turns a Hindi or Telugu voice note, an error-code photo or a brand's request into a case card | Household skips forms; the centre gets a complete card | Share of cases complete without a callback |
| Appliance identification | Gemini vision, or Document AI | Reads the model sticker, serial and invoice into the appliance record and warranty dates | Verified identity without typing, and the key that joins records across centres | Share of appliances with verified serial and date |
| Knowledge base | Gemini File Search, reached through the app's own tool call from the voice agent | Cited answers from manuals and error-code tables | Right steps, no vector database to run | Citation rate; top-3 diagnosis accuracy |
| Safe-fix guidance | Gemini, reading only the L6 safe-fix catalogue | Walks the household through one catalogued step at a time and checks the result | Fewer visits for things the household can fix | Self-resolution rate; reopen within 7 days; harm incidents |
| Experience search | Gemini embeddings with pgvector on Cloud SQL | Finds similar past cases and their root causes | Faster diagnosis; the data moat | Override rate of the diagnosis |
| Agents | ADK on Cloud Run | Clarify, self-fix, diagnosis, parts, quote, assignment and reminder agents calling tools over MCP | Testable, structured flow | Task success per agent |
| Address quality | Address Validation, Geocoding | Clean, geocoded household and centre addresses | Fewer failed visits | Failed-visit rate |
| Travel feasibility | Routes (distance matrix) | ETAs for the technician filter and parts ready-by | Honest arrival windows | ETA error |
| Batching | Route Optimization API, or OR-Tools first | Day routes and the marginal route cost per job | Technicians do more jobs a day; households get cheaper visits | Jobs per technician-day; travel minutes per job |
| Live arrival | Fleet Engine, Navigation SDK | Live position and ETA | "Technician is 15 minutes away" | Late-arrival complaints |
| Apps | Flutter, Firebase Auth, Firestore, FCM, App Check | Centre console, technician app and parts-centre app with offline sync and push | Works in basements; push is free | Jobs closed offline and synced; push delivery |
| Backend | Cloud Run, Cloud Scheduler, Cloud Tasks, Pub/Sub, Secret Manager | Call and WhatsApp webhooks, brand hand-offs, agents, reminder jobs | Scales to zero while the pilot is small | Cost per case |
| Learning loop | BigQuery, BigQuery ML, Looker Studio | First-time fix, self-resolution, predicted fix probability, assignment weights tuned from the centre's reassignments, care index check, dashboards for centres and brands | Assignment and the safe-fix catalogue improve with each closed job | First-time fix rate over time |
| Technician copilot | Gemini Live API | Voice and camera help on site; drafts the job card from a spoken summary | Fewer wrong parts; less typing | Repeat-visit rate; job-card completion time |
| Payment | Google Pay (UPI) where approved, else a payment gateway | Pay the approved quote | Fewer cash disputes | Share paid digitally |
| Build speed | AI Studio Build, Stitch, Antigravity, Gemini CLI | Prototype screens and apps | Faster pilot | Weeks to first pilot |

The Live API limits shape the call agent. Without context-window compression, an audio-only session is capped at 15 minutes and an audio-plus-video session at 2 minutes, and a single connection lasts about 10 minutes. With compression on and session resumption (handles are valid for 2 hours, and the server sends a GoAway message before it closes), the call can run on. Function calling and Google Search grounding are supported; Google Maps, code execution and URL context are not, so the agent reaches the knowledge base, slots and quotes through the app's own tools. Video input and Hindi and Telugu quality are not verified here and must be rehearsed ([session management](https://aistudio.google.com/docs/live-api/session-management), [tools](https://aistudio.google.com/docs/live-api/tools)).

### Ways to raise Google's share without hurting the product

- Put Gemini in every unstructured step: the call, intake, identification, knowledge, safe-fix guidance, copilot, job-card drafting and the plain-language explanation of a quote.
- Use Maps for every geographic decision: addresses, ETAs, batching, live arrival.
- Build the centre console and the technician and parts-centre apps on Flutter and Firebase.
- Make BigQuery the learning loop that retunes the assignment weights, shows which safe fixes work, and checks the care index.

### Where not to force Google

- **WhatsApp** is Meta's; there is no Google substitute, and Google Business Messages is discontinued.
- **Sheets, Apps Script and Calendar** are not production data layers: their quotas and concurrency limits bite, and Google is tightening Workspace API quotas. Offer an add-to-calendar link instead.
- **Firestore** should not carry relational queries such as technician first-time fix by category.
- **NotebookLM** has no general API, so it cannot be a backend component.
- **Agent Platform (formerly Vertex AI)** is more setup than a prototype needs; start with the Gemini API and ADK.

## Prototype: a live call on stage

The stage demo is one real call. A presenter phones the centre's line, Gemini Live answers as Keepwell, and the centre console, the technician screen and the household's WhatsApp thread update in parallel. Nothing on those screens is scripted: they draw the app's own state, so what the audience sees is what the agent actually did. The scenario below is a brief for the presenter, not a script for the agent.

### Recommended scenario: a washing machine that will not drain

| Beat | What happens on the call | What updates on screen |
| --- | --- | --- |
| 1 | The presenter phones the centre's line. Keepwell answers in the centre's name, says the call may be recorded and asks which appliance | Console: a new conversation on the call channel, recording notice logged |
| 2 | The agent asks: "Are you okay to try a quick, safe fix yourself?" The presenter says yes | The self-fix answer is logged for the case |
| 3 | The agent asks: "Would you like to switch to video, or carry on here?" The presenter says video and opens the link sent to the phone | Modality changes from voice to video inside the same conversation |
| 4 | The agent asks to see the sticker and the display, and reads brand, serial and the error code. It asks what sound it made, when it started and what has been tried. The presenter answers in Hindi or Telugu | Appliance record with brand-plus-serial identity, warranty dates and an alias for the centre's own number; the case card fills in; the safety flag stays clear |
| 5 | The agent offers one catalogued step and watches it on camera. The presenter reports that it did not help | A self-fix attempt row: the steps, the outcome "no change" |
| 6 | The agent re-runs diagnosis with that attempt as evidence, then books a technician and a window | Visit plan with "already tried"; assignment scores per criterion; the household hears the window and a price range |
| 7 | In the console the presenter reassigns the job to another technician | The reassignment is logged with a reason, as training signal |
| 8 | On the technician screen the plan is open; later a firm quote is approved and the household's OTP closes the job | Job card closes on the OTP; the appliance timeline gains the event |

This scenario touches every layer in one call: identity, the two consent questions, video diagnosis, clarifying questions, a safe fix, the failed-fix re-run, assignment, quote and OTP closure. The other three triggers (a message, a brand-forwarded request and a retailer handover) are in the simulated dataset and can be shown as recorded cases in the console, or run live if time allows.

### What to rehearse

- Keep the call to about five minutes, and turn on context-window compression and session resumption so the session limits do not cut it.
- Rehearse the switch from a phone call to the video link, Hindi and Telugu, and reading the sticker and the display by video. If video fails, the fallback is a photo sent to the centre's WhatsApp, which produces the same case card.
- Use the paid tier, a stable network and a second phone. Hold a labelled recording of a rehearsal run as a backup.
- Run on the simulated dataset only; no call touches a real household's data.

## Limits, risks and what Google does not cover

The largest risks are not technical: WhatsApp costs are unsettled, brands control who may service under warranty, and each centre has to be onboarded and trusted before an agent answers its line. The Google-side risks are quotas, preview status and data terms.

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| WhatsApp is Meta's, not Google's | Needs the WhatsApp Business Platform directly or through a provider such as Twilio, Gupshup or Interakt, with approval and template rules; each centre needs its own number | Apply early; test template approval before building reminders |
| WhatsApp price conflict | Press and Meta's page disagree on India's service and utility charges | Read the INR rate card; budget the worse case; fewer, richer messages |
| Data protection law | Notice and consent duties under the DPDP Rules start 13 May 2027, consent managers from November 2026 ([AZB](https://www.azbpartners.com/bank/update-indias-digital-personal-data-protection-framework-comes-into-effect/)); calls and video are recorded only after notice, and history is shared across centres | Build the consent ledger and access log now; give the recording notice at the start of every call and ask for video consent separately; get legal review; this doc is not legal advice |
| Brand control | Warranty repair and installation are restricted to authorised teams by brands such as Electrolux and Bosch | Refer a job outside the centre's authorisation to the brand's own route; pursue brand integrations |
| Centre adoption | A centre must trust an agent on its own line and move its calls onto it | Start with one category in one centre; run in shadow mode first, drafting case cards beside the existing process; then take overflow and after-hours calls |
| Unsafe self-fix advice | A wrong step could hurt someone or damage the appliance | Catalogue only; no tools, opened panels, wiring, gas or ladders; safety rules in code; two attempts or about ten minutes, then the visit; harm incidents target zero |
| Live call quality | Voice agents mishear and lose long calls; the Live API is in preview, with 15-minute audio limits without compression | Per-language test set; compression and resumption on; fall back to WhatsApp intake with the same case card |
| Cross-centre data leakage | One shared database holds many centres' prices and customers | Centre id on every row, row-level security, consent-checked views, an access log, and tests that try cross-centre reads |
| Identity mismatches | A misread serial or a reused phone number could merge two appliances or homes | Provisional appliances; merges are logged events with consent; alias rows are never deleted |
| Stale stock data | Parts readiness is only as good as the count | Discount unconfirmed stock; scan van stock in and out; confirm with the parts centre before the visit is confirmed |
| Wrong diagnosis | A confident wrong answer wastes a visit or creates a safety risk | Citation rule, confidence gate, safety rules in code, technician decides on site |
| Language accuracy | Hindi and Telugu accuracy varies by model (your list) | Per-language test set before launch |
| Gemini API terms | Free-tier prompts may be used to improve Google products; paid tier is not | Use the paid tier for any real household data |
| Quotas and previews | Live API and many MCP servers are in preview; Maps free caps are per SKU and Enterprise-tier SKUs get the lowest (1,000 a month per your list); budgets alert but do not stop spend | Restrict keys, set per-API quotas, add App Check, review the India price lists |
| Phone sign-in cost | Firebase phone auth SMS needs the Blaze plan, is billed per SMS, caps at 3,000 a day, and India delivery needs testing | Households need no sign-in because the call or WhatsApp identifies them; use Google sign-in or an email link for the centre and technician apps |
| Naming churn | Vertex AI became Agent Platform; NotebookLM became Gemini Notebook | Pin product names and versions in the architecture doc |
| Technician trust | An opaque assignment invites disputes | Show reasons, keep the score breakdown, log the centre's reassignments, offer an appeal |

What Google does not give you: no WhatsApp channel, and no field-service dispatch product. Maps supplies distance, ETA and route optimisation; assignment rules, the safe-fix catalogue, parts logic and pricing are your own code, which is where Keepwell's differentiation lives.

## More ideas, MVP cut and open questions

Build the first version around the loop that proves the proposition: the centre's call or message, clarifying questions, a safe fix, a diagnosed visit plan that records what was tried, technician assignment, closed job card, memory update, reminder. Run it for one appliance category with one or two centres, and test seven hypotheses before building the rest.

### More ideas

| Idea | What it does | Who gains | Phase |
| --- | --- | --- | --- |
| Installation as onboarding | A brand-forwarded or retailer-handed installation request; the installer scans model, serial and invoice, creating the verified appliance record | Household, brand, centre | MVP |
| Safe-fix library growth | Every successful and failed self-fix is evidence that promotes, edits or retires a catalogue entry | Household, centre | MVP |
| Repair-or-replace advisor | Uses age, repair history, quote and typical life to give an honest second opinion | Household trust; the centre's credibility | MVP+ |
| Bundled visits | One visit for several due appliances | Household, technician | MVP+ |
| Technician copilot | Live voice and camera help, job card drafted from a spoken summary | Technician, centre | 2 |
| Parts demand forecast | BigQuery ML on predicted parts and the installed base | Parts centres, centres | 2 |
| Community service days | Pooled demand from one gated community, scheduled by the centre | Technician, households | 2 |
| Repair guarantee and after-repair check | Service warranty per job type, follow-up message | Household | 2 |
| Retailer handover as a channel | A retailer hands over a sale; the centre books the installation and the first reminder | Retailer, centre | 2 |
| Brand dashboard | Anonymised failure rates by model, service times, warranty claims | Brands | 2 to 3 |
| Plan marketplace and claims automation | Compare AMC and extended warranty; Gemini checks claim documents | Household, plan providers | 3 |
| Technician training from the knowledge base | Micro-lessons built from solved cases | Technicians, centres | 3 |
| Appliance passport | Portable record for resale or a tenant move | Household | 3, speculative |

### Revenue options (hypotheses, none validated)

A per-centre subscription or per-case fee for the agent on its line; brand-paid installation scheduling and registration; parts referral fees; a household care plan sold through the centre (reminders, priority slots, waived visit fees); anonymised insights sold to brands. Start with the per-centre fee plus brand-paid installation, and test the household plan later.

### MVP cut

- **In:** the centre's line answered by a Gemini Live agent, and WhatsApp messages, both producing a case card; clarifying questions; appliance register with brand-plus-serial identity; one category; one or two centres onboarded by hand; centre console on Firestore with a simple web board; the safe-fix catalogue for the top fault codes with the two-attempt limit; visit plan using File Search over the manuals you can legally index; technician assignment inside the centre with simplified scoring; quote with approval; technician app on Flutter and Firebase with the job card; OTP closure; memory update; two reminder types.
- **Out for now:** Route Optimization API, Live API technician copilot, parts centre ranking beyond centre stock plus one partner, area batching beyond simple suggestions, brand dashboard, and brand and retailer hand-offs beyond one manually entered request type.
- **Category:** pick one with recurring service so reminders can prove value; air conditioners (seasonal) and water purifiers (filters, AMC) are candidates to test in interviews. Washing machines suit the stage demo because error codes and safe checks are well documented.

### Seven hypotheses to test

| Hypothesis | Test | Pass signal (set before testing) |
| --- | --- | --- |
| Households will describe a problem to an agent on the centre's line and complete the case without a callback | Agent on one centre's overflow and after-hours calls and WhatsApp, with a person watching | Share of cases complete with no callback; questions per case |
| Safe self-fixes resolve a useful share of cases without harm | Ask the two consent questions and offer catalogued fixes for the top fault codes at one centre; track yes rates for the self-fix and video questions, and reopens within 7 days | Self-resolution rate above a threshold set beforehand; zero harm incidents; the video yes rate |
| Diagnosis and parts prediction raise first-time fix, including after a failed self-fix | Baseline from the centre's last three months of job cards, then compare diagnosed jobs | Fix-rate gain over baseline |
| Centres will put an agent on their line and share stock | Interviews, then one or two pilot centres in shadow mode | Stock accuracy against a physical check; share of calls handed to the agent |
| Price lock and clustered slots are valued | Compare approval and acceptance rates with and without them | Acceptance rate of clustered slots |
| Someone will pay, and it is clear who | Willingness-to-pay interviews with centres and one brand | Stated payer and amount |
| The care index predicts breakdowns | Back-test on job history | Low scores precede more repairs |

### Open questions for the team

- Which category and which centres first?
- Are phones and other consumer electronics in scope, or only home appliances? The phone example suggests the safe-fix catalogue could cover both.
- Can you get a centre's job history to measure today's first-time fix rate?
- Which brands will you work with, and will they allow manual indexing and forwarding requests to a centre on Keepwell?
- Are technicians employed by centres or freelance? It changes assignment and incentives.
- Who pays for Keepwell: the centre, the brand, or both? It decides who holds the contract and the data.
- Will centres allow calls and video to be recorded and agree to shared technical history across centres?
- Which safe fixes will the manuals and a centre's reviewer approve for the first category, and who reviews them?
- Does the link-in-browser route for switching from a call to video work well enough on the phones your households use?
- I read "top" in "closed after getting the top from household" as an OTP, and the user has confirmed that closure is by OTP only. The job closes only when the household's OTP is verified; a tap-to-confirm button is not used.

## Sources

Pages opened in full:

- [Meta: Pricing on the WhatsApp Business Platform](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing.md)
- [Google: File Search](https://aistudio.google.com/docs/file-search)
- [Google: Live API session management](https://aistudio.google.com/docs/live-api/session-management)
- [Google: Live API tools](https://aistudio.google.com/docs/live-api/tools)
- [Google: Route Optimization API usage and billing](https://developers.google.com/maps/documentation/route-optimization/usage-and-billing)
- [NewsBytes: WhatsApp Business messages costlier in India](https://www.newsbytesapp.com/news/science/whatsapp-business-messages-get-costlier-in-india-from-today/story)

Read as search excerpts only; confirm before relying on them:

- [Kognitos on first-time fix](https://www.kognitos.com/blog/field-service-management/), [Salesforce on dispatch](https://salesforce.com/blog/what-is-dispatch-management), [AEX on first-time fix](https://aexinc.com/blog/how-to-increase-first-time-fix-rates), [Route Optimization quick reference](https://developers.google.com/maps/documentation/route-optimization/quick-reference)
- [Electrolux warranty terms](https://www.electrolux.in/support/general-warranty-terms-and-conditions), [Bosch installation](https://www.bosch-home.in/service/installation-service), [Samsung installation (MySmartPrice)](https://www.mysmartprice.com/gear/appliances/appliances-news/samsung-brings-4-hour-installation-for-refrigerators-acs-washing-machines/)
- [Urban Company](https://urbancompany.com/ahmedabad-tv-repair-behrampura), [NoBroker](https://www.nobroker.in/appliance-services-in-delhi), [Croma](https://www.croma.com/ew-knowMore), [Vijay Sales](https://www.vijaysales.com/vswarranty), [V-Guard](https://www.vguard.in/waterpurifier/preemptive-services), [consumer-rights guide](https://righttoinformation.wiki/_export/xhtml/washing-machine-fridge-repair-damage-india)
- [AZB on DPDP phasing](https://www.azbpartners.com/bank/update-indias-digital-personal-data-protection-framework-comes-into-effect/), [Stocktwits on DPDP transfers](https://stocktwits.com/news-articles/markets/equity/government-notifies-dpdp-rules-sets-18-month-roadmap-for-data-protection-regime-ws-e-19760652/cLPQ2MrREEA)

Your two uploaded Google lists (compiled 20 November 2026) are the source for every Google quota, limit and product statement not linked above. Claims marked general knowledge (OR-Tools, WhatsApp's three-button limit, PostGIS and pgvector support) were not verified in this session.
