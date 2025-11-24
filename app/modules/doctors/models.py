# app/modules/doctors/models.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Availability(Base):
    """
    A doctor's available time slot. One row = one slot.
    """
    __tablename__ = "availabilities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Owner (doctor) — FK to users.id (UUID)
    doctor_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False)

    is_booked: Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # (可选) 如果你在 User 模型上定义了 relationship("Availability", back_populates=...)
    # user: Mapped["User"] = relationship(back_populates="availabilities")

# 查询加速：某医生、时间窗口、是否被占用
Index(
    "idx_availability_doctor_start",
    Availability.doctor_id,
    Availability.start_time,
    Availability.is_booked,
)
