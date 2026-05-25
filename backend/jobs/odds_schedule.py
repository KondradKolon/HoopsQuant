"""
Scheduled entry points for odds jobs.

APScheduler must call these wrappers — do not pass frozen datetime kwargs into
add_job(), or every run will use the date from server startup.
"""

import logging
from datetime import datetime, timedelta

from jobs.odds_fetcher import run_odds_pipeline
from jobs.fetch_current_odds import fetch_and_store as fetch_current_odds

logger = logging.getLogger("odds_schedule")

# How far back / forward to pull NBA events on the 2-hour pipeline job
ODDS_PIPELINE_PAST_DAYS = 2
ODDS_PIPELINE_FUTURE_DAYS = 21
ODDS_PIPELINE_MAX_GAMES = 120


def scheduled_nba_odds_pipeline() -> None:
    """Fetch NBA odds for a rolling date window (recomputed each run)."""
    now = datetime.utcnow()
    start = (now - timedelta(days=ODDS_PIPELINE_PAST_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    end = (now + timedelta(days=ODDS_PIPELINE_FUTURE_DAYS)).strftime("%Y-%m-%dT23:59:59Z")
    logger.info("Scheduled NBA odds pipeline: %s → %s", start[:10], end[:10])
    run_odds_pipeline(
        start_iso=start,
        end_iso=end,
        max_games=ODDS_PIPELINE_MAX_GAMES,
        sleep_sec=0.35,
        refresh_existing=True,
    )


def scheduled_current_odds() -> None:
    """Hourly live/upcoming odds via /odds/multi."""
    fetch_current_odds()
