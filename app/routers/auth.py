# app/routers/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sql import get_session
from app.modules.users.schemas import RegisterRequest, RegisterResponse
from app.modules.users.service import register_user, EmailAlreadyExists

router = APIRouter(tags=["auth"])

@router.post(
    "/auth/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
    responses={
        201: {"description": "User created"},
        400: {"description": "Invalid payload"},
        409: {"description": "Email already registered"},
    },
)
async def auth_register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Register a new user (default role: `patient`).

    Notes:
    - Email is normalized to lowercase.
    - Password must pass strength checks (8–64 chars, ≥1 letter, ≥1 digit).
    """
    try:
        user_public = await register_user(session, payload)
    except EmailAlreadyExists:
        # Keep the message stable; clients can branch on status code.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email_already_exists",
        )
    except ValueError as e:
        # Any unexpected validation error from downstream layers
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "invalid_request",
        )
    return user_public
