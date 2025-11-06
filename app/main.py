# app/main.py (recordatorio)
from fastapi import FastAPI
from app.core.config import settings
from app.routers import health, auth, patients

app = FastAPI(title="Secure Healthcare Appointment System")

# Routing
app.include_router(health.router, prefix=settings.API_PREFIX, tags=["health"])
app.include_router(auth.router,   prefix=settings.API_PREFIX, tags=["auth"])
app.include_router(patients.router, prefix=settings.API_PREFIX, tags=["patients"])

@app.get("/")
def root():
    return {"message": "Healthcare System API running successfully"}
