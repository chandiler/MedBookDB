# app/routers/health.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.sql import get_session

router = APIRouter()

@router.get("/health")
async def health_root():
    return {"status": "ok"}

@router.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)):
    """
    Validates PostgreSQL connectivity with SELECT 1 and exposes server_version.
    Returns 503 if no connectivity (useful for readiness/liveness checks).
    """
    try:
        await session.execute(text("SELECT 1"))
        result = await session.execute(text("SHOW server_version"))
        version = result.scalar_one_or_none()
        return {"status": "ok", "database": "postgresql", "server_version": version}
    except SQLAlchemyError as exc:
        # Don't expose internal details
        raise HTTPException(status_code=503, detail="database_unavailable") from exc