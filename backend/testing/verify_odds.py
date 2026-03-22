"""verify_odds.py

Print games + stored odds for a date range.

Examples:
  python3 verify_odds.py --start 2026-01-01 --end 2026-02-01
  python3 verify_odds.py --start 2026-01-01 --end 2026-02-01 --bookmakers "Betclic PL" Superbet
"""

from __future__ import annotations

import argparse
from datetime import date, datetime

from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import Game


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify odds stored in DB")
    parser.add_argument("--start", default="2026-01-01", help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--end", default="2026-02-01", help="YYYY-MM-DD (exclusive)")
    parser.add_argument("--bookmakers", nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    start = _parse_date(args.start)
    end = _parse_date(args.end)
    want_books = set(args.bookmakers or [])

    db = SessionLocal()
    try:
        q = (
            db.query(Game)
            .options(joinedload(Game.odds))
            .filter(Game.game_date >= start)
            .filter(Game.game_date < end)
            .order_by(Game.game_date.asc(), Game.home_team.asc())
        )

        games = q.limit(int(args.limit)).all()
        print(f"Loaded {len(games)} games (limit={args.limit}) from {start} to {end} (exclusive)")

        for g in games:
            odds_rows = list(g.odds or [])
            
            if want_books:
                odds_rows = [o for o in odds_rows if o.bookmaker in want_books]
                

            if not odds_rows:
                continue

            print(f"\n{g.game_date}  {g.away_team} @ {g.home_team}  game_id={g.game_id}")
            for o in sorted(odds_rows, key=lambda r: (r.bookmaker or "")):
                print(
                    f"  - {o.bookmaker}: home={o.home_win_odds} away={o.away_win_odds}"
                )

            print(len(odds_rows))

    finally:
        db.close()
        


if __name__ == "__main__":
    main()
