# app/modules/users/service.py
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users import repository as users_repo
from app.modules.users.models import User
from app.modules.users.schemas import RegisterRequest, UserPublic, Role
from app.core.security import hash_password


# Service-level errors (map them to HTTP in the router)
class EmailAlreadyExists(Exception):
    pass


class WeakPassword(Exception):
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
        # role left as default (patient) inside repository/model
    )

    # 4) Map to public DTO
    return _to_public(user)
