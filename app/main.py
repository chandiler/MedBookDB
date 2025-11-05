# app/main.py
from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title="Secure Healthcare Appointment System")

@app.get("/")
def root():
    return {"message": "Healthcare System API running successfully", "env": settings.APP_ENV}
