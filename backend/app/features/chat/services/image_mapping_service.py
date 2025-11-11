"""
ImageMappingService - 이미지 매핑 우선순위 처리
"""
from typing import Optional
from app.features.scenarios.repository import ScenarioRepository


class ImageMappingService:
    """
    이미지 매핑 우선순위 처리

    우선순위:
    1. 스테이지 직접 할당 (ScenarioStageImage)
    2. 매핑 규칙 (ImageMappingRule)
    3. 시나리오 기본 이미지 (ScenarioDefaultImage)
    """

    def __init__(self, scenario_repo: ScenarioRepository):
        self.scenario_repo = scenario_repo

    async def resolve_image(
        self,
        scenario_id: str,
        stage_id: str,
        image_type: str = "background"
    ) -> Optional[str]:
        """
        이미지 URL 결정 (우선순위 기반)

        Args:
            scenario_id: 시나리오 ID
            stage_id: 스테이지 ID
            image_type: 이미지 타입 (background, character_sprite, thumbnail)

        Returns:
            이미지 URL 또는 None
        """
        # 1. 스테이지 직접 할당
        stage_image = await self.scenario_repo.get_stage_image(
            scenario_id, stage_id, image_type
        )
        if stage_image:
            return stage_image.image_url

        # 2. 매핑 규칙
        stage = await self.scenario_repo.get_stage(stage_id)
        if stage:
            mapping = await self.scenario_repo.get_image_mapping(
                scenario_id, stage.stage_type, image_type
            )
            if mapping:
                return mapping.image_url

        # 3. 시나리오 기본 이미지
        default = await self.scenario_repo.get_default_image(
            scenario_id, image_type
        )
        if default:
            return default.image_url

        return None

    async def resolve_all_images(
        self,
        scenario_id: str,
        stage_id: str
    ) -> dict:
        """
        모든 이미지 타입 한 번에 결정

        Args:
            scenario_id: 시나리오 ID
            stage_id: 스테이지 ID

        Returns:
            {
                "background": str | None,
                "character_sprite": str | None,
                "thumbnail": str | None
            }
        """
        return {
            "background": await self.resolve_image(scenario_id, stage_id, "background"),
            "character_sprite": await self.resolve_image(scenario_id, stage_id, "character_sprite"),
            "thumbnail": await self.resolve_image(scenario_id, stage_id, "thumbnail"),
        }
