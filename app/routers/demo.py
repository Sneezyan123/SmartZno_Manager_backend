from datetime import timedelta

from fastapi import APIRouter

from app import db
from app.schemas import DemoAccessCreate, DemoAccessResponse
from app.util import log_action, new_id, utcnow

router = APIRouter(prefix="/demo-accesses", tags=["demo"])


@router.post("", response_model=DemoAccessResponse)
async def create_demo(body: DemoAccessCreate) -> DemoAccessResponse:
    starts = utcnow()
    ends = starts + timedelta(days=body.days)
    demo_id = new_id("demo")
    doc = {
        "_id": demo_id,
        "student_id": body.student_id,
        "phone": body.phone,
        "course_ids": body.course_ids,
        "starts_at": starts.isoformat(),
        "ends_at": ends.isoformat(),
        "first_hw_submitted_at": None,
        "converted_at": None,
        "status": "active",
    }
    await db.insert_doc("demo_accesses", doc)
    await log_action("demo_access_created", {"id": demo_id, "days": body.days})
    return DemoAccessResponse(id=demo_id, starts_at=starts, ends_at=ends, status="active")
