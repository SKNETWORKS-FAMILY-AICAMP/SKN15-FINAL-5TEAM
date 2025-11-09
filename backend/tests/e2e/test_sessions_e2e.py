"""
E2E Tests - Sessions
Tests for session workflows: create, list, get detail, delete
"""
import pytest
from httpx import AsyncClient
from typing import Dict


@pytest.mark.asyncio
async def test_sessions_flow(
    client: AsyncClient,
    auth_headers: Dict[str, str],
    test_scenario_id: str
):
    """
    E2E: Complete sessions flow
    1. Create session
    2. List sessions
    3. Get session detail
    4. Delete session
    """
    # 1. Create session
    session_data = {
        "scenario_id": test_scenario_id,
        "user_name": "E2E Tester"
    }

    create_response = await client.post(
        "/api/sessions",
        json=session_data,
        headers=auth_headers
    )
    assert create_response.status_code == 200

    session = create_response.json()
    assert "session_id" in session
    assert session["scenario_id"] == test_scenario_id
    assert session["user_name"] == "E2E Tester"
    session_id = session["session_id"]

    # 2. List sessions
    list_response = await client.get("/api/sessions", headers=auth_headers)
    assert list_response.status_code == 200

    sessions = list_response.json()
    assert isinstance(sessions, list)
    assert len(sessions) > 0

    # Verify our session is in the list
    our_session = next((s for s in sessions if s["session_id"] == session_id), None)
    assert our_session is not None

    # 3. Get session detail
    detail_response = await client.get(
        f"/api/sessions/{session_id}",
        headers=auth_headers
    )
    assert detail_response.status_code == 200

    session_detail = detail_response.json()
    assert session_detail["session_id"] == session_id
    assert session_detail["scenario_id"] == test_scenario_id

    # 4. Delete session
    delete_response = await client.delete(
        f"/api/sessions/{session_id}",
        headers=auth_headers
    )
    assert delete_response.status_code == 200

    # Verify session is deleted
    verify_response = await client.get(
        f"/api/sessions/{session_id}",
        headers=auth_headers
    )
    assert verify_response.status_code == 404


@pytest.mark.asyncio
async def test_create_session_invalid_scenario(
    client: AsyncClient,
    auth_headers: Dict[str, str]
):
    """
    E2E: Create session with invalid scenario should fail
    """
    session_data = {
        "scenario_id": "nonexistent_scenario",
        "user_name": "Test User"
    }

    response = await client.post(
        "/api/sessions",
        json=session_data,
        headers=auth_headers
    )
    # Should return 400 or 404
    assert response.status_code in [400, 404]
