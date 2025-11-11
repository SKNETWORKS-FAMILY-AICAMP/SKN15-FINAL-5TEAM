"""
Router Handler - 라우터 스테이지 처리 (조건 분기)
"""
from typing import Dict, Any
from app.features.chat.agents.agent_response import AgentResponse
from app.core.tools import scene_tools


class RouterStageHandler:
    """
    Router 스테이지 핸들러

    역할:
    - 조건 기반 분기 (next_by_outcome)
    - 게임 상태에 따라 다음 스테이지 결정
    """

    def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> AgentResponse:
        """
        Router 스테이지 처리

        Args:
            state: GraphState
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            AgentResponse
        """
        # next_by_outcome 매핑
        next_by_outcome = stage.get("next_by_outcome", {})

        # 현재 outcome 결정 (간단한 버전)
        outcome = state.get("_outcome", "default")

        # 다음 스테이지 결정
        next_stage = next_by_outcome.get(outcome) or stage.get("next_stage")

        # Router는 즉시 완료 (대화 없음)
        children_ctx = {
            "beats": [],
            "speaker_pool": [],
            "stage_tag": state.get("stage_tag"),
            "stage_type": "router",
        }

        return AgentResponse(
            children_ctx=children_ctx,
            stage_complete=True,
            next_stage=next_stage
        )
