from datetime import datetime, timedelta, timezone

from app import db
from app.util import new_id


async def acquire_lock(name: str, ttl_seconds: int = 60) -> bool:
    now = datetime.now(timezone.utc)
    existing = await db.find_doc("crm_locks", {"_id": name})
    if existing:
        expires = existing.get("expires_at")
        if isinstance(expires, str):
            expires_dt = datetime.fromisoformat(expires)
        else:
            expires_dt = expires
        if expires_dt and expires_dt > now:
            return False
    doc = {
        "_id": name,
        "owner": new_id("lock"),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
    }
    # memory mode: overwrite; mongo would use upsert
    store = db.memory_store()
    locks = store.setdefault("crm_locks", [])
    locks[:] = [x for x in locks if x.get("_id") != name]
    locks.append(doc)
    if not db.using_memory():
        database = db.get_db()
        if database is not None:
            await database["crm_locks"].update_one({"_id": name}, {"$set": doc}, upsert=True)
    return True
