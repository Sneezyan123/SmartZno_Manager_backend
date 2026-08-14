from fastapi import APIRouter

from app import db
from app.schemas import LeadIncoming, LeadResponse
from app.services.spam import normalize_phone, quarantine_score
from app.services.telegram import notify_lead
from app.util import log_action, new_id, utcnow

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/incoming", response_model=LeadResponse)
async def incoming_lead(body: LeadIncoming) -> LeadResponse:
    phone = normalize_phone(body.phone)
    score = quarantine_score(
        honeypot=body.honeypot,
        form_started_at=body.form_started_at,
        email=body.email,
        phone=phone,
    )
    status = "quarantine" if score >= 50 else "new"
    lead_id = new_id("lead")
    doc = {
        "_id": lead_id,
        "phone": phone,
        "email": body.email,
        "name": body.name,
        "grade": body.grade,
        "subject_interest": body.subject_interest,
        "source": body.source,
        "telegram_id": body.telegram_id,
        "utm_source": body.utm_source,
        "utm_medium": body.utm_medium,
        "utm_campaign": body.utm_campaign,
        "utm_content": body.utm_content,
        "utm_term": body.utm_term,
        "quarantine_score": score,
        "status": status,
        "created_at": utcnow().isoformat(),
    }
    await db.insert_doc("leads", doc)
    tg = await notify_lead(doc)
    await log_action(
        "lead_incoming",
        {"id": lead_id, "status": status, "score": score, "telegram": tg.get("delivered")},
    )
    return LeadResponse(
        id=lead_id,
        status=status,
        quarantine_score=score,
        phone=phone,
        telegram_queued=True,
    )


@router.get("")
async def list_leads(limit: int = 50) -> list[dict]:
    return await db.list_docs("leads", limit=limit)
