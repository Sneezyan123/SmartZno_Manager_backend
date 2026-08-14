from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException

from app import db
from app.deps import require_api_key
from app.schemas import PaymentWebhook, SubscriptionResponse
from app.util import log_action, new_id, utcnow

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/webhook", response_model=SubscriptionResponse, dependencies=[Depends(require_api_key)])
async def payment_webhook(body: PaymentWebhook) -> SubscriptionResponse:
    sub = await db.find_doc("subscriptions", {"_id": body.subscription_id})
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    now = utcnow()
    patch: dict = {}
    if body.event == "paid":
        period_end = now + timedelta(days=30)
        patch = {
            "status": "active",
            "current_period_start": now.isoformat(),
            "current_period_end": period_end.isoformat(),
            "next_payment_at": period_end.isoformat(),
        }
        lms_action = "unblock"
    elif body.event == "failed":
        patch = {"status": "past_due"}
        lms_action = "block"
    else:
        patch = {"status": "cancelled"}
        lms_action = "block"

    updated = await db.update_doc("subscriptions", {"_id": body.subscription_id}, patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Subscription not found")

    await db.insert_doc(
        "payment_ledger",
        {
            "_id": new_id("pay"),
            "subscription_id": body.subscription_id,
            "event": body.event,
            "amount": body.amount,
            "provider": body.provider,
            "lms_action": lms_action,
            "at": now.isoformat(),
        },
    )
    await log_action(
        "payment_webhook",
        {"subscription_id": body.subscription_id, "event": body.event, "lms_action": lms_action},
    )

    next_pay = updated.get("next_payment_at")
    next_dt = None
    days = None
    if next_pay:
        from datetime import datetime, timezone

        try:
            next_dt = datetime.fromisoformat(str(next_pay).replace("Z", "+00:00"))
            if next_dt.tzinfo is None:
                next_dt = next_dt.replace(tzinfo=timezone.utc)
            days = int((next_dt - datetime.now(timezone.utc)).total_seconds() // 86400)
        except ValueError:
            pass

    return SubscriptionResponse(
        id=updated["_id"],
        status=updated["status"],
        subject=updated["subject"],
        plan=updated["plan"],
        price_month=updated["price_month"],
        next_payment_at=next_dt,
        days_until_payment=days,
    )
