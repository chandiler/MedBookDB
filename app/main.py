# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from .db import engine, init_db
from routes.admin_api import router as admin_router  

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Secure Healthcare Appointment System",
    lifespan=lifespan,
)

# Gắn admin routes
app.include_router(admin_router)

@app.get("/")
def root():
    return {"message": "Healthcare System API running successfully"}

@app.get("/health/db")
def health_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"db": "ok"}