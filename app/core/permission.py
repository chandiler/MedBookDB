# app/core/permission.py
from __future__ import annotations

from typing import Callable, Awaitable
from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sql import get_session
from app.dependencies import get_current_user
from app.modules.users.models import User

def require_roles(*allowed: str):
    async def dep(user: User = Depends(get_current_user)):
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="forbidden_role",
            )
        return user
    return dep


def require_owner_or_admin(
    owner_id_getter: Callable[[int, AsyncSession], Awaitable[str | None]],
):
    async def dep(
        resource_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_session),
        user: User = Depends(get_current_user),
    ):
        # admin → let it pass
        if user.role == "admin":
            return user

        owner = await owner_id_getter(resource_id, db)
        if owner is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )

        if str(owner) != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not_owner",
            )

        return user

    return dep
