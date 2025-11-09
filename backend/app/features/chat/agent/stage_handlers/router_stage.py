"""
Router Stage Handler - 라우팅 스테이지 처리

Features:
- 사용자 의도에 따른 분기
- Intent 매핑 기반 라우팅
"""
from typing import Dict, Any, Optional

from app.core.logging import get_parent_logger

from . import StageResult

logger = get_parent_logger("RouterStageHandler")


class RouterStageHandler:
    """
    라우터 스테이지 핸들러

    사용자 입력을 분석하여 다음 스테이지로 라우팅합니다.
    """

    def __init__(self):
        logger.info("__init__", "RouterStageHandler initialized")

    def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> StageResult:
        """
        라우터 스테이지 처리

        Args:
            state: 게임 상태
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            StageResult
        """
        stage_tag = stage.get("tag", "router")
        user_input = state.get("user_input", "").lower()
        intent_mapping = stage.get("intent_mapping", {})

        logger.debug("handle", "Handling router stage",
                    stage_tag=stage_tag,
                    user_input_len=len(user_input))

        # Intent 매핑 기반 라우팅
        next_stage = self._route_by_intent(user_input, intent_mapping)

        if not next_stage:
            # 기본 라우팅
            next_stage = stage.get("default_next") or stage.get("next")

        logger.info("handle", "Routing complete",
                   next_stage=next_stage)

        # Children context 구성
        children_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "router",
            "beats": stage.get("beats", []),
            "speaker_pool": stage.get("speaker_pool", []),
            "scenario_id": scenario.get("scenario_id", "unknown"),
        }

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=True,
            next_stage=next_stage
        )

    def _route_by_intent(
        self,
        user_input: str,
        intent_mapping: Dict[str, Any]
    ) -> Optional[str]:
        """Intent 매핑 기반 라우팅"""
        for intent, config in intent_mapping.items():
            keywords = config.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in user_input:
                    next_stage = config.get("next_stage")
                    logger.info("_route_by_intent", f"Intent matched: {intent}",
                               keyword=keyword,
                               next_stage=next_stage)
                    return next_stage

        return None


__all__ = ["RouterStageHandler"]
