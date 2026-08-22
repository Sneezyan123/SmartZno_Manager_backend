from fastapi import APIRouter

from app.schemas import TeacherResponse
from app.services.seed import SUBJECT_LABELS, ensure_teachers

router = APIRouter(prefix="/staff", tags=["staff"])


def teacher_response(doc: dict) -> TeacherResponse:
    subject = doc.get("subject") or "math"
    return TeacherResponse(
        id=doc["_id"],
        name=doc.get("name") or "",
        subject=subject,
        subject_label=SUBJECT_LABELS.get(subject, subject),
        role=doc.get("role") or "teacher",
        email=doc.get("email"),
        zoom_url=doc.get("zoom_url"),
    )


@router.get("/teachers", response_model=list[TeacherResponse])
async def list_teachers() -> list[TeacherResponse]:
    teachers = await ensure_teachers()
    teachers.sort(key=lambda t: t.get("name") or "")
    return [teacher_response(t) for t in teachers]
