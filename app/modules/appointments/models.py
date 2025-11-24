# app/modules/appointments/models.py
from __future__ import annotations

import uuid
from datetime import date, time
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Date,
    Time,
    String,
    Enum as SAEnum,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPKMixin, TimestampMixin, ReprMixin
from app.modules.users.models import User


class ApptStatus(PyEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Appointment(UUIDPKMixin, TimestampMixin, ReprMixin, Base):
    """
    Appointment model (UUID + async), linked to User by FK UUID.
    """

    __tablename__ = "appointments"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ApptStatus.SCHEDULED.value,
        server_default=ApptStatus.SCHEDULED.value,
    )

    # Relationship to User
    patient: Mapped[Optional[User]] = relationship(
        "User",
        foreign_keys=[patient_id],
        lazy="joined",
    )
    doctor: Mapped[Optional[User]] = relationship(
        "User",
        foreign_keys=[doctor_id],
        lazy="joined",
    )

    __table_args__ = (
        CheckConstraint("start_time < end_time", name="ck_appt_time_order"),
        # Avoid double booking: 1 doctor, same day, same start_time
        UniqueConstraint(
            "doctor_id", "appointment_date", "start_time",
            name="uq_appt_doctor_day_start",
        ),
        Index("ix_appt_doctor_date_start", "doctor_id", "appointment_date", "start_time"),
        Index("ix_appt_patient_date", "patient_id", "appointment_date"),
    )