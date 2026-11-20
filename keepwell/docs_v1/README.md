# Keepwell simulated dataset (v0.2)

A world to run the Keepwell agent against, not a script for it. Everything here is a raw input: centres and their technicians, brands and retailers, households and appliances, history, stock, calendars, documents, and 20 incoming cases that arrive through four triggers. Nothing here is an output of the app. There are no pre-written diagnoses, urgency calls, consent-gate answers, self-fix outcomes, visit plans, technician rankings, slot offers or case cards for today's cases. The answers sit in `evaluator_only/`, where the app must never read them. The generator in `gen/` also holds them (`gen/stories.py`), so keep that folder out of the app's reach too.

**Simulation clock:** Saturday 21 November 2026, 08:00 IST. History runs from the Keepwell pilot start (1 Sep 2025). The agent is treated as live from 1 Mar 2026: consent gates, urgency assessments, clarifying questions and self-fix attempts exist only for tickets from that date. All names, brands, places and phone numbers are fictional (phones use a non-allocated `+91 5xxxx xxxxx` range).

## What changed from v0.1

Keepwell is now a platform deployed for service centres and brands. It is the face of the centre and of the brand, not of the household.

- **One shared database, many centres.** Households and appliances have global ids (verified phone; brand plus normalised serial). Numbers that belong to a centre, a brand or a retailer are alias rows in `external_ref`. Operational rows carry `centre_id` and are isolated by row-level security.
- **No centre matching.** The receiving centre is given. The agent checks that centre's authority for the brand (`centre_authority`), its service area and its capacity. If it cannot act it says so and returns the request to the brand with the reason.
- **Four triggers:** household call, household message, brand-forwarded request, retailer handover. Each lands on one centre's line or integration.
- **Urgency is the agent's call,** from rules plus three fact questions; the household is never asked "how urgent". `needed_by` is stored separately.
- **Two consent gates before any self-fix.** Gate 1: "okay to try a safe fix?" Gate 2, only after yes: "switch to video or carry on here?" Silence counts as no. Safety cases skip both. Non-repair jobs get neither.
- **A safe-fix catalogue** whose CHECK constraints are the threshold: at most 6 steps, at most 12 minutes, reversible, no tools, a manual page and a named reviewer.
- **What was tried** is recorded for every attempt and carried into the visit plan. If a fix fails the agent re-runs the process.
- **Technician assignment happens inside the receiving centre.** Prices are per centre and private.
- **Cross-centre technical history** is readable only through `read_shared_history()`, which checks the household's consent and writes `access_log`.

## What is in the package

| Path | What it is |
|---|---|
| `keepwell_schema.sql` | Postgres 15+ schema, 63 tables, 7 views, 9 functions, row-level security. Apply first. |
| `csv/`, `load.sql` | 55 seeded tables (about 15.5k rows). From this folder: `psql -d keepwell -v ON_ERROR_STOP=1 -f load.sql` |
| `inbox/` | The 20 incoming cases: `inbox.json` (call logs, WhatsApp-style messages, brand and retailer payloads), per-case folders of `.ogg` calls and voice notes and `.jpg` photos, `brand_requests/` and `retailer_handovers/` (the same payloads as in `inbox.json`, one file per case). |
| `kb/` | 21 PDFs for the Gemini File Search layer: manuals with a "Household checks you may do yourself" section, error-code tables, bulletins, warranty and AMC terms, field guide, and the Keepwell safe-fix catalogue. |
| `scripts/` | `embed_experience_cases.py` and `upload_kb_to_file_search.py`. Both untested against the live API. |
| `evaluator_only/` | `CASE_GUIDE.md`, `ground_truth.json`, `voice_scripts.json`, `true_stock.csv`, and `personas/` (one card per case telling whoever plays the household how to answer, including the real situation). Marking and role-play material. |
| `DATA_DICTIONARY.md` | Every table, column, key and allowed value, generated from the schema. |
| `CAPTURE_KIT.md` | Shot list for replacing synthetic photos and voices with real ones, and for filming the stage case. |
| `keepwell_example_queries.sql` | 24 reference queries, each run against the seeded database. |
| `gen/` | The generator. `python3 gen/build.py out/` rebuilds everything byte for byte (seed 20261120). Voice needs the Piper Telugu and Kokoro Hindi/English models, which are not included (paths at the top of `gen/inbox.py`). `SKIP_INBOX=1` builds tables only. |

## The world at a glance

- 9 service centres (5 brand-authorised, 1 mixed, 2 independent, 1 installation-only), 37 technicians, 8 parts centres, 144 parts, 7 brands, 5 retailers. Each centre has one voice line and one WhatsApp number and its own price list (696 rows) and commercial terms.
- 165 households, 297 members, 341 appliances across five categories (AC, refrigerator, washing machine, RO purifier, geyser). 57 households are linked to more than one centre, which is what makes cross-centre history and consent testable.
- 395 historical and in-flight tickets: 250 household messages, 110 household calls, 28 brand-forwarded, 7 retailer handovers. 26 are in flight, booked for 22 to 25 Nov. Another 14 brand requests were declined at the authority check.
- 118 self-fix attempts from the 14 catalogue entries (12 active, 1 past review, 1 retired): 48 worked, 59 did not, 10 were abandoned, 1 stopped for safety. 48 tickets closed without a visit, each by OTP.
- 12 urgency rules (4 safety, 5 urgent, 1 standard, 2 planned) and 369 recorded urgency assessments, 9 of them reclassifications from the centre console.
- Past repairs follow a full lifecycle: estimate, firm quote, payer split, settlement, rating, appliance events, OTP closure. About 70 percent of repairs are fixed on the first visit, 41 of 158 firm quotes ran more than 10 percent over estimate, and average rating is 4.3.
- 829 stock rows across parts centres, centres and vans. Recorded quantity differs from true quantity in proportion to each location's accuracy; the truth is in `evaluator_only/true_stock.csv`.
- 674 experience cases with `embedding` left NULL. 993 consent rows with effective dates, scopes and withdrawals.
- Messy on purpose: some appliances have no model or purchase date, some consents are withdrawn, some members cannot raise tickets, 16 percent of appliances sit in a pincode no centre serves for that brand and category.

## The 20 incoming cases (inputs only)

| Trigger | Case | Centre | What arrives |
|---|---|---|---|
| Household message | C01 | Aerovane, Gachibowli | Telugu voice note, leak photo, sticker photo |
| | C02 | Aerovane, Gachibowli | Text with a display photo showing an error code |
| | C04 | AquaCare, Manikonda | Telugu-English text about RO water quality and a TDS meter photo |
| | C06 | Lakeshore, Jubilee Hills | Telugu-English text and a photo of a frosted freezer |
| | C08 | Cool Craft, Madhapur | Hindi reply to yesterday's reminder; three appliances to service; the AMC provider has changed |
| | C09 | Zenith Care Hub, Kondapur | Tenant on a new number, blurry rating-plate photo |
| | C10 | Frost and Wave, Kukatpally | New number, one line only |
| | C13 | Cool Craft, Madhapur | Telugu-English text about a washer lid and a very blurry sticker photo |
| | C14 | Cool Craft, Madhapur | Hindi text about two appliances; the household has not consented to share technical history |
| Household call | C03 | Frost and Wave, Kukatpally | Hindi call: washer shows E21, warranty just ended. **Best case for the stage prototype**: video switch, drain-filter fix that fails, re-run |
| | C05 | Heatwell, Banjara Hills | Hindi call: mild shock from the geyser tap; a safety case that skips both gates |
| | C11 | Cool Craft, Madhapur | English call from outside every centre's service area |
| | C12 | Lakeshore, Jubilee Hills | Telugu call: the same washer problem again after a repair |
| | C15 | Lakeshore, Jubilee Hills | Hindi call: burning smell and smoke from a washer motor; a safety case |
| | C16 | Aerovane, Gachibowli | Telugu call over traffic; household declines the self-fix |
| Brand forward | C17 | Zenith Care Hub, Kondapur | Zenith call-centre case: fridge freezer frosted, dF code |
| | C18 | Cool Craft, Madhapur | Aerovane forwards a warranty AC to an independent centre: authority fails |
| | C19 | AquaCare, Manikonda | Heatwell forwards a geyser case; the household's history sits at another centre and sharing is consented |
| Retailer handover | C07 | Zenith Care Hub, Kondapur | Digital Plaza hands over an AC installation with invoice and carton photos and a location pin |
| | C20 | Frost and Wave, Kukatpally | A washer installation; the retailer used a phone that matches a member of an existing household |

What each case should lead to, gate by gate, is in `evaluator_only/CASE_GUIDE.md`. `evaluator_only/personas/` tells whoever plays the household how to answer.

## How to use it

1. Apply the schema, then `load.sql`. Callers are found by `phone_hash` (HMAC-SHA256 of the number with the dev key in `gen/common.py`; `phone_enc` uses a dev-only Fernet key). Replace both with KMS in a real deployment.
2. Connect as role `kw_app` and `SET kw.centre_id = '<centre uuid>'` for the centre whose line is answering. Use `SET kw.role = 'platform'` only for batch jobs.
3. Run the two scripts in `scripts/` to fill embeddings and the File Search store.
4. Feed `inbox/inbox.json` events to the app one case at a time in timestamp order. A call event carries the dialled line, the caller number and a recording. The app creates the ticket, runs the gates, writes `fix_attempt`, `visit_plan`, `assignment_candidate` and `slot_proposal`, and closes by OTP. Compare with `evaluator_only/`.

## Known limits

- Photos are synthetic renders with real camera defects. They test the pipeline, not a vision model's real-world robustness.
- Calls and voice notes are synthesised speech degraded to phone quality. I could not listen to them. They are cleaner than real speakers, and each language is a single synthetic voice. Treat transcription accuracy on them as optimistic. Call recordings run 11 to 16 seconds.
- Video is not included. C03 is a call; the video session is the app's job, and `CAPTURE_KIT.md` says how to film the real one.
- The KB PDFs are 2 to 3 pages each, far shorter than real manuals. Retrieval will look easier than it will in practice.
- The safe-fix steps are drafted from the fictional manuals in this dataset. The named reviewers are fictional. Real fixes need a real reviewer and the real manual page.
- Technician metrics are sparse (the pilot is young), so first-time-fix rates swing widely. That is realistic and also a test of how ranking handles thin data.
- Only five appliance categories are seeded. Phones and other electronics are an open scope question in the design document.
- I tested the schema, load and queries on Postgres 16 with `point` standing in for PostGIS geography and `real[]` for pgvector. The geography and vector paths of the queries, and both scripts, have not been run on the real extensions.
- The seed has no rows in the app-output tables (`visit_plan`, `plan_hypothesis`, `plan_part`, `assignment_candidate`, `slot_proposal`, `visit_media`, `access_log`, `identity_merge`) by design.
