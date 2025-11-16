"""
Router Agent
시나리오 라우팅 에이전트
"""
from typing import Dict, Any
from ..graph_state import GraphState
from ..guards.fallback import get_fallback_manager, reset_fallback_count
from app.core.logging import get_parent_logger as get_service_logger
from app.core.llm.prompt_service import get_prompt_service
from app.core.llm import LLMClient

logger = get_service_logger("RouterAgent")


class RouterAgent:
    """Router Agent - 스테이지 분기 및 주제 분류"""

    def __init__(self):
        """Router Agent 초기화"""
        self.llm = LLMClient()
        self.prompt_service = get_prompt_service()
        self.fallback_manager = get_fallback_manager()

    async def route(self, state: GraphState) -> GraphState:
        """
        스테이지 라우팅 및 주제 분류

        1. 사용자 입력이 on_topic인지 off_topic인지 LLM으로 판별
        2. off_topic이면 Fallback 처리
        3. on_topic이면 off-topic 카운트 리셋 및 일반 라우팅
        """
        logger.info("route", "Routing stage and classifying topic")

        # 1. 주제 분류 (on_topic vs off_topic)
        is_off_topic = await self._check_on_topic(state)
        state["is_off_topic"] = is_off_topic

        if is_off_topic:
            # 2-A. off_topic: Fallback 처리
            logger.info("route", "Off-topic detected, triggering fallback")
            await self._handle_off_topic(state)
        else:
            # 2-B. on_topic: off-topic 카운트 리셋 및 일반 라우팅
            logger.info("route", "On-topic detected, resetting fallback count")
            await reset_fallback_count(state)
            self._handle_stage_routing(state)

        return state

    async def _check_on_topic(self, state: GraphState) -> bool:
        """
        LLM을 사용하여 사용자 입력이 on_topic인지 off_topic인지 분류

        Returns:
            True: off_topic (세계관/시나리오와 무관)
            False: on_topic (세계관/시나리오와 관련)
        """
        user_input = state.get("user_input", "")
        if not user_input or user_input.strip() == "":
            logger.debug("_check_on_topic", "No user input, treating as on_topic")
            return False

        try:
            # ✅ 최근 대화 포맷팅 (MessageHistoryService 직접 사용)
            from app.features.chat.services.message_history_service import get_message_history_service
            message_history_service = get_message_history_service()
            recent_dialogues = message_history_service.select_recent_messages(
                message_history=state.get("message_history", []),
                keep_count=8
            )
            logger.info("_check_on_topic", f"📊 recent_dialogues count: {len(recent_dialogues)}")

            # 🔍 디버깅: recent_dialogues 내용 전체 출력
            if recent_dialogues:
                logger.info("_check_on_topic", f"📝 recent_dialogues content: {recent_dialogues}")
            else:
                logger.warning("_check_on_topic", f"⚠️ No recent_dialogues! state keys: {list(state.keys())}")
                # message_history 직접 확인
                msg_history = state.get("message_history", [])
                logger.warning("_check_on_topic", f"⚠️ message_history from state: {msg_history}")

            recent_history = self.prompt_service._format_recent_dialogues(recent_dialogues)
            logger.info("_check_on_topic", f"📄 Formatted recent_history:\n{recent_history}")

            # ✅ 시나리오 정보 추출
            scenario = state.get("scenario") or state.get("scenario_data") or {}
            scenario_id = scenario.get("scenario_id", state.get("scenario_id", "unknown"))
            current_stage = state.get("current_stage", "unknown")

            # ✅ 프롬프트 생성 (PromptService 재사용)
            system_prompt, user_prompt = self.prompt_service.get_router_topic_classifier_prompt(
                user_text=user_input,
                recent_history=recent_history,
                scenario_id=scenario_id,
                current_stage=current_stage
            )

            if not system_prompt or not user_prompt:
                logger.warning("_check_on_topic", "Router prompts not available, defaulting to on_topic")
                return False

            # ✅ LLM 호출 (JSON 모드 - 이미 파싱된 Dict 반환)
            logger.debug("_check_on_topic", f"Calling LLM for topic classification: '{user_input[:50]}...'")
            response_data = await self.llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=200
            )

            # ✅ 결과 추출
            classification = response_data.get("classification", "on_topic")
            confidence = response_data.get("confidence", 0.5)
            explanation = response_data.get("explanation", "")

            is_off_topic = (classification == "off_topic")

            logger.info(
                "_check_on_topic",
                f"Topic classification: {classification} (confidence={confidence:.2f})",
                user_input=user_input[:50],
                explanation=explanation
            )

            return is_off_topic

        except Exception as e:
            logger.error("_check_on_topic", f"Topic classification failed: {e}", exc_info=True)
            # LLM 실패 시 on_topic으로 간주 (안전한 기본값)
            return False

    async def _handle_off_topic(self, state: GraphState) -> None:
        """
        off_topic 처리: Fallback Manager 호출

        Fallback Manager가 atmosphere 기반으로 처리:
        - limit 이하: LLM 대사 생성
        - limit + 1: 경고
        - limit + 2 이상: 10분 차단
        """
        user_input = state.get("user_input", "")

        # ✅ Fallback Manager 호출 (재사용)
        fallback_result = await self.fallback_manager.handle_off_topic(state, user_input)

        action = fallback_result.get("action", "allow")
        new_count = fallback_result.get("new_count", 0)
        remaining_count = fallback_result.get("remaining_count", 0)

        logger.info(
            "_handle_off_topic",
            f"Fallback action: {action}, count: {new_count}, remaining: {remaining_count}"
        )

        # Fallback Manager가 이미 state에 dialogues를 삽입했으므로
        # 여기서는 추가 작업 불필요

    def _handle_stage_routing(self, state: GraphState) -> None:
        """
        일반 스테이지 라우팅 로직 (on_topic일 때 실행)
        """
        stage_config = state.get("stage_config") or {}
        current_stage = state.get("current_stage", "intro")

        # 라우팅 로직
        routing_rules = stage_config.get("routing_logic", {}) if stage_config else {}
        default_next = stage_config.get("default_next_stage")

        # TODO: 실제 조건 기반 라우팅 구현
        # 현재는 기본 라우팅
        if default_next:
            state["next_stage"] = default_next
            state["routing_reason"] = "default_route"
        else:
            state["next_stage"] = current_stage
            state["routing_reason"] = "stay_same"

        logger.info("_handle_stage_routing", f"Routed to: {state['next_stage']}", reason=state["routing_reason"])
