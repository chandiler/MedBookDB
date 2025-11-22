# app/modules/users/models.py
from __future__ import annotations

import uuid
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import ForeignKey
import datetime as dt
from sqlalchemy import func

from sqlalchemy import (
    String,
    Boolean,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin, TimestampMixin, ReprMixin


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(nullable=False)
    details: Mapped[str | None] = mapped_column()
    timestamp: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class UserRole(PyEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class User(UUIDPKMixin, TimestampMixin, ReprMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=UserRole.PATIENT.value
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        CheckConstraint(
            "role IN ('patient', 'doctor', 'admin')", name="ck_users_role_valid"
        ),
        Index("ix_users_role", "role"),
        Index("ix_users_active_role", "is_active", "role"),
    )

    @property
    def role_enum(self) -> UserRole:
        """Get role as UserRole enum instance."""
        return UserRole(self.role)

    @role_enum.setter
    def role_enum(self, value: UserRole):
        """Set role from UserRole enum instance."""
        self.role = value.value
