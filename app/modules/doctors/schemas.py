# app/modules/doctors/schemas.py
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

class AvailabilityCreate(BaseModel):
    start_time: datetime = Field(..., description="ISO time with timezone")
    end_time:   datetime = Field(..., description="ISO time with timezone")

    @field_validator("end_time")
    @classmethod
    def _end_after_start(cls, v, info):
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v


class AvailabilityUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time:   Optional[datetime] = None
    is_booked:  Optional[bool]     = None

    @field_validator("end_time")
    @classmethod
    def _end_after_start(cls, v, info):
        start = info.data.get("start_time")
        if v and start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v


class AvailabilityPublic(BaseModel):
    id: int
    doctor_id: UUID
    start_time: datetime
    end_time: datetime
    is_booked: bool

    class Config:
        from_attributes = True
