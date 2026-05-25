"""
Odds pipeline diagnostics — verify scheduler + DB coverage in production.
"""

from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import func

from app.config import BOOKMAKERS, ODDS_API_KEY
from app.db.database import SessionLocal
from app.db.models import Game, Odds

router = APIRouter(prefix="/api/v1/odds", tags=["odds"])


@router.get("/status")
def odds_status():
    """Snapshot of odds ingestion health (for deployment checks)."""
    today = date.today()
    window_start = today - timedelta(days=3)
    window_end = today + timedelta(days=14)

    session = SessionLocal()
    try:
        upcoming = (
            session.query(Game)
            .filter(
                Game.home_score.is_(None),
                Game.game_date >= today,
                Game.game_date <= window_end,
            )
            .all()
        )
        upcoming_ids = [g.game_id for g in upcoming]

        odds_rows = (
            session.query(Odds.bookmaker, func.count(Odds.id))
            .group_by(Odds.bookmaker)
            .all()
        )
        total_odds = session.query(func.count(Odds.id)).scalar() or 0

        upcoming_with_odds = 0
        upcoming_detail = []
        for g in upcoming[:30]:
            rows = session.query(Odds).filter(Odds.game_id == g.game_id).all()
            books = {o.bookmaker: (o.home_win_odds, o.away_win_odds) for o in rows}
            if len(books) >= 1:
                upcoming_with_odds += 1
            upcoming_detail.append(
                {
                    "game_id": g.game_id,
                    "date": g.game_date.isoformat() if g.game_date else None,
                    "matchup": f"{g.home_team} vs {g.away_team}",
                    "bookmakers": list(books.keys()),
                    "odds_count": len(books),
                }
            )

        return {
            "odds_api_key_set": bool(ODDS_API_KEY),
            "configured_bookmakers": BOOKMAKERS,
            "total_odds_rows": total_odds,
            "odds_by_bookmaker": {bm: cnt for bm, cnt in odds_rows},
            "upcoming_games": len(upcoming),
            "upcoming_with_any_odds": upcoming_with_odds,
            "upcoming_without_odds": len(upcoming) - upcoming_with_odds,
            "coverage_pct": round(
                100 * upcoming_with_odds / len(upcoming), 1
            )
            if upcoming
            else None,
            "scheduler_jobs": {
                "nba_odds_pipeline": "every 2 hours at :15 UTC",
                "current_odds_multi": "every hour at :05 UTC",
                "odds_history_track": "every 30 minutes",
                "predictions": "every 6 hours",
            },
            "upcoming_sample": upcoming_detail,
        }
    finally:
        session.close()
