"""
Open Narrative Stage Handler - 오픈 내러티브 스테이지 처리

Features:
- 자유로운 스토리 진행
- LLM 기반 동적 내러티브 생성
"""
from typing import Dict, Any

from app.core.logging import get_parent_logger
from app.features.chat.services import ContextService

from . import StageResult

logger = get_parent_logger("OpenNarrativeStageHandler")


class OpenNarrativeStageHandler:
    """
    오픈 내러티브 스테이지 핸들러

    고정된 beats 없이 LLM이 자유롭게 스토리를 생성하는 스테이지를 처리합니다.
    """

    def __init__(self, context_service: ContextService = None):
        """
        Args:
            context_service: ContextService 인스턴스
        """
        self.context_service = context_service or ContextService()

        logger.info("__init__", "OpenNarrativeStageHandler initialized")

    async def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> StageResult:
        """
        오픈 내러티브 스테이지 처리

        Args:
            state: 게임 상태
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            StageResult
        """
        stage_tag = stage.get("tag", "open_narrative")
        speaker_pool = stage.get("speaker_pool", [])
        context_desc = stage.get("context", "오픈 내러티브 진행 중")

        logger.debug("handle", "Handling open narrative stage",
                    stage_tag=stage_tag)

        # 기본 context 구성
        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "open_narrative",
            "speaker_pool": speaker_pool,
            "scenario_id": scenario.get("scenario_id", "unknown"),
            "stage_objective": context_desc,
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

        logger.info("handle", "Open narrative stage processed",
                   beats_count=len(beats))

        # 종료 조건 체크 (특정 키워드 등)
        stage_complete = self._check_completion(state, stage)
        next_stage = stage.get("next") if stage_complete else None

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage
        )

    def _check_completion(self, state: Dict[str, Any], stage: Dict[str, Any]) -> bool:
        """종료 조건 체크"""
        completion_keywords = stage.get("completion_keywords", [])
        user_input = state.get("user_input", "").lower()

        for keyword in completion_keywords:
            if keyword.lower() in user_input:
                logger.info("_check_completion", f"Completion keyword matched: {keyword}")
                return True

        return False


__all__ = ["OpenNarrativeStageHandler"]
