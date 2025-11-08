# app/db/sql.py
from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

from app.core.config import settings

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

@asynccontextmanager
async def session_scope() -> AsyncSession:
    """
    Context manager para operaciones transaccionales.
    Maneja commit/rollback y cierre de sesión.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
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
    
    # Importar todos los modelos aquí para que se registren
    try:
        from app import models  # Esto importa todos los modelos
    except ImportError:
        # Si no hay modelos definidos aún, continuar
        pass
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)