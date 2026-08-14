"""Seed demo parent/student + subscriptions for local MVP."""

from __future__ import annotations

from datetime import timedelta

from app import db
from app.security import hash_password
from app.util import log_action, new_id, utcnow

DEMO_STUDENT_EMAIL = "pupil@smartzno.com"
DEMO_STUDENT_PASSWORD = "pupil123"


async def ensure_demo_data() -> None:
    existing = await db.find_doc("students", {"email": DEMO_STUDENT_EMAIL})
    if existing:
        return

    now = utcnow()
    parent_id = new_id("par")
    student_id = new_id("stu")

    await db.insert_doc(
        "parents",
        {
            "_id": parent_id,
            "name": "Олена Коваленко",
            "phone": "+380501112233",
            "email": "parent@smartzno.com",
            "created_at": now.isoformat(),
        },
    )

    await db.insert_doc(
        "students",
        {
            "_id": student_id,
            "email": DEMO_STUDENT_EMAIL,
            "password_hash": hash_password(DEMO_STUDENT_PASSWORD),
            "name": "Марія Коваленко",
            "phone": "+380671234567",
            "grade": "11",
            "primary_parent_id": parent_id,
            "telegram_id": None,
            "created_at": now.isoformat(),
        },
    )

    subs = [
        {
            "_id": new_id("sub"),
            "student_id": student_id,
            "parent_id": parent_id,
            "subject": "math",
            "plan": "premium",
            "price_month": 1490,
            "status": "active",
            "cohort_id": None,
            "curator_id": None,
            "current_period_start": (now - timedelta(days=18)).isoformat(),
            "current_period_end": (now + timedelta(days=12)).isoformat(),
            "next_payment_at": (now + timedelta(days=12)).isoformat(),
            "created_at": (now - timedelta(days=48)).isoformat(),
        },
        {
            "_id": new_id("sub"),
            "student_id": student_id,
            "parent_id": parent_id,
            "subject": "ukr",
            "plan": "standard",
            "price_month": 990,
            "status": "active",
            "cohort_id": None,
            "curator_id": None,
            "current_period_start": (now - timedelta(days=27)).isoformat(),
            "current_period_end": (now + timedelta(days=3)).isoformat(),
            "next_payment_at": (now + timedelta(days=3)).isoformat(),
            "created_at": (now - timedelta(days=27)).isoformat(),
        },
        {
            "_id": new_id("sub"),
            "student_id": student_id,
            "parent_id": parent_id,
            "subject": "history",
            "plan": "standard",
            "price_month": 990,
            "status": "past_due",
            "cohort_id": None,
            "curator_id": None,
            "current_period_start": (now - timedelta(days=35)).isoformat(),
            "current_period_end": (now - timedelta(days=5)).isoformat(),
            "next_payment_at": (now - timedelta(days=5)).isoformat(),
            "created_at": (now - timedelta(days=65)).isoformat(),
        },
    ]
    for sub in subs:
        await db.insert_doc("subscriptions", sub)

    await log_action(
        "demo_seed",
        {"student_id": student_id, "email": DEMO_STUDENT_EMAIL, "subscriptions": len(subs)},
    )
