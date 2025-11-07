"""
Auth Repository
사용자 데이터 액세스 계층
"""
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_parent_logger

logger = get_parent_logger("AuthRepository")


class UserData:
    """사용자 데이터 DTO"""
    def __init__(self, id: int, username: str, password_hash: str, role: str):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role


class AuthRepository:
    """
    사용자 인증 관련 데이터 액세스
    Layer 4: Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_username(self, username: str) -> Optional[UserData]:
        """
        username으로 사용자 조회

        Args:
            username: 사용자명

        Returns:
            UserData 또는 None
        """
        query = text("SELECT id, username, password_hash, role FROM users WHERE username = :username")
        result = await self.db.execute(query, {"username": username})
        row = result.fetchone()

        if not row:
            logger.debug("get_user_by_username", f"User not found: {username}")
            return None

        logger.debug("get_user_by_username", f"User found: {username}", user_id=row.id)
        return UserData(
            id=row.id,
            username=row.username,
            password_hash=row.password_hash,
            role=row.role
        )
