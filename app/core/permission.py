from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.orm import Session
from typing import Callable
from app.core.security import get_current_user, TokenData
from app.db.sql import get_session
def require_roles(*allowed: str):
    def dep(user: TokenData = Depends(get_current_user)):
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user
    return dep

def require_owner_or_admin(owner_id_getter: Callable[[int, Session], str]):
    def dep(
        resource_id: int = Path(..., ge=1),
        db: Session = Depends(get_session),
        user: TokenData = Depends(get_current_user),
    ):
        if user.role == "admin":
            return user
        if owner_id_getter(resource_id, db) != user.sub:
            raise HTTPException(status_code=403, detail="Not your resource")
        return user
    return dep
