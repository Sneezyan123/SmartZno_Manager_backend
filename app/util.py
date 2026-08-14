from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app import db


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
