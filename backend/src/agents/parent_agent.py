# ============================================================
# 🔥 ParentAgent — Full Story Progression Version
# ============================================================
from __future__ import annotations
import importlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, List

# ============================================================
# 🧩 Lazy Import Setup (state_tools)
# ============================================================
_state_tools_module = None
def get_state_tools():
    global _state_tools_module
    if _state_tools_module is None:
        _state_tools_module = importlib.import_module("src.tools.state_tools")
    return _state_tools_module

# ============================================================
# ⚙️ SceneTools Import
# ============================================================
from src.tools import scene_tools

# 🎯 Stage 핸들러 관련
from .stage_handlers import (
    FreeIntentHandler,
    MissionHandler,
    RouterStageHandler,
    SceneHandler,
)

# 🧱 유틸 계층
from .utils.fallback import trigger_fallback
from .utils.logger import log

# 🧠 LLM 클라이언트
from src.utils.llm_client import get_llm_client


# ============================================================
# 🧩 ParentAgent
# ============================================================
class ParentAgent:
    def __init__(self, locale="ko"):
        self.locale = locale
        self._handlers = {
            "mission": MissionHandler(locale),
            "scene": SceneHandler(locale),
            "free_intent": FreeIntentHandler(locale),
            "router": RouterStageHandler(),
        }
        self._scenario_cache = {}

    # ============================================================
    # 🎮 Main Run
    # ============================================================
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        st = get_state_tools()
        scenario = state.get("scenario") or state.get("scenario_data")

        if not scenario:
            from src.core.scenes_repo import ScenesRepo
            repo = ScenesRepo()
            scenario_id = "cutscene5_llm_driven"
            scenario = repo.load(scenario_id)
            if scenario:
                state["scenario"] = scenario
                state["current_stage"] = "INTRO"
                log("parent", f"✅ Auto-loaded scenario: {scenario_id}")
            else:
                log("parent", f"❌ Scenario load failed: {scenario_id}")
                return self._handle_missing_scenario(state)

        # --- Stage 판정
        stage_tag = self._ensure_current_stage(state, scenario)
        stage = scene_tools.get_stage(scenario, stage_tag)
        if not stage:
            return self._handle_missing_stage(state, stage_tag)

        # --- i18n Beats 처리
        if stage.get("beats") is None and stage.get("beats_i18n"):
            beats = scene_tools.resolve_i18n_beats(stage, scenario)
            if beats:
                stage["beats"] = beats

        # --- Handler 선택
        handler = self._handlers.get(stage.get("type"), self._handlers["scene"])
        result = handler.handle(state, stage, scenario)

        # --- 다음 Stage 처리
        next_stage = getattr(result, "next_stage", None)
        if next_stage:
            st = get_state_tools()
            st.set_current_stage(state, next_stage)
            st.reset_stage_turn(state)
            state["current_stage"] = next_stage
            log("parent", f"🔄 Stage advanced: {stage_tag} → {next_stage}")
            # 다음 스테이지 정의를 미리 로드
            next_stage_def = scene_tools.get_stage(scenario, next_stage)
        else:
            next_stage_def = None

        if next_stage:
            state["next_stage"] = next_stage
        else:
            state.pop("next_stage", None)

        # --- Scene/StateTools 반영
        state = self._update_state_with_tools(state, result, stage_tag)

        # --- Stage 참조 갱신 (다음 스테이지가 있을 경우)
        if next_stage_def:
            stage_tag = next_stage
            stage = next_stage_def
            if stage.get("beats") is None and stage.get("beats_i18n"):
                beats = scene_tools.resolve_i18n_beats(stage, scenario)
                if beats:
                    stage["beats"] = beats
        elif next_stage:
            # stage 정의를 찾지 못했을 때 경고만 남기고 stage_tag는 업데이트
            log("parent", f"⚠️ Stage '{next_stage}' not found in scenario")
            stage_tag = next_stage

        # --- Children Context 구성
        children_ctx = dict(result.children_ctx)
        if next_stage:
            children_ctx["stage_tag"] = stage_tag
        else:
            children_ctx.setdefault("stage_tag", stage_tag)
        # 🚨 get_stage_type() 방어
        if stage:
            if hasattr(scene_tools, "get_stage_type"):
                stage_type_value = scene_tools.get_stage_type(stage)
            else:
                stage_type_value = stage.get("type", "scene")
        else:
            stage_type_value = "scene"

        if next_stage:
            children_ctx["stage_type"] = stage_type_value
        else:
            children_ctx.setdefault("stage_type", stage_type_value)

        if stage:
            # 다음 스테이지가 있으면 무조건 beats 갱신, 없으면 기존 beats 유지
            if next_stage:
                children_ctx["beats"] = scene_tools.resolve_i18n_beats(stage, scenario, locale=self.locale)
                children_ctx["speaker_pool"] = stage.get("speaker_pool", [])
            else:
                if not children_ctx.get("beats"):
                    children_ctx["beats"] = scene_tools.resolve_i18n_beats(stage, scenario, locale=self.locale)
                if not children_ctx.get("speaker_pool"):
                    children_ctx["speaker_pool"] = stage.get("speaker_pool", [])
        else:
            children_ctx.setdefault("beats", [])
            children_ctx.setdefault("speaker_pool", [])

        children_ctx.setdefault("character_refs", scenario.get("character_refs", {}))
        children_ctx.setdefault("scenario_id", scenario.get("scenario_id", "unknown"))

        # Fallback
        if state.get("classification") in ("off_topic", "incoherent"):
            fallback_payload = self._prepare_fallback(state, stage)
            if fallback_payload:
                children_ctx["fallback"] = fallback_payload

        state["children_ctx"] = children_ctx
        state["next_node"] = "children_agent"

        # --- 상세 로깅: children_ctx 내용 확인
        beats_count = len(children_ctx.get("beats", []))
        speaker_pool = children_ctx.get("speaker_pool", [])
        log("parent", "→ Handed off to children_agent",
            stage_tag=children_ctx.get('stage_tag'),
            stage_type=children_ctx.get('stage_type'),
            beats_count=beats_count,
            speakers=speaker_pool)

        # 첫 3개 beats 미리보기
        if beats_count > 0:
            preview_beats = children_ctx.get("beats", [])[:3]
            for i, beat in enumerate(preview_beats):
                if isinstance(beat, dict):
                    goal = beat.get("goal", "")[:60]
                    log("parent", f"  Beat[{i}]: {goal}...")
                else:
                    log("parent", f"  Beat[{i}]: {type(beat)}")

        # --- StateTools 동기화
        state["state_tool_request"] = {"action": "update_state", "updates": {"stage": state.get("stage")}}
        state = st.run_state_tools(state)
        return state

    # ============================================================
    # ⚙️ StateTools/SceneTools 반영
    # ============================================================
    def _update_state_with_tools(self, state, result, stage_tag: str):
        try:
            if hasattr(result, "scene_tool_response"):
                res = result.scene_tool_response
                if getattr(res, "status", "") == "success" and getattr(res, "image_url", None):
                    state.setdefault("output", {})["scene_image_url"] = res.image_url

            if hasattr(result, "state_tool_response"):
                res = result.state_tool_response
                if getattr(res, "status", "") == "success" and getattr(res, "updated_state", None):
                    for key, val in res.updated_state.items():
                        state.setdefault("game", {})[key] = val

                    if getattr(res, "hidden_ending_triggered", False):
                        state.setdefault("game", {}).setdefault("flags", []).append("hidden_ending_triggered")
                        state["game"]["ending_type"] = getattr(res, "ending_type", "unknown")

            state.setdefault("game", {})["last_action"] = f"update_after_{stage_tag}"
        except Exception as e:
            log("parent", f"[update_state_with_tools] 오류: {e}")
        return state

    # ============================================================
    # 💬 After Dialogue
    # ============================================================
    def after_dialogue(self, state: Dict[str, Any]) -> Dict[str, Any]:
        st = get_state_tools()
        temp = st.get_temp_data(state)
        if temp.pop("skip_parent_after_dialogue", False):
            log("parent", "Skipping post-dialogue hooks (guardrail intervention)")
            state["next_node"] = "wait_user_input"
            return state

        scenario = scene_tools.resolve_scenario(state)
        scenario_module = self._load_scenario_module(scenario)
        completed_stage = self._consume_completed_stage(state)

        # stage turn 증가
        st.increment_stage_turn(state)

        # Stage 완료 처리
        if completed_stage and scenario and scenario_module and hasattr(scenario_module, "on_stage_complete"):
            try:
                stage_def = scene_tools.get_stage(scenario, completed_stage)
                scenario_module.on_stage_complete(state, stage_def, scenario)
            except Exception as e:
                log("parent", f"on_stage_complete failed: {e}")

        # 다음 Stage 전환
        next_stage = st.consume_pending_stage(state)
        if next_stage:
            st.set_current_stage(state, next_stage)
            st.reset_stage_turn(state)
            next_def = scene_tools.get_stage(scenario, next_stage)
            if next_def:
                self._invoke_stage_enter(state, next_stage, next_def, scenario, scenario_module)

        state["next_node"] = "router"
        return state

    # ============================================================
    # 🧱 Stage Helpers
    # ============================================================
    def _ensure_current_stage(self, state, scenario):
        st = get_state_tools()
        stage_tag = st.get_current_stage(state)
        if not stage_tag:
            stage_tag = scenario.get("default_stage", "INTRO")
            state.setdefault("game", {})["current_stage"] = stage_tag
        return stage_tag

    def _invoke_stage_enter(self, state, stage_tag, stage, scenario, scenario_module):
        """Stage 진입 이벤트 트리거"""
        st = get_state_tools()
        log("parent", f"[StageEnter] {stage_tag}")

        # RETURN_TO_FRONT 서사 자동 추가
        if stage_tag == "RETURN_TO_FRONT":
            narrative = self._compose_return_to_front_dialogue(state)
            state.setdefault("output", {}).setdefault("dialogues", []).append(narrative)

        # 엔딩 처리
        if stage_tag == "END_ROUTER":
            self._auto_determine_ending(state)

        if scenario_module and hasattr(scenario_module, "on_stage_enter"):
            try:
                scenario_module.on_stage_enter(state, stage, scenario)
            except Exception as e:
                log("parent", f"on_stage_enter failed: {e}")

        st.mark_stage_entered(state, stage_tag)

    # ============================================================
    # 🎬 RETURN_TO_FRONT 서사
    # ============================================================
    def _compose_return_to_front_dialogue(self, state):
        allies = state.get("allies_recruited", [])
        fails = state.get("recruit_failures", [])
        if allies and not fails:
            msg = f"좋아, {'와 '.join(allies)}를 모았어! 이제 렌고쿠 님을 도우러 가자!"
        elif allies and fails:
            msg = f"{'와 '.join(allies)}는 합류했지만, {', '.join(fails)}는 설득하지 못했어... 그래도 서두르자!"
        else:
            msg = "아무도 합류하지 못했어... 그래도 우리라도 어서 돌아가자!"
        return {"speaker": "tanjiro", "text": msg, "fx": "urgent_heartbeat|flame_flash"}

    # ============================================================
    # 🧩 엔딩 판정
    # ============================================================
    def _auto_determine_ending(self, state):
        order = state.get("recruit_order", [])
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])
        max_attempts = 3

        if not allies:
            state["_outcome"] = "BAD"
        elif order == ["inosuke", "zenitsu"] and \
                attempts.get("inosuke", 99) <= max_attempts and \
                attempts.get("zenitsu", 99) <= max_attempts:
            state["_outcome"] = "HIDDEN"
        else:
            state["_outcome"] = "BASIC"

        log("parent", f"[END_ROUTER] outcome={state['_outcome']} allies={allies}")

    # ============================================================
    # ⚠️ Missing Stage/Scenario
    # ============================================================
    def _handle_missing_scenario(self, state):
        st = get_state_tools()
        st.set_children_ctx(state, {"stage_tag": "unknown", "stage_type": "scene", "speaker_pool": [], "beats": []})
        state["next_node"] = "state_tools"
        return state

    def _handle_missing_stage(self, state, tag):
        st = get_state_tools()
        st.set_children_ctx(state, {"stage_tag": tag, "stage_type": "scene", "speaker_pool": [], "beats": []})
        state["next_node"] = "state_tools"
        return state

    # ============================================================
    # 🧩 Helper Utilities
    # ============================================================
    def _load_scenario_module(self, scenario):
        if not scenario:
            return None
        module_key = (scenario.get("module_id") or scenario.get("scenario_id") or "").replace("-", "_")
        if not module_key:
            return None
        module_name = f"src.scenarios.{module_key}"
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError:
            return None

    def _prepare_fallback(self, state, stage):
        if (stage.get("atmosphere") or "").lower() != "urgent":
            return None
        if not state.get("user_input"):
            return None
        return trigger_fallback(state, stage, reason="urgent_atmosphere")

    def _consume_completed_stage(self, state):
        st = get_state_tools()
        temp = st.get_temp_data(state)
        return temp.pop("completed_stage", None)


# ============================================================
# 🚀 Runner
# ============================================================
DEFAULT_AGENT = ParentAgent()

def run_parent_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    return DEFAULT_AGENT.run(state)

def parent_after_dialogue(state: Dict[str, Any]) -> Dict[str, Any]:
    return DEFAULT_AGENT.after_dialogue(state)

__all__ = ["ParentAgent", "run_parent_agent", "parent_after_dialogue"]
