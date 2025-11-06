# app/api/routes/doctor.py

from fastapi import APIRouter, Request
router = APIRouter(prefix="/doctor")

@router.get("/schedule")
def schedule(request: Request):
    return {"doctor": request.state.user["sub"], "items": []}
