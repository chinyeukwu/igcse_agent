# Agentic AI Tutor (IGCSE)

An adaptive learning platform for Pearson Edexcel IGCSE students. A FastAPI
backend serves AI‑generated quizzes, a chat tutor, progress analytics, and an
admin panel, backed by SQLite. Quizzes are generated and essays evaluated with
Anthropic Claude; quiz questions are modelled on real Pearson past papers.

## Features

- **AI quiz generation** — structured multiple‑choice questions per subject and
  difficulty, styled on authentic Pearson IGCSE questions.
- **Real scoring & history** — quizzes are graded and persisted; the dashboard
  shows genuine progress, analytics, and weak‑topic focus areas.
- **Chat tutor** — ask subject questions via the chat interface.
- **Essay evaluation** — rubric‑based scoring with Claude.
- **Admin panel** — user management and system statistics.
- **Notifications (optional)** — email/SMS reminders and a background scheduler.

## Tech stack

FastAPI · SQLAlchemy + SQLite · Anthropic Claude (`claude-opus-4-8`) ·
custom HTML/CSS/JS frontend (served from `src/frontend/`).

## Prerequisites

- Python 3.11+
- An `ANTHROPIC_API_KEY` (for live quiz generation / essay evaluation; the app
  falls back to sample questions if the API is unavailable)

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit .env and set ANTHROPIC_API_KEY
```

Configuration is read from environment variables; a local `.env` file is loaded
automatically (see `.env.example` for all options). `.env` is gitignored — never
commit real secrets.

## Running

```bash
# Windows helper script:
./run_backend.ps1
# or directly:
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Then open:

- `/` — chat tutor
- `/login` — sign in / create an account
- `/quiz` — take a quiz
- `/dashboard` — progress & analytics
- `/profile` — account settings
- `/admin` — admin panel (admin role required)
- `/docs` — API docs

The first account you create is a normal student. Grant admin via the database
(`users.role = 'admin'`) if you need the admin panel.

## Pearson question extraction (optional, improves quiz quality)

The quiz generator can few‑shot on real Pearson exam questions. To populate them:

```bash
# Point at the folder of Pearson PDFs (or set PEARSON_PAPERS_DIR in .env)
python -m scripts.extract_pearson --papers-dir "/path/to/pearson papers"
# regex-only (no Claude calls):
python -m scripts.extract_pearson --no-llm
```

This writes `PaperQuestion` rows and a `data/pearson_questions.json` cache that
the generator loads at runtime. Re‑running is idempotent.

## Tests

Script‑style checks live in `tests/` and are run directly (they add the repo
root to `sys.path`, so run them from the repo root):

```bash
python tests/test_phase1.py       # auth
python tests/test_phase2.py       # security / validation
python tests/test_phase3.py       # offline / cache
python tests/test_phase4.py       # quiz persistence
python tests/test_phase5.py       # admin
python tests/test_admin_tabs.py   # admin analytics + question bank
```

These run automatically on push via `.github/workflows/ci.yml`. The email tests
(`tests/test_email_*.py`) need live SMTP credentials and are excluded from CI.
Project documentation lives in `docs/`.

## Notes & known follow‑ups

- **Storage:** SQLite (single file at `data/igcse_tutor.db`). A Postgres/Supabase
  migration is a future step, not required for local use.
- **Notifications** are off by default. Set SMTP vars and
  `ENABLE_NOTIFICATION_SCHEDULER=true` to enable the daily/weekly jobs
  (`apscheduler` required; `twilio` optional for SMS).
- **Deployment** (Docker/CI/hosting) is intentionally out of scope of the current
  build; the app is run locally as above.
