"""get_odds_fetch_range.py

Computes an incremental [start, end] window for odds fetching.

It looks at the latest game_date for which we have at least one odds row,
backs up by a small buffer, then moves forward N days.

Outputs ONLY:
  START_ISO=...Z
  END_ISO=...Z

Examples:
  python3 get_odds_fetch_range.py --days 3
  python3 get_odds_fetch_range.py --days 7 --buffer-days 1 --fallback-start 2026-01-01
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

from sqlalchemy import func

from src.db.database.database import SessionLocal
from src.db.database.models import Game, Odds


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _as_start_iso(d: date) -> str:
    return f"{d.isoformat()}T00:00:00Z"


def _as_end_iso(d: date) -> str:
    return f"{d.isoformat()}T23:59:59Z"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute incremental odds fetch range")
    parser.add_argument("--days", type=int, default=3, help="How many days forward to fetch")
    parser.add_argument("--buffer-days", type=int, default=1, help="Days to subtract from last-odds date")
    parser.add_argument(
        "--fallback-start",
        default=None,
        help="YYYY-MM-DD to use when DB has no odds yet (otherwise uses min game_date)",
    )
    args = parser.parse_args()

    days = int(args.days)
    if days < 1:
        raise SystemExit("--days must be >= 1")

    buffer_days = max(0, int(args.buffer_days))

    db = SessionLocal()
    try:
        # latest game_date for which at least one odds row exists
        last_odds_date: date | None = (
            db.query(func.max(Game.game_date))
            .join(Odds, Odds.game_id == Game.game_id)
            .scalar()
        )

        if last_odds_date is not None:
            start_date = last_odds_date - timedelta(days=buffer_days)
        else:
            if args.fallback_start:
                start_date = _parse_date(str(args.fallback_start))
            else:
                min_game_date: date | None = db.query(func.min(Game.game_date)).scalar()
                start_date = min_game_date or date.today()

        end_date = start_date + timedelta(days=days)

        print(f"START_ISO={_as_start_iso(start_date)}")
        print(f"END_ISO={_as_end_iso(end_date)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
