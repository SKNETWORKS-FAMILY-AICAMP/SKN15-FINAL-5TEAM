# ============================================================
# 🧰 state_tools — 세션/스테이지 상태를 갱신·보조하는 헬퍼 모음
#  - SQLite 기반 체크포인트 저장, turn/flag 업데이트
#  - 시나리오 로딩, pending stage 재개, fallback 생성 지원
#  - ParentAgent, StateTools 노드 등에서 공통으로 사용
# ============================================================

import json
import importlib
import sqlite3
from functools import lru_cache
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from src.core.scenes_repo import ScenesRepo
from src.tools import scene_tools
from src.utils.fallback import trigger_fallback
from src.utils.logger import log
from src.config.constants import INTRO_STAGE_TAG

_SCENES_REPO = ScenesRepo()


class StateTools:
    def __init__(self, db_path: str = "data/game_state.db"):
        self.db_path = db_path
        self._initialize_database()

    # -----------------------------------------------
    # DB 초기화
    # -----------------------------------------------
    def _initialize_database(self):
        """SQLite 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS game_sessions (
                    session_id TEXT PRIMARY KEY,
                    scenario_id TEXT,
                    scene_id TEXT,
                    stage TEXT,
                    turn INTEGER,
                    total_remaining_turns INTEGER,
                    flags TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    # -----------------------------------------------
    # 핵심 요청 처리
    # -----------------------------------------------
    def process_request(self, state: dict):
        """state_tool_request를 기반으로 상태 갱신"""
        req = state.get("state_tool_request")
        if not req:
            return state

        action = req.get("action")
        if not action:
            return state

        try:
            if action == "update_state":
                self._update_turn_and_flags(state)
            elif action == "save_checkpoint":
                self._save_checkpoint(state)
        except Exception as e:
            print(f"[StateTools] process_request 오류: {e}")

        return state

    # -----------------------------------------------
    # 내부 업데이트 로직 (dict-safe)
    # -----------------------------------------------
    def _update_turn_and_flags(self, state: dict):
        """턴 / 플래그 단순 갱신"""
        game = state.get("game", {})
        meta = state.get("meta", {})

        session_id = meta.get("session_id", "unknown")
        scenario_id = game.get("scenario_id", "unknown")
        scene_id = game.get("scene_id", "unknown")
        stage = game.get("current_stage", INTRO_STAGE_TAG)
        turn = game.get("turn", 0)
        total_remaining_turns = game.get("total_remaining_turns", 0)
        flags_json = json.dumps(game.get("flags", []))

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT OR REPLACE INTO game_sessions
                (session_id, scenario_id, scene_id, stage, turn, total_remaining_turns, flags, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    scenario_id,
                    scene_id,
                    stage,
                    turn,
                    total_remaining_turns,
                    flags_json,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def _save_checkpoint(self, state: dict):
        """전체 상태 저장"""
        self._update_turn_and_flags(state)


# ==========================================================
# 🔹 시나리오 / 스테이지 관리
# ==========================================================
def ensure_scenario_state(state: dict, scenario_id: Optional[str] = None) -> Optional[dict]:
    """
    state에 시나리오 정보가 없으면 ScenesRepo를 통해 로드하고 저장한다.
    """
    scenario = resolve_scenario(state)
    if isinstance(scenario, dict):
        return scenario

    candidate_id = scenario_id or state.get("scenario_id")
    loaded = None
    if candidate_id:
        loaded = _SCENES_REPO.load(str(candidate_id))
    if not loaded:
        loaded = _SCENES_REPO.load_default()

    if loaded:
        state["scenario"] = loaded
        state["scenario_data"] = loaded
        resolved_id = loaded.get("scenario_id") or candidate_id
        if resolved_id:
            state["scenario_id"] = resolved_id
            state.setdefault("game", {})["scenario_id"] = resolved_id
        return loaded
    return None


def get_metadata(scenario: Optional[dict]) -> Dict[str, Any]:
    if not isinstance(scenario, dict):
        return {}
    meta = scenario.get("metadata")
    return meta if isinstance(meta, dict) else {}


def get_default_stage_tag(scenario: Optional[dict]) -> str:
    if not isinstance(scenario, dict):
        return INTRO_STAGE_TAG

    metadata = get_metadata(scenario)
    default_stage = metadata.get("default_stage") or scenario.get("default_stage")
    if isinstance(default_stage, str) and default_stage.strip():
        return default_stage.strip()

    stages = scene_tools.list_stages(scenario) if isinstance(scenario, dict) else []
    if stages:
        first = stages[0]
        if isinstance(first, dict):
            return first.get("tag") or first.get("id") or first.get("name") or INTRO_STAGE_TAG
    return INTRO_STAGE_TAG


@lru_cache(maxsize=16)
def load_scenario_module(scenario_id: str) -> Optional[Any]:
    """
    시나리오 전용 파이썬 모듈을 동적으로 로드.
    """
    if not scenario_id:
        return None
    module_key = scenario_id.replace("-", "_")
    module_name = f"src.scenarios.{module_key}"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None


def resolve_stage(state: dict, scenario: Optional[dict]) -> Tuple[str, Optional[dict]]:
    """
    현재 stage_tag와 stage 정의를 반환.
    """
    if scenario:
        resume_pending_stage(state, scenario)

    stage_tag = get_current_stage(state)
    if (not stage_tag) and scenario:
        stage_tag = get_default_stage_tag(scenario)
        set_current_stage(state, stage_tag)

    stage_def = scene_tools.get_stage(scenario, stage_tag) if scenario else None
    return stage_tag, stage_def


def update_stage_progress(state: dict, stage_tag: str, completed: bool) -> None:
    """
    스테이지 완료 여부에 따라 scene/temp/game 상태를 갱신한다.
    """
    scene_state = state.setdefault("scene", {})
    temp_data = state.setdefault("temp_data", {})
    game_state = state.setdefault("game", {})

    if completed:
        scene_state["stage_completed"] = True
        temp_data["completed_stage"] = stage_tag
        game_state["last_completed_stage"] = stage_tag
    else:
        scene_state["stage_completed"] = False
        temp_data.pop("completed_stage", None)


def consume_completed_stage(state: dict) -> Optional[str]:
    """
    temp_data에 기록된 completed_stage를 반환하고 제거한다.
    """
    temp = get_temp_data(state)
    if isinstance(temp, dict):
        return temp.pop("completed_stage", None)
    return None


def resume_pending_stage(state: dict, scenario: Optional[dict]) -> Optional[str]:
    """
    pending_stage가 존재하고 현재 스테이지가 완료된 경우 자동으로 다음 스테이지를 셋업한다.
    """
    game = state.get("game") or {}
    scene = state.get("scene") or {}
    pending = game.get("pending_stage")
    if not pending or not scene.get("stage_completed"):
        return None

    next_stage = consume_pending_stage(state)
    if not next_stage:
        return None

    set_current_stage(state, next_stage)
    reset_stage_turn(state)

    scenario_module = None
    scenario_id = (scenario or {}).get("scenario_id")
    if scenario_id:
        scenario_module = load_scenario_module(scenario_id)

    next_def = scene_tools.get_stage(scenario, next_stage) if scenario else None
    temp = get_temp_data(state)
    temp.pop("completed_stage", None)

    if next_def and scenario_module and hasattr(scenario_module, "on_stage_enter"):
        try:
            scenario_module.on_stage_enter(state, next_def, scenario)
        except Exception as exc:
            log("state_tools", f"resume_pending_stage invoke failed: {exc}")
    elif not next_def:
        log("state_tools", f"resume_pending_stage missing stage definition: {next_stage}")

    return next_stage


def prepare_fallback(state: dict, stage: Optional[dict], reason: str = "urgent_atmosphere") -> Optional[Dict[str, Any]]:
    """
    긴급 상황 등에서 fallback 대사를 생성한다.
    """
    if not isinstance(stage, dict):
        return None
    if (stage.get("atmosphere") or "").lower() != "urgent":
        return None
    if not state.get("user_input"):
        return None
    return trigger_fallback(state, stage, reason=reason)


def handle_missing_scenario(state: dict) -> dict:
    """
    시나리오가 없을 때 최소한의 children_ctx를 설정하고 state_tools 노드로 전환.
    """
    set_children_ctx(
        state,
        {
            "stage_tag": "unknown",
            "stage_type": "scene",
            "speaker_pool": [],
            "beats": [],
        },
    )
    state["next_node"] = "state_tools"
    return state


def handle_missing_stage(state: dict, tag: str) -> dict:
    """
    스테이지 정의가 없을 때 fallback children_ctx를 구성.
    """
    set_children_ctx(
        state,
        {
            "stage_tag": tag,
            "stage_type": "scene",
            "speaker_pool": [],
            "beats": [],
        },
    )
    state["next_node"] = "state_tools"
    return state


# ==========================================================
# 🔹 유틸 함수
# ==========================================================
def get_current_stage(state: dict) -> str:
    """현재 진행 중 stage_tag 반환"""
    try:
        game = state.get("game", {})
        scene = state.get("scene", {})
        current = (
            game.get("current_stage")
            or scene.get("current_stage")
            or state.get("current_stage")
        )
        if current:
            return current

        history = game.get("stage_history")
        if isinstance(history, list) and history:
            last = history[-1]
            if last:
                return last

        return INTRO_STAGE_TAG
    except Exception:
        return INTRO_STAGE_TAG


def get_scene_state(state: dict) -> Dict:
    """현재 scene 상태 딕셔너리 반환"""
    try:
        if "scene" in state and isinstance(state["scene"], dict):
            return state["scene"]
        if "game" in state and isinstance(state["game"].get("scene", {}), dict):
            return state["game"]["scene"]
        return {}
    except Exception:
        return {}


def get_temp_data(state: dict) -> Dict:
    """state 내부 temp_data 안전 조회"""
    try:
        if "temp_data" in state and isinstance(state["temp_data"], dict):
            return state["temp_data"]
        if "game" in state and isinstance(state["game"].get("temp_data", {}), dict):
            return state["game"]["temp_data"]
        return {}
    except Exception:
        return {}


# ==============================================================
# 🔹 시나리오 관련 유틸
# ==============================================================
def resolve_scenario(state: dict) -> Optional[dict]:
    """
    현재 state에서 시나리오 데이터를 안전하게 추출.
    - state["scenario"] → 우선 사용
    - state["scenario_data"] → 백업 사용
    - 없으면 None 반환
    """
    try:
        if "scenario" in state and state["scenario"]:
            return state["scenario"]
        if "scenario_data" in state and state["scenario_data"]:
            return state["scenario_data"]
        return None
    except Exception:
        return None


# ==========================================================
# 🔹 스테이지 턴 관리 유틸
# ==========================================================
def increment_stage_turn(state: dict) -> None:
    """
    현재 스테이지 턴을 1 증가시킴.
    없으면 자동 초기화함.
    """
    try:
        game = state.setdefault("game", {})
        scene = state.setdefault("scene", {})

        # scene 내부 turn 우선 증가
        scene["stage_turn"] = int(scene.get("stage_turn", 0)) + 1
        game["turn"] = int(game.get("turn", 0)) + 1
        state["stage_turn"] = int(state.get("stage_turn", 0)) + 1
    except Exception as e:
        print(f"[StateTools] increment_stage_turn 오류: {e}")


def reset_stage_turn(state: dict) -> None:
    """
    현재 스테이지 턴을 0으로 초기화.
    """
    try:
        game = state.setdefault("game", {})
        scene = state.setdefault("scene", {})
        scene["stage_turn"] = 0
        game["turn"] = 0
        state["stage_turn"] = 0
    except Exception as e:
        print(f"[StateTools] reset_stage_turn 오류: {e}")


# ==========================================================
# 🔹 스테이지 전환 관리 유틸
# ==========================================================
def consume_pending_stage(state: dict) -> Optional[str]:
    """
    pending_stage 값이 있으면 반환하고 제거.
    """
    try:
        game = state.setdefault("game", {})
        next_stage = game.pop("pending_stage", None)
        return next_stage
    except Exception as e:
        print(f"[StateTools] consume_pending_stage 오류: {e}")
        return None


def set_current_stage(state: dict, stage_tag: str) -> None:
    """
    현재 진행 중 스테이지를 설정.
    """
    try:
        game = state.setdefault("game", {})
        scene = state.setdefault("scene", {})
        game["current_stage"] = stage_tag
        scene["current_stage"] = stage_tag
        state["current_stage"] = stage_tag
    except Exception as e:
        print(f"[StateTools] set_current_stage 오류: {e}")


# ==========================================================
# 🔹 Children / Stage 기록 유틸
# ==========================================================
def set_children_ctx(state: dict, ctx: Optional[Dict[str, Any]]) -> None:
    """
    children_ctx를 안전하게 설정하고 agent_inputs bridge도 갱신.
    """
    try:
        normalized = dict(ctx or {})
        state["children_ctx"] = normalized

        agent_inputs = state.setdefault("agent_inputs", {})
        if isinstance(agent_inputs, dict):
            agent_inputs["children"] = dict(normalized)
    except Exception as e:
        print(f"[StateTools] set_children_ctx 오류: {e}")


def mark_stage_entered(state: dict, stage_tag: str) -> None:
    """
    스테이지 진입 기록. stage_history 유지 및 완료 플래그 리셋.
    """
    try:
        tag = stage_tag or "UNKNOWN"
        scene = state.setdefault("scene", {})
        game = state.setdefault("game", {})
        temp = state.setdefault("temp_data", {})

        # stage 정보 동기화
        scene["current_stage"] = tag
        scene["stage_completed"] = False
        game["current_stage"] = tag
        state["current_stage"] = tag

        # stage history
        history = game.setdefault("stage_history", [])
        if not history or history[-1] != tag:
            history.append(tag)

        state_history = state.setdefault("stage_history", [])
        if isinstance(state_history, list):
            if not state_history or state_history[-1] != tag:
                state_history.append(tag)

        # 완료 상태 초기화
        temp.pop("completed_stage", None)
    except Exception as e:
        print(f"[StateTools] mark_stage_entered 오류: {e}")


# ==========================================================
# 🔹 상태 Key-Path 도우미
# ==========================================================
def _resolve_parent(
    state: dict, path: str, create: bool
) -> Tuple[Optional[dict], Optional[str]]:
    if not path:
        return None, None
    parts = path.split(".")
    parent = state
    for key in parts[:-1]:
        if not isinstance(parent, dict):
            return None, None
        if key not in parent:
            if not create:
                return None, None
            parent[key] = {}
        elif not isinstance(parent[key], dict):
            if create:
                parent[key] = {}
            else:
                return None, None
        parent = parent[key]
    return parent if isinstance(parent, dict) else None, parts[-1]


def read_value(state: dict, path: str, default: Any = None) -> Any:
    """
    점 표기법(key1.key2) 기반으로 안전하게 값 조회.
    """
    if not path:
        return default
    current: Any = state
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def store_value(state: dict, path: str, value: Any) -> None:
    """
    점 표기법(key1.key2) 기반으로 값을 저장. 중간 dict 자동 생성.
    """
    if not path:
        return
    parent, leaf = _resolve_parent(state, path, create=True)
    if parent is None or leaf is None:
        return
    parent[leaf] = value


# ==========================================================
# 실행 함수
# ==========================================================
def run_state_tools(state: dict) -> dict:
    tools = StateTools()
    return tools.process_request(state)


__all__ = [
    "StateTools",
    "run_state_tools",
    "ensure_scenario_state",
    "get_metadata",
    "get_default_stage_tag",
    "load_scenario_module",
    "resolve_stage",
    "get_current_stage",
    "get_scene_state",
    "get_temp_data",
    "increment_stage_turn",
    "reset_stage_turn",
    "consume_pending_stage",
    "consume_completed_stage",
    "resume_pending_stage",
    "set_current_stage",
    "set_children_ctx",
    "mark_stage_entered",
    "update_stage_progress",
    "prepare_fallback",
    "handle_missing_scenario",
    "handle_missing_stage",
    "read_value",
    "store_value",
]
