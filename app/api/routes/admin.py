# app/api/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from app.core.permission import require_roles
from app.db.sql import get_session
from app.modules.users.models import User
from app.modules.users.schemas import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=list[UserPublic])
async def list_users(
    _=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_session),
):
    rows = await db.execute(select(User))
    return rows.scalars().all()

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    _=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_session),
):
    
    result = await db.execute(
        delete(User)
        .where(User.id == user_id)
        .returning(User.id)
    )
    deleted_id = result.scalar_one_or_none()
    if deleted_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    await db.commit()
    return {"deleted": str(deleted_id)}
