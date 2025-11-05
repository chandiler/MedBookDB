# app/models.py
from __future__ import annotations
from datetime import datetime, date, time
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    Boolean,
    UniqueConstraint,
    Index,
    text,
    Enum as SAEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------- Base ----------
class Base(DeclarativeBase):
    pass


# ---------- Enums ----------
class UserRole(str, Enum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"


class ApptStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


# ---------- Models ----------
class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), nullable=False)

    # dùng timestamptz nếu PostgreSQL; ở đây để DateTime + server_default
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    # Relationships
    doctor_availabilities: Mapped[List["DoctorAvailability"]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan", lazy="selectin"
    )

    appointments_as_patient: Mapped[List["Appointment"]] = relationship(
        back_populates="patient", foreign_keys="Appointment.patient_id", lazy="selectin"
    )

    appointments_as_doctor: Mapped[List["Appointment"]] = relationship(
        back_populates="doctor", foreign_keys="Appointment.doctor_id", lazy="selectin"
    )

    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User {self.user_id} {self.username} ({self.role})>"


Index("idx_users_role", User.role)


class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    availability_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    available_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))

    doctor: Mapped["User"] = relationship(back_populates="doctor_availabilities")

    __table_args__ = (
        # Do not allow reverse time entry
        CheckConstraint("start_time < end_time", name="ck_avail_time_order"),
        # A doctor should not have two cases starting at the same time on the same day
        UniqueConstraint(
            "doctor_id", "available_date", "start_time",
            name="uq_avail_doctor_day_start"
        ),
        Index("idx_avail_date", "available_date"),
        Index("idx_avail_doctor_day", "doctor_id", "available_date"),
    )

    def __repr__(self) -> str:
        return f"<Availability d={self.available_date} {self.start_time}-{self.end_time} doctor={self.doctor_id}>"


class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    patient_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)

    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    status: Mapped[ApptStatus] = mapped_column(
        SAEnum(ApptStatus, name="appt_status"), nullable=False, server_default=text("'scheduled'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    # Relationships
    patient: Mapped["User"] = relationship(back_populates="appointments_as_patient", foreign_keys=[patient_id])
    doctor: Mapped["User"] = relationship(back_populates="appointments_as_doctor", foreign_keys=[doctor_id])

    __table_args__ = (
        # valid time
        CheckConstraint("start_time < end_time", name="ck_appt_time_order"),
        # Avoid double-booking the same doctor – same day – same start time
        UniqueConstraint(
            "doctor_id", "appointment_date", "start_time",
            name="uq_appt_doctor_day_start"
        ),
        Index("idx_appt_date", "appointment_date"),
        Index("idx_appt_doctor_day_time", "doctor_id", "appointment_date", "start_time"),
    )

    def __repr__(self) -> str:
        return f"<Appt {self.appointment_id} d={self.appointment_date} {self.start_time}-{self.end_time}>"


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(String)  # can convert to JSONB if using PostgreSQL
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_ts", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Audit {self.log_id} {self.action} at {self.timestamp}>"