# infra/migrations/env.py
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context

# === App imports (tus settings y metadata) ===
from app.core.config import settings
from app.db.base import Base

# IMPORTA AQUÍ TODOS LOS MODELOS para que aparezcan en autogenerate:
# (cuando crees User, Appointment, etc., impórtalos aquí)
# from app.modules.users.models import User
# from app.modules.appointments.models import Appointment
# ...

# Alembic Config object
config = context.config

# Logging config (opcional, según alembic.ini)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata objetivo para 'autogenerate'
target_metadata = Base.metadata

# Inyecta la URL desde settings (lee .env vía pydantic-settings)
# Usaremos el mismo DSN (psycopg3) — Alembic puede trabajar con sync/async; aquí iremos por async engine.
if settings.SQL_DSN:
    config.set_main_option("sqlalchemy.url", settings.SQL_DSN)

def run_migrations_offline() -> None:
    """Modo offline: genera SQL sin conectarse a la DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,      # Detecta cambios de tipo
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    """Ejecuta las migraciones con una conexión SYNC (Alembic las corre en sync)."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Modo online con AsyncEngine; Alembic necesita una conexión sync, por eso usamos run_sync."""
    connectable: AsyncEngine = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,  # Alembic no necesita pool
    )

    async with connectable.connect() as async_conn:
        await async_conn.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
