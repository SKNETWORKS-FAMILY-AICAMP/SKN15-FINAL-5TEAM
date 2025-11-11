"""
Scene Handler - 기본 장면 스테이지 처리
"""
from typing import Dict, Any
from ..agent_response import AgentResponse
from app.core.tools import scene_tools


class SceneHandler:
    """
    Scene 스테이지 핸들러

    역할:
    - beats 기반 대화 생성
    - 스테이지 완료 조건 체크
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
        Scene 스테이지 처리

        Args:
            state: GraphState
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            AgentResponse
        """
        # Beats 준비
        beats = stage.get("beats")
        if not beats and stage.get("beats_i18n"):
            beats = scene_tools.resolve_i18n_beats(stage, scenario, self.locale)

        if not beats:
            beats = []

        # Speaker pool
        speaker_pool = stage.get("characters") or scene_tools.get_character_pool(scenario)

        # Children Agent 컨텍스트 구성
        children_ctx = {
            "beats": beats,
            "speaker_pool": speaker_pool,
            "stage_tag": state.get("stage_tag"),
            "stage_type": "scene",
        }

        # Fallback 대화 (beats가 없을 때)
        fallback = stage.get("fallback")
        if fallback:
            children_ctx["fallback"] = fallback

        # 스테이지 완료 조건
        stage_turn = state.get("stage_turn", 0)
        max_turns = stage.get("max_turns", 10)

        # Beats 모두 소비 또는 최대 턴 도달 시 완료
        beats_count = len(beats)
        stage_complete = (stage_turn >= beats_count) or (stage_turn >= max_turns)

        # 다음 스테이지
        next_stage = stage.get("next_stage") if stage_complete else None

        return AgentResponse(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage
        )
