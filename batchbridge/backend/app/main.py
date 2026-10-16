import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import (
    auth,
    cases,
    catalog,
    escalations,
    evidence,
    health,
    imports,
    inspections,
    reports,
)
from app.config import get_settings
from app.database import SessionLocal
from app.dependencies import enforce_origin
from app.models import AgentRun
from app.seed import seed_demo_data
from app.services.investigation import execute_investigation


@asynccontextmanager
async def lifespan(_app: FastAPI):
    recovery_tasks: list[asyncio.Task] = []
    if get_settings().seed_demo_data:
        with SessionLocal() as db:
            seed_demo_data(db)
    with SessionLocal() as db:
        interrupted = db.scalars(
            select(AgentRun).where(AgentRun.status.in_(["queued", "running"]))
        ).all()
        for run in interrupted:
            run.status = "queued"
        db.commit()
        recovery_tasks = [asyncio.create_task(execute_investigation(run.id)) for run in interrupted]
    yield
    for task in recovery_tasks:
        if not task.done():
            task.cancel()


app = FastAPI(
    title="BatchBridge API",
    version="0.1.0",
    description="Human-approved international food batch investigation workflow",
    lifespan=lifespan,
    dependencies=[Depends(enforce_origin)],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(evidence.router, prefix="/api/v1")
app.include_router(imports.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(inspections.router, prefix="/api/v1")
app.include_router(escalations.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "name": "BatchBridge API",
        "docs": "/docs",
        "health": "/health/ready",
    }
