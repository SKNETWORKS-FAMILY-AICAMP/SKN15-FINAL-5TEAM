# ============================================================
# 🔥 ParentAgent — Full Story Progression Version
# ============================================================
from __future__ import annotations
import importlib
import time
from typing import Any, Dict, Optional, List

# ============================================================
# ⚙️ SceneTools Import
# ============================================================
from src.tools import scene_tools
from src.tools.training_logger import log_agent

# 🎯 Stage 핸들러 관련
from .stage_handlers import (
    FreeIntentHandler,
    MissionHandler,
    RouterStageHandler,
    SceneHandler,
    OpenNarrativeHandler,
)

from src.utils.logger import log

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
            "open_narrative": OpenNarrativeHandler(locale),
        }

    # ============================================================
    # 🎮 Main Run
    # ============================================================
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        st = get_state_tools()
        scenario = st.ensure_scenario_state(state)
        if not scenario:
            log("parent", "❌ Scenario load failed: default scenario unavailable")
            return st.handle_missing_scenario(state)

        metadata = st.get_metadata(scenario)
        scenario_id = scenario.get("scenario_id") or state.get("scenario_id") or ""
        scenario_module = st.load_scenario_module(scenario_id)

        stage_tag, stage = st.resolve_stage(state, scenario)
        if not stage:
            return st.handle_missing_stage(state, stage_tag)
        state["stage_tag"] = stage_tag

        if (stage.get("type") or "").lower() == "mission" and not state.get("mission_target"):
            locked = (state.get("temp_data") or {}).get("locked_mission_target")
            if locked:
                state["mission_target"] = locked
            else:
                log("parent", f"⚠️ Mission stage has no active target (stage_tag={stage_tag})")

        while True:
            # open_narrative 스테이지는 beats 필요 없음 (LLM이 즉흥 생성)
            stage_type = (stage.get("type") or "scene").lower()
            if stage_type != "open_narrative":
                if stage.get("beats") is None and stage.get("beats_i18n"):
                    beats = scene_tools.resolve_i18n_beats(stage, scenario)
                    if beats:
                        stage["beats"] = beats

            handler = self._handlers.get(stage_type, self._handlers["scene"])
            result = handler.handle(state, stage, scenario)

            original_stage_tag = stage_tag
            stage_completed = bool(getattr(result, "stage_complete", False))

            st.update_stage_progress(state, original_stage_tag, stage_completed)
            scene_state = state.setdefault("scene", {})
            temp_data = state.setdefault("temp_data", {})
            game_state = state.setdefault("game", {})

            if stage_completed:
                temp_data.pop("intent", None)
                temp_data.pop("sticky_intent", None)

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

            auto_advance_tags = {
                str(tag).upper()
                for tag in (metadata.get("auto_advance_tags") or [])
                if isinstance(tag, str)
            }
            auto_advance_flag = bool(constraints.get("auto_advance"))
            stage_in_metadata = original_stage_tag.upper() in auto_advance_tags
            has_dialogue_payload = _has_dialogue_payload(child_payload)

            auto_advance_now = stage_completed and (
                auto_advance_flag
                or stage_in_metadata
                or not has_dialogue_payload
            )

            # open_narrative는 turn_count 기반 자동 전환
            turn_count = int(state.get("stage_turn", 0) or 0)
            narrative_turn_count = int(state.get("turn_count", 0) or 0)

            if current_stage_type == "open_narrative" and narrative_turn_count >= 5:
                auto_advance_now = True
                log("parent", "⚡ Auto-advance via open_narrative turn threshold",
                    stage_tag=original_stage_tag, turns=narrative_turn_count)
            elif stage_completed and turn_count >= 3:
                auto_advance_now = True
                log("parent", "⚡ Auto-advance via turn threshold", stage_tag=original_stage_tag, turns=turn_count)

            intent_triggers_next = False
            if next_stage:
                intent_triggers_next = self._user_requested_next_stage(state, stage, next_stage)
                if stage_completed and intent_triggers_next:
                    auto_advance_now = True
                    log("parent", "⚡ Auto-advance via routed intent", stage_tag=original_stage_tag, next_stage=next_stage)

            if next_stage:
                # open_narrative는 auto_advance_now일 때만 즉시 전환
                if current_stage_type in ("router", "free_intent", "open_narrative") or auto_advance_now:
                    immediate_advance = True

            if immediate_advance:
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
                children_ctx["beats"] = scene_tools.resolve_i18n_beats(stage, scenario)
                children_ctx["speaker_pool"] = stage.get("speaker_pool", [])
            else:
                if not children_ctx.get("beats") and not children_ctx.get("fallback"):
                    children_ctx["beats"] = scene_tools.resolve_i18n_beats(stage, scenario)
                if not children_ctx.get("speaker_pool"):
                    children_ctx["speaker_pool"] = stage.get("speaker_pool", [])
            objective = stage.get("objective")
            if objective:
                children_ctx["stage_objective"] = objective
            intent_mapping = stage.get("intent_mapping")
            if intent_mapping:
                children_ctx["intent_options"] = intent_mapping
        else:
            children_ctx.setdefault("beats", [])
            children_ctx.setdefault("speaker_pool", [])

        # --- 최근 맥락 요약 (LLM 호출 없이 rule-based로 구성)
        children_ctx["context_summary"] = self._build_context_summary(state)
        children_ctx["latest_user_input"] = state.get("user_input", "")
        children_ctx["recent_dialogues"] = self._collect_recent_dialogues(state)

        stage_key = (stage.get("tag") if isinstance(stage, dict) else stage_tag) or ""
        stage_key_upper = stage_key.upper()
        dynamic_speaker_stages = {
            str(tag).upper()
            for tag in (metadata.get("dynamic_speaker_stages") or [])
            if isinstance(tag, str)
        }
        if stage_key_upper in dynamic_speaker_stages:
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
        return_stage_meta = metadata.get("return_stage") or {}
        return_stage_tag = str(return_stage_meta.get("stage_tag") or "").upper()
        if return_stage_tag and stage_key_upper == return_stage_tag:
            queue_key = return_stage_meta.get("prefetch_queue_key", "mission_success_queue")
            queue = temp_data.get(queue_key) or []
            if queue:
                prefetch_list = children_ctx.setdefault("prefetch_dialogues", [])
                prefetch_list.extend(queue)
                temp_data.pop(queue_key, None)

            token = return_stage_meta.get("prefetch_token")
            if token and not temp_data.get(token):
                narrative = self._compose_return_to_front_dialogue(state, scenario)
                if narrative:
                    prefetch_list = children_ctx.setdefault("prefetch_dialogues", [])
                    prefetch_list.append(narrative)
                temp_data[token] = True

        children_ctx.setdefault("character_refs", scenario.get("character_refs", {}))
        children_ctx.setdefault("scenario_id", scenario.get("scenario_id", "unknown"))

        # Fallback
        if state.get("classification") in ("off_topic", "incoherent"):
            fallback_payload = st.prepare_fallback(state, stage)
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
    # 🧾 최근 맥락 요약 (Rule-based)
    # ============================================================
    def _build_context_summary(self, state: Dict[str, Any]) -> Optional[str]:
        """최근 사용자 입력과 직전 대사들을 간단히 요약한다."""
        summary_lines: List[str] = []

        user_input = (state.get("user_input") or "").strip()
        if user_input:
            summary_lines.append(f"사용자: {user_input}")

        message_history = state.get("message_history") or []
        if isinstance(message_history, list):
            for entry in message_history[-4:]:
                if not isinstance(entry, dict):
                    continue
                speaker = entry.get("speaker") or entry.get("role") or "unknown"
                text = (entry.get("text") or entry.get("content") or "").strip()
                if text:
                    summary_lines.append(f"기록({speaker}): {text}")

        recent_dialogues = (state.get("output") or {}).get("dialogues") or []
        if isinstance(recent_dialogues, list):
            for dialogue in recent_dialogues[-2:]:
                if not isinstance(dialogue, dict):
                    continue
                speaker = dialogue.get("speaker") or "unknown"
                text = (dialogue.get("text") or dialogue.get("content") or "").strip()
                if text:
                    summary_lines.append(f"직전({speaker}): {text}")

        if not summary_lines:
            return None

        return "\n".join(summary_lines)

    def _collect_recent_dialogues(self, state: Dict[str, Any], limit: int = 4) -> List[str]:
        """LLM 프롬프트용으로 최근 대사 몇 줄을 정리한다."""
        recent_lines: List[str] = []
        history = state.get("message_history") or []
        if isinstance(history, list):
            for entry in history[-limit:]:
                if not isinstance(entry, dict):
                    continue
                speaker = entry.get("speaker") or entry.get("role") or "unknown"
                text = (entry.get("text") or entry.get("content") or "").strip()
                if text:
                    recent_lines.append(f"{speaker}: {text}")

        output_dialogues = (state.get("output") or {}).get("dialogues") or []
        if isinstance(output_dialogues, list):
            for dialogue in output_dialogues[-limit:]:
                if not isinstance(dialogue, dict):
                    continue
                speaker = dialogue.get("speaker") or "unknown"
                text = (dialogue.get("text") or dialogue.get("content") or "").strip()
                if text:
                    recent_lines.append(f"{speaker}: {text}")

        return recent_lines[-limit:]

    def _user_requested_next_stage(
        self,
        state: Dict[str, Any],
        stage: Optional[Dict[str, Any]],
        next_stage: Optional[str],
    ) -> bool:
        """Router가 분기한 intent가 바로 다음 스테이지를 가리키는지 확인한다."""
        if not next_stage:
            return False

        temp = state.get("temp_data") or {}
        intent_key = (
            temp.get("intent")
            or temp.get("sticky_intent")
            or state.get("user_intent")
            or (state.get("routing_result") or {}).get("intent")
        )
        if not intent_key or not isinstance(stage, dict):
            return False

        mapping = stage.get("intent_mapping") or {}
        if isinstance(mapping, dict) and mapping.get(intent_key) == next_stage:
            return True

        return False

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

        scenario = st.ensure_scenario_state(state)
        scenario_id = (scenario or {}).get("scenario_id") or state.get("scenario_id") or ""
        scenario_module = st.load_scenario_module(scenario_id)
        completed_stage = st.consume_completed_stage(state)

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
        return_stage_meta = st.get_metadata(scenario).get("return_stage") or {}
        return_stage_tag = str(return_stage_meta.get("stage_tag") or "").upper()
        if return_stage_tag and stage_tag.upper() == return_stage_tag:
            token = return_stage_meta.get("prefetch_token")
            if token:
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
    def _compose_return_to_front_dialogue(self, state, scenario):
        allies = state.get("allies_recruited", [])
        fails = state.get("recruit_failures", [])
        st = get_state_tools()
        mission_meta = (st.get_metadata(scenario).get("mission") or {})
        name_map = mission_meta.get("ally_name_map") or {}
        dialogues = mission_meta.get("success_dialogues") or {}
        speaker = mission_meta.get("success_speaker", "tanjiro")
        fx = mission_meta.get("success_fx")

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
            template = dialogues.get("allies")
            msg = template.format(allies=_display(allies)) if template else ""
        elif allies and fails:
            template = dialogues.get("partial")
            msg = template.format(allies=_display(allies), fails=_display(fails)) if template else ""
        else:
            template = dialogues.get("none")
            msg = template if template else ""

        if not msg:
            return None

        payload = {"speaker": speaker, "text": msg}
        if fx:
            payload["fx"] = fx
        return payload

    # ============================================================
    # 🧩 엔딩 판정
    # ============================================================
    def _auto_determine_ending(self, state):
        st = get_state_tools()
        metadata = st.get_metadata(state.get("scenario") or state.get("scenario_data"))
        ending_meta = metadata.get("ending") or {}
        hidden_cfg = ending_meta.get("hidden_condition") or {}
        required_order = hidden_cfg.get("required_order") or []
        max_attempts = hidden_cfg.get("max_attempts", 3)

        order = state.get("recruit_order", [])
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])

        outcome = "BASIC"
        if not allies:
            outcome = "BAD"
        elif required_order:
            order_check = order[: len(required_order)] == required_order
            attempt_check = all(attempts.get(target, max_attempts + 1) <= max_attempts for target in required_order)
            if order_check and attempt_check:
                outcome = "HIDDEN"

        state["_outcome"] = outcome

        log("parent", f"[END_ROUTER] outcome={state['_outcome']} allies={allies}")

# ============================================================
# 🚀 Runner
# ============================================================
DEFAULT_AGENT = ParentAgent()

def run_parent_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    # Phase 4: 로그 수집
    start_time = time.perf_counter()

    try:
        result = DEFAULT_AGENT.run(state)

        # Model output 추출
        model_output = {
            "agent_inputs": result.get("agent_inputs"),
            "next_stage": result.get("next_stage"),
            "stage_tag": result.get("stage_tag"),
            "current_stage": result.get("current_stage"),
        }

        # 로그 저장 (result를 state로 전달 - children_ctx 포함)
        log_agent(
            agent_name="parent",
            state=result,  # 업데이트된 result 사용
            model_output=model_output,
            start_time=start_time,
            llm_model="gpt-4o-mini",  # Parent Agent uses default_model from settings (gpt-4o-mini)
        )

        return result

    except Exception as e:
        # 에러 발생 시에도 로그 수집 (실패 예시로 학습 가능)
        log_agent(
            agent_name="parent",
            state=state,
            model_output={"error": str(e)},
            start_time=start_time,
            is_error=True,
            error_message=str(e),
        )
        raise  # 에러는 다시 발생시켜 상위에서 처리

def parent_after_dialogue(state: Dict[str, Any]) -> Dict[str, Any]:
    return DEFAULT_AGENT.after_dialogue(state)

__all__ = ["ParentAgent", "run_parent_agent", "parent_after_dialogue"]
