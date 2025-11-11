"""
Parent Agent - 세션 검증 및 컨텍스트 준비
"""
from typing import Dict, Any
from ..graph_state import GraphState
from app.core.logging import get_parent_logger as get_service_logger
from app.features.chat.services import ScenarioService, StateService

logger = get_service_logger("ParentAgent")


class ParentAgent:
    """Parent Agent - 전체 워크플로우 조율"""

    def __init__(self, scenario_service: ScenarioService = None, state_service: StateService = None):
        self.scenario_service = scenario_service or ScenarioService()
        self.state_service = state_service or StateService()

    def execute(self, state: GraphState) -> GraphState:
        """Parent Agent 실행"""
        logger.info("execute", "Parent agent started")

        # 세션 검증
        required = ["session_id", "user_id", "scenario_id", "user_input"]
        for field in required:
            if not state.get(field):
                state["error"] = f"Missing: {field}"
                return state

        scenario_id = state["scenario_id"]

        # 시나리오 로드
        scenario = self.scenario_service.load_scenario(scenario_id)
        if not scenario:
            logger.error("execute", "Scenario not found", scenario_id=scenario_id)
            state["error"] = f"Scenario not found: {scenario_id}"
            return state

        state["scenario"] = scenario
        logger.info("execute", "Scenario loaded", scenario_id=scenario_id)

        # 기본값 설정
        if "turn_count" not in state:
            state["turn_count"] = 0

        # 현재 스테이지 결정
        if "current_stage" not in state:
            # 시나리오에서 첫 번째 스테이지 가져오기
            stages = scenario.get("stages", [])
            if stages:
                first_stage = stages[0]
                state["current_stage"] = first_stage.get("tag", "TRAIN_PRELUDE")
                state["stage_type"] = first_stage.get("type", "scene")
                logger.info("execute", f"Set initial stage: {state['current_stage']} (type: {state['stage_type']})")
            else:
                state["current_stage"] = "TRAIN_PRELUDE"
                state["stage_type"] = "scene"
                logger.warning("execute", "No stages found, using default")

        return state
