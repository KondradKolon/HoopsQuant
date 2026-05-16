"""
Database dependencies for FastAPI routes
"""
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import User
from app.middleware import get_current_user_id
from fastapi import Depends, HTTPException, status


def get_db() -> Session:
    """
    Get database session for dependency injection
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user object
    Usage: current_user: User = Depends(get_current_user)
    """
    user = db.query(User).filter(User.supabase_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
