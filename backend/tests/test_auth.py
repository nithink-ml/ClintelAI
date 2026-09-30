"""Integration tests for Authentication, Authorization, RBAC, Profile, and Preferences."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_auth_full_lifecycle():
    unique_id = uuid.uuid4().hex[:8]
    test_email = f"priya.{unique_id}@example.com"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register a new user
        reg_payload = {
            "email": test_email,
            "password": "SecurePassword123!",
            "full_name": "Dr. Priya Sharma",
            "preferred_language": "ta",
        }
        reg_resp = await client.post(f"{settings.API_V1_STR}/auth/register", json=reg_payload)
        assert reg_resp.status_code == 201, reg_resp.text
        tokens = reg_resp.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 2. Prevent duplicate email registration
        dup_resp = await client.post(f"{settings.API_V1_STR}/auth/register", json=reg_payload)
        assert dup_resp.status_code == 400
        assert "already exists" in dup_resp.json()["detail"]

        # 3. Login with credentials
        login_resp = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": test_email, "password": "SecurePassword123!"},
        )
        assert login_resp.status_code == 200
        login_tokens = login_resp.json()
        assert "access_token" in login_tokens

        # 4. Fail login with incorrect password
        bad_login = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": test_email, "password": "WrongPassword999"},
        )
        assert bad_login.status_code == 401

        # 5. Fetch /me profile details
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        me_resp = await client.get(f"{settings.API_V1_STR}/auth/me", headers=auth_headers)
        assert me_resp.status_code == 200
        user_data = me_resp.json()
        assert user_data["email"] == test_email
        assert user_data["profile"]["full_name"] == "Dr. Priya Sharma"
        assert user_data["preferences"]["preferred_language"] == "ta"

        # 6. Update user profile
        profile_update = {
            "city": "Chennai",
            "state": "Tamil Nadu",
            "blood_group": "O+",
            "phone_number": "+91 9876543210",
        }
        prof_resp = await client.put(
            f"{settings.API_V1_STR}/users/me/profile",
            json=profile_update,
            headers=auth_headers,
        )
        assert prof_resp.status_code == 200
        prof_data = prof_resp.json()
        assert prof_data["city"] == "Chennai"
        assert prof_data["blood_group"] == "O+"

        # 7. Update user language preference
        pref_update = {
            "preferred_language": "hi",
            "theme": "dark",
            "emergency_alerts_enabled": True,
        }
        pref_resp = await client.put(
            f"{settings.API_V1_STR}/users/me/preferences",
            json=pref_update,
            headers=auth_headers,
        )
        assert pref_resp.status_code == 200
        pref_data = pref_resp.json()
        assert pref_data["preferred_language"] == "hi"
        assert pref_data["theme"] == "dark"

        # 8. Manage Emergency Contacts (Add, List, Delete)
        contact_payload = {
            "name": "Ramesh Sharma",
            "relationship": "Spouse",
            "phone_number": "+91 9876500000",
            "is_primary": True,
        }
        add_contact = await client.post(
            f"{settings.API_V1_STR}/users/me/emergency-contacts",
            json=contact_payload,
            headers=auth_headers,
        )
        assert add_contact.status_code == 201
        contact_id = add_contact.json()["id"]

        list_contacts = await client.get(
            f"{settings.API_V1_STR}/users/me/emergency-contacts",
            headers=auth_headers,
        )
        assert list_contacts.status_code == 200
        assert len(list_contacts.json()) == 1

        del_contact = await client.delete(
            f"{settings.API_V1_STR}/users/me/emergency-contacts/{contact_id}",
            headers=auth_headers,
        )
        assert del_contact.status_code == 200

        # 9. Test RBAC: Normal user cannot access admin endpoint
        admin_resp = await client.get(
            f"{settings.API_V1_STR}/users/admin/users",
            headers=auth_headers,
        )
        assert admin_resp.status_code == 403
        assert "Operation not permitted" in admin_resp.json()["detail"]

        # 10. Test Refresh Token Rotation
        rotate_resp = await client.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert rotate_resp.status_code == 200
        new_tokens = rotate_resp.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

        # Attempting to re-use old rotated refresh token MUST be rejected
        reuse_resp = await client.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert reuse_resp.status_code == 401

        # 11. Test Logout
        logout_resp = await client.post(
            f"{settings.API_V1_STR}/auth/logout",
            json={"refresh_token": new_tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert logout_resp.status_code == 200


@pytest.mark.asyncio
async def test_password_validation_rules():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Password without digits
        resp = await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "invalid.pwd@example.com",
                "password": "onlylettershere",
                "full_name": "Test User",
            },
        )
        assert resp.status_code == 422

        # Password too short (<8 chars)
        resp2 = await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "short.pwd@example.com",
                "password": "p1",
                "full_name": "Test User",
            },
        )
        assert resp2.status_code == 422
