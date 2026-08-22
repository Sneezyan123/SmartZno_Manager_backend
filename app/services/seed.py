"""Seed demo parent/student + subscriptions for local MVP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import db
from app.security import hash_password
from app.util import kyiv_tz, log_action, new_id, utcnow

DEMO_STUDENT_EMAIL = "pupil@smartzno.com"
DEMO_STUDENT_PASSWORD = "pupil123"

SUBJECT_LABELS = {
    "ukr": "Українська мова",
    "math": "Математика",
    "history": "Історія України",
    "eng": "Англійська",
    "bio": "Біологія",
    "geo": "Географія",
}

SEED_TEACHERS = [
    {
        "_id": "tch_anna",
        "name": "Анна",
        "role": "teacher",
        "subject": "math",
        "email": "anna@smartzno.com",
        "zoom_url": "https://zoom.us/j/smartzno-anna",
        "capacity_limit": 8,
    },
    {
        "_id": "tch_daria",
        "name": "Дарія",
        "role": "teacher",
        "subject": "ukr",
        "email": "daria@smartzno.com",
        "zoom_url": "https://zoom.us/j/smartzno-daria",
        "capacity_limit": 8,
    },
    {
        "_id": "tch_illia",
        "name": "Ілля",
        "role": "teacher",
        "subject": "history",
        "email": "illia@smartzno.com",
        "zoom_url": "https://zoom.us/j/smartzno-illia",
        "capacity_limit": 8,
    },
    {
        "_id": "tch_maria",
        "name": "Марія",
        "role": "teacher",
        "subject": "eng",
        "email": "maria@smartzno.com",
        "zoom_url": "https://zoom.us/j/smartzno-maria",
        "capacity_limit": 8,
    },
    {
        "_id": "tch_khrystyna",
        "name": "Христина",
        "role": "teacher",
        "subject": "bio",
        "email": "khrystyna@smartzno.com",
        "zoom_url": "https://zoom.us/j/smartzno-khrystyna",
        "capacity_limit": 8,
    },
    {
        "_id": "tch_yulia",
        "name": "Юлія",
        "role": "teacher",
        "subject": "geo",
        "email": "yulia@smartzno.com",
        "zoom_url": "https://zoom.us/j/smartzno-yulia",
        "capacity_limit": 8,
    },
]


async def ensure_teachers() -> list[dict]:
    now = utcnow()
    teachers: list[dict] = []
    for seed in SEED_TEACHERS:
        existing = await db.find_doc("staff", {"_id": seed["_id"]})
        if existing is None:
            existing = await db.find_doc("staff", {"email": seed["email"]})
        if existing is None:
            doc = {**seed, "created_at": now.isoformat()}
            await db.insert_doc("staff", doc)
            teachers.append(doc)
        else:
            teachers.append(existing)
    return teachers


def _kyiv_at(day, hour: int, minute: int = 0):
    tz = kyiv_tz()
    local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
    return local.astimezone(timezone.utc)


async def ensure_demo_consultations() -> None:
    existing = await db.list_docs("consultations", limit=1)
    if existing:
        return

    student = await db.find_doc("students", {"email": DEMO_STUDENT_EMAIL})
    now_kyiv = utcnow().astimezone(kyiv_tz())
    cursor = now_kyiv.date()
    if now_kyiv.hour >= 20:
        cursor += timedelta(days=1)
    weekdays: list = []
    while len(weekdays) < 3:
        if cursor.weekday() < 5:
            weekdays.append(cursor)
        cursor += timedelta(days=1)
    slots = [
        (weekdays[0], 16, 0, "tch_anna", "math", 45, "Розбір діагностики з математики"),
        (weekdays[1], 11, 0, "tch_daria", "ukr", 45, "Консультація: типові помилки в тестах"),
        (weekdays[2], 18, 30, "tch_illia", "history", 60, "НМТ історія — хронологія ХХ ст."),
    ]
    for i, (day, hour, minute, teacher_id, subject, duration, notes) in enumerate(slots, start=1):
        starts = _kyiv_at(day, hour, minute)
        ends = starts + timedelta(minutes=duration)
        teacher = next((t for t in SEED_TEACHERS if t["_id"] == teacher_id), SEED_TEACHERS[0])
        is_existing_student = i == 1 and student is not None
        await db.insert_doc(
            "consultations",
            {
                "_id": f"con_demo_{i}",
                "teacher_id": teacher_id,
                "teacher_name": teacher["name"],
                "starts_at": starts.isoformat(),
                "ends_at": ends.isoformat(),
                "duration_min": duration,
                "subject": subject,
                "student_name": student["name"]
                if is_existing_student
                else ("Олег Мельник" if i == 2 else "Софія Бондар"),
                "student_phone": student.get("phone")
                if is_existing_student
                else ("+380931112233" if i == 2 else "+380673334455"),
                "student_id": student["_id"] if is_existing_student else None,
                "lead_id": None,
                "notes": notes,
                "meeting_url": teacher.get("zoom_url"),
                "status": "scheduled",
                "created_at": utcnow().isoformat(),
            },
        )


async def ensure_demo_data() -> None:
    existing = await db.find_doc("students", {"email": DEMO_STUDENT_EMAIL})
    if not existing:
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

    await ensure_teachers()
    await ensure_demo_consultations()
