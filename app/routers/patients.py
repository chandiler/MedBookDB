# app/routers/patients.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sql import get_session
from app.dependencies import get_current_user, require_roles
from app.modules.users.models import User
from app.modules.users.schemas import (
    PatientListItem,
    PatientListParams,
    PatientPage,
    PatientUpdateRequest,
)
from app.modules.users.service import (
    list_patients,
    get_patient_by_id as get_patient_by_id_svc,
    update_patient as update_patient_svc,
    delete_patient as delete_patient_svc,
    PatientNotFound,
)

router = APIRouter(tags=["patients"])


@router.get(
    "/patients",
    response_model=PatientPage,
    summary="List patients (doctor/admin only)",
)
async def patients_index(
    q: str | None = Query(None, description="Search on email/first_name/last_name"),
    is_active: bool | None = Query(None),
    email_verified: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    order_by: str = Query("created_at", pattern="^(created_at|last_name|email)$"),
    order_dir: str = Query("desc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles("doctor", "admin")),
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
    return await list_patients(session, params)


@router.get(
    "/patients/{patient_id}",
    response_model=PatientListItem,
    summary="Get a patient by id (doctor/admin only)",
)
async def patients_show(
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles("doctor", "admin")),
):
    try:
        return await get_patient_by_id_svc(session, patient_id)
    except PatientNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient_not_found",
        )


@router.put(
    "/patients/{patient_id}",
    response_model=PatientListItem,
    summary="Update a patient by id (doctor/admin only)",
)
async def patients_update(
    patient_id: UUID,
    payload: PatientUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles("doctor", "admin")),
):
    try:
        return await update_patient_svc(session, patient_id, payload)
    except PatientNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient_not_found",
        )


@router.delete(
    "/patients/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a patient by id (doctor/admin only)",
)
async def patients_delete(
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles("doctor", "admin")),
):
    """
    Delete a patient by id.

    Notes:
    - Requires a valid Bearer token with role 'doctor' or 'admin'.
    - Returns 204 on success, 404 if the patient does not exist.
    """
    try:
        await delete_patient_svc(session, patient_id)
    except PatientNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient_not_found",
        )
