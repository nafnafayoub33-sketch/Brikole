"""Liveness, and the schema version the web app was built against."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.deps import DbSession, SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "env": settings.env}


@router.get("/health/db")
def health_db(db: DbSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
