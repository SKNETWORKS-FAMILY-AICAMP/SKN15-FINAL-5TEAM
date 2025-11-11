"""
Free Intent Handler - 자유 의도 파싱 스테이지
"""
from typing import Dict, Any
from app.features.chat.agents.agent_response import AgentResponse
from app.core.tools import scene_tools


class FreeIntentHandler:
    """
    Free Intent 스테이지 핸들러

    역할:
    - 사용자 intent에 따라 분기 (intent_mapping)
    """

    def __init__(self, locale: str = "ko"):
        self.locale = locale

    def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> AgentResponse:
        """
        Free Intent 스테이지 처리

        Args:
            state: GraphState
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            AgentResponse
        """
        # Intent mapping
        intent_mapping = stage.get("intent_mapping", {})

        # 사용자 intent (Router에서 파악된 것)
        temp = state.get("temp_data", {})
        intent = temp.get("intent") or temp.get("sticky_intent") or state.get("user_intent")

        # 다음 스테이지 결정
        next_stage = None
        if intent and intent in intent_mapping:
            next_stage = intent_mapping[intent]
        else:
            next_stage = stage.get("next_stage")

        # Beats (안내 메시지)
        beats = stage.get("beats")
        if not beats and stage.get("beats_i18n"):
            beats = scene_tools.resolve_i18n_beats(stage, scenario, self.locale)

        speaker_pool = stage.get("characters") or scene_tools.get_character_pool(scenario)

        children_ctx = {
            "beats": beats or [],
            "speaker_pool": speaker_pool,
            "stage_tag": state.get("stage_tag"),
            "stage_type": "free_intent",
        }

        # 1턴 후 완료
        stage_turn = state.get("stage_turn", 0)
        stage_complete = stage_turn >= 1

        return AgentResponse(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage
        )
