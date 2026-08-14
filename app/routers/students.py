from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt

from app import db
from app.config import Settings, get_settings
from app.schemas import (
    StudentLoginRequest,
    StudentMeResponse,
    StudentRegisterRequest,
    StudentSubscriptionItem,
    StudentTokenResponse,
)
from app.security import hash_password, verify_password
from app.util import log_action, new_id, utcnow

router = APIRouter(prefix="/students", tags=["students"])

SUBJECT_LABELS = {
    "ukr": "Українська мова",
    "math": "Математика",
    "history": "Історія України",
    "eng": "Англійська",
    "bio": "Біологія",
    "geo": "Географія",
}


def _create_student_token(student_id: str, email: str, settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_ttl_min)
    payload = {"sub": student_id, "email": email, "role": "student", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def require_student(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if payload.get("role") != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student token required")
    student = await db.find_doc("students", {"_id": payload.get("sub")})
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Student not found")
    return student


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _days_left(next_payment_at: datetime | None) -> int | None:
    if not next_payment_at:
        return None
    delta = next_payment_at - datetime.now(timezone.utc)
    return int(delta.total_seconds() // 86400)


def _subscription_item(doc: dict[str, Any]) -> StudentSubscriptionItem:
    next_pay = _parse_dt(doc.get("next_payment_at") or doc.get("current_period_end"))
    days = _days_left(next_pay)
    subject = doc.get("subject", "")
    return StudentSubscriptionItem(
        id=doc["_id"],
        subject=subject,
        subject_label=SUBJECT_LABELS.get(subject, subject),
        plan=doc.get("plan", "standard"),
        price_month=int(doc.get("price_month", 0)),
        status=doc.get("status", "trialing"),
        next_payment_at=next_pay,
        current_period_end=next_pay,
        days_until_payment=days,
        is_overdue=bool(days is not None and days < 0)
        or doc.get("status") in {"past_due", "blocked"},
    )


@router.post("/register", response_model=StudentTokenResponse)
async def register(
    body: StudentRegisterRequest,
    settings: Settings = Depends(get_settings),
) -> StudentTokenResponse:
    email = body.email.lower().strip()
    if await db.find_doc("students", {"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    now = utcnow()
    parent_id = new_id("par")
    student_id = new_id("stu")

    await db.insert_doc(
        "parents",
        {
            "_id": parent_id,
            "name": body.parent_name or f"Батьки {body.name}",
            "phone": body.parent_phone or body.phone,
            "email": None,
            "created_at": now.isoformat(),
        },
    )
    await db.insert_doc(
        "students",
        {
            "_id": student_id,
            "email": email,
            "password_hash": hash_password(body.password),
            "name": body.name,
            "phone": body.phone,
            "grade": body.grade,
            "primary_parent_id": parent_id,
            "telegram_id": body.telegram_id,
            "created_at": now.isoformat(),
        },
    )

    period_end = now + timedelta(days=5)
    await db.insert_doc(
        "subscriptions",
        {
            "_id": new_id("sub"),
            "student_id": student_id,
            "parent_id": parent_id,
            "subject": body.subject_interest or "math",
            "plan": "standard",
            "price_month": 990,
            "status": "trialing",
            "cohort_id": None,
            "curator_id": None,
            "current_period_start": now.isoformat(),
            "current_period_end": period_end.isoformat(),
            "next_payment_at": period_end.isoformat(),
            "created_at": now.isoformat(),
        },
    )

    await log_action("student_register", {"student_id": student_id, "email": email})
    token = _create_student_token(student_id, email, settings)
    return StudentTokenResponse(access_token=token, student_id=student_id, name=body.name)


@router.post("/login", response_model=StudentTokenResponse)
async def login(
    body: StudentLoginRequest,
    settings: Settings = Depends(get_settings),
) -> StudentTokenResponse:
    email = body.email.lower().strip()
    student = await db.find_doc("students", {"email": email})
    if not student or not verify_password(body.password, student["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = _create_student_token(student["_id"], email, settings)
    return StudentTokenResponse(
        access_token=token,
        student_id=student["_id"],
        name=student.get("name") or email,
    )


@router.get("/me", response_model=StudentMeResponse)
async def me(student: dict = Depends(require_student)) -> StudentMeResponse:
    subs = await db.find_docs("subscriptions", {"student_id": student["_id"]}, limit=50)
    items = [_subscription_item(s) for s in subs]
    items.sort(key=lambda x: (x.days_until_payment is None, x.days_until_payment or 0))
    return StudentMeResponse(
        id=student["_id"],
        email=student["email"],
        name=student.get("name") or "",
        phone=student.get("phone"),
        grade=student.get("grade"),
        subscriptions=items,
    )
