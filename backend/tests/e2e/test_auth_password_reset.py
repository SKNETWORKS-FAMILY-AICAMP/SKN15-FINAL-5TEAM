"""
Password Reset Tests
비밀번호 재설정 기능 테스트
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient):
    """
    Complete password reset flow
    1. Request password reset
    2. Reset password with token
    3. Login with new password
    """
    # 1. Request password reset (먼저 사용자 생성)
    signup_data = {
        "username": "reset_test_user",
        "password": "old_password_123",
        "display_name": "Reset Test User",
        "email": "reset@example.com"
    }

    signup_response = await client.post("/api/auth/register", json=signup_data)
    assert signup_response.status_code in [201, 409]  # Created or already exists

    # 2. Request password reset
    reset_request_data = {
        "email": "reset@example.com"
    }

    reset_request_response = await client.post(
        "/api/auth/password-reset/request",
        json=reset_request_data
    )
    assert reset_request_response.status_code == 200

    # Extract token from response (개발 환경에서만)
    response_data = reset_request_response.json()
    message = response_data["message"]

    # Extract token from message
    if "dev only" in message.lower():
        token = message.split(": ")[-1]
    else:
        pytest.skip("Token not returned in dev mode")

    # 3. Reset password with token
    reset_confirm_data = {
        "token": token,
        "new_password": "new_password_456"
    }

    reset_confirm_response = await client.post(
        "/api/auth/password-reset/confirm",
        json=reset_confirm_data
    )
    assert reset_confirm_response.status_code == 200

    # 4. Login with new password
    login_data = {
        "username": "reset_test_user",
        "password": "new_password_456"
    }

    login_response = await client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200

    token_data = login_response.json()
    assert "access_token" in token_data


@pytest.mark.asyncio
async def test_password_reset_invalid_token(client: AsyncClient):
    """
    Password reset with invalid token should fail
    """
    reset_data = {
        "token": "invalid_token_12345",
        "new_password": "new_password_123"
    }

    response = await client.post("/api/auth/password-reset/confirm", json=reset_data)
    assert response.status_code == 400  # Bad request


@pytest.mark.asyncio
async def test_password_reset_used_token(client: AsyncClient):
    """
    Password reset with already used token should fail
    """
    # This test requires creating a token and using it twice
    # For now, we'll skip this test
    pytest.skip("Token reuse test requires additional setup")
