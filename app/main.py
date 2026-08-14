from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.routers import (
    auth,
    cohorts,
    curators,
    demo,
    diagnostics,
    health,
    leads,
    payments,
    students,
    subscriptions,
)
from app.services.seed import ensure_demo_data


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await db.connect_db()
    await ensure_demo_data()
    yield
    await db.close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(leads.router)
    app.include_router(diagnostics.router)
    app.include_router(demo.router)
    app.include_router(subscriptions.router)
    app.include_router(payments.router)
    app.include_router(cohorts.router)
    app.include_router(curators.router)
    app.include_router(students.router)
    return app


app = create_app()
