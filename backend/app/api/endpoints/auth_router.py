from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.core.auth import (
    create_access_token, 
    get_password_hash, 
    verify_password, 
    get_current_user,
    UserSession
)
from app.core.errors import AuthenticationError
from app.config.settings import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Mock Database for Skeleton
MOCK_USERS_DB = {}

@router.post("/register", status_code=201)
async def register(user_in: UserRegister):
    if user_in.email in MOCK_USERS_DB:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = get_password_hash(user_in.password)
    MOCK_USERS_DB[user_in.email] = {
        "id": f"usr_{len(MOCK_USERS_DB)+1}",
        "email": user_in.email,
        "hashed_password": hashed_pwd
    }
    return {"message": "User registered successfully", "email": user_in.email}

@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = MOCK_USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise AuthenticationError("Incorrect email or password")
        
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"]}
    )
    return TokenResponse(access_token=access_token)

@router.get("/me", response_model=UserSession)
async def get_me(current_user: UserSession = Depends(get_current_user)):
    return current_user
