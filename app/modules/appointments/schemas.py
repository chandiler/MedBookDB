# app/modules/appointments/schemas.py
from __future__ import annotations

from datetime import date, time, datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class AppointmentCreateRequest(BaseModel):
    """
    Payload to create appointment.
    - patient_id will be taken from current_user (role patient), not allowed to be sent by client.
    """
    doctor_id: UUID
    appointment_date: date
    start_time: time
    end_time: time


class AppointmentPublic(BaseModel):
    """
    DTO returns a detailed appointment.
    """
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_date: date
    start_time: time
    end_time: time
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppointmentListItem(BaseModel):
    """
    Used for lists
    """
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_date: date
    start_time: time
    end_time: time
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AppointmentListPage(BaseModel):
    """
    Page the appointments list (with pagination).
    """
    items: List[AppointmentListItem]
    total: int
    limit: int
    offset: int
    has_next: bool