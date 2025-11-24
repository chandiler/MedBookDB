# app/routers/doctors.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query,status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permission import require_roles
from app.db.sql import get_session
from app.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.users.schemas import PatientListItem, PatientListParams, PatientPage, PatientUpdateRequest
from app.modules.users.service import DoctorNotFound, list_doctors, update_doctor

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

@router.put(
    "/doctors/{doctor_id}",
    response_model=PatientListItem,
    summary="Update a doctor by id (doctor/admin only)",
)
async def doctors_update(
    doctor_id: UUID,
    payload: PatientUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles("doctor", "admin")),
):
    """
    Update a doctor (first_name, last_name, phone) by id.

    Notes:
    - Requires a valid Bearer token with role 'doctor' or 'admin'.
    - Returns 404 if the doctor does not exist or is not role='doctor'.
    """
    try:
        return await update_doctor(session, doctor_id, payload)
    except DoctorNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="doctor_not_found",
        )
