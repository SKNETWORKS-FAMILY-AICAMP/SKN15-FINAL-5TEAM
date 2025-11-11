"""
Parent Agent - 세션 검증 및 컨텍스트 준비
"""
from typing import Dict, Any
from ..graph_state import GraphState
from app.core.logging import get_parent_logger as get_service_logger

logger = get_service_logger("ParentAgent")


class ParentAgent:
    """Parent Agent - 전체 워크플로우 조율"""

    def execute(self, state: GraphState) -> GraphState:
        """Parent Agent 실행"""
        logger.info("execute", "Parent agent started")

        # 세션 검증
        required = ["session_id", "user_id", "scenario_id", "user_input"]
        for field in required:
            if not state.get(field):
                state["error"] = f"Missing: {field}"
                return state

        # 기본값 설정
        if "turn_count" not in state:
            state["turn_count"] = 0
        if "current_stage" not in state:
            state["current_stage"] = "intro"
        if "stage_type" not in state:
            state["stage_type"] = "open_narrative"

        return state
