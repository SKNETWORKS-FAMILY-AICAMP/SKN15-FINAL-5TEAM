"""
Images Feature - UseCase
이미지 매핑 비즈니스 로직
Layer 3: UseCase (4-Layer Architecture)
"""
from typing import List, Optional, Dict, Any

from app.features.images.repository import ImagesRepository
from app.features.images.schemas import (
    ImageMappingCreate,
    ImageMappingUpdate,
    ImageMappingResponse,
    ImageQueryResponse
)
from app.core.logging import get_usecase_logger
from app.core.errors import NotFoundException

logger = get_usecase_logger("Images")


class ImagesUseCase:
    """
    [Layer 3] UseCase
    책임: 이미지 매핑 비즈니스 로직, 트랜잭션 관리
    금지: HTTP 요청/응답 직접 처리
    """

    def __init__(self, repository: ImagesRepository):
        """
        UseCase 초기화

        Args:
            repository: ImagesRepository 인스턴스
        """
        self.repository = repository

    async def create_image_mapping(
        self,
        data: ImageMappingCreate
    ) -> ImageMappingResponse:
        """
        이미지 매핑 생성

        Args:
            data: 생성 데이터

        Returns:
            ImageMappingResponse
        """
        logger.info("create_image_mapping", f"Creating image: {data.image_key}",
                   category=data.mapping_category, scenario_id=data.scenario_id)

        image = await self.repository.create_image_mapping(
            scenario_id=data.scenario_id,
            mapping_category=data.mapping_category,
            image_key=data.image_key,
            image_url=data.image_url,
            extra_data=data.extra_data
        )

        return ImageMappingResponse.model_validate(image)

    async def get_image_by_key(
        self,
        image_key: str,
        scenario_id: Optional[str] = None
    ) -> Optional[ImageMappingResponse]:
        """
        이미지 키로 조회

        Args:
            image_key: 이미지 키
            scenario_id: 시나리오 ID (우선순위)

        Returns:
            ImageMappingResponse 또는 None
        """
        image = await self.repository.get_image_by_key(
            image_key=image_key,
            scenario_id=scenario_id
        )

        if not image:
            logger.warning("get_image_by_key", f"Image not found: {image_key}",
                         scenario_id=scenario_id)
            return None

        return ImageMappingResponse.model_validate(image)

    async def query_images(
        self,
        scenario_id: Optional[str] = None,
        mapping_category: Optional[str] = None,
        image_key: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> ImageQueryResponse:
        """
        조건에 맞는 이미지 조회

        Args:
            scenario_id: 시나리오 ID 필터
            mapping_category: 카테고리 필터
            image_key: 이미지 키 필터
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            ImageQueryResponse
        """
        images, total_count = await self.repository.query_images(
            scenario_id=scenario_id,
            mapping_category=mapping_category,
            image_key=image_key,
            limit=limit,
            offset=offset
        )

        return ImageQueryResponse(
            images=[ImageMappingResponse.model_validate(img) for img in images],
            total_count=total_count
        )

    async def update_image_mapping(
        self,
        mapping_id: int,
        data: ImageMappingUpdate
    ) -> ImageMappingResponse:
        """
        이미지 매핑 수정

        Args:
            mapping_id: 매핑 ID
            data: 수정 데이터

        Returns:
            ImageMappingResponse

        Raises:
            NotFoundException: 매핑을 찾을 수 없음
        """
        image = await self.repository.update_image_mapping(
            mapping_id=mapping_id,
            image_url=data.image_url,
            extra_data=data.extra_data
        )

        if not image:
            raise NotFoundException(f"Image mapping not found: {mapping_id}")

        logger.info("update_image_mapping", f"Updated image: {mapping_id}")

        return ImageMappingResponse.model_validate(image)

    async def delete_image_mapping(self, mapping_id: int) -> None:
        """
        이미지 매핑 삭제

        Args:
            mapping_id: 매핑 ID

        Raises:
            NotFoundException: 매핑을 찾을 수 없음
        """
        success = await self.repository.delete_image_mapping(mapping_id)

        if not success:
            raise NotFoundException(f"Image mapping not found: {mapping_id}")

        logger.info("delete_image_mapping", f"Deleted image: {mapping_id}")

    async def get_character_image(
        self,
        character_name: str,
        emotion: str = "normal",
        scenario_id: Optional[str] = None
    ) -> Optional[str]:
        """
        캐릭터 이미지 URL 조회

        Args:
            character_name: 캐릭터 이름
            emotion: 감정 상태
            scenario_id: 시나리오 ID

        Returns:
            이미지 URL 또는 None

        Note:
            image_key 형식: "{character_name}_{emotion}"
            예: "rengoku_normal", "tanjiro_happy"
        """
        image_key = f"{character_name}_{emotion}"
        image = await self.repository.get_image_by_key(
            image_key=image_key,
            scenario_id=scenario_id
        )

        if image:
            return image.image_url

        # Fallback to "normal" emotion
        if emotion != "normal":
            logger.warning("get_character_image", f"Emotion not found, fallback to normal",
                         character=character_name, emotion=emotion)
            image_key = f"{character_name}_normal"
            image = await self.repository.get_image_by_key(
                image_key=image_key,
                scenario_id=scenario_id
            )
            if image:
                return image.image_url

        logger.warning("get_character_image", f"Character image not found",
                     character=character_name, emotion=emotion)
        return None

    async def get_background_image(
        self,
        stage_tag: str,
        scenario_id: Optional[str] = None
    ) -> Optional[str]:
        """
        배경 이미지 URL 조회

        Args:
            stage_tag: 스테이지 태그
            scenario_id: 시나리오 ID

        Returns:
            이미지 URL 또는 None

        Note:
            image_key 형식: "bg_{stage_tag}"
            예: "bg_train_interior", "bg_forest"
        """
        image_key = f"bg_{stage_tag}"
        image = await self.repository.get_image_by_key(
            image_key=image_key,
            scenario_id=scenario_id
        )

        if image:
            return image.image_url

        logger.warning("get_background_image", f"Background image not found",
                     stage_tag=stage_tag, scenario_id=scenario_id)
        return None
