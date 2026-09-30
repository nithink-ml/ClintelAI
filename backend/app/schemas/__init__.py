"""Pydantic schemas package for ClintelAI."""

from app.schemas.emergency_contact import (
    EmergencyContactCreate,
    EmergencyContactResponse,
    EmergencyContactUpdate,
)
from app.schemas.health import HealthResponse, ServiceHealthDetail
from app.schemas.preference import (
    LanguageCode,
    PreferenceResponse,
    PreferenceUpdate,
    ThemeOption,
)
from app.schemas.profile import (
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from app.schemas.token import RefreshTokenRequest, TokenResponse
from app.schemas.user import (
    UserDetailResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

__all__ = [
    "EmergencyContactCreate",
    "EmergencyContactResponse",
    "EmergencyContactUpdate",
    "HealthResponse",
    "LanguageCode",
    "PreferenceResponse",
    "PreferenceUpdate",
    "ProfileCreate",
    "ProfileResponse",
    "ProfileUpdate",
    "RefreshTokenRequest",
    "ServiceHealthDetail",
    "ThemeOption",
    "TokenResponse",
    "UserDetailResponse",
    "UserLoginRequest",
    "UserRegisterRequest",
    "UserResponse",
]
