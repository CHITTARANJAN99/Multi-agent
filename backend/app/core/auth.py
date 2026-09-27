from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config.settings import settings
from app.core.errors import AuthenticationError
from app.core.logging_config import logger

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None

class UserSession(BaseModel):
    user_id: str
    email: str
    is_active: bool = True

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a bcrypt hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Generates a bcrypt hash for a plain text password."""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserSession:
    """
    Dependency function to validate JWT token and return the current user's session.
    """
    if not token:
        raise AuthenticationError("Not authenticated", detail="Authorization header missing or invalid format")
        
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            raise AuthenticationError("Could not validate credentials", detail="Token claims missing")
        token_data = TokenData(user_id=user_id, email=email)
    except jwt.PyJWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise AuthenticationError("Could not validate credentials", detail="Invalid token signature or expired")

    # In production, check database if user exists and is active.
    # Returning a mock UserSession for architecture skeleton.
    return UserSession(user_id=token_data.user_id, email=token_data.email, is_active=True)
