# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.core.config import settings
from app.routers import health, auth, patients, admin  # ← Agregar admin aquí

# Importar desde db/sql.py (async)
from app.db.sql import engine, AsyncSessionLocal

# Define lifespan event
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    The lifespan function is used to manage the FastAPI application lifecycle.
    """
    # Inicializar base de datos (crear tablas si no existen)
    await init_db()
    yield

app = FastAPI(
    title="Secure Healthcare Appointment System",
    lifespan=lifespan,
)

# Routing
app.include_router(health.router, prefix=settings.API_PREFIX, tags=["health"])
app.include_router(auth.router, prefix=settings.API_PREFIX, tags=["auth"])
app.include_router(patients.router, prefix=settings.API_PREFIX, tags=["patients"])
app.include_router(admin.router, prefix=settings.API_PREFIX, tags=["admin"])  # ← Cambiar esta línea

@app.get("/")
def root():
    return {"message": "Healthcare System API running successfully"}

# Endpoint checks database connection status (async)
@app.get("/health/db")
async def health_db():
    """
    Test the connection to the database
    """
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"db": "ok"}

# Función para inicializar la base de datos
async def init_db():
    """
    Initialize database tables
    """
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()
    
    # Importar todos los modelos aquí para que se registren
    # Asegúrate de importar todos tus modelos
    try:
        from app import models  # Esto importa todos los modelos
    except ImportError:
        # Si no hay modelos definidos aún, continuar
        pass
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)