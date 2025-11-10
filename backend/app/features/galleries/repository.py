"""
Galleries Feature - Repository
갤러리 이미지 DB 접근 레이어
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, delete, func
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from .models import GalleryImage, GalleryImageLike, GalleryImageView
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
        extra_metadata: Optional[Dict[str, Any]] = None
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
            extra_metadata: 추가 메타데이터

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
            extra_metadata=extra_metadata
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
        offset: int = 0,
        viewer_user_id: Optional[str] = None
    ) -> List[Tuple[GalleryImage, int, int, bool]]:
        """
        사용자 이미지 목록 조회 (통계 정보 포함)

        Args:
            user_id: 이미지 소유자 ID
            scenario_id: 시나리오 ID 필터 (선택적)
            limit: 페이징 크기
            offset: 페이징 오프셋
            viewer_user_id: 조회하는 사용자 ID (좋아요 여부 확인용, 선택적)

        Returns:
            List[Tuple[GalleryImage, like_count, view_count, user_liked]]
        """
        logger.debug("list_user_images", f"Listing images for user {user_id}",
                    scenario_id=scenario_id, limit=limit)

        # user_liked 계산
        if viewer_user_id:
            is_liked_expr = (
                select(func.count(GalleryImageLike.like_id))
                .where(
                    and_(
                        GalleryImageLike.image_id == GalleryImage.image_id,
                        GalleryImageLike.user_id == viewer_user_id
                    )
                )
                .scalar_subquery() > 0
            )
        else:
            is_liked_expr = False

        stmt = (
            select(
                GalleryImage,
                func.count(func.distinct(GalleryImageLike.like_id)).label("like_count"),
                func.count(func.distinct(GalleryImageView.view_id)).label("view_count"),
                is_liked_expr.label("user_liked")
            )
            .outerjoin(GalleryImageLike, GalleryImage.image_id == GalleryImageLike.image_id)
            .outerjoin(GalleryImageView, GalleryImage.image_id == GalleryImageView.image_id)
            .where(GalleryImage.user_id == user_id)
        )

        if scenario_id:
            stmt = stmt.where(GalleryImage.scenario_id == scenario_id)

        stmt = (
            stmt
            .group_by(GalleryImage.image_id)
            .order_by(GalleryImage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        images = result.all()

        logger.debug("list_user_images", f"Found {len(images)} images")
        return images

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

    async def get_images_by_user_id(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Tuple[GalleryImage, int, int, bool]]:
        """
        사용자의 모든 갤러리 이미지 조회 (통계 정보 포함)
        마이페이지용 - 모든 시나리오의 이미지를 조회

        Args:
            user_id: 사용자 ID
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            List[Tuple[GalleryImage, like_count, view_count, user_liked]]
        """
        logger.debug("get_images_by_user_id", f"Getting all images for user {user_id}",
                    limit=limit, offset=offset)

        # list_user_images 메서드를 재사용 (scenario_id 필터 없이, viewer는 본인)
        return await self.list_user_images(
            user_id=user_id,
            scenario_id=None,  # 모든 시나리오
            limit=limit,
            offset=offset,
            viewer_user_id=user_id  # 본인의 좋아요 여부 확인
        )

    # ============================================================
    # Like Management
    # ============================================================

    async def toggle_image_like(
        self,
        image_id: str,
        user_id: str
    ) -> bool:
        """
        이미지 좋아요 토글

        Args:
            image_id: 이미지 ID
            user_id: 사용자 ID

        Returns:
            is_liked (True: 좋아요 추가, False: 좋아요 취소)
        """
        logger.info("toggle_image_like", f"Toggling like for image {image_id}", user_id=user_id)

        # 기존 좋아요 확인
        stmt = select(GalleryImageLike).where(
            and_(
                GalleryImageLike.image_id == image_id,
                GalleryImageLike.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        existing_like = result.scalar_one_or_none()

        if existing_like:
            # 좋아요 취소
            await self.db.delete(existing_like)
            await self.db.flush()

            logger.info("toggle_image_like", f"Like removed", image_id=image_id)
            return False
        else:
            # 좋아요 추가
            like = GalleryImageLike(image_id=image_id, user_id=user_id)
            self.db.add(like)
            await self.db.flush()

            logger.info("toggle_image_like", f"Like added", image_id=image_id)
            return True

    # ============================================================
    # View Management
    # ============================================================

    async def record_image_view(
        self,
        image_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        이미지 조회 기록

        Args:
            image_id: 이미지 ID
            user_id: 사용자 ID (선택)
            ip_address: IP 주소 (선택)

        Returns:
            성공 여부
        """
        logger.info("record_image_view", f"Recording view for image {image_id}",
                   user_id=user_id, ip_address=ip_address)

        try:
            view = GalleryImageView(
                image_id=image_id,
                user_id=user_id,
                ip_address=ip_address
            )
            self.db.add(view)
            await self.db.flush()

            logger.info("record_image_view", f"View recorded", image_id=image_id)
            return True
        except Exception as e:
            logger.error("record_image_view", f"Failed to record view: {e}", image_id=image_id)
            return False
