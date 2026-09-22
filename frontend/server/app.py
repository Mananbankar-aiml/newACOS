"""ACOS API — FastAPI application factory."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from starlette.middleware.cors import CORSMiddleware

from core.config import settings
from core.db import client, ensure_indexes
from routers import admin, agents, approvals, auth, files, insights, records, users
from seed import bootstrap_admin, ensure_agents_and_schedules, seed_demo_records
import scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("acos")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_indexes()
    await ensure_agents_and_schedules()
    await seed_demo_records()
    await bootstrap_admin()
    task = None
    if not settings.IS_SERVERLESS:
        task = asyncio.create_task(scheduler.loop())
    else:
        logger.info("Serverless runtime detected — scheduler loop disabled; call /api/internal/scheduler/tick from cron.")
    yield
    if task:
        task.cancel()
    client.close()


def build_cors_kwargs() -> dict:
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if not origins or origins == ["*"]:
        # Wildcard + credentials is invalid per the CORS spec, so credentials are disabled here.
        return {"allow_origins": ["*"], "allow_credentials": False}
    return {"allow_origins": origins, "allow_credentials": True}


def create_app() -> FastAPI:
    app = FastAPI(title="ACOS API", version="1.0.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(CORSMiddleware, allow_methods=["*"], allow_headers=["*"], **build_cors_kwargs())
    for r in (auth.router, users.router, records.router, approvals.router, agents.router, files.router, insights.router, admin.router):
        app.include_router(r, prefix="/api")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "llm_configured": bool(settings.LLM_API_KEY), "llm_model": settings.LLM_MODEL, "google_auth": bool(settings.GOOGLE_CLIENT_ID),
                "email_provider": "resend" if settings.RESEND_API_KEY else "console"}

    @app.post("/api/internal/scheduler/tick")
    async def scheduler_tick(x_cron_secret: str = Header(None)):
        expected = os.environ.get("CRON_SECRET")
        if not expected or x_cron_secret != expected:
            raise HTTPException(401, "Invalid cron secret")
        return {"ran": await scheduler.tick()}

    return app


app = create_app()
