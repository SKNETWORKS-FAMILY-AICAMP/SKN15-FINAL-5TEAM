"""
Users Feature - UseCase
사용자 프로필 및 통계 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.logging import get_usecase_logger

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
        # TODO: UserRepository 생성 필요
        # self.repository = UserRepository(db)

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

        # TODO: Repository로 사용자 조회
        # user = await self.repository.get_user_by_id(user_id)
        # if not user:
        #     logger.warning("get_user_profile", "User not found", user_id=user_id)
        #     return None

        # 임시 응답
        profile = {
            "user_id": user_id,
            "username": "temp_user",
            "display_name": "임시 사용자",
            "email": "temp@example.com",
            "credits": 1000,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        logger.info("get_user_profile", "Profile retrieved", user_id=user_id)
        return profile

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

        async with self.db.begin():
            # TODO: Repository로 프로필 업데이트
            # user = await self.repository.update_user(user_id, updates)
            # if not user:
            #     logger.warning("update_user_profile", "User not found", user_id=user_id)
            #     return None

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

        # TODO: Repository들로 통계 조회
        # total_dialogues = await self.chat_repository.count_user_dialogues(user_id)
        # total_sessions = await self.session_repository.count_user_sessions(user_id)
        # completed_scenarios = await self.scenario_repository.count_completed_scenarios(user_id)
        # ... 등등

        # 임시 응답
        stats = {
            "total_dialogues": 0,
            "total_sessions": 0,
            "completed_scenarios": 0,
            "total_credits_used": 0,
            "total_affinity_points": 0,
            "achievements": [],
            "rank": "bronze",
            "created_at": datetime.utcnow().isoformat(),
            "last_active_at": datetime.utcnow().isoformat()
        }

        logger.info("get_user_stats", "Stats retrieved", user_id=user_id)
        return stats
