# app/modules/users/repository.py
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, or_, asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, UserRole
class EmailAlreadyExistsError(Exception):
    """Raised when trying to insert a user with an email that already exists."""


class InvalidUserDataError(Exception):
    """Raised when DB-level constraints fail (e.g., bad CHECK constraints)."""


async def get_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
    """
    Returns a User by primary key or None if not found.
    """
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """
    Returns a User by email (normalized to lowercase) or None.
    """
    email = email.strip().lower()
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password_hash: str,
    first_name: str,
    last_name: str,
    phone: Optional[str] = None,
    role: UserRole | str = UserRole.PATIENT,
    is_active: bool = True,
    email_verified: bool = False,
) -> User:
    """
    Inserts a new user row and returns the persisted ORM instance.

    Notes:
    - This function expects a *hashed* password (bcrypt) – do NOT pass plain text.
    - Email is normalized to lowercase and must satisfy the DB CHECK constraint.
    - Uniqueness and CHECK violations are mapped to clean Python exceptions.
    """
    # Normalize/defensive defaults
    normalized_email = email.strip().lower()
    role_value = role.value if isinstance(role, UserRole) else str(role)

    user = User(
        email=normalized_email,
        password_hash=password_hash,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=phone,
        role=role_value,
        is_active=is_active,
        email_verified=email_verified,
    )

    session.add(user)
    try:
        # Flush to force INSERT and surface constraint violations here
        await session.flush()
    except IntegrityError as exc:
        # Unique email or CHECK constraints hit here.
        # Distinguish common cases by constraint names if you wish.
        message = str(exc.orig).lower() if exc.orig else str(exc).lower()

        # Heuristics by constraint name (as defined in models.py)
        if "uq_users_email" in message or "unique" in message:
            raise EmailAlreadyExistsError("Email already registered") from exc

        if "ck_users_email_lowercase" in message or "ck_users_role_valid" in message:
            raise InvalidUserDataError("User data violates DB constraints") from exc

        # Generic fallback
        raise InvalidUserDataError("Failed to insert user") from exc

    # Optionally refresh to ensure defaults (server_default) are visible
    await session.refresh(user)
    return user


async def update_lastname(
    session: AsyncSession, *, user_id: UUID, new_last_name: str
) -> Optional[User]:
    """
    Simple example update (kept for illustration). Returns the updated user or None.
    """
    user = await get_by_id(session, user_id)
    if not user:
        return None
    user.last_name = new_last_name.strip()
    await session.flush()
    await session.refresh(user)
    return user

async def list_patients_repo(
    session: AsyncSession,
    *,
    q: Optional[str],
    is_active: Optional[bool],
    email_verified: Optional[bool],
    order_by: str,
    order_dir: str,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    # Base WHERE: only patients
    conditions = [User.role == "patient"]

    # Flags
    if is_active is not None:
        conditions.append(User.is_active == is_active)
    if email_verified is not None:
        conditions.append(User.email_verified == email_verified)

    # Search (ILIKE on email/first/last names)
    if q:
        term = f"%{q.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(User.email).ilike(term),
                func.lower(User.first_name).ilike(term),
                func.lower(User.last_name).ilike(term),
            )
        )

    # Order
    col_map = {
        "created_at": User.created_at,
        "last_name": User.last_name,
        "email": User.email,
    }
    col = col_map.get(order_by, User.created_at)
    ordering = asc(col) if order_dir == "asc" else desc(col)

    # Total count
    total_stmt = select(func.count()).select_from(User).where(*conditions)
    total = (await session.execute(total_stmt)).scalar_one()

    # Page
    stmt = (
        select(User)
        .where(*conditions)
        .order_by(ordering, User.id)  # tie-breaker for stable paging
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return rows, total

async def get_patient_by_id_repo(
    session: AsyncSession, *, patient_id: UUID
) -> Optional[User]:
    """
    Return a patient by UUID or None if not found (enforces role='patient').
    """
    stmt = select(User).where(User.id == patient_id, User.role == "patient")
    result = await session.execute(stmt)
    return result.scalar_one_or_none()