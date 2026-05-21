"""
Games API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models import Game, Prediction
from app.dependencies import get_db

router = APIRouter(prefix="/api/v1/games", tags=["games"])


@router.get("/upcoming")
async def get_upcoming_games(
    limit: int = Query(10, le=100, ge=1),
    season: str = Query("2025-26"),
    db: Session = Depends(get_db)
):
    """Get upcoming (not yet played) games with predictions"""
    try:
        games = db.query(Game).filter(
            Game.home_score == None,
            Game.season == season
        ).limit(limit).all()

        result = []
        for game in games:
            pred = db.query(Prediction).filter(
                Prediction.game_id == game.game_id
            ).first()

            result.append({
                "game_id": game.game_id,
                "date": game.game_date.isoformat() if game.game_date else None,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "prediction": {
                    "home_win_prob": pred.home_win_prob if pred else None,
                    "away_win_prob": pred.away_win_prob if pred else None,
                    "confidence": pred.confidence if pred else None,
                    "model": pred.model_name if pred else None
                } if pred else None
            })

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch upcoming games: {str(e)}"
        )


@router.get("/{game_id}/prediction")
async def get_game_prediction(
    game_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed prediction for a specific game"""
    try:
        game = db.query(Game).filter(Game.game_id == game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found"
            )

        pred = db.query(Prediction).filter(
            Prediction.game_id == game_id
        ).first()

        return {
            "game": {
                "game_id": game.game_id,
                "date": game.game_date.isoformat() if game.game_date else None,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "home_score": game.home_score,
                "away_score": game.away_score,
                "season": game.season
            },
            "prediction": {
                "home_win_prob": pred.home_win_prob,
                "away_win_prob": pred.away_win_prob,
                "confidence": pred.confidence,
                "model": pred.model_name,
                "created_at": pred.created_at.isoformat() if pred.created_at else None
            } if pred else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch game prediction: {str(e)}"
        )


@router.get("")
async def get_games(
    season: str = Query("2025-26"),
    limit: int = Query(20, le=100, ge=1),
    db: Session = Depends(get_db)
):
    """Get games for a specific season"""
    try:
        games = db.query(Game).filter(
            Game.season == season
        ).limit(limit).all()

        return [
            {
                "game_id": g.game_id,
                "date": g.game_date.isoformat() if g.game_date else None,
                "home_team": g.home_team,
                "away_team": g.away_team,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "home_team_wins": g.home_team_wins
            }
            for g in games
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch games: {str(e)}"
        )


@router.get("/count")
async def count_games(
    season: str = Query("2025-26"),
    db: Session = Depends(get_db)
):
    """Get count of games in database for a season"""
    try:
        count = db.query(Game).filter(Game.season == season).count()
        return {"season": season, "total_games": count}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to count games: {str(e)}"
        )
