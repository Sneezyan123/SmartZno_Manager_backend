from fastapi import APIRouter, HTTPException

from app import db
from app.schemas import CohortEnrollRequest, CohortEnrollResponse
from app.util import log_action, new_id, utcnow

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


async def ensure_default_cohort(cohort_id: str) -> dict:
    existing = await db.find_doc("cohorts", {"_id": cohort_id})
    if existing:
        return existing
    doc = {
        "_id": cohort_id,
        "name": "Когорта-заглушка",
        "subject": "math",
        "level": "standard",
        "capacity": 30,
        "enrolled_count": 0,
        "start_date": utcnow().date().isoformat(),
        "created_at": utcnow().isoformat(),
    }
    await db.insert_doc("cohorts", doc)
    return doc


@router.post("/{cohort_id}/enroll", response_model=CohortEnrollResponse)
async def enroll(cohort_id: str, body: CohortEnrollRequest) -> CohortEnrollResponse:
    cohort = await ensure_default_cohort(cohort_id)
    capacity = int(cohort.get("capacity", 30))
    enrolled = int(cohort.get("enrolled_count", 0))
    if enrolled >= capacity:
        raise HTTPException(status_code=409, detail="Cohort is full")
    cohort["enrolled_count"] = enrolled + 1
    sub = await db.find_doc("subscriptions", {"_id": body.subscription_id})
    if sub:
        sub["cohort_id"] = cohort_id
        sub["student_id"] = body.student_id
    await log_action(
        "cohort_enroll",
        {"cohort_id": cohort_id, "student_id": body.student_id, "subscription_id": body.subscription_id},
    )
    return CohortEnrollResponse(
        cohort_id=cohort_id,
        enrolled=True,
        capacity_left=capacity - cohort["enrolled_count"],
    )


@router.post("")
async def create_cohort(name: str = "Нова когорта", subject: str = "math", capacity: int = 30) -> dict:
    cohort_id = new_id("cohort")
    doc = {
        "_id": cohort_id,
        "name": name,
        "subject": subject,
        "level": "standard",
        "capacity": capacity,
        "enrolled_count": 0,
        "start_date": utcnow().date().isoformat(),
        "created_at": utcnow().isoformat(),
    }
    await db.insert_doc("cohorts", doc)
    return doc
