from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app import db
from app.schemas import SubscriptionCreate, SubscriptionResponse
from app.util import log_action, new_id, utcnow

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _days_until(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int((dt - datetime.now(timezone.utc)).total_seconds() // 86400)
    except ValueError:
        return None


def _to_response(doc: dict) -> SubscriptionResponse:
    next_pay = doc.get("next_payment_at") or doc.get("current_period_end")
    next_dt = None
    if next_pay:
        try:
            next_dt = datetime.fromisoformat(str(next_pay).replace("Z", "+00:00"))
        except ValueError:
            next_dt = None
    return SubscriptionResponse(
        id=doc["_id"],
        status=doc["status"],
        subject=doc["subject"],
        plan=doc["plan"],
        price_month=doc["price_month"],
        next_payment_at=next_dt,
        days_until_payment=_days_until(str(next_pay) if next_pay else None),
    )


@router.post("", response_model=SubscriptionResponse)
async def create_subscription(body: SubscriptionCreate) -> SubscriptionResponse:
    sub_id = new_id("sub")
    now = utcnow()
    period_end = now + timedelta(days=30)
    doc = {
        "_id": sub_id,
        "student_id": body.student_id,
        "parent_id": body.parent_id,
        "subject": body.subject,
        "plan": body.plan,
        "price_month": body.price_month,
        "status": "trialing",
        "cohort_id": body.cohort_id,
        "curator_id": None,
        "current_period_start": now.isoformat(),
        "current_period_end": period_end.isoformat(),
        "next_payment_at": period_end.isoformat(),
        "created_at": now.isoformat(),
    }
    await db.insert_doc("subscriptions", doc)
    await log_action("subscription_created", {"id": sub_id, "subject": body.subject, "plan": body.plan})
    return _to_response(doc)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(subscription_id: str) -> SubscriptionResponse:
    doc = await db.find_doc("subscriptions", {"_id": subscription_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return _to_response(doc)
