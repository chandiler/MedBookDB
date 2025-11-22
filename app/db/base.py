# app/db/base.py
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class UUIDPKMixin:
    """Primary Key UUID (v4) estándar para todas las tablas."""

    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)


class TimestampMixin:
    """Timestamps automáticos (server-side)."""

    created_at: Mapped[dt.datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ReprMixin:
    """__repr__ útil para debug/logging."""

    def __repr__(self) -> str:
        cols: list[str] = []
        for k in getattr(self, "__mapper__").c.keys():
            v: Any = getattr(self, k, None)
            if k in {"password", "password_hash"}:
                v = "***"
            cols.append(f"{k}={v!r}")
        return f"<{self.__class__.__name__} {' '.join(cols)}>"


__all__ = ["Base", "UUIDPKMixin", "TimestampMixin", "ReprMixin"]
