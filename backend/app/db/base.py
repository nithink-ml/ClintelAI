"""Database Base and all models registration for Alembic migrations."""

from app.db.session import Base
from app.models.alert import HealthAlert
from app.models.audit_log import AuditLog
from app.models.emergency_contact import EmergencyContact
from app.models.preference import UserPreference
from app.models.profile import Profile
from app.models.provider import Doctor, DoctorAffiliation, Facility
from app.models.token import RefreshToken
from app.models.user import User

__all__ = [
    "AuditLog",
    "Base",
    "Doctor",
    "DoctorAffiliation",
    "EmergencyContact",
    "Facility",
    "HealthAlert",
    "Profile",
    "RefreshToken",
    "User",
    "UserPreference",
]
