"""
E2E Tests - Scenarios
Tests for scenario workflows: list, detail, like, comment
"""
import pytest
from httpx import AsyncClient
from typing import Dict


@pytest.mark.asyncio
async def test_scenarios_flow(
    client: AsyncClient,
    auth_headers: Dict[str, str],
    test_scenario_id: str
):
    """
    E2E: Complete scenarios flow
    1. List scenarios
    2. Get scenario detail
    3. Like scenario
    4. Create comment
    5. Get comments
    """
    # 1. List scenarios
    list_response = await client.get("/api/scenarios", headers=auth_headers)
    assert list_response.status_code == 200

    scenarios = list_response.json()
    assert isinstance(scenarios, list)

    # 2. Get scenario detail
    detail_response = await client.get(
        f"/api/scenarios/{test_scenario_id}",
        headers=auth_headers
    )
    assert detail_response.status_code == 200

    scenario = detail_response.json()
    assert scenario["scenario_id"] == test_scenario_id
    assert "title" in scenario
    assert "description" in scenario
    assert "like_count" in scenario
    assert "user_liked" in scenario

    # 3. Like scenario
    like_response = await client.post(
        f"/api/scenarios/{test_scenario_id}/like",
        headers=auth_headers
    )
    assert like_response.status_code == 200

    like_result = like_response.json()
    assert "is_liked" in like_result
    assert "like_count" in like_result

    # 4. Create comment
    comment_data = {
        "content": "This is a great scenario! E2E test comment."
    }

    comment_response = await client.post(
        f"/api/scenarios/{test_scenario_id}/comments",
        json=comment_data,
        headers=auth_headers
    )
    assert comment_response.status_code == 200

    comment = comment_response.json()
    assert comment["content"] == comment_data["content"]
    assert "id" in comment
    comment_id = comment["id"]

    # 5. Get comments
    comments_response = await client.get(
        f"/api/scenarios/{test_scenario_id}/comments",
        headers=auth_headers
    )
    assert comments_response.status_code == 200

    comments = comments_response.json()
    assert isinstance(comments, list)
    assert len(comments) > 0

    # Verify our comment is in the list
    our_comment = next((c for c in comments if c["id"] == comment_id), None)
    assert our_comment is not None


@pytest.mark.asyncio
async def test_scenario_not_found(
    client: AsyncClient,
    auth_headers: Dict[str, str]
):
    """
    E2E: Get non-existent scenario should return 404
    """
    response = await client.get(
        "/api/scenarios/nonexistent_scenario",
        headers=auth_headers
    )
    assert response.status_code == 404
