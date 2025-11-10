"""
Galleries Feature - UseCase
사용자 이미지 갤러리 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from app.core.logging import get_usecase_logger
from .repository import GalleryRepository
from .models import GalleryImage
from .services import ImageGenerationService

logger = get_usecase_logger("Gallery")


class GalleryUseCase:
    """
    [Layer 2] UseCase
    책임: 이미지 갤러리 비즈니스 로직, 트랜잭션 경계
    금지: DB 직접 접근 (Repository 사용), HTTP 처리 (Controller가 담당)
    """

    def __init__(self, db: AsyncSession):
        """
        UseCase 초기화

        Args:
            db: 데이터베이스 세션 (Controller에서 주입)
        """
        self.db = db
        self.repository = GalleryRepository(db)
        self.image_service = ImageGenerationService()

    async def list_user_images(
        self,
        user_id: str,
        scenario_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        viewer_user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        사용자 이미지 목록 조회 (통계 정보 포함)

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID 필터 (선택적)
            limit: 페이징 크기
            offset: 페이징 오프셋
            viewer_user_id: 조회하는 사용자 ID (좋아요 여부 확인용, 선택적)

        Returns:
            이미지 목록
            [
                {
                    "image_id": str,
                    "user_id": str,
                    "scenario_id": str,
                    "session_id": str,
                    "stage_tag": str,
                    "image_url": str,
                    "image_type": str,  # "generated", "unlocked", "default"
                    "extra_metadata": Dict,
                    "created_at": str,
                    "like_count": int,
                    "view_count": int,
                    "user_liked": bool
                },
                ...
            ]
        """
        logger.info("list_user_images", "Listing user images",
                   user_id=user_id, scenario_id=scenario_id, limit=limit)

        # Repository로 이미지 목록 조회 (통계 정보 포함)
        images_with_stats = await self.repository.list_user_images(
            user_id=user_id,
            scenario_id=scenario_id,
            limit=limit,
            offset=offset,
            viewer_user_id=viewer_user_id
        )

        # Tuple (GalleryImage, like_count, view_count, user_liked) → Dict 변환
        images = [
            self._image_to_dict(
                image=img,
                like_count=like_count,
                view_count=view_count,
                user_liked=user_liked
            )
            for img, like_count, view_count, user_liked in images_with_stats
        ]

        logger.info("list_user_images", f"Retrieved {len(images)} images",
                   user_id=user_id)

        return images

    async def save_generated_image(
        self,
        user_id: str,
        scenario_id: str,
        session_id: str,
        stage_tag: str,
        image_url: str,
        image_type: str = "generated",
        generation_prompt: Optional[str] = None,
        generation_model: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        생성된 이미지 저장

        Args:
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
            저장된 이미지 정보
            {
                "image_id": str,
                "user_id": str,
                "scenario_id": str,
                "session_id": str,
                "stage_tag": str,
                "image_url": str,
                "image_type": str,
                "extra_metadata": Dict,
                "created_at": str
            }
        """
        logger.info("save_generated_image", "Saving generated image",
                   user_id=user_id, scenario_id=scenario_id, stage_tag=stage_tag)

        # 이미지 URL 검증
        if not image_url:
            logger.warning("save_generated_image", "Empty image URL")
            raise ValueError("이미지 URL이 필요합니다.")

        # 이미지 ID 생성
        image_id = str(uuid.uuid4())

        # 메타데이터 기본값
        extra_metadata = extra_metadata or {}

        async with self.db.begin():
            # Repository로 이미지 저장
            image = await self.repository.create_image(
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

            logger.info("save_generated_image", "Image saved",
                       image_id=image_id)

        return self._image_to_dict(image)

    async def generate_and_save_image(
        self,
        user_id: str,
        scenario_id: str,
        session_id: str,
        stage_tag: str,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        이미지 생성 및 저장

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            session_id: 세션 ID
            stage_tag: 스테이지 태그
            prompt: 생성 프롬프트
            size: 이미지 크기
            quality: 품질
            style: 스타일

        Returns:
            저장된 이미지 정보
        """
        logger.info("generate_and_save_image", "Generating and saving image",
                   user_id=user_id, scenario_id=scenario_id, stage_tag=stage_tag)

        # 이미지 생성
        generation_result = await self.image_service.generate_image(
            prompt=prompt,
            size=size,
            quality=quality,
            style=style
        )

        # 이미지 저장
        image = await self.save_generated_image(
            user_id=user_id,
            scenario_id=scenario_id,
            session_id=session_id,
            stage_tag=stage_tag,
            image_url=generation_result["url"],
            image_type="generated",
            generation_prompt=generation_result.get("revised_prompt", prompt),
            generation_model=generation_result["model"],
            metadata={
                "size": size,
                "quality": quality,
                "style": style
            }
        )

        logger.info("generate_and_save_image", "Image generated and saved",
                   image_id=image["image_id"])

        return image

    async def unlock_image(
        self,
        user_id: str,
        scenario_id: str,
        image_id: str
    ) -> Dict[str, Any]:
        """
        이미지 언락 (해금)

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            image_id: 이미지 ID

        Returns:
            언락된 이미지 정보
        """
        logger.info("unlock_image", "Unlocking image",
                   user_id=user_id, image_id=image_id)

        async with self.db.begin():
            # Repository로 이미지 언락
            unlocked = await self.repository.unlock_image(
                image_id=image_id,
                user_id=user_id
            )

            if not unlocked:
                logger.warning("unlock_image", "Image not found or no permission",
                              image_id=image_id)
                raise ValueError("이미지를 찾을 수 없거나 권한이 없습니다.")

            logger.info("unlock_image", "Image unlocked",
                       image_id=image_id)

        return self._image_to_dict(unlocked)

    async def get_unlocked_images(
        self,
        user_id: str,
        scenario_id: str
    ) -> List[Dict[str, Any]]:
        """
        사용자가 언락한 이미지 목록 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            언락한 이미지 목록
        """
        logger.info("get_unlocked_images", "Getting unlocked images",
                   user_id=user_id, scenario_id=scenario_id)

        # Repository로 언락 이미지 조회
        unlocked_orm = await self.repository.get_unlocked_images(
            user_id=user_id,
            scenario_id=scenario_id
        )

        # ORM → Dict 변환
        unlocked = [self._image_to_dict(img) for img in unlocked_orm]

        logger.info("get_unlocked_images", f"Retrieved {len(unlocked)} unlocked images",
                   user_id=user_id)

        return unlocked

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
        logger.info("toggle_image_like", "Toggling image like",
                   image_id=image_id, user_id=user_id)

        async with self.db.begin():
            is_liked = await self.repository.toggle_image_like(
                image_id=image_id,
                user_id=user_id
            )

            logger.info("toggle_image_like", f"Like toggled to {is_liked}",
                       image_id=image_id)

        return is_liked

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
        logger.info("record_image_view", "Recording image view",
                   image_id=image_id, user_id=user_id, ip_address=ip_address)

        async with self.db.begin():
            success = await self.repository.record_image_view(
                image_id=image_id,
                user_id=user_id,
                ip_address=ip_address
            )

            if success:
                logger.info("record_image_view", "View recorded",
                           image_id=image_id)
            else:
                logger.warning("record_image_view", "Failed to record view",
                              image_id=image_id)

        return success

    def _image_to_dict(
        self,
        image: GalleryImage,
        like_count: int = 0,
        view_count: int = 0,
        user_liked: bool = False
    ) -> Dict[str, Any]:
        """
        GalleryImage ORM → Dict 변환

        Args:
            image: GalleryImage ORM 객체
            like_count: 좋아요 개수
            view_count: 조회수
            user_liked: 사용자 좋아요 여부

        Returns:
            이미지 dict
        """
        return {
            "image_id": str(image.image_id),
            "user_id": str(image.user_id),
            "scenario_id": image.scenario_id,
            "session_id": str(image.session_id) if image.session_id else None,
            "stage_tag": image.stage_tag,
            "image_url": image.image_url,
            "image_type": image.image_type,
            "generation_prompt": image.generation_prompt,
            "generation_model": image.generation_model,
            "extra_metadata": image.extra_metadata,
            "is_unlocked": image.is_unlocked,
            "is_favorite": image.is_favorite,
            "created_at": image.created_at.isoformat() if image.created_at else None,
            "unlocked_at": image.unlocked_at.isoformat() if image.unlocked_at else None,
            "like_count": like_count,
            "view_count": view_count,
            "user_liked": user_liked
        }
