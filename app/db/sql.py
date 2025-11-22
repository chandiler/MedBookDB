# app/db/sql.py
from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text, insert
from app.core.config import settings

from app.core.config import settings
from app.modules.users.models import AuditLog

# from app.dependencies import get_current_user  # <-- import the user resolver


async def write_audit_log(session, user_id, action, details):
    stmt = insert(AuditLog).values(user_id=user_id, action=action, details=details)
    await session.execute(stmt)


engine = create_async_engine(
    settings.SQL_DSN,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_timeout=settings.DB_POOL_TIMEOUT,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)


# @asynccontextmanager
# async def session_scope() -> AsyncSession:
#     """
#     Context manager for transactional operations.
#     Handles commit/rollback and session closure.
#     """
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise

# async def get_session() -> AsyncSession:
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise


async def get_session(request: Request) -> AsyncSession:
    """
    Provide a DB session for each request.
    Automatically apply commit/rollback and write audit logs.
    """

    # Lazy import to avoid circular import
    from app.dependencies import get_current_user

    async with AsyncSessionLocal() as session:
        user_id = None

        # Resolve user from JWT (if available)
        try:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            user = await get_current_user(token=token, session=session)
            if user:
                user_id = user.id
        except Exception:
            pass

        action = f"{request.method} {request.url.path}"

        try:
            yield session

            await session.commit()

            await session.execute(
                insert(AuditLog).values(
                    user_id=user_id,
                    action=f"{action} COMMIT",
                    details="Operation completed successfully",
                )
            )
            await session.commit()

        except Exception as exc:

            await session.rollback()

            await session.execute(
                insert(AuditLog).values(
                    user_id=user_id,
                    action=f"{action} ROLLBACK",
                    details=str(exc),
                )
            )
            await session.commit()

            raise


async def ping_db() -> bool:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        return True


async def init_db():
    """
    Initialize database tables
    """
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    # Import all models here so they get registered
    try:
        from app import models  # This imports all models
    except ImportError:
        # If no models are defined yet, continue
        pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
