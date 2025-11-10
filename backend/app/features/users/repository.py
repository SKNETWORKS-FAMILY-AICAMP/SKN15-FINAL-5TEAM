"""
Users Repository
사용자 데이터 액세스 계층
Layer 4: Repository
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_parent_logger

logger = get_parent_logger("UserRepository")


class UserRepository:
    """
    사용자 데이터 액세스
    Layer 4: Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 ID로 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 정보 또는 None
        """
        query = text("""
            SELECT
                user_id, username, display_name, email,
                is_active, is_verified, role,
                total_sessions, total_bubbles,
                last_login_at, created_at, updated_at
            FROM users
            WHERE user_id = :user_id
        """)

        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            logger.debug("get_user_by_id", "User not found", user_id=user_id)
            return None

        return {
            "user_id": str(row.user_id),
            "username": row.username,
            "display_name": row.display_name,
            "email": row.email,
            "is_active": row.is_active,
            "is_verified": row.is_verified,
            "role": row.role,
            "total_sessions": row.total_sessions or 0,
            "total_bubbles": row.total_bubbles or 0,
            "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def update_user_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> bool:
        """
        사용자 프로필 업데이트

        Args:
            user_id: 사용자 ID
            display_name: 표시 이름 (선택)
            email: 이메일 (선택)

        Returns:
            성공 여부
        """
        # 업데이트할 필드 구성
        updates = []
        params = {"user_id": user_id, "updated_at": datetime.utcnow()}

        if display_name is not None:
            updates.append("display_name = :display_name")
            params["display_name"] = display_name

        if email is not None:
            updates.append("email = :email")
            params["email"] = email

        if not updates:
            return True  # 업데이트할 것이 없음

        updates.append("updated_at = :updated_at")

        query = text(f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE user_id = :user_id
        """)

        await self.db.execute(query, params)
        await self.db.commit()

        logger.info("update_user_profile", "Profile updated", user_id=user_id)
        return True

    async def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 통계 정보
        """
        query = text("""
            SELECT
                u.total_sessions,
                u.total_bubbles,
                uc.current_credits,
                COUNT(DISTINCT s.session_id) as active_sessions,
                MAX(s.created_at) as last_session_at
            FROM users u
            LEFT JOIN user_credits uc ON u.user_id = uc.user_id
            LEFT JOIN sessions s ON u.user_id = s.user_id
            WHERE u.user_id = :user_id
            GROUP BY u.user_id, u.total_sessions, u.total_bubbles, uc.current_credits
        """)

        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            return None

        return {
            "total_sessions": row.total_sessions or 0,
            "total_bubbles": row.total_bubbles or 0,
            "current_credits": row.current_credits or 0,
            "active_sessions": row.active_sessions or 0,
            "last_session_at": row.last_session_at.isoformat() if row.last_session_at else None,
        }

    async def get_user_credits(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 크레딧 조회

        Args:
            user_id: 사용자 ID

        Returns:
            크레딧 정보
        """
        query = text("""
            SELECT
                COALESCE(bubble_count, 0) as current_credits,
                COALESCE(total_purchased, 0) as total_earned,
                COALESCE(total_consumed, 0) as total_consumed
            FROM user_credits
            WHERE user_id = :user_id
        """)

        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            # 크레딧 레코드가 없으면 기본값 반환
            return {
                "current_credits": 0,
                "total_earned": 0,
                "total_consumed": 0
            }

        return {
            "current_credits": row.current_credits,
            "total_earned": row.total_earned,
            "total_consumed": row.total_consumed,
        }

    async def consume_credits(
        self,
        user_id: str,
        amount: int,
        description: str
    ) -> bool:
        """
        크레딧 소비

        Args:
            user_id: 사용자 ID
            amount: 소비할 양
            description: 사용 목적

        Returns:
            성공 여부
        """
        # 현재 크레딧 확인
        check_query = text("""
            SELECT bubble_count
            FROM user_credits
            WHERE user_id = :user_id
        """)
        result = await self.db.execute(check_query, {"user_id": user_id})
        row = result.fetchone()

        if not row or row.bubble_count < amount:
            logger.warning(
                "consume_credits",
                "Insufficient credits",
                user_id=user_id,
                required=amount,
                available=row.bubble_count if row else 0
            )
            return False

        # 크레딧 차감
        update_query = text("""
            UPDATE user_credits
            SET
                bubble_count = bubble_count - :amount,
                total_consumed = total_consumed + :amount,
                last_updated = :updated_at
            WHERE user_id = :user_id
        """)

        await self.db.execute(update_query, {
            "user_id": user_id,
            "amount": amount,
            "updated_at": datetime.utcnow()
        })
        await self.db.commit()

        logger.info(
            "consume_credits",
            "Credits consumed",
            user_id=user_id,
            amount=amount,
            description=description
        )
        return True
