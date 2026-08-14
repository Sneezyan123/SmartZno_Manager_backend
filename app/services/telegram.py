"""Telegram notify for new leads / diagnostics.

If TELEGRAM_BOT_TOKEN or TELEGRAM_NOTIFY_CHAT_ID is missing, messages are
stored in memory (and printed) so local demo still works.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app import db
from app.config import get_settings
from app.util import new_id, utcnow

logger = logging.getLogger(__name__)

_outbox: list[dict[str, Any]] = []


def telegram_outbox() -> list[dict[str, Any]]:
    return list(_outbox)


async def send_telegram(text: str, *, kind: str = "notify") -> dict[str, Any]:
    settings = get_settings()
    record: dict[str, Any] = {
        "_id": new_id("tg"),
        "kind": kind,
        "text": text,
        "at": utcnow().isoformat(),
        "delivered": False,
        "error": None,
    }

    token = (settings.telegram_bot_token or "").strip()
    chat_id = (settings.telegram_notify_chat_id or "").strip()

    if not token or not chat_id:
        record["error"] = "telegram_not_configured"
        print(f"[telegram stub] {text.replace(chr(10), ' | ')}", flush=True)
        _outbox.append(record)
        await db.insert_doc("telegram_outbox", record)
        return record

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            res = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
            )
            res.raise_for_status()
            record["delivered"] = True
    except Exception as exc:  # noqa: BLE001 — surface soft-fail to CRM
        record["error"] = str(exc)
        logger.warning("Telegram send failed: %s", exc)

    _outbox.append(record)
    await db.insert_doc("telegram_outbox", record)
    return record


async def notify_lead(doc: dict[str, Any]) -> dict[str, Any]:
    lines = [
        "🆕 Нова заявка SmartZno",
        f"ID: {doc.get('_id')}",
        f"Імʼя: {doc.get('name') or '—'}",
        f"Телефон: {doc.get('phone')}",
        f"Клас: {doc.get('grade') or '—'}",
        f"Предмет: {doc.get('subject_interest') or '—'}",
        f"Джерело: {doc.get('source') or '—'}",
        f"Статус: {doc.get('status')} (spam {doc.get('quarantine_score', 0)})",
    ]
    if doc.get("utm_source"):
        lines.append(
            f"UTM: {doc.get('utm_source')}/{doc.get('utm_medium')}/{doc.get('utm_campaign')}"
        )
    return await send_telegram("\n".join(lines), kind="lead")


async def notify_diagnostic(doc: dict[str, Any]) -> dict[str, Any]:
    lines = [
        "📊 Діагностика SmartZno",
        f"ID: {doc.get('_id')}",
        f"Предмет: {doc.get('subject')}",
        f"Бал: {doc.get('score')}/200 · перцентиль {doc.get('percentile')}",
        f"Трек: {doc.get('recommended_track')} → {doc.get('offer_segment')}",
        f"Клас: {doc.get('grade') or '—'}",
        f"Телефон: {doc.get('contact_phone') or '—'}",
        f"Email: {doc.get('contact_email') or '—'}",
        f"Імʼя: {doc.get('contact_name') or '—'}",
    ]
    return await send_telegram("\n".join(lines), kind="diagnostic")
