from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app import db


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def kyiv_tz():
    try:
        return ZoneInfo("Europe/Kyiv")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=3))


def as_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=kyiv_tz())
    return value.astimezone(timezone.utc)


async def log_action(action: str, payload: dict[str, Any]) -> None:
    await db.insert_doc(
        "crm_logs",
        {
            "_id": new_id("log"),
            "action": action,
            "payload": payload,
            "at": utcnow().isoformat(),
        },
    )
