"""
Watchlist API Routes (Protected - requires authentication)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import Watchlist, Game, User
from app.dependencies import get_db
from app.middleware import get_current_user_id

router = APIRouter(prefix="/api/v1/me/watchlist", tags=["watchlist"])


@router.get("")
async def get_watchlist(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current user's watchlist"""
    try:
        user = db.query(User).filter(User.supabase_id == user_id).first()
        if not user:
            return []

        watchlist_items = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()

        games = []
        for item in watchlist_items:
            game = db.query(Game).filter(Game.game_id == item.game_id).first()
            if game:
                games.append({
                    "game_id": game.game_id,
                    "date": game.game_date.isoformat() if game.game_date else None,
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "added_at": item.added_at.isoformat() if item.added_at else None
                })

        return games
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get watchlist: {str(e)}"
        )


@router.post("/{game_id}")
async def add_to_watchlist(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Add a game to user's watchlist"""
    try:
        user = db.query(User).filter(User.supabase_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        game = db.query(Game).filter(Game.game_id == game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found"
            )

        existing = db.query(Watchlist).filter(
            Watchlist.user_id == user.id,
            Watchlist.game_id == game_id
        ).first()

        if existing:
            return {"message": "Already in watchlist", "status": "already_exists"}

        watchlist_item = Watchlist(user_id=user.id, game_id=game_id)
        db.add(watchlist_item)
        db.commit()

        return {"message": "Added to watchlist", "status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to watchlist: {str(e)}"
        )


@router.delete("/{game_id}")
async def remove_from_watchlist(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Remove a game from user's watchlist"""
    try:
        user = db.query(User).filter(User.supabase_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        item = db.query(Watchlist).filter(
            Watchlist.user_id == user.id,
            Watchlist.game_id == game_id
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not in watchlist"
            )

        db.delete(item)
        db.commit()

        return {"message": "Removed from watchlist", "status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove from watchlist: {str(e)}"
        )
