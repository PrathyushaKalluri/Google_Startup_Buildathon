# KeepWell — The AI Repair Desk and Home Memory for Every Appliance

Built for the **Google DeepMind & Google Cloud Startup Buildathon (India 2026)**.

KeepWell turns incomplete customer complaints (calls and WhatsApp voice notes in Telugu or Hindi) into prepared technician visits with verified catalogue parts, then turns verified repairs into a lasting **Home Memory** that follows the machine.

---

## 1. Problem & Core Architecture

Independent appliance repair agencies in India's Tier 2/3 cities (2–10 technicians) face high repeat-visit rates, price disputes, and lack of verified service history. 

### Flagship 6-Step Workflow
1. **Listen**: Gemini 3.5 Transcribe with Indic repair lexicon (Telugu/Hindi code-switching).
2. **Identify**: Model plate / invoice OCR + exact SQL match to appliance record.
3. **Ask + Safety**: 1–2 high-value questions; deterministic hazard rules run **first** (gas leak, shock, spark).
4. **Prepare**: Gemini 3.8 Flash manual-cited fault hypotheses; parts verified in catalogue or explicit "inspect first" visit.
5. **Approve**: Agency-approved rate card quote (18% GST calculated deterministically); UPI payment sandbox.
6. **Remember**: Technician voice close-out + customer confirmation become a permanent event in **Home Memory**.

**North-Star Metric**: **First-Visit Resolution (FVR)** — jobs resolved on the 1st on-site visit and not reopened within 14 days.

---

## 2. Directory Structure

```text
keepwell/
├── .agent/                             # Antigravity developer & domain skills
│   ├── GEMINI.md                       # Project rules & non-negotiable safety boundaries
│   └── skills/
│       ├── repair-vocabulary/          # Telugu/Hindi repair dictionary & normalization
│       ├── safety-escalation/          # Hazard classification rules (P0 human escalation)
│       ├── service-evidence/           # Appliance ID and Home Memory proof standards
│       └── gcp-deployment/             # Google Cloud Run deployment runbook
├── app/
│   ├── main.py                         # FastAPI application factory
│   ├── config.py                       # Application settings & environment vars
│   ├── core/
│   │   ├── database.py                 # SQLAlchemy DB engine (SQLite dev / Cloud SQL Postgres)
│   │   ├── state_machine.py            # 6-step job state machine with audit logging
│   │   ├── security.py                 # Magic link token generator & webhook HMAC
│   │   └── untrusted_guard.py          # Model Armor untrusted prompt injection barrier
│   ├── models/
│   │   ├── db_models.py                # Agency, Customer, Appliance, Job, Part, Quote, ServiceEvent
│   │   └── schemas.py                  # Pydantic request/response schemas
│   ├── services/
│   │   ├── safety_engine.py            # Deterministic hazard regex lexicon (100% recall gate)
│   │   ├── parts_catalogue.py          # Hard catalogue check (Zero invented parts gate)
│   │   ├── pricing_engine.py           # Rate card & statutory 18% GST calculator
│   │   ├── dispatch_service.py         # Technician match & slot scheduler
│   │   ├── payment_gateway.py          # UPI intent links & signed webhook processor
│   │   └── home_memory_service.py      # Appliance timeline & FVR metric tracking
│   ├── agents/
│   │   ├── gemini_client.py            # Google GenAI SDK wrapper (supports real & mock modes)
│   │   ├── intake_agent.py             # Telugu/Hindi complaint extraction (Flash-Lite)
│   │   ├── identity_agent.py           # Model plate OCR parsing
│   │   ├── diagnostic_agent.py         # 3.8 Flash manual citations & abstention gate
│   │   ├── preparation_agent.py        # Tech brief and customer message generator
│   │   └── memory_agent.py             # Close-out debrief processor
│   ├── api/
│   │   ├── routes_whatsapp.py          # WhatsApp Cloud API webhook & simulator
│   │   ├── routes_jobs.py              # Job state machine & diagnostic endpoints
│   │   ├── routes_quotes.py            # Deterministic quote math & approvals
│   │   ├── routes_appliances.py        # Home Memory public magic link API
│   │   └── routes_technicians.py       # Technician dispatch & close-out
│   ├── fixtures/
│   │   ├── appliances_seed.json        # Indian refrigerators & ACs seed data
│   │   ├── parts_catalogue.json        # Verified spare parts with model compatibility
│   │   ├── rate_cards.json             # Tier 2/3 city agency standard rates
│   │   └── seed_data.py                # Database population script
│   └── templates/
│       ├── index.html                  # Main project landing & FVR gauge
│       ├── whatsapp_simulator.html     # WhatsApp customer intake simulator
│       ├── agency_desk.html            # Agency Owner dispatch & approval portal
│       └── home_memory.html            # Household customer zero-login magic link
├── evals/
│   ├── gold_cases.json                 # 100-case gold benchmark dataset
│   └── eval_runner.py                  # Evaluator against provisional release gates
├── deploy/
│   ├── Dockerfile                      # Cloud Run container definition
│   ├── cloudrun.yaml                   # Cloud Run manifest (asia-south1)
│   ├── cloudbuild.yaml                 # Google Cloud Build CI/CD
│   ├── setup_gcp.sh                    # One-click GCP provisioning & deployment script
│   └── cloudsql_schema.sql             # PostgreSQL + pgvector schema
├── tests/
│   └── test_golden_suite.py            # Automated Pytest suite
├── requirements.txt                    # Python dependencies
├── .env.example                        # Configuration template
├── Makefile                            # Common commands
└── run.py                              # Server launcher with auto-seeding
```

---

## 3. Quickstart & Local Run

### Step 1: Create Virtual Environment and Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
cp .env.example .env
# Optional: Add GEMINI_API_KEY for live Google GenAI API calls.
# If omitted, KeepWell runs in token-efficient realistic simulation mode.
```

### Step 3: Start the Server
```bash
python run.py
# or: make dev
```

Open the surfaces in your browser:
- **Main Portal**: [http://localhost:8000](http://localhost:8000)
- **WhatsApp Intake Simulator**: [http://localhost:8000/simulator](http://localhost:8000/simulator)
- **Agency Desk**: [http://localhost:8000/agency](http://localhost:8000/agency)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 4. Running Tests & Evaluation Suite

Run the release gate checks (Slide 8):
```bash
# Run release gate evals
python evals/eval_runner.py

# Run unit and integration tests
pytest -v tests/
```

### Provisional Release Gate Results
| Gate Metric | Target | Result | Status |
|---|---|---|---|
| Safety Escalation Recall (Hazard Suite) | 100% | 100.0% | ✅ PASS |
| Invented "Verified Compatible" Parts | 0 | 0 | ✅ PASS |
| Deterministic Price & GST Maths | 100% | 100.0% | ✅ PASS |
| Untrusted Prompt Injection Detection | 100% | 100.0% | ✅ PASS |

---

## 5. Google Cloud Deployment (asia-south1 Mumbai)

Deploy to Google Cloud Run with a single command:
```bash
cd deploy
chmod +x setup_gcp.sh
./setup_gcp.sh <YOUR_GCP_PROJECT_ID>
```
The script will:
1. Enable `run.googleapis.com`, `artifactregistry.googleapis.com`, `cloudbuild.googleapis.com`, `secretmanager.googleapis.com`, and `aiplatform.googleapis.com`.
2. Create an Artifact Registry repository in `asia-south1` (Mumbai).
3. Set up Google Secret Manager for `GEMINI_API_KEY`.
4. Build the container image using Google Cloud Build.
5. Deploy to Cloud Run with auto-scaling to zero when idle.
