"""
E2E Test Configuration
Pytest fixtures for end-to-end testing
"""
import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.core.config import get_settings
from app.core.db.base import Base

settings = get_settings()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """
    Create a test database engine
    Uses the same database as development but with a test schema
    """
    # Use test database URL (you can override in .env.test)
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for a single test
    Automatically rolls back after the test
    """
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client for making API requests
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_headers(client: AsyncClient) -> Dict[str, str]:
    """
    Create a test user and return auth headers
    """
    # Create test user (signup)
    signup_data = {
        "username": "testuser",
        "password": "testpass123",
        "display_name": "Test User"
    }

    # Try to sign up (might fail if user exists)
    signup_response = await client.post("/api/auth/signup", json=signup_data)

    # Login
    login_data = {
        "username": "testuser",
        "password": "testpass123"
    }

    login_response = await client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200

    token_data = login_response.json()
    access_token = token_data["access_token"]

    return {
        "Authorization": f"Bearer {access_token}"
    }


@pytest.fixture
async def test_user_id(auth_headers: Dict[str, str], client: AsyncClient) -> str:
    """
    Get the test user's ID
    """
    response = await client.get("/api/users/me", headers=auth_headers)
    assert response.status_code == 200

    user_data = response.json()
    return user_data["user_id"]


@pytest.fixture
async def test_scenario_id() -> str:
    """
    Return a test scenario ID
    """
    return "cutscene5_llm_driven"


@pytest.fixture
async def test_session_id(
    client: AsyncClient,
    auth_headers: Dict[str, str],
    test_scenario_id: str
) -> str:
    """
    Create a test chat session and return its ID
    """
    session_data = {
        "scenario_id": test_scenario_id,
        "user_name": "Test User"
    }

    response = await client.post(
        "/api/sessions",
        json=session_data,
        headers=auth_headers
    )

    assert response.status_code == 200
    session = response.json()
    return session["session_id"]
