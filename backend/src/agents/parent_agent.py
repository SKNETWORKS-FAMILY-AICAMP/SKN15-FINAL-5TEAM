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

        scenario_module = self._load_scenario_module(scenario)

        # --- Pending Stage (auto-resume between inputs)
        self._resume_pending_stage(state, scenario)
        stage_tag = self._ensure_current_stage(state, scenario)
        stage = scene_tools.get_stage(scenario, stage_tag)
        if not stage:
            return self._handle_missing_stage(state, stage_tag)

        if (stage.get("type") or "").lower() == "mission" and not state.get("mission_target"):
            locked = (state.get("temp_data") or {}).get("locked_mission_target")
            if locked:
                state["mission_target"] = locked
            else:
                log("parent", f"⚠️ Mission stage has no active target (stage_tag={stage_tag})")

        while True:
            if stage.get("beats") is None and stage.get("beats_i18n"):
                beats = scene_tools.resolve_i18n_beats(stage, scenario)
                if beats:
                    stage["beats"] = beats

            handler = self._handlers.get(stage.get("type"), self._handlers["scene"])
            result = handler.handle(state, stage, scenario)

            original_stage_tag = stage_tag
            stage_completed = bool(getattr(result, "stage_complete", False))

            scene_state = state.setdefault("scene", {})
            temp_data = state.setdefault("temp_data", {})
            game_state = state.setdefault("game", {})

            if stage_completed:
                scene_state["stage_completed"] = True
                temp_data["completed_stage"] = original_stage_tag
                game_state["last_completed_stage"] = original_stage_tag
            else:
                scene_state["stage_completed"] = False
                temp_data.pop("completed_stage", None)

            next_stage = getattr(result, "next_stage", None)
            next_stage_def = None
            immediate_advance = False
            current_stage_type = (stage.get("type") or "scene").lower() if isinstance(stage, dict) else "scene"
            constraints = stage.get("constraints") or {}

            def _has_dialogue_payload(ctx: Dict[str, Any]) -> bool:
                if ctx.get("beats"):
                    return True
                fallback = ctx.get("fallback")
                if isinstance(fallback, dict) and fallback.get("dialogues"):
                    return True
                if ctx.get("prefetch_dialogues"):
                    return True
                return False

            child_payload = result.children_ctx or {}

            auto_advance_now = stage_completed and (
                bool(constraints.get("auto_advance"))
                or original_stage_tag in {"INTRO", "RETURN_TO_FRONT"}
                or current_stage_type == "mission"
                or not _has_dialogue_payload(child_payload)
            )

            if next_stage:
                if current_stage_type in ("router", "free_intent") or auto_advance_now:
                    immediate_advance = True

            if immediate_advance:
                st = get_state_tools()
                st.set_current_stage(state, next_stage)
                st.reset_stage_turn(state)
                state["current_stage"] = next_stage
                log("parent", f"🔄 Stage advanced: {stage_tag} → {next_stage}")
                next_stage_def = scene_tools.get_stage(scenario, next_stage)
                scene_state["stage_completed"] = False
                temp_data.pop("completed_stage", None)
                game_state.pop("pending_stage", None)
                state.pop("next_stage", None)
                if next_stage_def:
                    try:
                        self._invoke_stage_enter(state, next_stage, next_stage_def, scenario, scenario_module)
                    except Exception as e:
                        log("parent", f"stage_enter failed: {e}")

                    stage_tag = next_stage
                    stage = next_stage_def
                    continue
            if next_stage and not immediate_advance:
                game_state["pending_stage"] = next_stage
                state["next_stage"] = next_stage
                log("parent", f"⏳ Stage completed: {stage_tag} → pending {next_stage}")
            else:
                game_state.pop("pending_stage", None)
                state.pop("next_stage", None)
            break

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
        elif next_stage and immediate_advance:
            # stage 정의를 찾지 못했을 때 경고만 남기고 stage_tag는 업데이트
            log("parent", f"⚠️ Stage '{next_stage}' not found in scenario")
            stage_tag = next_stage

        # --- Children Context 구성
        children_ctx = dict(result.children_ctx)
        if next_stage and immediate_advance:
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

        if next_stage and immediate_advance:
            children_ctx["stage_type"] = stage_type_value
        else:
            children_ctx.setdefault("stage_type", stage_type_value)

        if stage:
            # 다음 스테이지가 있으면 무조건 beats 갱신, 없으면 기존 beats 유지
            if next_stage and immediate_advance:
                children_ctx["beats"] = scene_tools.resolve_i18n_beats(stage, scenario, locale=self.locale)
                children_ctx["speaker_pool"] = stage.get("speaker_pool", [])
            else:
                if not children_ctx.get("beats") and not children_ctx.get("fallback"):
                    children_ctx["beats"] = scene_tools.resolve_i18n_beats(stage, scenario, locale=self.locale)
                if not children_ctx.get("speaker_pool"):
                    children_ctx["speaker_pool"] = stage.get("speaker_pool", [])
        else:
            children_ctx.setdefault("beats", [])
            children_ctx.setdefault("speaker_pool", [])

        # RETURN_TO_FRONT 및 엔딩 스테이지에서 영입 동료 화자 풀에 반영
        stage_key = (stage.get("tag") if isinstance(stage, dict) else stage_tag) or ""
        if stage_key in {"RETURN_TO_FRONT", "END_HIDDEN", "END_BASIC"}:
            recruits = state.get("allies_recruited", [])
            if recruits:
                pool = list(children_ctx.get("speaker_pool", []) or [])
                for recruit in recruits:
                    if recruit and recruit not in pool:
                        pool.append(recruit)
                if pool:
                    children_ctx["speaker_pool"] = pool
                beats = children_ctx.get("beats") or []
                if isinstance(beats, list) and beats:
                    enriched_beats = []
                    for beat in beats:
                        if isinstance(beat, dict):
                            beat_copy = dict(beat)
                            hints = beat_copy.get("speaker_hint")
                            if isinstance(hints, list):
                                hints = hints[:]
                            elif hints:
                                hints = [hints]
                            else:
                                hints = []
                            for recruit in recruits:
                                if recruit not in hints:
                                    hints.append(recruit)
                            beat_copy["speaker_hint"] = hints
                            enriched_beats.append(beat_copy)
                        else:
                            enriched_beats.append(beat)
                    children_ctx["beats"] = enriched_beats

        # RETURN_TO_FRONT 서사 프리롤 (한 번만 출력)
        if stage_key == "RETURN_TO_FRONT":
            queue = temp_data.get("mission_success_queue") or []
            if queue:
                prefetch_list = children_ctx.setdefault("prefetch_dialogues", [])
                prefetch_list.extend(queue)
                temp_data.pop("mission_success_queue", None)

            token = "__return_to_front_preface__"
            if not temp_data.get(token):
                narrative = self._compose_return_to_front_dialogue(state)
                if narrative:
                    prefetch_list = children_ctx.setdefault("prefetch_dialogues", [])
                    prefetch_list.append(narrative)
                temp_data[token] = True

        children_ctx.setdefault("character_refs", scenario.get("character_refs", {}))
        children_ctx.setdefault("scenario_id", scenario.get("scenario_id", "unknown"))

        # Fallback
        if state.get("classification") in ("off_topic", "incoherent"):
            fallback_payload = self._prepare_fallback(state, stage)
            if fallback_payload:
                children_ctx["fallback"] = fallback_payload

        state["children_ctx"] = children_ctx
        state["stage_tag"] = children_ctx.get("stage_tag", stage_tag)
        state["next_node"] = "children_agent"

        # --- 상세 로깅: children_ctx 내용 확인
        beats = children_ctx.get("beats") or []
        if not beats:
            mission_target = (children_ctx.get("mission") or {}).get("target") or state.get("mission_target")
            if mission_target:
                log("parent", f"⚠️ Mission target={mission_target} has empty beats! Using fallback.")
        beats_count = len(beats)
        speaker_pool = children_ctx.get("speaker_pool", [])
        log("parent", "→ Handed off to children_agent",
            stage_tag=children_ctx.get('stage_tag'),
            stage_type=children_ctx.get('stage_type'),
            beats_count=beats_count,
            speakers=speaker_pool)

        # 첫 3개 beats 미리보기
        if beats_count > 0:
            preview_beats = beats[:3]
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
            state["stage_tag"] = next_stage
        else:
            current = st.get_current_stage(state)
            if current:
                state["stage_tag"] = current

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

        # RECRUIT 진입 시 안내 플래그 초기화
        if stage_tag == "RECRUIT":
            temp = state.setdefault("temp_data", {})
            temp.pop("mission_intro_shown", None)
            temp.pop("mission_success_queue", None)
            mission_state = state.setdefault("mission", {})
            mission_state["active"] = False
            mission_state["target"] = None
            state["mission_target"] = None

        # RETURN_TO_FRONT 서사 자동 추가
        if stage_tag == "RETURN_TO_FRONT":
            token = "__return_to_front_preface__"
            temp = state.setdefault("temp_data", {})
            temp.pop(token, None)  # 새 스테이지 진입 시 프리롤 플래그 초기화

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
        name_map = {
            "inosuke": "이노스케",
            "zenitsu": "젠이츠",
            "tanjiro": "탄지로",
            "kanao": "카나오",
        }

        def _display(names):
            converted = [name_map.get(name, name) for name in names]
            if not converted:
                return ""
            if len(converted) == 1:
                return converted[0]
            if len(converted) == 2:
                return f"{converted[0]}와 {converted[1]}"
            return ", ".join(converted[:-1]) + f" 그리고 {converted[-1]}"

        if allies and not fails:
            msg = f"좋아, {_display(allies)}를 모았어! 이제 렌고쿠 님을 도우러 가자!"
        elif allies and fails:
            msg = f"{_display(allies)}는 합류했지만, {_display(fails)}는 설득하지 못했어... 그래도 서두르자!"
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

    def _resume_pending_stage(self, state: Dict[str, Any], scenario: Dict[str, Any]) -> None:
        """
        이전 턴에서 stage가 완료된 뒤 pending_stage만 남아 있을 경우
        다음 사용자 입력 전에 자동으로 다음 스테이지로 진입시킨다.
        """
        game = state.get("game") or {}
        scene = state.get("scene") or {}
        pending = game.get("pending_stage")
        if not pending:
            return
        if not scene.get("stage_completed"):
            return

        st = get_state_tools()
        next_stage = st.consume_pending_stage(state)
        if not next_stage:
            return

        st.set_current_stage(state, next_stage)
        st.reset_stage_turn(state)

        scenario_module = self._load_scenario_module(scenario)
        next_def = scene_tools.get_stage(scenario, next_stage)
        temp = st.get_temp_data(state)
        temp.pop("completed_stage", None)
        if next_def:
            try:
                self._invoke_stage_enter(state, next_stage, next_def, scenario, scenario_module)
            except Exception as e:
                log("parent", f"resume_pending_stage invoke failed: {e}")
        else:
            log("parent", f"resume_pending_stage missing stage definition: {next_stage}")

# ============================================================
# 🚀 Runner
# ============================================================
DEFAULT_AGENT = ParentAgent()

def run_parent_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    return DEFAULT_AGENT.run(state)

def parent_after_dialogue(state: Dict[str, Any]) -> Dict[str, Any]:
    return DEFAULT_AGENT.after_dialogue(state)

__all__ = ["ParentAgent", "run_parent_agent", "parent_after_dialogue"]
