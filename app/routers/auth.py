# app/routers/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import InvalidTokenError, create_access_token, decode_token, is_refresh_token
from app.db.sql import get_session
from app.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.users.schemas import LoginRequest, LoginResponse, MeResponse, RefreshRequest, RegisterRequest, RegisterResponse
from app.modules.users.service import InvalidCredentials, login_user, register_user, EmailAlreadyExists
from app.core.config import settings

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

@router.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtain a Bearer token with email and password",
    responses={
        200: {"description": "Authenticated"},
        401: {"description": "Invalid credentials"},
    },
)
async def auth_login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await login_user(session, payload)
    except InvalidCredentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")


@router.get(
    "/auth/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the current user's profile",
)
async def auth_me(current_user: User = Depends(get_current_user)):
    # Reuse the public DTO from the service helper
    from app.modules.users.service import _to_public
    return _to_public(current_user)


# === Optional: refresh flow (only if you want refresh tokens) ===
@router.post(
    "/auth/refresh",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange a refresh token for a new access token",
    responses={401: {"description": "Invalid refresh token"}},
)
async def auth_refresh(request: RefreshRequest):
    try:
        payload = decode_token(request.refresh_token)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

    if not is_refresh_token(payload):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_type")

    user_id = payload.get("sub")
    new_access = create_access_token(subject=str(user_id))
    return LoginResponse(
        access_token=new_access,
        expires_in=settings.ACCESS_EXPIRES_MIN * 60,
        refresh_token=request.refresh_token,  # or rotate if you implement rotation
    )