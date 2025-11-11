"""
Images Feature - Repository
이미지 매핑 데이터 접근
Layer 4: Repository (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional, Dict, Any

from .models import ImageMapping
from app.core.logging import get_repository_logger

logger = get_repository_logger("Images")


class ImagesRepository:
    """
    [Layer 4] Repository
    책임: 이미지 매핑 CRUD
    금지: 비즈니스 로직, HTTP 처리
    """

    def __init__(self, db: AsyncSession):
        """
        Repository 초기화

        Args:
            db: 데이터베이스 세션
        """
        self.db = db

    async def create_image_mapping(
        self,
        scenario_id: Optional[str],
        mapping_category: str,
        image_key: str,
        image_url: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> ImageMapping:
        """
        이미지 매핑 생성

        Args:
            scenario_id: 시나리오 ID (전역 이미지는 None)
            mapping_category: 카테고리 (character, bg, cutscene, stage)
            image_key: 이미지 키
            image_url: 이미지 URL
            extra_data: 추가 메타데이터

        Returns:
            ImageMapping
        """
        image_mapping = ImageMapping(
            scenario_id=scenario_id,
            mapping_category=mapping_category,
            image_key=image_key,
            image_url=image_url,
            extra_data=extra_data or {}
        )
        self.db.add(image_mapping)
        await self.db.flush()

        logger.info("create_image_mapping", f"Created image mapping: {image_key}",
                   mapping_id=image_mapping.id, category=mapping_category)

        return image_mapping

    async def get_image_mapping_by_id(self, mapping_id: int) -> Optional[ImageMapping]:
        """
        ID로 이미지 매핑 조회

        Args:
            mapping_id: 매핑 ID

        Returns:
            ImageMapping 또는 None
        """
        result = await self.db.execute(
            select(ImageMapping).where(ImageMapping.id == mapping_id)
        )
        return result.scalar_one_or_none()

    async def get_image_by_key(
        self,
        image_key: str,
        scenario_id: Optional[str] = None
    ) -> Optional[ImageMapping]:
        """
        이미지 키로 매핑 조회 (시나리오 우선순위)

        Args:
            image_key: 이미지 키
            scenario_id: 시나리오 ID (우선순위)

        Returns:
            ImageMapping 또는 None

        Note:
            1. scenario_id가 있으면 해당 시나리오용 이미지를 먼저 찾음
            2. 없으면 전역 이미지(scenario_id=NULL)를 찾음
        """
        query = select(ImageMapping).where(ImageMapping.image_key == image_key)

        if scenario_id:
            # 시나리오별 이미지 우선
            query = query.where(
                or_(
                    ImageMapping.scenario_id == scenario_id,
                    ImageMapping.scenario_id.is_(None)
                )
            ).order_by(
                ImageMapping.scenario_id.desc().nulls_last()
            )
        else:
            # 전역 이미지만
            query = query.where(ImageMapping.scenario_id.is_(None))

        result = await self.db.execute(query)
        image = result.scalar_one_or_none()

        logger.debug("get_image_by_key", f"Image lookup: {image_key}",
                    scenario_id=scenario_id, found=image is not None)

        return image

    async def query_images(
        self,
        scenario_id: Optional[str] = None,
        mapping_category: Optional[str] = None,
        image_key: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[ImageMapping], int]:
        """
        조건에 맞는 이미지 매핑 조회

        Args:
            scenario_id: 시나리오 ID 필터
            mapping_category: 카테고리 필터
            image_key: 이미지 키 필터 (LIKE 검색)
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            (이미지 매핑 리스트, 전체 개수)
        """
        # 필터 조건 구성
        conditions = []
        if scenario_id is not None:
            conditions.append(
                or_(
                    ImageMapping.scenario_id == scenario_id,
                    ImageMapping.scenario_id.is_(None)
                )
            )
        if mapping_category:
            conditions.append(ImageMapping.mapping_category == mapping_category)
        if image_key:
            conditions.append(ImageMapping.image_key.like(f"%{image_key}%"))

        # 쿼리 구성
        query = select(ImageMapping)
        if conditions:
            query = query.where(and_(*conditions))

        # 전체 개수 조회
        count_query = select(ImageMapping.id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total_count = len(count_result.all())

        # 페이징 적용
        query = query.order_by(ImageMapping.id.desc()).limit(limit).offset(offset)

        # 결과 조회
        result = await self.db.execute(query)
        images = result.scalars().all()

        logger.info("query_images", f"Found {len(images)}/{total_count} images",
                   scenario_id=scenario_id, category=mapping_category)

        return list(images), total_count

    async def update_image_mapping(
        self,
        mapping_id: int,
        image_url: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Optional[ImageMapping]:
        """
        이미지 매핑 수정

        Args:
            mapping_id: 매핑 ID
            image_url: 새 이미지 URL
            extra_data: 새 메타데이터

        Returns:
            업데이트된 ImageMapping 또는 None
        """
        image = await self.get_image_mapping_by_id(mapping_id)
        if not image:
            return None

        if image_url is not None:
            image.image_url = image_url
        if extra_data is not None:
            image.extra_data = extra_data

        await self.db.flush()

        logger.info("update_image_mapping", f"Updated image mapping: {mapping_id}",
                   new_url=image_url)

        return image

    async def delete_image_mapping(self, mapping_id: int) -> bool:
        """
        이미지 매핑 삭제

        Args:
            mapping_id: 매핑 ID

        Returns:
            성공 여부
        """
        image = await self.get_image_mapping_by_id(mapping_id)
        if not image:
            return False

        await self.db.delete(image)
        await self.db.flush()

        logger.info("delete_image_mapping", f"Deleted image mapping: {mapping_id}")

        return True
