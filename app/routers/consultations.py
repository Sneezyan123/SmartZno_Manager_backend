from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status

from app import db
from app.routers.staff import teacher_response
from app.schemas import (
    ConsultLeadOption,
    ConsultationCreate,
    ConsultationMetaResponse,
    ConsultationResponse,
    ConsultationUpdate,
    ConsultStudentOption,
)
from app.services.seed import SUBJECT_LABELS, ensure_teachers
from app.util import as_utc, log_action, new_id, utcnow

router = APIRouter(prefix="/consultations", tags=["consultations"])


def _to_response(doc: dict) -> ConsultationResponse:
    starts = as_utc(doc.get("starts_at")) or utcnow()
    duration = int(doc.get("duration_min") or 45)
    ends = as_utc(doc.get("ends_at")) or (starts + timedelta(minutes=duration))
    subject = doc.get("subject") or "math"
    created = as_utc(doc.get("created_at"))
    return ConsultationResponse(
        id=doc["_id"],
        teacher_id=doc.get("teacher_id") or "",
        teacher_name=doc.get("teacher_name") or "",
        starts_at=starts,
        ends_at=ends,
        duration_min=duration,
        subject=subject,
        subject_label=SUBJECT_LABELS.get(subject, subject),
        student_name=doc.get("student_name") or "",
        student_phone=doc.get("student_phone"),
        student_id=doc.get("student_id"),
        lead_id=doc.get("lead_id"),
        notes=doc.get("notes"),
        meeting_url=doc.get("meeting_url"),
        status=doc.get("status") or "scheduled",
        created_at=created,
    )


async def _teacher_or_404(teacher_id: str) -> dict:
    teacher = await db.find_doc("staff", {"_id": teacher_id})
    if teacher is None or teacher.get("role") != "teacher":
        teachers = await ensure_teachers()
        teacher = next((t for t in teachers if t["_id"] == teacher_id), None)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


async def _assert_free(
    teacher_id: str,
    starts: datetime,
    ends: datetime,
    exclude_id: str | None = None,
) -> None:
    items = await db.find_docs("consultations", {"teacher_id": teacher_id}, limit=500)
    for item in items:
        if exclude_id and item.get("_id") == exclude_id:
            continue
        if item.get("status") == "cancelled":
            continue
        other_start = as_utc(item.get("starts_at"))
        other_end = as_utc(item.get("ends_at"))
        if other_start is None:
            continue
        if other_end is None:
            other_end = other_start + timedelta(minutes=int(item.get("duration_min") or 45))
        if _overlaps(starts, ends, other_start, other_end):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="У цього викладача вже є запис на цей час",
            )


def _in_range(starts: datetime, date_from: datetime | None, date_to: datetime | None) -> bool:
    if date_from and starts < date_from:
        return False
    if date_to and starts > date_to:
        return False
    return True


@router.get("/meta", response_model=ConsultationMetaResponse)
async def meta() -> ConsultationMetaResponse:
    teachers = await ensure_teachers()
    teachers.sort(key=lambda t: t.get("name") or "")
    students_raw = await db.list_docs("students", limit=100)
    leads_raw = await db.list_docs("leads", limit=80)
    students = [
        ConsultStudentOption(
            id=s["_id"],
            name=s.get("name") or s.get("email") or "",
            phone=s.get("phone"),
            grade=s.get("grade"),
        )
        for s in students_raw
    ]
    leads = [
        ConsultLeadOption(
            id=lead["_id"],
            name=lead.get("name"),
            phone=lead.get("phone"),
            subject_interest=lead.get("subject_interest"),
        )
        for lead in leads_raw
        if lead.get("status") != "quarantine"
    ]
    return ConsultationMetaResponse(
        teachers=[teacher_response(t) for t in teachers],
        students=students,
        leads=leads,
    )


@router.get("", response_model=list[ConsultationResponse])
async def list_consultations(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    teacher_id: str | None = None,
    status_filter: str | None = None,
) -> list[ConsultationResponse]:
    query: dict = {}
    if teacher_id:
        query["teacher_id"] = teacher_id
    if status_filter:
        query["status"] = status_filter
    items = await db.find_docs("consultations", query, limit=500) if query else await db.list_docs(
        "consultations", limit=500
    )
    from_utc = as_utc(date_from)
    to_utc = as_utc(date_to)
    result: list[ConsultationResponse] = []
    for item in items:
        starts = as_utc(item.get("starts_at"))
        if starts is None:
            continue
        if not _in_range(starts, from_utc, to_utc):
            continue
        result.append(_to_response(item))
    result.sort(key=lambda c: c.starts_at)
    return result


@router.post("", response_model=ConsultationResponse, status_code=201)
async def create_consultation(body: ConsultationCreate) -> ConsultationResponse:
    teacher = await _teacher_or_404(body.teacher_id)
    starts = as_utc(body.starts_at)
    if starts is None:
        raise HTTPException(status_code=400, detail="Invalid starts_at")
    duration = body.duration_min
    ends = starts + timedelta(minutes=duration)
    await _assert_free(body.teacher_id, starts, ends)
    subject = body.subject or teacher.get("subject") or "math"
    consult_id = new_id("con")
    doc = {
        "_id": consult_id,
        "teacher_id": body.teacher_id,
        "teacher_name": teacher.get("name") or "",
        "starts_at": starts.isoformat(),
        "ends_at": ends.isoformat(),
        "duration_min": duration,
        "subject": subject,
        "student_name": body.student_name.strip(),
        "student_phone": body.student_phone,
        "student_id": body.student_id,
        "lead_id": body.lead_id,
        "notes": body.notes,
        "meeting_url": body.meeting_url or teacher.get("zoom_url"),
        "status": "scheduled",
        "created_at": utcnow().isoformat(),
    }
    await db.insert_doc("consultations", doc)
    await log_action("consultation_created", {"id": consult_id, "teacher_id": body.teacher_id})
    return _to_response(doc)


@router.patch("/{consultation_id}", response_model=ConsultationResponse)
async def update_consultation(consultation_id: str, body: ConsultationUpdate) -> ConsultationResponse:
    doc = await db.find_doc("consultations", {"_id": consultation_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Consultation not found")

    patch = body.model_dump(exclude_unset=True)
    teacher_id = patch.get("teacher_id") or doc.get("teacher_id")
    teacher = await _teacher_or_404(teacher_id)

    starts = as_utc(patch["starts_at"]) if "starts_at" in patch else as_utc(doc.get("starts_at"))
    if starts is None:
        raise HTTPException(status_code=400, detail="Invalid starts_at")
    duration = int(patch.get("duration_min") or doc.get("duration_min") or 45)
    ends = starts + timedelta(minutes=duration)
    new_status = patch.get("status") or doc.get("status")
    if new_status != "cancelled":
        await _assert_free(teacher_id, starts, ends, exclude_id=consultation_id)

    if "student_name" in patch and patch["student_name"]:
        patch["student_name"] = patch["student_name"].strip()
    if "subject" not in patch:
        if patch.get("teacher_id") and patch["teacher_id"] != doc.get("teacher_id"):
            patch["subject"] = teacher.get("subject") or doc.get("subject")
    patch.update(
        {
            "teacher_id": teacher_id,
            "teacher_name": teacher.get("name") or doc.get("teacher_name"),
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
            "duration_min": duration,
            "updated_at": utcnow().isoformat(),
        }
    )
    if not patch.get("meeting_url") and patch.get("teacher_id") != doc.get("teacher_id"):
        patch["meeting_url"] = teacher.get("zoom_url")

    updated = await db.update_doc("consultations", {"_id": consultation_id}, patch)
    await log_action("consultation_updated", {"id": consultation_id, "fields": list(body.model_dump(exclude_unset=True))})
    return _to_response(updated or {**doc, **patch})


@router.delete("/{consultation_id}", response_model=ConsultationResponse)
async def cancel_consultation(consultation_id: str) -> ConsultationResponse:
    doc = await db.find_doc("consultations", {"_id": consultation_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    updated = await db.update_doc(
        "consultations",
        {"_id": consultation_id},
        {"status": "cancelled", "updated_at": utcnow().isoformat()},
    )
    await log_action("consultation_cancelled", {"id": consultation_id})
    return _to_response(updated or {**doc, "status": "cancelled"})
