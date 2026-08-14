"""Background worker stubs — no production scheduler in skeleton."""

from datetime import datetime, timezone


async def demo_expiry_sweep() -> dict:
    return {"worker": "demo_expiry", "ran_at": datetime.now(timezone.utc).isoformat(), "processed": 0}


async def subscription_dunning_sweep() -> dict:
    return {"worker": "dunning", "ran_at": datetime.now(timezone.utc).isoformat(), "processed": 0}


async def curator_sla_sweep() -> dict:
    return {"worker": "curator_sla", "ran_at": datetime.now(timezone.utc).isoformat(), "breaches": 0}
