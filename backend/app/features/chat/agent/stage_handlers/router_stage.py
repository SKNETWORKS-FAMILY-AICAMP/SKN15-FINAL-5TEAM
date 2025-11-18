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

        # next_by_outcome이 있으면 조건 기반 라우팅 (hidden ending 체크)
        next_by_outcome = stage.get("next_by_outcome")
        if next_by_outcome:
            outcome = self._check_ending_condition(state, scenario)
            next_stage = next_by_outcome.get(outcome) or stage.get("default_next")
            logger.info("handle", f"Outcome-based routing: {outcome} -> {next_stage}")
        elif not next_stage:
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

    def _check_ending_condition(
        self,
        state: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> str:
        """
        엔딩 조건 확인

        recruit_order와 allies_recruited를 기반으로 hidden ending 조건 체크

        Args:
            state: 게임 상태
            scenario: 시나리오 데이터

        Returns:
            "HIDDEN" 또는 "BASIC"
        """
        # scenario.metadata.ending.hidden_condition 가져오기
        metadata = scenario.get("metadata", {})
        ending_config = metadata.get("ending", {})
        hidden_condition = ending_config.get("hidden_condition", {})
        required_order = hidden_condition.get("required_order", [])

        if not required_order:
            logger.debug("_check_ending_condition", "No required_order - defaulting to BASIC")
            return "BASIC"

        recruit_order = state.get("recruit_order", [])
        allies = state.get("allies_recruited", [])

        # 조건 1: recruit_order가 required_order와 일치
        order_match = recruit_order == required_order

        # 조건 2: required_order의 모든 타겟이 allies에 포함
        all_recruited = all(target in allies for target in required_order)

        logger.info("_check_ending_condition",
                   "Checking ending conditions",
                   recruit_order=recruit_order,
                   required_order=required_order,
                   allies=allies,
                   order_match=order_match,
                   all_recruited=all_recruited)

        if order_match and all_recruited:
            logger.info("_check_ending_condition", "🎉 HIDDEN ending unlocked!")
            return "HIDDEN"
        else:
            logger.info("_check_ending_condition", "BASIC ending")
            return "BASIC"


__all__ = ["RouterStageHandler"]
