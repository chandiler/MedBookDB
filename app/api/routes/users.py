# app/api/routes/users.py
from fastapi import APIRouter, Depends
from app.core.permission import get_current_user
from app.modules.users.schemas import MeResponse 
from app.modules.users.models import User as UserModel

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=MeResponse)
async def users_me(user: UserModel = Depends(get_current_user)):
    return user
