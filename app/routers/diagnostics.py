from fastapi import APIRouter, HTTPException

from app import db
from app.schemas import DiagnosticAttemptCreate, DiagnosticAttemptResponse
from app.services.scoring import score_diagnostic
from app.services.spam import normalize_phone, quarantine_score
from app.services.telegram import notify_diagnostic
from app.util import log_action, new_id, utcnow

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.post("/attempts", response_model=DiagnosticAttemptResponse)
async def create_attempt(body: DiagnosticAttemptCreate) -> DiagnosticAttemptResponse:
    score, percentile, track, segment = score_diagnostic(body.subject, body.answers)
    attempt_id = new_id("diag")
    phone = normalize_phone(body.contact_phone) if body.contact_phone else None
    doc = {
        "_id": attempt_id,
        "subject": body.subject,
        "answers": body.answers,
        "score": score,
        "percentile": percentile,
        "recommended_track": track,
        "offer_segment": segment,
        "contact_phone": phone,
        "contact_email": body.contact_email,
        "contact_name": body.contact_name,
        "grade": body.grade,
        "utm_source": body.utm_source,
        "utm_medium": body.utm_medium,
        "utm_campaign": body.utm_campaign,
        "created_at": utcnow().isoformat(),
    }
    await db.insert_doc("diagnostic_attempts", doc)

    # Also create a CRM lead when contact is provided
    if phone:
        q = quarantine_score(
            honeypot=body.honeypot,
            form_started_at=body.form_started_at,
            email=body.contact_email,
            phone=phone,
        )
        lead_id = new_id("lead")
        lead = {
            "_id": lead_id,
            "phone": phone,
            "email": body.contact_email,
            "name": body.contact_name,
            "grade": body.grade,
            "subject_interest": body.subject,
            "source": "diagnostic",
            "telegram_id": None,
            "utm_source": body.utm_source,
            "utm_medium": body.utm_medium,
            "utm_campaign": body.utm_campaign,
            "utm_content": None,
            "utm_term": None,
            "quarantine_score": q,
            "status": "quarantine" if q >= 50 else "new",
            "diagnostic_id": attempt_id,
            "created_at": utcnow().isoformat(),
        }
        await db.insert_doc("leads", lead)

    tg = await notify_diagnostic(doc)
    await log_action(
        "diagnostic_attempt",
        {"id": attempt_id, "score": score, "segment": segment, "telegram": tg.get("delivered")},
    )
    return DiagnosticAttemptResponse(
        id=attempt_id,
        subject=body.subject,
        score=score,
        percentile=percentile,
        recommended_track=track,
        offer_segment=segment,
        telegram_queued=True,
    )


@router.get("/attempts/{attempt_id}", response_model=DiagnosticAttemptResponse)
async def get_attempt(attempt_id: str) -> DiagnosticAttemptResponse:
    doc = await db.find_doc("diagnostic_attempts", {"_id": attempt_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return DiagnosticAttemptResponse(
        id=doc["_id"],
        subject=doc["subject"],
        score=doc["score"],
        percentile=doc["percentile"],
        recommended_track=doc["recommended_track"],
        offer_segment=doc["offer_segment"],
    )
