# app/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.sql import get_session

router = APIRouter()

@router.get("/health")
async def health_root():
    return {"status": "ok"}

@router.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)):
    await session.execute(text("SELECT 1"))
    result = await session.execute(text("SHOW server_version"))
    version = result.scalar_one_or_none()
    return {"status": "ok", "database": "postgresql", "server_version": version}
