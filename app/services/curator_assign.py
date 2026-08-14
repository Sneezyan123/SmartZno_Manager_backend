from app import db


SEED_CURATORS = [
    {"_id": "cur_1", "name": "Олена Куратор", "role": "curator", "capacity_limit": 40, "load": 12},
    {"_id": "cur_2", "name": "Ігор Куратор", "role": "curator", "capacity_limit": 40, "load": 18},
    {"_id": "cur_3", "name": "Марія Premium", "role": "curator", "capacity_limit": 25, "load": 8},
]


async def ensure_curators() -> list[dict]:
    existing = await db.list_docs("staff", limit=50)
    curators = [s for s in existing if s.get("role") == "curator"]
    if curators:
        return curators
    for c in SEED_CURATORS:
        await db.insert_doc("staff", dict(c))
    return list(SEED_CURATORS)


async def assign_least_load(*, prefer_premium: bool = False) -> dict:
    curators = await ensure_curators()
    pool = curators
    if prefer_premium:
        premium = [c for c in curators if "Premium" in c.get("name", "")]
        if premium:
            pool = premium
    available = [c for c in pool if c.get("load", 0) < c.get("capacity_limit", 40)]
    if not available:
        available = pool
    chosen = min(available, key=lambda c: c.get("load", 0))
    chosen["load"] = int(chosen.get("load", 0)) + 1
    return chosen
