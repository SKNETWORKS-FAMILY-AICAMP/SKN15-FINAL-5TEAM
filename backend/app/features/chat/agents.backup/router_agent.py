"""
Router Agent
시나리오 라우팅 에이전트
"""
from typing import Dict, Any
from .graph_state import GraphState
from app.core.logging import get_service_logger

logger = get_service_logger("RouterAgent")


class RouterAgent:
    """Router Agent - 스테이지 분기 처리"""

    def route(self, state: GraphState) -> GraphState:
        """스테이지 라우팅"""
        logger.info("route", "Routing stage")
        
        stage_config = state.get("stage_config", {})
        current_stage = state.get("current_stage", "intro")
        
        # 라우팅 로직
        routing_rules = stage_config.get("routing_logic", {})
        default_next = stage_config.get("default_next_stage")
        
        # TODO: 실제 조건 기반 라우팅
        # 현재는 기본 라우팅
        if default_next:
            state["next_stage"] = default_next
            state["routing_reason"] = "default_route"
        else:
            state["next_stage"] = current_stage
            state["routing_reason"] = "stay_same"
        
        logger.info("route", f"Routed to: {state['next_stage']}", reason=state["routing_reason"])
        return state
