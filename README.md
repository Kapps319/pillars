# AI Intent Lead Finder

A general-purpose lead-finding web app: it scans **public** web/social sources for
posts showing real buy/sell intent for *any* product, classifies each post as
**BUY / SELL / MENTION / SPAM** with a confidence score and human-readable
reasons, extracts product/price/date/location, and surfaces everything in a SaaS
dashboard with filters, lead statuses and CSV export.

> - “F1 tickets are so expensive” → **MENTION** (low score)
> - “Looking for 2 Abu Dhabi GP tickets, ready to buy today, DM me” → **BUY** (high score)
> - “Selling 3 CAT1 World Cup tickets” → **SELL** (high score)

Plug in any product/market — F1 tickets, laptops, cars, apartments, watches,
concerts, appointments.

*(Note: this repository also contains an unrelated “Pillars” PWA at the root —
`index.html`, `app.js`, etc. The lead finder lives in `backend/`, `frontend/`
and the infra files.)*

## Quick start (zero API keys needed)

```bash
cp .env.example .env      # optional — compose works with the example defaults
docker compose up --build
```

Then open **http://localhost:3000** and sign in with the seeded demo account:

| | |
|---|---|
| Email | `demo@leadfinder.app` |
| Password | `demo12345` |

You'll see a seeded campaign (“Ticket intent radar”) with ~30 classified sample
leads — filter them, open a lead drawer to read the classification reasons and
extracted fields, change statuses, export CSV, or create your own campaign and
hit **Run now**. API docs live at **http://localhost:8000/docs**.

Everything runs keyless by default: the **mock source** (local JSON fixtures)
plus the **rules-only classifier**. Adding real keys activates live sources and
the LLM with **no code changes** (see below).

## Architecture

```
Next.js (App Router, TS, Tailwind, TanStack Query)
        │ JWT (access + refresh)
FastAPI /api/v1 ──► PostgreSQL (FTS) ── Alembic migrations
        │ run-campaign → ScrapingJob
        ├─ Celery worker (Redis broker) — with an automatic in-process
        │  fallback so everything works without the worker
        └─ SourceRegistry → SourceAdapter
             mock · reddit · google (CSE) · manual_url (robots.txt-aware)
             twitter (built, disabled) · instagram/facebook/linkedin (ToS stubs)
                     │ RawPost
             3-stage classifier
               1. rules filter          (config/keywords.yml)
               2. LLMClient             (rules | claude | openai)
               3. extraction + scoring  (config/weights.yml)
```

### Data sources — what's real and why

| Source | Status | Notes |
|---|---|---|
| Mock/sample | ✅ live, default ON | ~30 realistic fixture posts; powers the first-boot demo |
| Reddit | ✅ live | official API, OAuth “script” app, free tier |
| Google web search | ✅ live | Custom Search JSON API, 100 free queries/day |
| Manual URL | ✅ live | robots.txt-aware, rate-limited public-page scraper |
| X/Twitter | 🔌 built, disabled | paid API; set `TWITTER_BEARER` + add `twitter` to `SOURCES_ENABLED` |
| Instagram / Facebook | 🚫 stub | Graph API only reaches accounts you own — no public keyword search exists |
| LinkedIn | 🚫 stub | no public post-search API; scraping violates its User Agreement |

The stubs raise `NotImplementedError` with an explanation: the architecture is
ready, but we ship nothing that violates a platform's ToS. Public data and
official APIs only; robots.txt and rate limits respected.

### The classifier

1. **Rules filter** — regex/keyword signals (strong buy/sell phrases, spam
   markers, urgency, contactability) from `backend/app/config/keywords.yml`.
2. **LLM classifier** — `LLMClient` interface with three implementations:
   `RulesOnlyClient` (default, keyless), `ClaudeClient` (Anthropic),
   `OpenAIClient`. Strict JSON output validated with Pydantic, one retry on
   malformed output, graceful fallback to rules on any failure. Select with
   `LLM_PROVIDER=rules|claude|openai`.
3. **Scoring + extraction** — deterministic price/date/location/product
   extraction plus a weighted lead score (`backend/app/config/weights.yml`):
   strong keywords, product/location/date match, price mention, urgency,
   contactability, spam penalty, recency. Every lead carries its “reason why”.

Prompts and keyword lists are config files, so another language (e.g. Arabic)
is `keywords.ar.yml` + `prompts/classify_ar.yml` — no code changes.

## Activating live sources & the LLM

Edit `.env` (or add keys in the UI under **Integrations**) and restart:

```bash
# Reddit (free): create a “script” app at reddit.com/prefs/apps
REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=... REDDIT_USER_AGENT="leadfinder by u/you"

# Google (free tier): Custom Search JSON API + Programmable Search Engine
GOOGLE_API_KEY=... GOOGLE_CSE_ID=...

# LLM classification via Claude
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

Missing/invalid keys are logged and that source/feature is skipped — the app
never crashes because of a key.

## Local development (without Docker)

```bash
# Backend (Python 3.12)
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://leadfinder:leadfinder@localhost:5432/leadfinder
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload            # http://localhost:8000/docs

# Frontend (Node 20+)
cd frontend
npm install
npm run dev                              # http://localhost:3000

# Tests (37 tests incl. golden classifier cases; run on SQLite, no services needed)
cd backend && python -m pytest tests -q
```

## Environment variables

Every variable is documented inline in [`.env.example`](.env.example). Highlights:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` / `REDIS_URL` | Postgres + Redis connections |
| `SECRET_KEY` | JWT signing + encryption key for stored integration secrets |
| `LLM_PROVIDER` | `rules` (default, keyless) \| `claude` \| `openai` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | LLM classifier keys |
| `REDDIT_CLIENT_ID/SECRET/USER_AGENT` | Reddit source |
| `GOOGLE_API_KEY` / `GOOGLE_CSE_ID` | Google web search source |
| `TWITTER_BEARER` | X source (disabled by default) |
| `SOURCES_ENABLED` | Comma list of active source adapters |
| `SEARCH_BACKEND` | `postgres` (default) \| `elasticsearch` (flag reserved) |
| `CELERY_ENABLED` | `false` forces the in-process job fallback |
| `SEED_ON_STARTUP` | Seed demo user/campaign/leads on boot |

## Project layout

```
backend/
  app/api/v1/        auth, campaigns, leads, sources, jobs, integrations, admin, health
  app/classifier/    rules.py · llm/ (base, rules, claude, openai, factory) · scoring · pipeline
  app/config/        keywords.yml · weights.yml · prompts/classify_en.yml
  app/models/        SQLAlchemy models  ·  app/schemas/  Pydantic v2 schemas
  app/services/      scraping job runner (celery + sync fallback), lead queries, CSV
  app/sources/       SourceAdapter + registry + adapters
  alembic/           migrations (initial schema, verified against Postgres 16)
  data/fixtures/     sample_posts.json (~30 posts)
  tests/             pytest suite incl. golden classifier tests
frontend/
  app/               login/register · dashboard · campaigns · leads · settings · integrations
  components/        UI kit, charts, leads table + drawer
  lib/               typed API client with token refresh
docs/                DEPLOY.md · ADDING_A_SOURCE.md
```

## More docs

- [docs/DEPLOY.md](docs/DEPLOY.md) — AWS (ECS/Fargate + RDS + ElastiCache) and
  GCP (Cloud Run + Cloud SQL + Memorystore) deployment guides
- [docs/ADDING_A_SOURCE.md](docs/ADDING_A_SOURCE.md) — implement a new
  `SourceAdapter` in ~30 lines

## Security notes

- Passwords are bcrypt-hashed; JWT access (30 min) + refresh (7 days) tokens.
- Integration API keys are Fernet-encrypted at rest (key derived from
  `SECRET_KEY`) and only ever returned masked.
- The demo credentials are for local demos only — disable `SEED_ON_STARTUP`
  and change `SECRET_KEY` before deploying anywhere public.
