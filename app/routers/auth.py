from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.deps import DEMO_USERS, create_access_token, get_current_user
from app.schemas import LoginRequest, MeResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, settings: Settings = Depends(get_settings)) -> TokenResponse:
    user = DEMO_USERS.get(body.email.lower())
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(body.email.lower(), user["role"], settings)
    return TokenResponse(access_token=token, role=user["role"])


@router.get("/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_user)) -> MeResponse:
    return MeResponse(email=user["email"], role=user["role"])
