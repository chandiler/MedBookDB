# app/modules/doctors/repository.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Sequence, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.doctors.models import Availability


def _utcnow():
    return datetime.now(timezone.utc)


async def create_availability(
    db: AsyncSession, *, doctor_id: str, start_time: datetime, end_time: datetime
) -> Availability:
    slot = Availability(
        doctor_id=doctor_id,
        start_time=start_time,
        end_time=end_time,
        is_booked=False,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(slot)
    await db.flush()
    return slot


async def list_by_doctor(
    db: AsyncSession, *, doctor_id: str
) -> Sequence[Availability]:
    rows = await db.execute(
        select(Availability).where(Availability.doctor_id == doctor_id).order_by(Availability.start_time)
    )
    return rows.scalars().all()


async def get_owner_id_by_slot(db: AsyncSession, *, slot_id: int) -> Optional[str]:
    row = await db.execute(
        select(Availability.doctor_id).where(Availability.id == slot_id)
    )
    return row.scalar_one_or_none()


async def update_availability(
    db: AsyncSession,
    *,
    slot_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    is_booked: Optional[bool] = None,
) -> int:
    stmt = (
        update(Availability)
        .where(Availability.id == slot_id)
        .values(
            **{
                k: v
                for k, v in {
                    "start_time": start_time,
                    "end_time": end_time,
                    "is_booked": is_booked,
                    "updated_at": _utcnow(),
                }.items()
                if v is not None
            }
        )
    )
    res = await db.execute(stmt)
    return res.rowcount or 0 # type: ignore


async def delete_availability(db: AsyncSession, *, slot_id: int) -> int:
    res = await db.execute(delete(Availability).where(Availability.id == slot_id))
    return res.rowcount or 0 # type: ignore
