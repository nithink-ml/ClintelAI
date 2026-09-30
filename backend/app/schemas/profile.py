"""Pydantic schemas for user profile data."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, description="User full name")
    date_of_birth: date | None = Field(default=None, description="Date of birth")
    gender: str | None = Field(default=None, max_length=50, description="Gender identity")
    phone_number: str | None = Field(
        default=None, max_length=30, description="Contact phone number"
    )
    blood_group: str | None = Field(default=None, max_length=10, description="Blood group")
    city: str | None = Field(default=None, max_length=100, description="City")
    state: str | None = Field(default=None, max_length=100, description="State")
    pincode: str | None = Field(default=None, max_length=20, description="Postal / PIN code")


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    date_of_birth: date | None = None
    gender: str | None = None
    phone_number: str | None = None
    blood_group: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None


class ProfileResponse(ProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
