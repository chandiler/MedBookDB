# app/modules/appointments/service.py
from __future__ import annotations

from typing import Tuple, List
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointments.models import Appointment, ApptStatus
from app.modules.appointments.schemas import (
    AppointmentCreateRequest,
    AppointmentPublic,
    AppointmentListItem,
    AppointmentListPage,
)
from app.modules.users.models import User


# Custom errors để router mapping sang HTTP
class AppointmentConflict(Exception):
    """
    Duplicate slots / constraint violations (double booking, etc.)
    """


class AppointmentNotFound(Exception):
    """
    No appointment found
    """


class AppointmentForbidden(Exception):
    """
    User does not have permission to operate this appointment
    """


def _to_public(appt: Appointment) -> AppointmentPublic:
    return AppointmentPublic.model_validate(appt)


def _to_list_item(appt: Appointment) -> AppointmentListItem:
    return AppointmentListItem.model_validate(appt)


# CREATE
async def create_appointment_svc(
    session: AsyncSession,
    payload: AppointmentCreateRequest,
    current_user: User,
) -> AppointmentPublic:
    """
    Create new appointment (transaction-safe because using get_session).

    Logic:
    - Only allow role 'patient' to create (matches requirement).
    - patient_id = current_user.id
    - Check not to double book the same doctor, same day, same start_time.
    """
    if current_user.role != "patient":
        raise AppointmentForbidden("only_patients_can_create")

    # Check conflict đơn giản
    stmt_conflict = select(Appointment).where(
        and_(
            Appointment.doctor_id == payload.doctor_id,
            Appointment.appointment_date == payload.appointment_date,
            Appointment.start_time == payload.start_time,
            Appointment.status != ApptStatus.CANCELLED.value,
        )
    )
    if (await session.execute(stmt_conflict)).scalar_one_or_none():
        raise AppointmentConflict("slot_already_taken")

    appt = Appointment(
        patient_id=current_user.id,
        doctor_id=payload.doctor_id,
        appointment_date=payload.appointment_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=ApptStatus.SCHEDULED.value,
    )

    session.add(appt)
    await session.flush()
    await session.refresh(appt)
    return _to_public(appt)


# MY APPOINTMENTS
async def list_my_appointments_svc(
    session: AsyncSession,
    current_user: User,
    limit: int,
    offset: int,
) -> AppointmentListPage:
    """
    Get appointment for current user.
    - patient => appointment where user is patient
    - doctor => appointment where user is doctor
    - admin => view all (demo for admin rights)
    """
    if current_user.role == "patient":
        cond = Appointment.patient_id == current_user.id
    elif current_user.role == "doctor":
        cond = Appointment.doctor_id == current_user.id
    else:  # admin
        cond = True  # no filter

    # Count total
    total_stmt = select(func.count()).select_from(Appointment).where(cond)
    total = (await session.execute(total_stmt)).scalar_one()

    # Page
    stmt = (
        select(Appointment)
        .where(cond)
        .order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())
        .limit(limit)
        .offset(offset)
    )
    rows: List[Appointment] = (await session.execute(stmt)).scalars().all()
    items = [_to_list_item(a) for a in rows]
    has_next = offset + limit < total

    return AppointmentListPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_next=has_next,
    )


# CANCEL
async def cancel_appointment_svc(
    session: AsyncSession,
    appointment_id: UUID,
    current_user: User,
) -> AppointmentPublic:
    """
    User cancels appointment:
    - patient can only cancel his own appointment
    - doctor can only cancel appointments in which he is the doctor
    - admin cancels all
    """
    appt = await session.get(Appointment, appointment_id)
    if not appt:
        raise AppointmentNotFound("appointment_not_found")

    # Permission
    if current_user.role == "patient" and appt.patient_id != current_user.id:
        raise AppointmentForbidden("not_owner")
    if current_user.role == "doctor" and appt.doctor_id != current_user.id:
        raise AppointmentForbidden("not_owner")
    # admin => full access

    # If canceled, it can be considered idempotent and returned immediately.
    if appt.status == ApptStatus.CANCELLED.value:
        return _to_public(appt)

    appt.status = ApptStatus.CANCELLED.value
    await session.flush()
    await session.refresh(appt)
    return _to_public(appt)


# DOCTOR VIEW SCHEDULED
async def list_appointments_by_doctor_svc(
    session: AsyncSession,
    doctor_id: UUID,
    limit: int,
    offset: int,
) -> AppointmentListPage:
    """
    Get appointment for 1 doctor (status = scheduled).
    Admin or the doctor himself will call this endpoint (router checks permissions).
    """
    cond = (
        (Appointment.doctor_id == doctor_id)
        & (Appointment.status == ApptStatus.SCHEDULED.value)
    )

    total_stmt = select(func.count()).select_from(Appointment).where(cond)
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = (
        select(Appointment)
        .where(cond)
        .order_by(Appointment.appointment_date, Appointment.start_time)
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    items = [_to_list_item(a) for a in rows]
    has_next = offset + limit < total

    return AppointmentListPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_next=has_next,
    )