# app/routers/appointments.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sql import get_session
from app.dependencies import get_current_user
from app.modules.users.models import User
from app.core.permissions import require_roles

from app.modules.appointments.schemas import (
    AppointmentCreateRequest,
    AppointmentPublic,
    AppointmentListPage,
)
from app.modules.appointments.service import (
    create_appointment_svc,
    list_my_appointments_svc,
    cancel_appointment_svc,
    list_appointments_by_doctor_svc,
    AppointmentConflict,
    AppointmentNotFound,
    AppointmentForbidden,
)

router = APIRouter(tags=["appointments"])


# Implement /appointments/create (POST)
@router.post(
    "/appointments/create",
    response_model=AppointmentPublic,
    summary="Create appointment (transactional execution)",
)
async def appointments_create(
    payload: AppointmentCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),  # Bearer required
):
    try:
        return await create_appointment_svc(session, payload, current_user)
    except AppointmentForbidden as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e) or "forbidden",
        )
    except AppointmentConflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="appointment_conflict",
        )


# Implement /appointments/my (GET)
@router.get(
    "/appointments/my",
    response_model=AppointmentListPage,
    summary="Retrieve current user's appointments",
)
async def appointments_my(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await list_my_appointments_svc(session, current_user, limit, offset)


# Implement /appointments/{id}/cancel (PUT)
@router.put(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentPublic,
    summary="Cancel an appointment",
)
async def appointments_cancel(
    appointment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    try:
        return await cancel_appointment_svc(session, appointment_id, current_user)
    except AppointmentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="appointment_not_found",
        )
    except AppointmentForbidden as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e) or "forbidden",
        )


# Implement /appointments/doctor/{id} (GET)
@router.get(
    "/appointments/doctor/{doctor_id}",
    response_model=AppointmentListPage,
    summary="Doctor views their scheduled appointments",
)
async def appointments_for_doctor(
    doctor_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    # Only for doctor or admin to call: use require_roles from core/permission.py
    current_user: User = Depends(require_roles("doctor", "admin")),
):
    # If doctor, show their own schedule.
    if current_user.role == "doctor" and current_user.id != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cannot_view_other_doctor_schedule",
        )

    return await list_appointments_by_doctor_svc(
        session,
        doctor_id=doctor_id,
        limit=limit,
        offset=offset,
    )