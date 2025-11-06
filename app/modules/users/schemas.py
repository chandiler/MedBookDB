# app/modules/users/schemas.py
from __future__ import annotations

import re
from enum import Enum
from typing import Optional
from uuid import UUID
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator, StringConstraints

class Role(str, Enum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"

NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
PhoneStr = Annotated[str, StringConstraints(pattern=r"^\+?[1-9]\d{1,14}$")]  # E.164 simple

PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d\S]{8,64}$")

class RegisterRequest(BaseModel):
    email: EmailStr = Field(...)
    password: SecretStr = Field(..., description="8–64 chars, at least one letter and one digit")
    first_name: NameStr
    last_name: NameStr
    phone: Optional[PhoneStr] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: SecretStr) -> SecretStr:
        if not PASSWORD_RE.match(v.get_secret_value()):
            raise ValueError(
                "Password must be 8–64 chars and include at least one letter and one digit"
            )
        return v


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    role: Role
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


RegisterResponse = UserPublic



class ErrorResponse(BaseModel):
    error: str
    message: str
    status: int


# --- Login / Me / Refresh ---

class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None  # include only if you enable refresh flow


LoginResponse = TokenPair
MeResponse = UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str
