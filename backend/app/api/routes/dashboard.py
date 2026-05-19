"""
Dashboard API Routes - Main user-facing endpoints for predictions, picks, and arbitrage
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from app.db.models import Game, Prediction, UserPick, User, OddsHistory
from app.db.models import Odds
from app.dependencies import get_db, get_current_user
from datetime import datetime, timedelta
from app.api.routes.arbitrage import get_arbitrage_opportunities

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# ─────────────────────────────────────────────────────────────
# 1. UPCOMING GAMES WITH PREDICTIONS
# ─────────────────────────────────────────────────────────────

@router.get("/games/upcoming")
async def get_upcoming_games(session: Session = Depends(get_db)):
    """Get today/upcoming games with predictions and odds"""
    try:
        today = datetime.utcnow().date()

        games = session.query(Game).filter(
            Game.game_date >= today,
            Game.home_score.is_(None)
        ).order_by(Game.game_date).all()

        result = []
        for game in games:
            prediction = session.query(Prediction).filter(
                Prediction.game_id == game.game_id
            ).first()

            odds = session.query(Odds).filter(
                Odds.game_id == game.game_id
            ).all()

            result.append({
                "game_id": game.game_id,
                "game_date": game.game_date.isoformat() if game.game_date else None,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "prediction": {
                    "home_win_prob": prediction.home_win_prob if prediction else None,
                    "away_win_prob": prediction.away_win_prob if prediction else None,
                    "confidence": prediction.confidence if prediction else None,
                } if prediction else None,
                "best_odds": {
                    "home": max([o.home_win_odds for o in odds if o.home_win_odds]) if odds else None,
                    "away": max([o.away_win_odds for o in odds if o.away_win_odds]) if odds else None,
                } if odds else None
            })

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch upcoming games: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────
# 2. ARBITRAGE OPPORTUNITIES
# ─────────────────────────────────────────────────────────────

@router.get("/arbitrage")
async def get_arbitrage_dashboard(
    limit: int = Query(20, le=100),
    min_ev: float = Query(0.01, ge=0, le=1),
    session: Session = Depends(get_db)
):
    """Get current arbitrage opportunities"""
    try:
        games = session.query(Game).filter(Game.home_score == None).all()

        opportunities = []

        for game in games:
            odds_list = session.query(Odds).filter(Odds.game_id == game.game_id).all()

            if len(odds_list) < 2:
                continue

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

            for i in range(len(bookmakers_data)):
                for j in range(i + 1, len(bookmakers_data)):
                    book1 = bookmakers_data[i]
                    book2 = bookmakers_data[j]

                    home_arb = 1 - (book1["home_prob"] + book2["away_prob"])
                    away_arb = 1 - (book1["away_prob"] + book2["home_prob"])

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

        opportunities.sort(key=lambda x: x["ev_percent"], reverse=True)
        return {
            "count": len(opportunities[:limit]),
            "opportunities": opportunities[:limit],
            "updated_at": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan arbitrage: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────
# 3. USER PICKS & ROI STATS
# ─────────────────────────────────────────────────────────────

@router.get("/picks/stats")
async def get_user_picks_stats(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Get user's picks performance stats"""
    try:
        picks = session.query(UserPick).filter(
            UserPick.user_id == current_user.id,
            UserPick.result != None
        ).all()

        if not picks:
            return {
                "total_picks": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "roi": 0.0,
                "units_won": 0.0,
            }

        wins = len([p for p in picks if p.result == "WIN"])
        losses = len([p for p in picks if p.result == "LOSS"])
        total_profit = sum([p.profit for p in picks if p.profit])
        total_stake = sum([p.stake for p in picks])

        return {
            "total_picks": len(picks),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / len(picks) if picks else 0, 3),
            "total_profit": round(total_profit, 2),
            "roi": round((total_profit / total_stake * 100) if total_stake > 0 else 0, 2),
            "units_won": round(total_profit / 100, 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get picks stats: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────
# 4. USER PICKS HISTORY
# ─────────────────────────────────────────────────────────────

@router.get("/picks")
async def get_user_picks(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Get user's pick history"""
    try:
        picks = session.query(UserPick).filter(
            UserPick.user_id == current_user.id
        ).order_by(UserPick.placed_at.desc()).limit(limit).all()

        return [{
            "id": p.id,
            "game_id": p.game_id,
            "pick_team": p.pick_team,
            "pick_type": p.pick_type,
            "odds": p.odds,
            "stake": p.stake,
            "result": p.result,
            "profit": p.profit,
            "placed_at": p.placed_at.isoformat() if p.placed_at else None,
        } for p in picks]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get picks: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────
# 5. SAVE USER PICK
# ─────────────────────────────────────────────────────────────

@router.post("/picks")
async def save_user_pick(
    game_id: str,
    pick_team: str,
    odds: float,
    stake: float = 100,
    pick_type: str = "moneyline",
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Save user's pick (for tracking later)"""
    
    try:
        pick = UserPick(
            user_id=current_user.id,
            game_id=game_id,
            pick_team=pick_team,
            pick_type=pick_type,
            odds=odds,
            stake=stake,
            result="PENDING"
        )
        
        session.add(pick)
        session.commit()
        
        return {
            "id": pick.id,
            "message": "Pick saved",
            "status": "PENDING"
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ─────────────────────────────────────────────────────────────
# 6. LEADERBOARD
# ─────────────────────────────────────────────────────────────

@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db)
):
    """Get top performers leaderboard"""
    try:
        results = session.query(
            User.name,
            User.email,
            func.count(UserPick.id).label('total_picks'),
            func.sum(func.cast(UserPick.result == "WIN", Integer)).label('wins'),
            func.sum(UserPick.profit).label('total_profit')
        ).join(UserPick).filter(
            UserPick.result != None
        ).group_by(User.id).order_by(
            func.sum(UserPick.profit).desc()
        ).limit(limit).all()

        return [{
            "rank": i+1,
            "name": r[0],
            "email": r[1],
            "picks": r[2],
            "wins": r[3],
            "profit": round(r[4], 2) if r[4] else 0,
            "roi": round((r[4] / (r[2] * 100)) * 100, 2) if r[2] else 0
        } for i, r in enumerate(results)]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get leaderboard: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────
# 7. GET USER ALERTS
# ─────────────────────────────────────────────────────────────

@router.get("/alerts")
async def get_user_alerts(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Get user's alert preferences"""
    try:
        from app.db.models import UserAlert

        alert = session.query(UserAlert).filter(
            UserAlert.user_id == current_user.id
        ).first()

        if not alert:
            alert = UserAlert(user_id=current_user.id)
            session.add(alert)
            session.commit()

        return {
            "alerts_arbitrage": alert.alerts_arbitrage,
            "alerts_sharp": alert.alerts_sharp,
            "alerts_picks": alert.alerts_picks,
            "alerts_lineup": alert.alerts_lineup,
            "min_roi": alert.min_roi,
            "min_confidence": alert.min_confidence,
            "email": alert.email,
            "sms": alert.sms,
            "push": alert.push,
            "phone_number": alert.phone_number,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────
# 8. UPDATE USER ALERTS
# ─────────────────────────────────────────────────────────────

@router.put("/alerts")
async def update_user_alerts(
    alerts_arbitrage: bool = None,
    alerts_sharp: bool = None,
    alerts_picks: bool = None,
    alerts_lineup: bool = None,
    min_roi: float = None,
    min_confidence: float = None,
    email: bool = None,
    sms: bool = None,
    push: bool = None,
    phone_number: str = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Update user's alert preferences"""
    
    from app.db.models import UserAlert
    
    try:
        alert = session.query(UserAlert).filter(
            UserAlert.user_id == current_user.id
        ).first()
        
        if not alert:
            alert = UserAlert(user_id=current_user.id)
            session.add(alert)
        
        # Update only provided fields
        if alerts_arbitrage is not None:
            alert.alerts_arbitrage = alerts_arbitrage
        if alerts_sharp is not None:
            alert.alerts_sharp = alerts_sharp
        if alerts_picks is not None:
            alert.alerts_picks = alerts_picks
        if alerts_lineup is not None:
            alert.alerts_lineup = alerts_lineup
        if min_roi is not None:
            alert.min_roi = min_roi
        if min_confidence is not None:
            alert.min_confidence = min_confidence
        if email is not None:
            alert.email = email
        if sms is not None:
            alert.sms = sms
        if push is not None:
            alert.push = push
        if phone_number is not None:
            alert.phone_number = phone_number
        
        alert.updated_at = datetime.utcnow()
        session.commit()
        
        return {
            "message": "Alerts updated",
            "status": "success"
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
