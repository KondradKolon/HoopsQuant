"""
Arbitrage Scanner API Routes
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.models import Game, Odds
from app.dependencies import get_db

router = APIRouter(prefix="/api/v1/arbitrage", tags=["arbitrage"])


@router.get("/opportunities")
async def get_arbitrage_opportunities(
    limit: int = Query(20, le=100),
    min_ev: float = Query(0.01, ge=0, le=1, description="Minimum EV (0.01 = 1%)"),
    db: Session = Depends(get_db)
):
    """
    Find cross-bookmaker arbitrage opportunities
    
    Returns games where implied probabilities are less than 1 (profitable arbs)
    
    - **limit**: Maximum number of opportunities to return
    - **min_ev**: Minimum EV percentage required (0.01 = 1%)
    """
    try:
        # Get all upcoming games
        games = db.query(Game).filter(Game.home_score == None).all()
        
        opportunities = []
        
        for game in games:
            # Get all odds for this game
            odds_list = db.query(Odds).filter(Odds.game_id == game.game_id).all()
            
            if len(odds_list) < 2:
                continue  # Need at least 2 bookmakers for arbitrage
            
            # Calculate implied probabilities
            bookmakers_data = []
            for odd in odds_list:
                if odd.home_win_odds and odd.away_win_odds:
                    home_prob = 1 / odd.home_win_odds
                    away_prob = 1 / odd.away_win_odds
                    bookmakers_data.append({
                        "bookmaker": odd.bookmaker,
                        "home_prob": home_prob,
                        "away_prob": away_prob,
                        "home_odds": odd.home_win_odds,
                        "away_odds": odd.away_win_odds
                    })
            
            # Check for arbitrage between each pair of bookmakers
            for i in range(len(bookmakers_data)):
                for j in range(i + 1, len(bookmakers_data)):
                    book1 = bookmakers_data[i]
                    book2 = bookmakers_data[j]
                    
                    # Home arbitrage: best home odds from book1 + best away odds from book2
                    home_arb = 1 - (book1["home_prob"] + book2["away_prob"])
                    
                    # Away arbitrage: best away odds from book1 + best home odds from book2
                    away_arb = 1 - (book1["away_prob"] + book2["home_prob"])
                    
                    # Check if profitable
                    if home_arb >= min_ev:
                        opportunities.append({
                            "game_id": game.game_id,
                            "game_date": game.game_date.isoformat() if game.game_date else None,
                            "home_team": game.home_team,
                            "away_team": game.away_team,
                            "type": "home_arb",
                            "ev_percent": round(home_arb * 100, 2),
                            "bookmaker_1": book1["bookmaker"],
                            "bookmaker_2": book2["bookmaker"],
                            "bet_1": {
                                "side": "home",
                                "odds": round(book1["home_odds"], 2),
                                "implied_prob": round(book1["home_prob"] * 100, 2)
                            },
                            "bet_2": {
                                "side": "away",
                                "odds": round(book2["away_odds"], 2),
                                "implied_prob": round(book2["away_prob"] * 100, 2)
                            }
                        })
                    
                    if away_arb >= min_ev:
                        opportunities.append({
                            "game_id": game.game_id,
                            "game_date": game.game_date.isoformat() if game.game_date else None,
                            "home_team": game.home_team,
                            "away_team": game.away_team,
                            "type": "away_arb",
                            "ev_percent": round(away_arb * 100, 2),
                            "bookmaker_1": book1["bookmaker"],
                            "bookmaker_2": book2["bookmaker"],
                            "bet_1": {
                                "side": "away",
                                "odds": round(book1["away_odds"], 2),
                                "implied_prob": round(book1["away_prob"] * 100, 2)
                            },
                            "bet_2": {
                                "side": "home",
                                "odds": round(book2["home_odds"], 2),
                                "implied_prob": round(book2["home_prob"] * 100, 2)
                            }
                        })
        
        # Sort by EV descending and limit
        opportunities.sort(key=lambda x: x["ev_percent"], reverse=True)
        return opportunities[:limit]
    
    except Exception as e:
        return {"error": str(e)}
