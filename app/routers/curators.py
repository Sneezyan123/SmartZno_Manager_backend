from datetime import datetime, timedelta

from fastapi import APIRouter

from app import db
from app.schemas import CuratorAssignRequest, CuratorAssignResponse, SlaItem
from app.services.curator_assign import assign_least_load
from app.util import log_action, new_id, utcnow

router = APIRouter(prefix="/curators", tags=["curators"])


@router.post("/assign", response_model=CuratorAssignResponse)
async def assign(body: CuratorAssignRequest) -> CuratorAssignResponse:
    curator = await assign_least_load(prefer_premium=body.prefer_premium)
    sub = await db.find_doc("subscriptions", {"_id": body.subscription_id})
    if sub is not None:
        sub["curator_id"] = curator["_id"]
    await log_action(
        "curator_assign",
        {
            "curator_id": curator["_id"],
            "student_id": body.student_id,
            "subscription_id": body.subscription_id,
        },
    )
    return CuratorAssignResponse(
        curator_id=curator["_id"],
        curator_name=curator["name"],
        load=int(curator.get("load", 0)),
    )


@router.get("/sla", response_model=list[SlaItem])
async def sla_breaches() -> list[SlaItem]:
    now = utcnow()
    items = await db.list_docs("homework_submissions", limit=100)
    if not items:
        demo = {
            "_id": new_id("hw"),
            "student_id": "stu_demo",
            "due_at": (now - timedelta(hours=30)).isoformat(),
            "reviewed_at": None,
            "sla_hours": 24,
        }
        await db.insert_doc("homework_submissions", demo)
        items = [demo]

    result: list[SlaItem] = []
    for hw in items:
        due_raw = hw.get("due_at")
        if isinstance(due_raw, str):
            due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
        else:
            due_at = due_raw or now
        reviewed = hw.get("reviewed_at")
        breach = reviewed is None and (now - due_at).total_seconds() > 24 * 3600
        if breach:
            result.append(
                SlaItem(
                    homework_id=hw["_id"],
                    student_id=hw.get("student_id", ""),
                    due_at=due_at,
                    breach=True,
                )
            )
    return result
