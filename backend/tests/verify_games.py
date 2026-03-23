"""verify_games.py

Quick sanity check for what games exist in the DB for a date range.

Examples:
  python3 verify_games.py --start 2026-01-01 --end 2026-02-01
  python3 verify_games.py --start 2025-10-01 --end 2025-11-01 --limit 50
"""

from __future__ import annotations

import argparse
from datetime import date, datetime

from database import SessionLocal
from models import Game


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify games stored in DB")
    parser.add_argument("--start", default="2026-01-01", help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--end", default="2026-02-01", help="YYYY-MM-DD (exclusive)")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    start = _parse_date(args.start)
    end = _parse_date(args.end)

    db = SessionLocal()
    try:
        q = (
            db.query(Game)
            .filter(Game.game_date >= start)
            .filter(Game.game_date < end)
            .order_by(Game.game_date.asc(), Game.home_team.asc())
        )

        total = q.count()
        games = q.limit(int(args.limit)).all()

        print(f"Games in DB from {start} to {end} (exclusive): {total}")
        for g in games:
            print(
                f"{g.game_date}  {g.away_team} @ {g.home_team}"
                f"  game_id={g.game_id} season={g.season}"
            )

        if total > len(games):
            print(f"... (showing first {len(games)} of {total})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
