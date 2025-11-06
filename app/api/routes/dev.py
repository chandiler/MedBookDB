# app/api/routes/dev.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sql import get_session
from app.modules.users.models import User as UserModel   # ✅ 正确路径
from app.core.config import settings

router = APIRouter(prefix="/_dev", tags=["dev"])

@router.post("/promote-admin")
async def promote_admin(email: str, db: AsyncSession = Depends(get_session)):
    # 仅在 DEBUG 下开放
    if not getattr(settings, "DEBUG", False):
        raise HTTPException(status_code=404, detail="not_found")

    email_lower = email.lower()

    # 先确认用户存在
    row = await db.execute(select(UserModel.id, UserModel.role).where(UserModel.email == email_lower))
    found = row.first()
    if not found:
        raise HTTPException(status_code=404, detail="user_not_found")

    # 提权
    await db.execute(
        update(UserModel)
        .where(UserModel.email == email_lower)
        .values(role="admin")
    )
    await db.commit()

    return {"email": email_lower, "role": "admin"}
