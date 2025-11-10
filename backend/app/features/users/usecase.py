"""
Users Feature - UseCase
사용자 프로필 및 통계 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.logging import get_usecase_logger
from .repository import UserRepository

logger = get_usecase_logger("User")


class UserUseCase:
    """
    [Layer 2] UseCase
    책임: 사용자 관리 비즈니스 로직, 트랜잭션 경계
    금지: DB 직접 접근 (Repository 사용), HTTP 처리 (Controller가 담당)
    """

    def __init__(self, db: AsyncSession):
        """
        UseCase 초기화

        Args:
            db: 데이터베이스 세션 (Controller에서 주입)
        """
        self.db = db
        self.repository = UserRepository(db)

    async def get_user_profile(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        사용자 프로필 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 프로필 정보
            {
                "user_id": str,
                "username": str,
                "display_name": str,
                "email": str,
                "credits": int,
                "created_at": str,
                "updated_at": str
            }
        """
        logger.info("get_user_profile", "Getting user profile", user_id=user_id)

        # Repository로 사용자 조회
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            logger.warning("get_user_profile", "User not found", user_id=user_id)
            return None

        logger.info("get_user_profile", "Profile retrieved", user_id=user_id)
        return user

    async def update_user_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        사용자 프로필 수정

        Args:
            user_id: 사용자 ID
            display_name: 표시 이름 (선택적)
            email: 이메일 (선택적)

        Returns:
            수정된 프로필 정보
        """
        logger.info("update_user_profile", "Updating user profile",
                   user_id=user_id)

        # 수정할 필드 구성
        updates = {}
        if display_name is not None:
            updates["display_name"] = display_name
        if email is not None:
            updates["email"] = email

        if not updates:
            logger.warning("update_user_profile", "No fields to update")
            return await self.get_user_profile(user_id)

        # Repository로 프로필 업데이트
        success = await self.repository.update_user_profile(
            user_id,
            display_name=updates.get("display_name"),
            email=updates.get("email")
        )

        if not success:
            logger.warning("update_user_profile", "Update failed", user_id=user_id)
            return None

        logger.info("update_user_profile", "Profile updated",
                   user_id=user_id, fields=list(updates.keys()))

        # 업데이트된 프로필 반환
        return await self.get_user_profile(user_id)

    async def get_user_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        사용자 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 통계
            {
                "total_dialogues": int,  # 총 대화 수
                "total_sessions": int,  # 총 세션 수
                "completed_scenarios": int,  # 완료한 시나리오 수
                "total_credits_used": int,  # 사용한 크레딧
                "total_affinity_points": int,  # 총 친밀도 점수
                "achievements": List[str],  # 달성한 업적
                "rank": str,  # 사용자 등급
                "created_at": str,  # 가입일
                "last_active_at": str  # 마지막 활동
            }
        """
        logger.info("get_user_stats", "Getting user stats", user_id=user_id)

        # Repository로 통계 조회
        stats = await self.repository.get_user_stats(user_id)

        if not stats:
            # 사용자가 없으면 기본값 반환
            stats = {
                "total_sessions": 0,
                "total_bubbles": 0,
                "current_credits": 0,
                "active_sessions": 0,
                "last_session_at": None
            }

        logger.info("get_user_stats", "Stats retrieved", user_id=user_id)
        return stats

    async def get_user_credits(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        사용자 크레딧 조회

        Args:
            user_id: 사용자 ID

        Returns:
            크레딧 정보
        """
        logger.info("get_user_credits", "Getting user credits", user_id=user_id)

        credits = await self.repository.get_user_credits(user_id)

        logger.info("get_user_credits", "Credits retrieved", user_id=user_id)
        return credits

    async def consume_user_credits(
        self,
        user_id: str,
        amount: int,
        description: str
    ) -> Dict[str, Any]:
        """
        사용자 크레딧 소비

        Args:
            user_id: 사용자 ID
            amount: 소비할 양
            description: 사용 목적

        Returns:
            소비 결과
        """
        logger.info("consume_user_credits", "Consuming credits",
                   user_id=user_id, amount=amount)

        # 크레딧 소비
        success = await self.repository.consume_credits(user_id, amount, description)

        if not success:
            logger.warning("consume_user_credits", "Failed to consume credits",
                          user_id=user_id, amount=amount)
            return {
                "success": False,
                "message": "Insufficient credits",
                "remaining_credits": 0
            }

        # 남은 크레딧 조회
        credits = await self.repository.get_user_credits(user_id)

        logger.info("consume_user_credits", "Credits consumed successfully",
                   user_id=user_id, amount=amount)

        return {
            "success": True,
            "message": "Credits consumed successfully",
            "remaining_credits": credits["current_credits"]
        }
