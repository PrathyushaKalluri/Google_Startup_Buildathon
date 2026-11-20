# KeepWell — Google Startup Buildathon

Monorepo for our Google DeepMind & Google Cloud Startup Buildathon (India 2026) entry. Three apps plus the research and pitch material.

| Folder | What it is | Stack | Port |
|---|---|---|---|
| `keepwell/` | Main backend: AI repair desk + Home Memory | Python, FastAPI, SQLite, Gemini | 8000 |
| `circuit_app/` | Round 3 simulation (Gnani STT + one LLM making decisions) | Python, Claude or Gemini | 8000 |
| `GharSaathi/` | Clickable household-maintenance prototype | React, TypeScript, Vite, Tailwind | 5173 |

Docs at the root (`Keepwell *.md`, pitch decks, `research_notes/`, `spec_parts/`, `reports/`) are reference material, not code.

`keepwell/` and `circuit_app/` both use port 8000, so don't run them at the same time.

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm (only for `GharSaathi`)
- Git
- API keys (ask the owner; never commit them or paste them in chat):
  - `GEMINI_API_KEY` for `keepwell/` (and `circuit_app/` if using Gemini)
  - `ANTHROPIC_API_KEY` for `circuit_app/` if using Claude
  - `GNANI_STT_API_KEY` for `circuit_app/`

## Get the code

```bash
git clone https://github.com/PrathyushaKalluri/Google_Startup_Buildathon.git
cd Google_Startup_Buildathon
```

## 1. keepwell (main backend)

```bash
cd keepwell
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env
```

In `.env`, set at least `GEMINI_API_KEY`. WhatsApp (`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`) is optional and only needed to test the live webhook. Payments run in sandbox mode (`UPI_SANDBOX_MODE=true`) by default.

Run it:

```bash
python3 run.py                     # or: make dev
```

Open http://localhost:8000.

Other commands (`make help` lists them):

```bash
make seed      # repopulate the DB from fixtures
make test      # pytest
make eval      # 100-case evaluation harness
make clean     # delete keepwell.db and caches
```

**About `keepwell.db`:** a seeded SQLite file is committed so everyone starts with the same demo data. If it causes merge conflicts, delete it (`make clean`) and run `make seed`. Don't commit local changes to it.

## 2. circuit_app (Round 3 simulation)

```bash
cd circuit_app
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env
```

In `.env`:

- `LLM_PROVIDER=claude` or `gemini`, plus the matching API key
- `GNANI_STT_API_KEY` — use the **new** key; the old one was shared in chat and must be revoked
- `LLM_MODEL` — run the check below and copy a model id it lists

Verify before recording:

```bash
python check_setup.py                    # lists models your key can use
python check_setup.py my_test_clip.ogg   # also makes one real Gnani call (uses 1 credit)
```

Run it:

```bash
python run.py                      # http://localhost:8000
python -m pytest -q                # 11 offline tests, no keys needed
```

Also see `circuit_app/README.md` and `circuit_app/TEAM_PLAN_START_HERE.md` for the recording flow and role assignments. Still to do before recording:

- Add 1–3 real AC troubleshooting excerpts to `circuit_app/knowledge/` (it only has a generic seed).
- Keep the real sample JSON responses from the Pine Labs and Delhivery docs in a notes file for the "wizard" to paste.
- Have a 15–30 s voice note (Telugu, Hindi or English) ready.

## 3. GharSaathi (frontend prototype)

```bash
cd GharSaathi
npm install
npm run dev                        # http://localhost:5173
npm run build                      # typecheck + production build
```

No API keys needed.

## What is NOT in git (set up locally)

- `.env` files — copy from each folder's `.env.example`
- `.venv/` — create per the steps above
- `node_modules/`, `GharSaathi/dist/` — from `npm install` / `npm run build`
- `keepwell/storage/` — local media uploads, created at runtime

## Working together

- Pull before you start: `git pull --rebase origin main`
- Never commit `.env`, API keys or tokens. `.gitignore` already excludes them.
- Commit small and push often to avoid conflicts, especially on the same files.
