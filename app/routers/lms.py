from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app import db
from app.config import Settings, get_settings
from app.routers.students import require_student
from app.util import utcnow

router = APIRouter(prefix="/lms", tags=["lms"])


class ProgressBody(BaseModel):
    lessons: dict[str, Any] = Field(default_factory=dict)
    profile: dict[str, Any] = Field(default_factory=dict)


class CuratorCheckBody(BaseModel):
    student_id: str
    lesson_id: str
    checked: bool = True


def _public_progress(student_id: str, doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"student_id": student_id, "lessons": {}, "profile": {}}
    return {
        "student_id": student_id,
        "lessons": doc.get("lessons", {}),
        "profile": doc.get("profile", {}),
        "updated_at": doc.get("updated_at"),
    }


@router.get("/progress")
async def get_progress(student: dict[str, Any] = Depends(require_student)) -> dict[str, Any]:
    doc = await db.find_doc("lms_progress", {"student_id": student["_id"]})
    return _public_progress(student["_id"], doc)


@router.put("/progress")
async def put_progress(
    body: ProgressBody,
    student: dict[str, Any] = Depends(require_student),
) -> dict[str, Any]:
    await db.upsert_doc(
        "lms_progress",
        {"student_id": student["_id"]},
        {
            "lessons": body.lessons,
            "profile": body.profile,
            "updated_at": utcnow().isoformat(),
        },
    )
    return {"ok": True, "store": "mongo" if not db.using_memory() else "memory"}


@router.get("/parent-digest")
async def parent_digest(student: dict[str, Any] = Depends(require_student)) -> dict[str, Any]:
    doc = await db.find_doc("lms_progress", {"student_id": student["_id"]})
    lessons: dict[str, Any] = (doc or {}).get("lessons", {})
    profile: dict[str, Any] = (doc or {}).get("profile", {})
    hw_done = sum(1 for p in lessons.values() if p.get("homeworkChecked"))
    hw_total = len(lessons)
    cards = 0
    cards_n = 0
    for p in lessons.values():
        seen = len(p.get("cardsSeen") or [])
        if seen or p.get("theoryDone"):
            cards += 1
            cards_n += 1
    last_mock = None
    last_score = None
    for lid, p in lessons.items():
        if str(lid).startswith("m7-") and p.get("homeworkChecked"):
            last_mock = lid
            last_score = p.get("homeworkScore")
    return {
        "student_name": student.get("name"),
        "level": profile.get("level", "B"),
        "trackId": profile.get("trackId"),
        "hwDone": hw_done,
        "hwTracked": hw_total,
        "lessonsTouched": cards_n,
        "lastMock": last_mock,
        "lastMockScore": last_score,
        "lastHwAt": profile.get("lastHwAt"),
        "curatorCheckedCount": sum(1 for v in (profile.get("curatorChecked") or {}).values() if v),
    }


@router.post("/curator/homework-checked")
async def curator_homework_checked(
    body: CuratorCheckBody,
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if x_api_key not in {settings.crm_api_key, settings.lms_api_key}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    doc = await db.find_doc("lms_progress", {"student_id": body.student_id})
    lessons = dict((doc or {}).get("lessons") or {})
    lesson = dict(lessons.get(body.lesson_id) or {})
    lesson["curatorChecked"] = body.checked
    lesson["updatedAt"] = utcnow().isoformat()
    lessons[body.lesson_id] = lesson
    profile = dict((doc or {}).get("profile") or {})
    checked = dict(profile.get("curatorChecked") or {})
    checked[body.lesson_id] = body.checked
    profile["curatorChecked"] = checked
    await db.upsert_doc(
        "lms_progress",
        {"student_id": body.student_id},
        {"lessons": lessons, "profile": profile, "updated_at": utcnow().isoformat()},
    )
    return {"ok": True, "lesson_id": body.lesson_id, "checked": body.checked}
