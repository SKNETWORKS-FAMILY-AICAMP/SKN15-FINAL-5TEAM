from __future__ import annotations

from typing import Any, Dict, Optional


def _ensure_dict(parent: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = parent.get(key)
    if isinstance(value, dict):
        return value
    value = {}
    parent[key] = value
    return value


def get_scene_state(state: Dict[str, Any]) -> Dict[str, Any]:
    return _ensure_dict(state, "scene")


def get_temp_data(state: Dict[str, Any]) -> Dict[str, Any]:
    return _ensure_dict(state, "temp_data")


def get_current_stage(state: Dict[str, Any]) -> str:
    scene = get_scene_state(state)
    if state.get("current_stage"):
        scene.setdefault("current_stage", state["current_stage"])
        scene.setdefault("current_scene", state["current_stage"])
        return str(state["current_stage"])
    if scene.get("current_stage"):
        state["current_stage"] = scene["current_stage"]
        return str(scene["current_stage"])
    if scene.get("current_scene"):
        state["current_stage"] = scene["current_scene"]
        scene["current_stage"] = scene["current_scene"]
        return str(scene["current_scene"])
    return ""


def set_current_stage(state: Dict[str, Any], stage_tag: Optional[str]) -> None:
    scene = get_scene_state(state)
    if stage_tag is None:
        return
    stage_tag = str(stage_tag)
    scene["current_stage"] = stage_tag
    scene["current_scene"] = stage_tag
    scene["stage_completed"] = False
    state["current_stage"] = stage_tag
    history = state.setdefault("stage_history", [])
    if history and history[-1] == stage_tag:
        return
    history.append(stage_tag)


def increment_stage_turn(state: Dict[str, Any]) -> int:
    scene = get_scene_state(state)
    scene_turn = int(scene.get("stage_turn", 0) or 0) + 1
    scene["stage_turn"] = scene_turn
    state["stage_turn"] = scene_turn
    return scene_turn


def reset_stage_turn(state: Dict[str, Any]) -> None:
    scene = get_scene_state(state)
    scene["stage_turn"] = 0
    state["stage_turn"] = 0


def get_stage_memory(state: Dict[str, Any], stage_tag: str) -> Dict[str, Any]:
    store = _ensure_dict(state, "stage_states")
    stage_store = store.get(stage_tag)
    if isinstance(stage_store, dict):
        return stage_store
    stage_store = {}
    store[stage_tag] = stage_store
    return stage_store


def ensure_agent_inputs(state: Dict[str, Any]) -> Dict[str, Any]:
    agent_inputs = state.get("agent_inputs")
    if not isinstance(agent_inputs, dict):
        agent_inputs = {}
        state["agent_inputs"] = agent_inputs
    return agent_inputs


def set_children_ctx(state: Dict[str, Any], payload: Dict[str, Any]) -> None:
    agent_inputs = ensure_agent_inputs(state)
    agent_inputs["children"] = payload
    state["children_ctx"] = payload
    temp = get_temp_data(state)
    temp["children_ctx"] = payload


def mark_pending_stage(state: Dict[str, Any], next_stage: Optional[str]) -> None:
    temp = get_temp_data(state)
    if next_stage:
        temp["pending_stage"] = next_stage
    else:
        temp.pop("pending_stage", None)


def consume_pending_stage(state: Dict[str, Any]) -> Optional[str]:
    temp = get_temp_data(state)
    return temp.pop("pending_stage", None)


def mark_stage_entered(state: Dict[str, Any], stage_tag: str) -> None:
    temp = get_temp_data(state)
    temp["last_stage_enter"] = stage_tag


def get_last_stage_entered(state: Dict[str, Any]) -> Optional[str]:
    temp = get_temp_data(state)
    return temp.get("last_stage_enter")


def mark_stage_completed(state: Dict[str, Any], stage_tag: str) -> None:
    scene = get_scene_state(state)
    scene["stage_completed"] = True
    scene["current_stage"] = stage_tag
    scene["current_scene"] = stage_tag
    state["current_stage"] = stage_tag


def store_value(state: Dict[str, Any], path: str, value: Any) -> None:
    """
    Store a value in the state's stage memory using dot notation.
    Example: store_value(state, "mission.RECRUIT.active_lane", "zenitsu_lane")
    """
    parts = [part for part in path.split(".") if part]
    if not parts:
        return
    current: Dict[str, Any] = state
    for part in parts[:-1]:
        next_candidate = current.get(part)
        if isinstance(next_candidate, dict):
            current = next_candidate
            continue
        next_candidate = {}
        current[part] = next_candidate
        current = next_candidate
    current[parts[-1]] = value


def read_value(state: Dict[str, Any], path: str, default: Any = None) -> Any:
    parts = [part for part in path.split(".") if part]
    current: Any = state
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        return default
    return current


__all__ = [
    "get_scene_state",
    "get_temp_data",
    "get_current_stage",
    "set_current_stage",
    "increment_stage_turn",
    "reset_stage_turn",
    "get_stage_memory",
    "ensure_agent_inputs",
    "set_children_ctx",
    "mark_pending_stage",
    "consume_pending_stage",
    "mark_stage_entered",
    "get_last_stage_entered",
    "store_value",
    "read_value",
    "mark_stage_completed",
]
