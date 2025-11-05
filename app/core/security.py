# app/core/security.py
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# =========
# Passwords
# =========

# Passlib context using bcrypt; you can tune "rounds" via env if needed.
_pwd_ctx = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    default="bcrypt_sha256",
    deprecated="auto",
)

def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    """
    if not isinstance(plain_password, str) or plain_password == "":
        raise ValueError("Password must be a non-empty string")
    return _pwd_ctx.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.
    """
    if not password_hash or not plain_password:
        return False
    try:
        return _pwd_ctx.verify(plain_password, password_hash)
    except Exception:
        # Deliberately swallow detailed errors to avoid oracle info
        return False


# =====
# JWTs
# =====

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


# Default algorithm (HS256 for school project; prefer RS256 in production).
ALGORITHM = "HS256"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _exp_from_minutes(minutes: int) -> datetime:
    return _utcnow() + timedelta(minutes=minutes)


def _exp_from_days(days: int) -> datetime:
    return _utcnow() + timedelta(days=days)


def create_access_token(
    *,
    subject: str,                # typically the user id (UUID as str)
    email: Optional[str] = None,
    role: Optional[str] = None,  # "patient" | "doctor" | "admin"
    scopes: Optional[list[str]] = None,
    expires_minutes: Optional[int] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a short-lived Bearer access token.
    """
    exp_minutes = expires_minutes or settings.ACCESS_EXPIRES_MIN
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "type": TokenType.ACCESS.value,
        "iat": int(_utcnow().timestamp()),
        "exp": int(_exp_from_minutes(exp_minutes).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if email:
        to_encode["email"] = email
    if role:
        to_encode["role"] = role
    if scopes:
        to_encode["scopes"] = scopes
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(
    *,
    subject: str,
    expires_days: Optional[int] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a long-lived refresh token.
    """
    exp_days = expires_days or settings.REFRESH_EXPIRES_DAYS
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "type": TokenType.REFRESH.value,
        "iat": int(_utcnow().timestamp()),
        "exp": int(_exp_from_days(exp_days).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)


class InvalidTokenError(Exception):
    """Raised when a token is missing/invalid/expired or claims are malformed."""


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT. Raises InvalidTokenError on failure.
    """
    if not token:
        raise InvalidTokenError("missing_token")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        # JWTError covers expired signature, invalid signature, bad format, etc.
        raise InvalidTokenError("invalid_token") from exc

    # Minimal sanity checks on claims
    if "sub" not in payload or "type" not in payload:
        raise InvalidTokenError("invalid_claims")

    return payload


def is_access_token(payload: Dict[str, Any]) -> bool:
    return payload.get("type") == TokenType.ACCESS.value


def is_refresh_token(payload: Dict[str, Any]) -> bool:
    return payload.get("type") == TokenType.REFRESH.value
