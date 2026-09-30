"""Pydantic schemas for emergency contacts."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmergencyContactBase(BaseModel):
    name: str = Field(
        ..., min_length=2, max_length=255, description="Full name of emergency contact"
    )
    relationship: str = Field(
        ..., min_length=2, max_length=100, description="Relationship to user (e.g. Spouse, Parent)"
    )
    phone_number: str = Field(
        ..., min_length=5, max_length=30, description="Emergency contact phone number"
    )
    is_primary: bool = Field(default=False, description="Primary contact flag")


class EmergencyContactCreate(EmergencyContactBase):
    pass


class EmergencyContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    relationship: str | None = Field(default=None, min_length=2, max_length=100)
    phone_number: str | None = Field(default=None, min_length=5, max_length=30)
    is_primary: bool | None = None


class EmergencyContactResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    relationship: str
    phone_number: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
