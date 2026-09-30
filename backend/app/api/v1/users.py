"""User profile, language preference, and emergency contacts endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, log_audit_event, require_role
from app.models.emergency_contact import EmergencyContact
from app.models.preference import UserPreference
from app.models.profile import Profile
from app.models.user import User
from app.schemas.emergency_contact import (
    EmergencyContactCreate,
    EmergencyContactResponse,
)
from app.schemas.preference import PreferenceResponse, PreferenceUpdate
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.schemas.user import UserResponse

router = APIRouter()


# ==============================================================================
# Profile Management
# ==============================================================================


@router.get(
    "/me/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        # Create empty profile if not found
        profile = Profile(user_id=current_user.id, full_name="User")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return ProfileResponse.model_validate(profile)


@router.put(
    "/me/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User Profile",
)
async def update_my_profile(
    payload: ProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = Profile(user_id=current_user.id, full_name="User")
        db.add(profile)

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(profile, field, val)

    await db.commit()
    await db.refresh(profile)

    await log_audit_event(
        db=db,
        action="PROFILE_UPDATED",
        user_id=current_user.id,
        request=request,
        details={"fields_updated": list(update_data.keys())},
    )

    return ProfileResponse.model_validate(profile)


# ==============================================================================
# Preference & Language Management
# ==============================================================================


@router.get(
    "/me/preferences",
    response_model=PreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Language & App Preferences",
)
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreferenceResponse:
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    res = await db.execute(stmt)
    pref = res.scalar_one_or_none()
    if not pref:
        pref = UserPreference(
            user_id=current_user.id,
            preferred_language="en",
            theme="system",
        )
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    return PreferenceResponse.model_validate(pref)


@router.put(
    "/me/preferences",
    response_model=PreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Language & App Preferences",
)
async def update_my_preferences(
    payload: PreferenceUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreferenceResponse:
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    res = await db.execute(stmt)
    pref = res.scalar_one_or_none()

    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(pref, field, val)

    await db.commit()
    await db.refresh(pref)

    await log_audit_event(
        db=db,
        action="PREFERENCE_UPDATED",
        user_id=current_user.id,
        request=request,
        details=update_data,
    )

    return PreferenceResponse.model_validate(pref)


# ==============================================================================
# Emergency Contacts Management
# ==============================================================================


@router.get(
    "/me/emergency-contacts",
    response_model=list[EmergencyContactResponse],
    status_code=status.HTTP_200_OK,
    summary="List Emergency Contacts",
)
async def list_my_emergency_contacts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EmergencyContactResponse]:
    stmt = (
        select(EmergencyContact)
        .where(EmergencyContact.user_id == current_user.id)
        .order_by(EmergencyContact.is_primary.desc(), EmergencyContact.created_at.asc())
    )
    res = await db.execute(stmt)
    contacts = res.scalars().all()
    return [EmergencyContactResponse.model_validate(c) for c in contacts]


@router.post(
    "/me/emergency-contacts",
    response_model=EmergencyContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Emergency Contact",
)
async def create_emergency_contact(
    payload: EmergencyContactCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmergencyContactResponse:
    # If set as primary, unmark existing primary contacts
    if payload.is_primary:
        await db.execute(
            update(EmergencyContact)
            .where(EmergencyContact.user_id == current_user.id)
            .values(is_primary=False)
        )

    contact = EmergencyContact(
        user_id=current_user.id,
        name=payload.name.strip(),
        relationship=payload.relationship.strip(),
        phone_number=payload.phone_number.strip(),
        is_primary=payload.is_primary,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)

    await log_audit_event(
        db=db,
        action="EMERGENCY_CONTACT_ADDED",
        user_id=current_user.id,
        request=request,
        details={"name": contact.name, "relationship": contact.relationship},
    )

    return EmergencyContactResponse.model_validate(contact)


@router.delete(
    "/me/emergency-contacts/{contact_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Emergency Contact",
)
async def delete_emergency_contact(
    contact_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(EmergencyContact).where(
        EmergencyContact.id == contact_id,
        EmergencyContact.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    contact = res.scalar_one_or_none()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Emergency contact not found"
        )

    await db.delete(contact)
    await db.commit()

    await log_audit_event(
        db=db,
        action="EMERGENCY_CONTACT_DELETED",
        user_id=current_user.id,
        request=request,
        details={"contact_id": str(contact_id)},
    )

    return {"detail": "Emergency contact deleted successfully"}


# ==============================================================================
# Role-Based Access Control (RBAC) Admin Endpoint Demonstration
# ==============================================================================


@router.get(
    "/admin/users",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List All Users (Admin Only)",
    description="Demonstrates RBAC protection using require_role('admin').",
)
async def admin_list_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role("admin")),
) -> list[UserResponse]:
    stmt = select(User).order_by(User.created_at.desc())
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [UserResponse.model_validate(u) for u in users]
