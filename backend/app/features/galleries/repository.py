"""
Galleries Feature - Repository
갤러리 이미지 DB 접근 레이어
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, delete, func
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import GalleryImage
from app.core.logging import get_repository_logger

logger = get_repository_logger("Gallery")


class GalleryRepository:
    """
    [Layer 4] Repository
    책임: 갤러리 이미지 CRUD
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_image(
        self,
        image_id: str,
        user_id: str,
        scenario_id: str,
        session_id: Optional[str],
        stage_tag: str,
        image_url: str,
        image_type: str = "generated",
        generation_prompt: Optional[str] = None,
        generation_model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GalleryImage:
        """
        이미지 생성

        Args:
            image_id: 이미지 ID (UUID)
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            session_id: 세션 ID
            stage_tag: 스테이지 태그
            image_url: 이미지 URL
            image_type: 이미지 타입 (generated, unlocked, default)
            generation_prompt: AI 생성 프롬프트
            generation_model: AI 생성 모델명
            metadata: 추가 메타데이터

        Returns:
            생성된 GalleryImage
        """
        logger.info("create_image", f"Creating image for user {user_id}", image_id=image_id)

        image = GalleryImage(
            image_id=image_id,
            user_id=user_id,
            scenario_id=scenario_id,
            session_id=session_id,
            stage_tag=stage_tag,
            image_url=image_url,
            image_type=image_type,
            generation_prompt=generation_prompt,
            generation_model=generation_model,
            metadata=metadata
        )

        self.db.add(image)
        await self.db.flush()

        logger.info("create_image", f"Image created", image_id=image_id)
        return image

    async def get_image(self, image_id: str) -> Optional[GalleryImage]:
        """
        이미지 조회

        Args:
            image_id: 이미지 ID

        Returns:
            GalleryImage 또는 None
        """
        stmt = select(GalleryImage).where(GalleryImage.image_id == image_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_user_images(
        self,
        user_id: str,
        scenario_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[GalleryImage]:
        """
        사용자 이미지 목록 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID 필터 (선택적)
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            GalleryImage 리스트
        """
        logger.debug("list_user_images", f"Listing images for user {user_id}",
                    scenario_id=scenario_id, limit=limit)

        stmt = select(GalleryImage).where(GalleryImage.user_id == user_id)

        if scenario_id:
            stmt = stmt.where(GalleryImage.scenario_id == scenario_id)

        stmt = stmt.order_by(GalleryImage.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        images = result.scalars().all()

        logger.debug("list_user_images", f"Found {len(images)} images")
        return list(images)

    async def get_unlocked_images(
        self,
        user_id: str,
        scenario_id: str
    ) -> List[GalleryImage]:
        """
        사용자가 언락한 이미지 목록

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            언락한 GalleryImage 리스트
        """
        logger.debug("get_unlocked_images", f"Getting unlocked images for user {user_id}",
                    scenario_id=scenario_id)

        stmt = (
            select(GalleryImage)
            .where(
                and_(
                    GalleryImage.user_id == user_id,
                    GalleryImage.scenario_id == scenario_id,
                    GalleryImage.is_unlocked == True
                )
            )
            .order_by(GalleryImage.unlocked_at.desc())
        )

        result = await self.db.execute(stmt)
        images = result.scalars().all()

        logger.debug("get_unlocked_images", f"Found {len(images)} unlocked images")
        return list(images)

    async def unlock_image(
        self,
        image_id: str,
        user_id: str
    ) -> Optional[GalleryImage]:
        """
        이미지 언락

        Args:
            image_id: 이미지 ID
            user_id: 사용자 ID (권한 체크용)

        Returns:
            언락된 GalleryImage 또는 None
        """
        logger.info("unlock_image", f"Unlocking image {image_id}", user_id=user_id)

        stmt = select(GalleryImage).where(
            and_(
                GalleryImage.image_id == image_id,
                GalleryImage.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        image = result.scalar_one_or_none()

        if not image:
            logger.warning("unlock_image", f"Image not found or no permission", image_id=image_id)
            return None

        image.is_unlocked = True
        image.unlocked_at = datetime.utcnow()
        await self.db.flush()

        logger.info("unlock_image", f"Image unlocked", image_id=image_id)
        return image

    async def toggle_favorite(
        self,
        image_id: str,
        user_id: str
    ) -> Optional[bool]:
        """
        즐겨찾기 토글

        Args:
            image_id: 이미지 ID
            user_id: 사용자 ID

        Returns:
            새로운 즐겨찾기 상태 (True/False) 또는 None (이미지 없음)
        """
        logger.info("toggle_favorite", f"Toggling favorite for image {image_id}", user_id=user_id)

        stmt = select(GalleryImage).where(
            and_(
                GalleryImage.image_id == image_id,
                GalleryImage.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        image = result.scalar_one_or_none()

        if not image:
            logger.warning("toggle_favorite", f"Image not found", image_id=image_id)
            return None

        image.is_favorite = not image.is_favorite
        await self.db.flush()

        logger.info("toggle_favorite", f"Favorite toggled to {image.is_favorite}", image_id=image_id)
        return image.is_favorite

    async def delete_image(
        self,
        image_id: str,
        user_id: str
    ) -> bool:
        """
        이미지 삭제

        Args:
            image_id: 이미지 ID
            user_id: 사용자 ID (권한 체크용)

        Returns:
            삭제 성공 여부
        """
        logger.warning("delete_image", f"Deleting image {image_id}", user_id=user_id)

        stmt = delete(GalleryImage).where(
            and_(
                GalleryImage.image_id == image_id,
                GalleryImage.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        await self.db.flush()

        success = result.rowcount > 0

        if success:
            logger.warning("delete_image", f"Image deleted", image_id=image_id)
        else:
            logger.warning("delete_image", f"Image not found or no permission", image_id=image_id)

        return success

    async def count_user_images(
        self,
        user_id: str,
        scenario_id: Optional[str] = None
    ) -> int:
        """
        사용자 이미지 개수

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID 필터 (선택적)

        Returns:
            이미지 개수
        """
        stmt = select(func.count(GalleryImage.image_id)).where(
            GalleryImage.user_id == user_id
        )

        if scenario_id:
            stmt = stmt.where(GalleryImage.scenario_id == scenario_id)

        result = await self.db.execute(stmt)
        count = result.scalar_one()

        return count
