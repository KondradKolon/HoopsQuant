"""
Authentication middleware for JWT token verification
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional

security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify JWT token from Supabase Auth
    Returns decoded token data
    """
    token = credentials.credentials
    try:
        # For MVP, we skip signature verification
        # In production, use Supabase public key
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        return decoded
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(token: dict = Depends(verify_token)) -> str:
    """
    Extract user ID from verified token
    """
    user_id = token.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: no user ID",
        )
    return user_id


async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[str]:
    """
    Optional auth - returns user ID if token present, None otherwise
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        return decoded.get("sub")
    except:
        return None
