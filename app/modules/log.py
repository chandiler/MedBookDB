from __future__ import annotations

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import AuditLog


async def write_audit_log(
    session: AsyncSession,
    user_id: str | None,
    action: str,
    details: str | None = None,
):
    """
    Write an audit log entry.

    action:
        "REGISTER"
        "CREATE_APPOINTMENT"
        "UPDATE_PATIENT"
        "DELETE_USER"

    details:
    """
    stmt = insert(AuditLog).values(
        user_id=user_id,
        action=action,
        details=details,
    )
    await session.execute(stmt)
