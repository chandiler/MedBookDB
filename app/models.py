# app/models.py

# Allow forward reference to undefined class
from __future__ import annotations
# Used for fields of date, time, creation time
from datetime import datetime, date, time
# Used to define Enums like user roles, appointment statuses
from enum import Enum
# Data type suggestion for relationship
from typing import List, Optional

# Import SQLAlchemy components
from sqlalchemy import (
    CheckConstraint, # Logical constraints
    Date, # Date and time data types
    DateTime, 
    ForeignKey, # Foreign keys (relationships between tables)
    Integer,
    String,
    Time,
    Boolean,
    UniqueConstraint, # Unique constraint
    Index, # Create index to speed up queries
    text, # Allows writing pure SQL
    Enum as SAEnum, # Using Enum in SQLAlchemy (alias to avoid duplicate names)
)

from sqlalchemy.orm import (
    DeclarativeBase, # Base class for all ORM models
    Mapped, mapped_column, # Define data types and columns
    relationship # Declare relationships between tables
)


# Base class for ORM — all models inherit from here
class Base(DeclarativeBase):
    pass
    # Base is used to let SQLAlchemy know all the tables in the project
    # When calling Base.metadata.create_all(engine) -> 
    # SQLAlchemy will create all tables that inherit Base


# Enum for user and appointment status
class UserRole(str, Enum):
    # User roles in the system
    patient = "patient"
    doctor = "doctor"
    admin = "admin"


class ApptStatus(str, Enum):
    # Appointment status
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


# Model: User — User table
class User(Base):
    # Table name in database
    __tablename__ = "users"

    # Main columns
    # Primary key (auto-increment)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Enum representing user roles
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), nullable=False)

    # Automatically save creation time
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    # Relationships
    doctor_availabilities: Mapped[List["DoctorAvailability"]] = relationship(
        back_populates="doctor", # Link back to DoctorAvailability.doctor
        cascade="all, delete-orphan", # Delete all when user (doctor) is deleted
        lazy="selectin" # Load relations efficiently (JOIN)
    )


    appointments_as_patient: Mapped[List["Appointment"]] = relationship(
        back_populates="patient", # Link back to Appointment.patient
        foreign_keys="Appointment.patient_id", # Specify specific foreign key column
        lazy="selectin"
    )

    appointments_as_doctor: Mapped[List["Appointment"]] = relationship(
        back_populates="doctor", # Link back to Appointment.doctor
        foreign_keys="Appointment.doctor_id",
        lazy="selectin"
    )

    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="user", # Link back to AuditLog.user
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Display user information in log/debug
    def __repr__(self) -> str:
        return f"<User {self.user_id} {self.username} ({self.role})>"

# Create index to speed up role-based queries
Index("idx_users_role", User.role)


# Model: Doctor Availability
class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    availability_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Each free shift is associated with 1 doctor
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    available_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Default doctor is free during this time frame
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))

    # Reverse relationship to User
    doctor: Mapped["User"] = relationship(back_populates="doctor_availabilities")

    __table_args__ = (
        # Constraint: start time must be less than end time
        CheckConstraint("start_time < end_time", name="ck_avail_time_order"),
        
        # Constraint: 1 doctor cannot have 2 cases with the same time on the same day
        UniqueConstraint(
            "doctor_id", "available_date", "start_time",
            name="uq_avail_doctor_day_start"
        ),

        # Create index for quick query by date or by doctor
        Index("idx_avail_date", "available_date"),
        Index("idx_avail_doctor_day", "doctor_id", "available_date"),
    )

    def __repr__(self) -> str:
        return f"<Availability d={self.available_date} {self.start_time}-{self.end_time} doctor={self.doctor_id}>"


# Model: Appointment
class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Link to users table (both patient and doctor)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)

    # Appointment time
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Appointment status (default = scheduled)
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
        # Constraint start time < end time
        CheckConstraint("start_time < end_time", name="ck_appt_time_order"),

        # Avoid double appointments with the same doctor - same day - same start time
        UniqueConstraint(
            "doctor_id", "appointment_date", "start_time",
            name="uq_appt_doctor_day_start"
        ),

        # Index supports quick search of appointments by date or doctor
        Index("idx_appt_date", "appointment_date"),
        Index("idx_appt_doctor_day_time", "doctor_id", "appointment_date", "start_time"),
    )

    def __repr__(self) -> str:
        return f"<Appt {self.appointment_id} d={self.appointment_date} {self.start_time}-{self.end_time}>"


# Model: AuditLog — User activity log
class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # If user is deleted, user_id in log = NULL
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    # Action (e.g., "created appointment")
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    # Details
    details: Mapped[Optional[str]] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

    __table_args__ = (
        # Index theo thời gian để truy vấn log nhanh
        Index("idx_audit_ts", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Audit {self.log_id} {self.action} at {self.timestamp}>"