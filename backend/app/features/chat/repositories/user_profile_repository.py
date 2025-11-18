"""
UserProfile Repository - 사용자 프로필 저장소
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from ..models.user_profile import UserProfile
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserProfileRepository:
    """사용자 프로필 Repository

    목적: 최소 기억 유지 (이름, 호칭, 말투, 취향 등)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """사용자 프로필 조회

        Args:
            user_id: 사용자 ID

        Returns:
            UserProfile 또는 None
        """
        try:
            query = select(UserProfile).where(UserProfile.user_id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("get_profile", f"Failed to get profile for user {user_id}: {e}")
            return None

    async def create_or_update_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        speaking_style: Optional[str] = None,
        likes: Optional[list] = None,
        dislikes: Optional[list] = None,
        personality_traits: Optional[dict] = None
    ) -> UserProfile:
        """프로필 생성 또는 업데이트

        Args:
            user_id: 사용자 ID
            display_name: 선호하는 호칭
            speaking_style: 말투
            likes: 좋아하는 것들
            dislikes: 싫어하는 것들
            personality_traits: 성격 특성

        Returns:
            UserProfile
        """
        profile = await self.get_profile(user_id)

        if profile:
            # 업데이트
            if display_name is not None:
                profile.display_name = display_name
            if speaking_style is not None:
                profile.speaking_style = speaking_style
            if likes is not None:
                profile.likes = likes
            if dislikes is not None:
                profile.dislikes = dislikes
            if personality_traits is not None:
                profile.personality_traits = personality_traits

            profile.updated_at = datetime.utcnow()
            logger.info("create_or_update_profile", f"Updated profile for user {user_id}")
        else:
            # 생성
            profile = UserProfile(
                user_id=user_id,
                display_name=display_name,
                speaking_style=speaking_style,
                likes=likes or [],
                dislikes=dislikes or [],
                personality_traits=personality_traits or {}
            )
            self.db.add(profile)
            logger.info("create_or_update_profile", f"Created profile for user {user_id}")

        await self.db.flush()
        return profile

    async def get_profile_for_prompt(self, user_id: str) -> str:
        """프롬프트용 프로필 텍스트 생성

        Args:
            user_id: 사용자 ID

        Returns:
            프로필 텍스트 (포맷팅된 문자열)
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return "(사용자 프로필 없음)"

        lines = []
        if profile.display_name:
            lines.append(f"호칭: {profile.display_name}")
        if profile.speaking_style:
            lines.append(f"말투: {profile.speaking_style}")
        if profile.likes:
            lines.append(f"좋아하는 것: {', '.join(profile.likes)}")
        if profile.dislikes:
            lines.append(f"싫어하는 것: {', '.join(profile.dislikes)}")
        if profile.personality_traits:
            traits_list = [f"{k}({v})" for k, v in profile.personality_traits.items()]
            lines.append(f"성격: {', '.join(traits_list)}")

        return "\n".join(lines) if lines else "(사용자 프로필 비어있음)"

    async def delete_profile(self, user_id: str) -> bool:
        """프로필 삭제

        Args:
            user_id: 사용자 ID

        Returns:
            삭제 성공 여부
        """
        try:
            profile = await self.get_profile(user_id)
            if profile:
                await self.db.delete(profile)
                await self.db.flush()
                logger.info("delete_profile", f"Deleted profile for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error("delete_profile", f"Failed to delete profile for user {user_id}: {e}")
            return False
