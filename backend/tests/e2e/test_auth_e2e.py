"""
E2E Tests - Authentication
Tests for auth workflows: signup, login, get user
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_flow(client: AsyncClient):
    """
    E2E: Complete auth flow
    1. Signup
    2. Login
    3. Get user profile
    """
    # 1. Signup
    signup_data = {
        "username": "e2e_test_user",
        "password": "secure_password_123",
        "display_name": "E2E Test User"
    }

    signup_response = await client.post("/api/auth/signup", json=signup_data)
    print(f"Signup response: {signup_response.status_code}")

    # Signup might return 200 or 409 if user exists
    assert signup_response.status_code in [200, 409]

    # 2. Login
    login_data = {
        "username": "e2e_test_user",
        "password": "secure_password_123"
    }

    login_response = await client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200

    token_data = login_response.json()
    assert "access_token" in token_data
    assert "token_type" in token_data
    assert token_data["token_type"] == "bearer"

    access_token = token_data["access_token"]

    # 3. Get user profile
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_response = await client.get("/api/users/me", headers=headers)
    assert profile_response.status_code == 200

    profile = profile_response.json()
    assert profile["username"] == "e2e_test_user"
    assert profile["display_name"] == "E2E Test User"
    assert "user_id" in profile


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """
    E2E: Login with invalid credentials should fail
    """
    login_data = {
        "username": "nonexistent_user",
        "password": "wrong_password"
    }

    response = await client.post("/api/auth/login", json=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_user_without_auth(client: AsyncClient):
    """
    E2E: Get user profile without auth should fail
    """
    response = await client.get("/api/users/me")
    assert response.status_code == 401
