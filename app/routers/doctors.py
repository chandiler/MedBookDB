# app/routers/doctors.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sql import get_session
from app.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.users.schemas import PatientListParams, PatientPage
from app.modules.users.service import list_doctors

router = APIRouter(tags=["doctors"])


@router.get(
    "/doctors",
    response_model=PatientPage,
    summary="List doctors (Bearer required, no role checks)",
)
async def doctors_index(
    q: str | None = Query(None, description="Search on email/first_name/last_name"),
    is_active: bool | None = Query(None),
    email_verified: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    order_by: str = Query("created_at", pattern="^(created_at|last_name|email)$"),
    order_dir: str = Query("desc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),  # Bearer only
):
    params = PatientListParams(
        q=q,
        is_active=is_active,
        email_verified=email_verified,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
    )
    return await list_doctors(session, params)
