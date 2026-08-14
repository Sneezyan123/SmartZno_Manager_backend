from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_memory: dict[str, list[dict[str, Any]]] = {}
_use_memory = False

MEMORY_COLLECTIONS = (
    "leads",
    "diagnostic_attempts",
    "demo_accesses",
    "subscriptions",
    "cohorts",
    "staff",
    "students",
    "parents",
    "homework_submissions",
    "payment_ledger",
    "crm_locks",
    "crm_logs",
    "telegram_outbox",
)


def memory_store() -> dict[str, list[dict[str, Any]]]:
    return _memory


def using_memory() -> bool:
    return _use_memory


async def connect_db() -> None:
    global _client, _db, _use_memory
    settings = get_settings()
    try:
        _client = AsyncIOMotorClient(
            settings.mongodb_crm_uri,
            serverSelectionTimeoutMS=1500,
        )
        await _client.admin.command("ping")
        _db = _client[settings.mongodb_crm_db]
        _use_memory = False
    except Exception:
        _client = None
        _db = None
        _use_memory = True
        for key in MEMORY_COLLECTIONS:
            _memory.setdefault(key, [])


async def close_db() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def get_db() -> AsyncIOMotorDatabase | None:
    return _db


async def insert_doc(collection: str, doc: dict[str, Any]) -> dict[str, Any]:
    if _use_memory or _db is None:
        _memory.setdefault(collection, []).append(doc)
        return doc
    await _db[collection].insert_one(doc)
    return doc


async def find_doc(collection: str, query: dict[str, Any]) -> dict[str, Any] | None:
    if _use_memory or _db is None:
        items = _memory.get(collection, [])
        for item in items:
            if all(item.get(k) == v for k, v in query.items()):
                return item
        return None
    return await _db[collection].find_one(query)


async def find_docs(collection: str, query: dict[str, Any], limit: int = 100) -> list[dict[str, Any]]:
    if _use_memory or _db is None:
        items = _memory.get(collection, [])
        matched = [item for item in items if all(item.get(k) == v for k, v in query.items())]
        return matched[:limit]
    cursor = _db[collection].find(query).limit(limit)
    return await cursor.to_list(length=limit)


async def list_docs(collection: str, limit: int = 100) -> list[dict[str, Any]]:
    if _use_memory or _db is None:
        return list(_memory.get(collection, []))[:limit]
    cursor = _db[collection].find().limit(limit)
    return await cursor.to_list(length=limit)


async def update_doc(collection: str, query: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any] | None:
    if _use_memory or _db is None:
        items = _memory.get(collection, [])
        for item in items:
            if all(item.get(k) == v for k, v in query.items()):
                item.update(patch)
                return item
        return None
    from pymongo import ReturnDocument

    result = await _db[collection].find_one_and_update(
        query,
        {"$set": patch},
        return_document=ReturnDocument.AFTER,
    )
    return result
