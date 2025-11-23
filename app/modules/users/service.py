# app/modules/users/service.py
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.users import repository as users_repo
from app.modules.users.models import User
from app.modules.users.schemas import RegisterRequest, UserPublic, Role, LoginRequest, LoginResponse,    PatientListParams,PatientListItem,PatientPage

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings

from app.modules.users.repository import get_patient_by_id_repo, list_patients_repo

# Service-level errors (map them to HTTP in the router)
class EmailAlreadyExists(Exception):
    pass


class WeakPassword(Exception):
    pass

class InvalidCredentials(Exception):
    pass

def _to_public(user: User) -> UserPublic:
    """
    Convert ORM model to public DTO.
    """
    # Role is stored as string in DB; cast to API enum
    role_value = Role(user.role) if user.role in {r.value for r in Role} else Role.patient
    return UserPublic.model_validate(
        {
            "id": user.id,
            "email": user.email,
            "role": role_value,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
    )


async def register_user(session: AsyncSession, payload: RegisterRequest) -> UserPublic:
    """
    Business flow for user registration:
      1) Normalize and check email uniqueness.
      2) Hash password with bcrypt.
      3) Persist user.
      4) Return public DTO.

    Notes:
      - Password complexity was validated at DTO level, but you may re-check here
        or enforce additional policies if needed.
      - New users are created with role 'patient' by default (server-side decision).
    """
    email = payload.email.strip().lower()

    # 1) Uniqueness check (early 409 if exists)
    existing = await users_repo.get_by_email(session, email)
    if existing:
        raise EmailAlreadyExists("email_already_exists")

    # 2) Hash password (never store plain text)
    password_hash = hash_password(payload.password.get_secret_value())

    # 3) Persist (default role = patient, is_active = true)
    user = await users_repo.create_user(
        session,
        email=email,
        password_hash=password_hash,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
         role=payload.role.value,
        # role left as default (patient) inside repository/model
    )

    # 4) Map to public DTO
    return _to_public(user)

async def login_user(session: AsyncSession, payload: LoginRequest) -> LoginResponse:
    """
    1) Fetch user by email
    2) Verify bcrypt password
    3) Issue access (and optionally refresh) tokens
    """
    user = await users_repo.get_by_email(session, payload.email)
    if not user:
        raise InvalidCredentials("invalid_credentials")

    if not verify_password(payload.password.get_secret_value(), user.password_hash):
        raise InvalidCredentials("invalid_credentials")

    # Optional: check is_active / email_verified here if you want stricter behavior
    access = create_access_token(
        subject=str(user.id),
        email=user.email,
        role=user.role,
        scopes=["profile:read", "appointments:read"],  # adjust as needed
    )
    # If you want refresh tokens, uncomment below and include in response.
    # refresh = create_refresh_token(subject=str(user.id))

    return LoginResponse(
        access_token=access,
        expires_in=settings.ACCESS_EXPIRES_MIN * 60,
        refresh_token=None,  # or refresh
    )


def _to_patient_item(u: User) -> PatientListItem:
    return PatientListItem.model_validate(u)

async def list_patients(
    session: AsyncSession,
    params: PatientListParams,
) -> PatientPage:
    """List patients with search, flags, ordering, and pagination."""
    users, total = await list_patients_repo(
        session,
        q=params.q,
        is_active=params.is_active,
        email_verified=params.email_verified,
        order_by=params.order_by,
        order_dir=params.order_dir,
        limit=params.limit,
        offset=params.offset,
    )
    items = [_to_patient_item(u) for u in users]
    has_next = params.offset + params.limit < total
    return PatientPage(
        items=items,
        total=total,
        limit=params.limit,
        offset=params.offset,
        has_next=has_next,
    )

class PatientNotFound(Exception):
    pass

def _to_patient_item(u: User) -> PatientListItem:
    return PatientListItem.model_validate(u)

async def get_patient_by_id(
    session: AsyncSession, patient_id: UUID
) -> PatientListItem:
    user = await get_patient_by_id_repo(session, patient_id=patient_id)
    if not user:
        raise PatientNotFound("patient_not_found")
    return _to_patient_item(user)