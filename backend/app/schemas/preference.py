"""Pydantic schemas for user preferences and settings."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LanguageCode = Literal["en", "ta", "hi", "ml", "te", "kn"]
ThemeOption = Literal["light", "dark", "system"]


class PreferenceBase(BaseModel):
    preferred_language: LanguageCode = Field(
        default="en", description="Preferred language code (en, ta, hi, ml, te, kn)"
    )
    theme: ThemeOption = Field(default="system", description="UI theme mode (light, dark, system)")
    emergency_alerts_enabled: bool = Field(
        default=True, description="Receive verified regional health alert notifications"
    )
    location_sharing_enabled: bool = Field(
        default=False, description="Enable location discovery for nearby doctors and facilities"
    )


class PreferenceUpdate(BaseModel):
    preferred_language: LanguageCode | None = None
    theme: ThemeOption | None = None
    emergency_alerts_enabled: bool | None = None
    location_sharing_enabled: bool | None = None


class PreferenceResponse(PreferenceBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
