# Circuit — Round 3 Part 1: the agent (draft)

**Status:** sections 3, 5, 6 and 7 are finished. Sections 1, 2 and 4 must be filled from the real run: click **Export decision log** on the trace page after recording and copy from it. Anything in [square brackets] is a placeholder. Delete this status note before submitting.

Recording link: [paste unlisted YouTube/Drive link]
Model: [exact LLM_MODEL from .env, e.g. the Claude or Gemini model id]
System prompt: `data/04_RUNTIME_SYSTEM_PROMPT.md` (v0.6), plus the output protocol in `circuit/agent.py`.

## 1. One person's story (100 words max) — FILL AFTER THE RUN

Template, rewrite to match what actually happened on screen:

> On [Sunday 4 October], Meera in Ramagundam sends Sri Sai Electronics a Telugu voice note: the AC runs but doesn't cool. Within a minute the agency's assistant, Circuit, replies, asks for the model label and confirms the warranty is over. It ranks the agency's technicians; the dispatcher assigns Ravi, who accepts. Meera picks the [11 AM] slot and grants access. Her son approves up to ₹[amount] in his UPI app. Ravi confirms the cleaning kit is in his bag, the route checks out, and the owner signs off. Circuit tells Meera Ravi is coming, ready to fix it on the first visit.

## 2. Every decision Circuit made — PASTE FROM THE EXPORT

Paste the table from **Export decision log**. It already has the required columns: when, what the agent received, where it came from, what it decided, why (rule), what it did or said and to whom, through what. Do not edit the decisions; only tidy wording if needed.

[paste table here]

## 3. What Circuit knows on day one

| What it knows | Who provides it | How |
| --- | --- | --- |
| Agency name, service area, hours, calling hours | Agency owner | Onboarding form on the landing page |
| Technicians, their skills and free slots | Agency owner or dispatcher | Google Sheet or a photo of the register, updated daily |
| Price list (inspection fee, labour, consumables) | Agency owner | Same sheet |
| Parts in stock and which models they fit | Agency owner | Stock list; compatibility only from a parts catalogue, never guessed |
| Machine Kundli: each machine's model, warranty and past repairs | The agency's own past job records, with the household's consent | Imported at onboarding, then added to after every job |
| Mistri Gyan: safe household checks, likely causes and technician tests per symptom | Servify, from reviewed repair outcomes | Shared fault library, reviewed before use |
| Manufacturer troubleshooting excerpts | Public brand support pages | Indexed for search, each with its source |
| Rules: safety, who may approve what, when a job is "ready" | Circuit team | The runtime system prompt (rules R01–R15) |

In the demo, the agency, technicians, stock and the one Machine Kundli record are fictional fixtures, labelled `SYNTHETIC_FIXTURE` on screen.

## 4. Every call to Gnani, Pine Labs and Delhivery — CHECK AGAINST THE EXPORT

Copy the exact request and response for each call from the "Partner calls" section of the export. The endpoints Circuit uses:

| Partner | When | Endpoint | Request | Response | Mode |
| --- | --- | --- | --- | --- | --- |
| Gnani | Voice note arrives | `POST https://api.vachana.ai/stt/v3` | Header `X-API-Key-ID`; multipart `audio_file`, `language_code=te-IN` | [paste: `success`, `request_id`, `timestamp`, `transcript` as returned] | LIVE |
| Pine Labs | Payer must approve a ceiling | UPI Reserve Pay mandate creation, per Pine Labs docs [paste exact section/URL used] | Amount ceiling in paise, merchant reference, line items | [paste the documented response the Wizard fed in, with `status: ACTIVE`] | DOC_SIMULATED |
| Delhivery | Technician assigned, before the ready check | Delhivery Maps Distance Matrix, per the Maps API Reference [paste exact section] | Technician base to household landmark, two-wheeler | [paste the documented response] | DOC_SIMULATED |

## 5. Capabilities that don't exist yet (3)

These are the three things the rails would need for Circuit to run without a human filling the gap. Machine Kundli and Mistri Gyan are Circuit's own data stores, built and owned by Servify, so they are not counted here.

| # | Partner | Proposed endpoint | What it does | Data the partner already holds that makes it possible |
| --- | --- | --- | --- | --- |
| 1 | Gnani | `POST /stt/v3` with `return_confidence=true` | Returns a confidence score per word and flags uncertain spans (model numbers, amounts, codes), so Circuit reads back only what's shaky | Its speech models already score every word internally while decoding, trained on Indian accents and code-mixed speech |
| 2 | Pine Labs | `POST /api/pay/v1/orders/{id}/capture-on-event` | Captures payment only when a signed real-world event arrives (technician's job-done code plus the household's "yes, it works") | It already holds the mandate, the order, the merchant and, through Grantex, the record of what the agent was allowed to spend |
| 3 | Delhivery | `POST /api/cmu/create.json` with `deliver_to_person` and `deliver_by` | Hands a part to a named technician by an appointment deadline, not just to an address | Its last-mile rider network, pincode serviceability and live shipment tracking |

## 6. Mockups of every touchpoint

Screenshots from the running console (take them during the rehearsal or the real take):

1. **Household, WhatsApp-style chat:** voice note, Circuit's first question, the label answer, slot buttons, the "Ravi is coming" message.
2. **Payer:** the itemised approval request and the *Approve up to ₹…* button.
3. **Technician:** the job offer with *Accept*, then *Confirm kit in my bag*.
4. **Agency dispatcher and owner:** the ranked technicians with *Assign*, and *Sign off READY*.
5. **Live trace:** the S5 readiness gate with every condition ticked.
6. **Landing page:** https://claude.ai/artifact/XDhbAZG6KthSpGiRQX6rbS

## 7. How agent-ready is each rail

| Rail | Score | Why |
| --- | --- | --- |
| Gnani (voice) | 6/10 | Telugu speech-to-text works over a simple API, but it returns no confidence score, outbound calling is limited to whitelisted test numbers, and its noise filter removes the machine sounds a diagnosis needs. |
| Pine Labs (payments) | 7/10 | Mandates, Reserve Pay, payment links, refunds, agent payments (P3P) and scoped permissions (Grantex) already exist; what's missing is capture triggered by a physical event, and Reserve Pay caps at ₹10,000. |
| Delhivery (logistics) | 4/10 | Maps covers address checks, geocoding and travel times, but nothing in the rail knows a technician, an appointment or a handover to a person; parcels go to addresses, not people. |

Adjust a score if something broke differently during the real run, and say so in the reason.
