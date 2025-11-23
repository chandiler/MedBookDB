# app/core/permission.py

from __future__ import annotations
from uuid import UUID
from typing import Callable, Awaitable
from fastapi import Depends, HTTPException, Request, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.sql import get_session
from app.modules.users.models import User 

def current_user(request: Request):
    """
    返回 middleware 注入的 token 摘要(dict: sub/role/email/...)
    适合做 RBAC/owner 判断，不适合直接序列化为用户详情。
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return user

async def get_current_user(
    ctx = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    查库并返回 ORM User（用于 /users/me 这类需要完整字段的响应）
    """
    try:
        uid = UUID(str(ctx.get("sub")))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_subject")

    row = await db.execute(select(User).where(User.id == uid))
    user = row.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    return user

def require_roles(*allowed_roles: str):
    def dep(user=Depends(current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_role")
        return user
    return dep

def require_owner_or_admin(owner_id_getter: Callable[[int, AsyncSession], Awaitable[str | None]]):
    async def dep(
        resource_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_session),
        user=Depends(current_user),
    ):
        if user.get("role") == "admin":
            return user
        owner = await owner_id_getter(resource_id, db)
        if owner is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        if str(owner) != str(user.get("sub")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_owner")
        return user
    return dep
