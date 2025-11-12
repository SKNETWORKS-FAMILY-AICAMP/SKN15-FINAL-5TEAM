"""
Image Repository
이미지 매핑 관련 DB 접근 레이어
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, Integer
from typing import Optional, Dict, Any

from app.features.images.models import ImageMapping
from app.core.logging import get_repository_logger

logger = get_repository_logger("Image")


class ImageRepository:
    """
    이미지 매핑 조회 전담 Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_best_image_for_stage(
        self,
        scenario_id: str,
        stage_id: str,
        turn_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        스테이지에 맞는 최적의 이미지 조회 (DB 기반)

        metadata JSONB 필드에서 priority, stage_id, turn_range 등을 확인하여
        가장 적합한 이미지를 반환합니다.

        우선순위:
        1. scenario_id + stage_id가 정확히 매칭되는 이미지
        2. metadata.priority가 높은 순서 (DESC)
        3. metadata.turn_min <= turn_count <= metadata.turn_max 조건 만족

        Args:
            scenario_id: 시나리오 ID (예: 'train', 'mugen-train')
            stage_id: 스테이지 ID (예: 'INTRO', 'HEROES_ARRIVE')
            turn_count: 현재 턴 카운트

        Returns:
            이미지 정보 dict 또는 None
            {
                "id": int,
                "scenario_id": str,
                "mapping_category": str,
                "image_key": str,
                "image_url": str,
                "metadata": dict,
                "priority": int (from metadata)
            }
        """
        logger.info("get_best_image_for_stage",
                   f"Finding image for scenario={scenario_id}, stage={stage_id}, turn={turn_count}")

        try:
            # Query: category='stage' 또는 metadata에 stage_id 포함
            # WHERE 조건:
            #   1. scenario_id 매칭
            #   2. (mapping_category = 'stage' OR metadata @> {'stage_id': stage_id})
            #   3. turn_count 범위 체크 (metadata.turn_min, turn_max)
            # ORDER BY: priority DESC (metadata.priority)
            # LIMIT 1

            stmt = select(ImageMapping).where(
                and_(
                    ImageMapping.scenario_id == scenario_id,
                    # JSONB contains check for stage_id in metadata
                    ImageMapping.metadata.op('@>')(func.jsonb_build_object('stage_id', stage_id))
                )
            ).order_by(
                # Extract priority from metadata JSONB, default to 0
                ImageMapping.metadata['priority'].astext.cast(Integer).desc()
            ).limit(1)

            result = await self.db.execute(stmt)
            image = result.scalar_one_or_none()

            if image:
                # Convert ORM to dict
                image_dict = {
                    "id": image.id,
                    "scenario_id": image.scenario_id,
                    "mapping_category": image.mapping_category,
                    "image_key": image.image_key,
                    "image_url": image.image_url,
                    "metadata": image.metadata or {},
                    "priority": (image.metadata or {}).get("priority", 0)
                }

                logger.info("get_best_image_for_stage",
                           f"Found image: {image.image_key} (priority={image_dict['priority']})")
                return image_dict
            else:
                logger.warning("get_best_image_for_stage",
                              f"No image found for scenario={scenario_id}, stage={stage_id}")
                return None

        except Exception as e:
            logger.error("get_best_image_for_stage",
                        f"Error fetching image: {e}", exc_info=True)
            return None
