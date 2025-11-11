"""
Mission Handler - 미션 스테이지 처리
"""
from typing import Dict, Any
from ..agent_response import AgentResponse
from app.core.tools import scene_tools


class MissionHandler:
    """
    Mission 스테이지 핸들러

    역할:
    - 목표 기반 미션 처리
    - 성공/실패 조건 체크
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
        Mission 스테이지 처리

        Args:
            state: GraphState
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            AgentResponse
        """
        # 미션 목표
        mission_target = state.get("mission_target")

        # Beats (미션 설명 또는 힌트)
        beats = stage.get("beats")
        if not beats and stage.get("beats_i18n"):
            beats = scene_tools.resolve_i18n_beats(stage, scenario, self.locale)

        # Speaker pool
        speaker_pool = stage.get("characters") or scene_tools.get_character_pool(scenario)

        # Children Agent 컨텍스트
        children_ctx = {
            "beats": beats or [],
            "speaker_pool": speaker_pool,
            "stage_tag": state.get("stage_tag"),
            "stage_type": "mission",
            "mission": {
                "target": mission_target,
                "active": True
            }
        }

        # 미션 완료 조건 (간단한 버전)
        mission_state = state.get("mission", {})
        stage_complete = mission_state.get("completed", False)

        # 다음 스테이지
        next_stage = stage.get("next_stage") if stage_complete else None

        return AgentResponse(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage
        )
