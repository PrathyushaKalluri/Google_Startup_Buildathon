# Fourth rail: Machine Kundli + Mistri Gyan

## 1. Machine Kundli — per-machine truth

Structured, consent-scoped:
- machine ID;
- make/model;
- serial hash;
- owner/consent reference;
- warranty status + evidence;
- previous service events;
- fitted parts;
- functional tests;
- later outcomes.

A new demo case generally starts without a trusted Kundli history.

## 2. Mistri Gyan — reusable repair intelligence

Contains reviewed:
- permitted manufacturer troubleshooting/manual passages;
- regional symptom vocabulary;
- model applicability;
- error-code meaning;
- safe discriminating tests;
- verified fault relationships;
- reviewed part-compatibility evidence;
- anonymized verified outcomes;
- limitations/conflicts.

### RAG

Initial retrieval can use SQLite FTS5.

Every chunk requires:
`source_id`, URL/file, rights, capture/review time, publisher, appliance, brand, model scope, section, text, evidence tier and safety class.

A URL pointer is not an indexed document.

Generic AC guidance can justify questions such as:
- Is the unit set to Cool?
- Is airflow weak or normal?
- Is an error code visible?
- Can you send the model label?

It cannot justify:
- “PCB is definitely failed.”
- an exact replacement SKU;
- a statistical probability not calibrated from real data.

## 3. Agency operational data

Separate tables:
- technicians;
- skills;
- shifts;
- offered slots;
- actual agency assignment;
- current stock/hold;
- compatible SKU source;
- price book;
- service area;
- policies.

RAG prose never proves current stock or technician availability.

## 4. Learning loop

Prediction
→ field observation
→ work performed
→ functional proof
→ customer later recurrence
→ S10 correction
→ S11 review queue
→ only reviewed, appropriately sourced knowledge enters Mistri Gyan.

Role-play/synthetic cases do not auto-promote into verified repair history.
