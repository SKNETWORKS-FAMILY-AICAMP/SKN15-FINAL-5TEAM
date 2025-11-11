"""
StateTools - GraphState 관리 도구
tm_work의 state_tools를 현재 아키텍처에 맞게 간소화
"""
from typing import Dict, Any, Optional
from app.core.tools import scene_tools


def ensure_scenario_state(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    시나리오 데이터가 state에 없으면 로드

    Args:
        state: GraphState

    Returns:
        시나리오 데이터 또는 None
    """
    # 이미 로드되어 있으면 반환
    scenario = state.get("scenario") or state.get("scenario_data")
    if scenario:
        return scenario

    # scenario_id로 로드
    scenario_id = state.get("scenario_id")
    if not scenario_id:
        print("⚠️ No scenario_id in state")
        return None

    scenario = scene_tools.load_scenario(scenario_id)
    if scenario:
        state["scenario"] = scenario
        state["scenario_data"] = scenario

    return scenario


def get_metadata(scenario: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """시나리오 메타데이터 조회"""
    return scene_tools.get_metadata(scenario) if scenario else {}


def resolve_stage(state: Dict[str, Any], scenario: Dict[str, Any]) -> tuple[str, Optional[Dict[str, Any]]]:
    """
    현재 스테이지 해석

    Args:
        state: GraphState
        scenario: 시나리오 데이터

    Returns:
        (stage_tag, stage_definition)
    """
    stage_tag = state.get("stage_tag") or state.get("current_stage") or "INTRO"
    stage = scene_tools.get_stage(scenario, stage_tag)

    return stage_tag, stage


def get_current_stage(state: Dict[str, Any]) -> Optional[str]:
    """현재 스테이지 태그 조회"""
    return state.get("stage_tag") or state.get("current_stage")


def set_current_stage(state: Dict[str, Any], stage_tag: str):
    """현재 스테이지 설정"""
    state["current_stage"] = stage_tag
    state["stage_tag"] = stage_tag


def reset_stage_turn(state: Dict[str, Any]):
    """스테이지 턴 초기화"""
    state["stage_turn"] = 0


def increment_stage_turn(state: Dict[str, Any]):
    """스테이지 턴 증가"""
    state["stage_turn"] = state.get("stage_turn", 0) + 1


def increment_turn_count(state: Dict[str, Any]):
    """전체 턴 카운트 증가"""
    state["turn_count"] = state.get("turn_count", 0) + 1


def get_temp_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """임시 데이터 조회 (없으면 빈 dict 반환)"""
    if "temp_data" not in state:
        state["temp_data"] = {}
    return state["temp_data"]


def update_stage_progress(state: Dict[str, Any], stage_tag: str, completed: bool):
    """
    스테이지 진행 상황 업데이트

    Args:
        state: GraphState
        stage_tag: 스테이지 태그
        completed: 완료 여부
    """
    if "scene" not in state:
        state["scene"] = {}

    state["scene"]["stage_completed"] = completed

    if completed:
        temp = get_temp_data(state)
        temp["completed_stage"] = stage_tag


def consume_completed_stage(state: Dict[str, Any]) -> Optional[str]:
    """
    완료된 스테이지 소비 (temp_data에서 제거하고 반환)

    Returns:
        완료된 스테이지 태그 또는 None
    """
    temp = get_temp_data(state)
    return temp.pop("completed_stage", None)


def consume_pending_stage(state: Dict[str, Any]) -> Optional[str]:
    """
    대기 중인 다음 스테이지 소비

    Returns:
        다음 스테이지 태그 또는 None
    """
    game = state.get("game", {})
    next_stage = game.pop("pending_stage", None) or state.pop("next_stage", None)
    return next_stage


def mark_stage_entered(state: Dict[str, Any], stage_tag: str):
    """스테이지 진입 마킹"""
    if "scene" not in state:
        state["scene"] = {}
    state["scene"]["entered_stage"] = stage_tag
    state["scene"]["stage_completed"] = False


def handle_missing_scenario(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    시나리오가 없을 때 에러 처리

    Returns:
        에러 상태
    """
    state["output"] = {
        "error": "Scenario not found",
        "dialogues": []
    }
    state["next_node"] = "END"
    return state


def handle_missing_stage(state: Dict[str, Any], stage_tag: str) -> Dict[str, Any]:
    """
    스테이지가 없을 때 에러 처리

    Args:
        state: GraphState
        stage_tag: 찾을 수 없는 스테이지 태그

    Returns:
        에러 상태
    """
    state["output"] = {
        "error": f"Stage '{stage_tag}' not found",
        "dialogues": []
    }
    state["next_node"] = "END"
    return state


def run_state_tools(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    state_tool_request를 처리 (tm_work 호환성)

    Args:
        state: GraphState

    Returns:
        업데이트된 state
    """
    request = state.get("state_tool_request")
    if not request:
        return state

    action = request.get("action")

    if action == "update_state":
        updates = request.get("updates", {})
        for key, value in updates.items():
            if key in state:
                if isinstance(state[key], dict) and isinstance(value, dict):
                    state[key].update(value)
                else:
                    state[key] = value
            else:
                state[key] = value

    # 요청 소비
    state.pop("state_tool_request", None)

    return state


def load_scenario_module(scenario_id: str):
    """
    시나리오 Python 모듈 로드 (훅용)

    Args:
        scenario_id: 시나리오 ID

    Returns:
        모듈 또는 None
    """
    # 현재는 모듈 시스템 없음 (나중에 확장 가능)
    return None
