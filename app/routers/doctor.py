# app/routers/doctor.py
from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permission import  require_roles, require_owner_or_admin
from app.db.sql import get_session
from app.modules.doctors.schemas import (
    AvailabilityCreate,
    AvailabilityUpdate,
    AvailabilityPublic,
)
from app.modules.doctors import repository as repo
from app.modules.users.models import User

router = APIRouter(prefix="/availability", tags=["doctor-availability"])

@router.post(
    "/create",
    response_model=AvailabilityPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_slot(
    payload: AvailabilityCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_roles("doctor")),  # <-- explicitly a User
):
    # Now user is a User ORM instance, not a dict
    doctor_id = user.id
    print("Creating availability for doctor_id:", doctor_id)
    print("Creating availability with start_time:", payload.start_time)
    print("Creating availability with end_time:", payload.end_time)
    rec = await repo.create_availability(db, doctor_id=doctor_id,start_time=payload.start_time, end_time=payload.end_time)
    return rec

# 6.2: 查看某医生的全部可用时段（对任何已登录用户或公开接口均可）
@router.get(
    "/doctor/{doctor_id}",
    response_model=list[AvailabilityPublic],
)
async def list_doctor_slots(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    items = await repo.list_by_doctor(db, doctor_id=doctor_id)
    return items


# --- 共用的“拥有者获取器”，给 require_owner_or_admin 用 ---
async def _get_owner_id(resource_id: int, db: AsyncSession) -> str | None:
    """
    返回该 availability 记录的拥有者(doctor)的 UUID 字符串；不存在返回 None
    """
    print("Getting owner for availability id:", resource_id)
    owner = await repo.get_owner_id_by_slot(db, slot_id=resource_id)
    return str(owner) if owner else None


# 6.3: 修改时段（医生本人或管理员）
@router.put(
    "/{resource_id}/update",
    response_model=AvailabilityPublic,
)
async def update_slot(
    resource_id: int = Path(..., ge=1),
    payload: AvailabilityUpdate = None,
    db: AsyncSession = Depends(get_session),
    response_model=AvailabilityPublic,
   # user=Depends(require_owner_or_admin(_get_owner_id)),
):
    print("Updating availability id:", resource_id)
    print("Update payload:", payload.start_time, payload.end_time, payload.is_booked)
    rec = await repo.update_availability(db, slot_id=resource_id, start_time=payload.start_time, end_time=payload.end_time, is_booked=payload.is_booked)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    availability = await repo.get_availability_by_id(db, slot_id=resource_id)
    return availability


# 6.4: 删除时段（医生本人或管理员）
@router.delete(
    "/{resource_id}/delete",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_slot(
    resource_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_session),
    user=Depends(require_owner_or_admin(_get_owner_id)),
):
    ok = await repo.delete_availability(db, slot_id=resource_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return None
