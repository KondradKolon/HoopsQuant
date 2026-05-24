# HoopsQuant

End-to-end NBA betting analytics platform: ingest historical and live NBA data, train probabilistic win-prediction models, surface Elo ratings, scan cross-bookmaker arbitrage, and let users track their own picks.

**Live:** <https://hoops-quant.vercel.app>
**API:** <https://hoopsquant-production.up.railway.app/api/v1/health>

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind, Recharts |
| Backend | FastAPI, SQLAlchemy 2, APScheduler |
| ML | scikit-learn (LogisticRegression + Platt calibration), XGBoost, pandas |
| Database | PostgreSQL (Supabase in prod, Postgres 15 locally) |
| Auth | Supabase Auth (Google / GitHub OAuth) |
| Hosting | Vercel (frontend) · Railway (backend) · Supabase (DB) |

---

## Features

- **Today's Picks** dashboard with model win probabilities, Expected Value, Kelly stake sizing and a five-tier bet rating (ELITE → PASS)
- **Elo Rankings** by conference with per-team trend charts and Elo-based upcoming-game probabilities
- **Arbitrage Scanner** (cross-bookmaker, requires ≥2 books per game — see known issues)
- **My Picks** — placed bet history with win rate and ROI
- **Auth** via Supabase OAuth + guest demo mode
- **Background jobs** (APScheduler): NBA games fetch, odds fetch, prediction generation

---

## Run locally

```bash
# 1. Database (optional — defaults connect to local Postgres on 5432)
docker compose up -d db

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, ODDS_API_KEY, etc.
python main.py         # serves on :8000

# 3. Frontend
cd ../frontend
npm install
cp .env.example .env.local   # fill NEXT_PUBLIC_SUPABASE_* and NEXT_PUBLIC_API_URL
npm run dev                  # serves on :3000
```

---

## Tests

Backend uses **pytest** with an in-memory SQLite fixture for fast integration tests:

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

CI runs ruff + pytest on every push to `main` (see `.github/workflows/ci.yml`).
~50 unit/integration tests cover API routes, prediction services, and Elo helpers.

---

## Deployment

| Service | Required env vars |
|---------|------------------|
| Vercel (frontend) | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| Railway (backend) | `DATABASE_URL`, `ALLOWED_ORIGINS`, `ODDS_API_KEY`, optional `SUPABASE_*` |

`NEXT_PUBLIC_*` variables are inlined at build time — change them in the Vercel dashboard and trigger a redeploy, not just a restart.

---

## Known issues

- **Two-pipeline odds ingestion** (`jobs/odds_fetcher.py` + `jobs/fetch_current_odds.py`) can produce duplicate `Game` rows under different synthetic `game_id` values. Consolidation is tracked in `REFACTOR_PLAN.md`.
- **JWT signature verification is disabled** in `app/middleware.py` (decode-only) for MVP. Replace with Supabase JWKS verification before any real public launch.
- **Odds coverage depends on bookmaker schedule.** The account is limited to Superbet + Stake; some upcoming games won't have lines yet until ~24h before tip-off. The UI shows "Odds unavailable" in that case.

---

## Repo layout

```
backend/
  app/            FastAPI app, routes, models, ML services
  jobs/           Scheduled fetchers (NBA stats, odds), scheduler
  scripts/        One-off training / seeding scripts
  tests/          pytest suite (unit + integration)
frontend/
  app/            Next.js App Router pages
  components/     Shared UI (TeamLogo, InfoIcon, ...)
  lib/            API client (with light response cache), team metadata, Supabase client
```
