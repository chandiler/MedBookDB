# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.core.config import settings
from app.routers import health, auth, patients, admin, appointments, doctor

# Import from db/sql.py (async)
from app.db.sql import engine, AsyncSessionLocal

# Define lifespan event
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    The lifespan function is used to manage the FastAPI application lifecycle.
    """
    # Initialize database (create tables if they don't exist)
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
app.include_router(admin.router, prefix=settings.API_PREFIX, tags=["admin"]) 
app.include_router(appointments.router, prefix=settings.API_PREFIX, tags=["appointments"])
app.include_router(doctor.router, prefix=settings.API_PREFIX, tags=["doctor"])

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

# Function to initialize the database
async def init_db():
    """
    Initialize database tables
    """
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()
    
    # Import all models here so they get registered
    # Make sure to import all your models
    try:
        from app import models  # This imports all models
    except ImportError:
        # If no models are defined yet, continue
        pass
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)