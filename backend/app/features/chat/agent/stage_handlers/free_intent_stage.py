"""
Free Intent Stage Handler - 자유 의도 스테이지 처리

Features:
- 사용자 자유 입력 기반 처리
- LLM 동적 beats 생성
"""
from typing import Dict, Any

from app.core.logging import get_parent_logger
from app.features.chat.services import ContextService

from . import StageResult

logger = get_parent_logger("FreeIntentStageHandler")


class FreeIntentStageHandler:
    """
    자유 의도 스테이지 핸들러

    사용자가 자유롭게 행동을 선택할 수 있는 스테이지를 처리합니다.
    LLM을 사용하여 동적으로 beats를 생성합니다.
    """

    def __init__(self, context_service: ContextService = None):
        """
        Args:
            context_service: ContextService 인스턴스
        """
        self.context_service = context_service or ContextService()

        logger.info("__init__", "FreeIntentStageHandler initialized")

    async def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> StageResult:
        """
        자유 의도 스테이지 처리

        Args:
            state: 게임 상태
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            StageResult
        """
        stage_tag = stage.get("tag", "free_intent")
        speaker_pool = stage.get("speaker_pool", [])

        logger.debug("handle", "Handling free intent stage",
                    stage_tag=stage_tag)

        # 기본 context 구성
        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "free_intent",
            "speaker_pool": speaker_pool,
            "scenario_id": scenario.get("scenario_id", "unknown"),
        }

        # Context 빌딩
        children_ctx = self.context_service.build_children_context(
            base_ctx=base_ctx,
            state=state,
            scenario=scenario,
            stage=stage
        )

        # LLM 기반 동적 beats 생성
        beats = await self.context_service.generate_beats(state, children_ctx)
        children_ctx["beats"] = beats

        logger.info("handle", "Free intent stage processed",
                   beats_count=len(beats))

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=False  # 자유 의도는 명시적 완료 필요
        )


__all__ = ["FreeIntentStageHandler"]
