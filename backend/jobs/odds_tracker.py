"""
Odds Tracker Job - Fetch and store odds history every 30 minutes
For detecting sharp money movements
"""

import logging
from datetime import datetime
from app.db.database import SessionLocal
from app.db.models import OddsHistory, Game, Odds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s: %(message)s'
)
logger = logging.getLogger("odds_tracker")


def track_odds():
    """Fetch and store current odds as history"""
    
    session = SessionLocal()
    
    try:
        logger.info("🔄 Tracking odds...")
        
        # Get upcoming games
        games = session.query(Game).filter(
            Game.home_score.is_(None)  # Upcoming games only
        ).all()
        
        if not games:
            logger.info("No upcoming games to track")
            return
        
        # For each game, get current odds and store as history
        tracked_count = 0
        for game in games:
            odds_list = session.query(Odds).filter(
                Odds.game_id == game.game_id
            ).all()
            
            if not odds_list:
                continue
            
            # Store each bookmaker's odds as history snapshot
            for odds in odds_list:
                history = OddsHistory(
                    game_id=game.game_id,
                    bookmaker=odds.bookmaker,
                    home_odds=odds.home_win_odds,
                    away_odds=odds.away_win_odds,
                    spread=None,  # Can be extended later
                    total=None,   # Can be extended later
                    timestamp=datetime.utcnow()
                )
                session.add(history)
                tracked_count += 1
        
        session.commit()
        logger.info(f"✅ Stored {tracked_count} odds snapshots from {len(games)} games")
        
    except Exception as e:
        logger.error(f"❌ Error tracking odds: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    track_odds()
