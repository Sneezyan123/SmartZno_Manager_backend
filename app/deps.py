from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from app.config import Settings, get_settings

Role = Literal["admin", "sales_manager", "curator_lead", "targetologist"]

# Skeleton demo users (password = role name for local only)
DEMO_USERS: dict[str, dict] = {
    "admin@smartzno.com": {"password": "admin", "role": "admin", "name": "Admin"},
    "sales@smartzno.com": {
        "password": "sales_manager",
        "role": "sales_manager",
        "name": "Sales Manager",
    },
    "curator@smartzno.com": {
        "password": "curator_lead",
        "role": "curator_lead",
        "name": "Curator Lead",
    },
    "ads@smartzno.com": {
        "password": "targetologist",
        "role": "targetologist",
        "name": "Targetologist",
    },
}


def create_access_token(subject: str, role: Role, settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_ttl_min)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, settings: Settings) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


async def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if x_api_key not in {settings.crm_api_key, settings.lms_api_key}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token, settings)
    return {"email": payload.get("sub"), "role": payload.get("role")}
