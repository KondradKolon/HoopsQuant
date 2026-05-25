# Odds ingestion pipeline

## Schedule (UTC, when Railway API is running)

| Job | Cadence | What it does |
|-----|---------|----------------|
| **Current NBA odds** | Every hour at **:05** | `fetch_current_odds` — `/events?league=usa-nba` + `/odds/multi` (10 events per call) |
| **NBA odds pipeline** | Every **2 hours** at **:15** | `run_odds_pipeline` — rolling window (2 days back → 21 days ahead), refreshes existing lines |
| **Odds history** | Every **30 min** | Copies current `odds` rows → `odds_history` for upcoming games |
| **Predictions** | Every **6 hours** | ML predictions (not odds) |
| **NBA box scores** | Daily **03:00** | `nba_fetcher_2026` |

On deploy, a **background initial seed** runs once: current odds + 2h pipeline + predictions + history track.

## Environment (Railway)

```env
ODDS_API_KEY=...
BOOKMAKERS=Superbet,Stake
```

- **Bookmakers:** Your odds-api.io account allows **2 active** bookmakers at a time (swap via their dashboard every 12h if needed). Names must match API exactly — check `GET /bookmakers/selected`.
- **Not** every 6 hours for odds — that interval is **predictions only**.

## Verify production

```bash
curl https://hoopsquant-production.up.railway.app/api/v1/odds/status
```

Look for:

- `odds_api_key_set: true`
- `configured_bookmakers` matches Railway env
- `upcoming_with_any_odds` close to `upcoming_games`
- `coverage_pct` near 100% during NBA season

Local DB check:

```bash
cd backend
python tests/verify_odds.py --start 2026-05-01 --end 2026-05-31
```

Manual fetch (uses `.env`):

```bash
cd backend
python -m jobs.fetch_current_odds
python -c "from jobs.odds_schedule import scheduled_nba_odds_pipeline; scheduled_nba_odds_pipeline()"
```

Bulk historical backfill (run on Railway where `DATABASE_URL` points to Supabase):

```bash
python scripts/seed_odds_to_supabase.py
```

## Common issues

1. **`BOOKMAKERS` empty or wrong names** → API returns no markets; status shows 0 odds.
2. **`ODDS_API_KEY` missing on Railway** → all jobs no-op; status shows `odds_api_key_set: false`.
3. **Scheduler only runs while the API process is up** — if Railway sleeps the service, jobs pause until next request/wake.
4. **Arbitrage needs ≥2 bookmakers** per game with stored ML — set two bookmakers in `BOOKMAKERS` that both post NBA moneylines.

## Fixed bugs (2026-05)

- Scheduler was passing **frozen “today” dates** from server startup → pipeline only ever queried one day.
- Pipeline **skipped games** when all bookmakers existed → lines never updated.
- Hourly fetch used **all basketball** events, not `league=usa-nba`.
- `/odds/multi` without `bookmakers` param → silent 400 (documented in code comments).
