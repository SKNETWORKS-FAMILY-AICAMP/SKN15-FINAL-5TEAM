'''Router → ParentAgent.run()
         ↓
      children_ctx
         ↓
ChildrenAgent.run()
         ↓
SceneDialogueTools (tone_profiles + prompt)
         ↓
LLM → tone-aware dialogues
         ↓
DialogueAgent (UI 출력)'''

from __future__ import annotations

import importlib
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Dict, Optional, List

from . import scene_tools, state_tools
from .stage_handlers import (
    FreeIntentHandler,
    MissionHandler,
    RouterStageHandler,
    SceneHandler,
    StageResult,
)
from .utils.fallback import trigger_fallback
from .utils.logger import log
from src.utils.llm_client import get_llm_client


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

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        ParentAgent의 핵심 실행 메서드.
        - 현재 stage를 판단하고 해당 handler를 실행.
        - children_agent에 전달할 컨텍스트(children_ctx)를 구성.
        """

        # --- 0️⃣ 시나리오 자동 로드 처리 (Router에서 안 넘어온 경우) ---
        scenario = state.get("scenario") or state.get("scenario_data")
        if not scenario:
            user_intent = state.get("user_intent") or (state.get("routing_result") or {}).get("intent")
            if user_intent == "on_topic_start":
                from src.core.scenes_repo import ScenesRepo
                repo = ScenesRepo()
                scenario_id = "cutscene5_llm_driven"
                scenario = repo.load(scenario_id)
                if scenario:
                    state["scenario"] = scenario
                    state["current_stage"] = "INTRO"
                    log("parent", f"✅ Auto-loaded scenario: {scenario_id}")
                else:
                    log("parent", f"❌ Failed to load scenario: {scenario_id}")
            else:
                log("parent", f"⚠️ No scenario loaded in state (intent={user_intent})")
                # 시나리오가 없으면 빈 응답 처리
                return self._handle_missing_scenario(state)
        else:
            state["scenario"] = scenario

        # --- 1️⃣ 현재 stage 정보 확보 ---
        stage_tag = self._ensure_current_stage(state, scenario)
        stage = scene_tools.get_stage(scenario, stage_tag)
        if not stage:
            return self._handle_missing_stage(state, stage_tag)

        # --- 2️⃣ i18n beats → beats 변환 (한국어 시나리오 대응) ---
        if stage.get("beats") is None and stage.get("beats_i18n"):
            beats = scene_tools.resolve_i18n_beats(stage, scenario)
            if beats:
                stage["beats"] = beats

        # --- 3️⃣ 해당 stage handler 선택 ---
        handler = self._handlers.get(stage.get("type"))
        if not handler:
            log("parent", f"⚠️ Unknown stage type: {stage.get('type')}")
            return state

        # --- 4️⃣ LLM 호출 전 fallback 준비 ---
        fallback_payload = None
        if state.get("classification") in ("off_topic", "incoherent"):
            fallback_payload = self._prepare_fallback(state, stage)

        # --- 5️⃣ stage handler 실행 ---
        result = handler.handle(state, stage, scenario)
        fallback_payload = result.fallback_payload or fallback_payload

        # --- 6️⃣ 다음 stage 판정 ---
        next_stage = getattr(result, "next_stage", None)
        if next_stage:
            state["next_stage"] = next_stage
            state["next_stage_tag"] = next_stage  # legacy compatibility
        else:
            state.pop("next_stage", None)
            state.pop("next_stage_tag", None)

        # --- 7️⃣ scene/state 갱신 ---
        state = state_tools.update_state(state, result, stage_tag)

        # --- 8️⃣ children_ctx 구성 ---
        if getattr(result, "stage_complete", False) and next_stage:
            log("codex_fix", "Stage complete; routing next stage", current=stage_tag, next=next_stage)
            state_tools.set_current_stage(state, next_stage)
            state_tools.reset_stage_turn(state)
            state_tools.get_scene_state(state)["stage_completed"] = True
            state["next_node"] = "router"
            return state

        children_ctx = dict(result.children_ctx)
        children_ctx.setdefault("stage_tag", stage_tag)
        children_ctx.setdefault("stage_type", scene_tools.get_stage_type(stage))
        children_ctx.setdefault("character_refs", scenario.get("character_refs", {}))
        children_ctx.setdefault("speaker_pool", stage.get("speaker_pool", []))
        children_ctx.setdefault("scenario_id", scenario.get("scenario_id", "mugen_train"))

        if fallback_payload and "fallback" not in children_ctx:
            children_ctx["fallback"] = fallback_payload

        state["children_ctx"] = children_ctx
        state["next_node"] = "children_agent"

        log("parent", f"→ Handed off to children_agent (stage={stage_tag}, type={stage.get('type')})")
        return state



    def after_dialogue(self, state: Dict[str, Any]) -> Dict[str, Any]:
        temp = state_tools.get_temp_data(state)
        if temp.pop("skip_parent_after_dialogue", False):
            log("parent", "Skipping post-dialogue hooks (guardrail intervention)")
            state["next_node"] = "wait_user_input"
            return state

        force_resume = temp.get("force_story_resume", False)

        scenario = scene_tools.resolve_scenario(state)
        scenario_module = self._load_scenario_module(scenario) if scenario else None
        completed_stage = self._consume_completed_stage(state)
        current_stage = state_tools.get_current_stage(state)

        if not force_resume:
            state_tools.increment_stage_turn(state)

        if completed_stage and scenario:
            stage_def = scene_tools.get_stage(scenario, completed_stage)
            if stage_def and scenario_module and hasattr(scenario_module, "on_stage_complete"):
                try:
                    scenario_module.on_stage_complete(state, stage_def, scenario)
                except Exception as exc:  # pragma: no cover - defensive
                    log("parent", f"on_stage_complete failed: {exc}", stage=completed_stage)

        next_stage = state_tools.consume_pending_stage(state)
        if next_stage and scenario:
            state_tools.set_current_stage(state, next_stage)
            state_tools.reset_stage_turn(state)
            next_def = scene_tools.get_stage(scenario, next_stage)
            if next_def:
                self._invoke_stage_enter(state, next_stage, next_def, scenario, scenario_module)

        if temp.pop("force_story_resume", False):
            return self._auto_continue(state)

        scene_state = state_tools.get_scene_state(state)
        if scene_state.get("stage_completed") and not temp.get("auto_resume_active"):
            log("codex_fix", "Auto-advancing completed stage", stage=state_tools.get_current_stage(state))
            return self._auto_continue(state)

        state["next_node"] = "router"
        return state

    # ----------------------------------------------------------------- helpers
    def _ensure_current_stage(self, state: Dict[str, Any], scenario: Dict[str, Any]) -> str:
        stage_tag = state_tools.get_current_stage(state)
        if stage_tag:
            return stage_tag
        stages = scene_tools.list_stages(scenario)
        if not stages:
            raise ValueError("Scenario does not define any stages")
        first_stage = stages[0]
        stage_tag = first_stage.get("tag") or first_stage.get("id") or "INTRO"
        state_tools.set_current_stage(state, stage_tag)
        state_tools.reset_stage_turn(state)
        return stage_tag

    def _resolve_handler(self, stage: Dict[str, Any]):
        stage_type = scene_tools.get_stage_type(stage)
        handler = self._handlers.get(stage_type)
        if handler:
            return handler
        log("parent", f"No handler registered for type '{stage_type}', using scene handler")
        return self._handlers["scene"]

    def _load_scenario_module(self, scenario: Optional[Dict[str, Any]]) -> Any:
        if not scenario:
            return None
        scenario_id = scenario.get("module_id") or scenario.get("scenario_id")
        if not scenario_id:
            return None
        module_key = str(scenario_id).replace("-", "_")
        if module_key in self._scenario_cache:
            return self._scenario_cache[module_key]
        module_name = f"src.scenarios.{module_key}"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            module = None
        self._scenario_cache[module_key] = module
        return module

    def _invoke_stage_enter(
        self,
        state: Dict[str, Any],
        stage_tag: str,
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
        scenario_module: Any,
    ) -> None:
        if state.pop("stage_forced_complete", False):
            log("codex_fix", "[FALLBACK-SHORTCUT] stage skip after auto-resume", stage=stage_tag)
            return

        reaction_config = self._get_reaction_config(state, scenario)
        if reaction_config.get("enabled", True) and state.get("last_user_choice") not in (None, "auto_resume"):
            self._generate_reaction_dialogue(state, scenario, reaction_config)
        last_stage = state_tools.get_last_stage_entered(state)
        if last_stage == stage_tag:
            return

        if stage_tag == "RETURN_TO_FRONT":
            narrative = self._compose_return_to_front_dialogue(state)
            output = state.setdefault("output", {})
            output.setdefault("dialogues", []).append(narrative)
            log("parent", f"[RETURN_TO_FRONT NARRATIVE] {narrative['text']}")

        if stage_tag in ("RETURN_TO_FRONT", "END_HIDDEN", "END_BASIC", "END_BAD"):
            allies = state.get("allies_recruited", [])
            dynamic_pool = list(stage.get("speaker_pool", []))
            for ally in allies:
                if ally not in dynamic_pool:
                    dynamic_pool.append(ally)
            if stage_tag == "END_BASIC":
                dynamic_pool = [speaker for speaker in dynamic_pool if speaker != "akaza"]
            elif stage_tag == "END_BAD":
                if "akaza" not in dynamic_pool:
                    dynamic_pool.append("akaza")
            stage["speaker_pool"] = dynamic_pool
            log("parent", f"[DYNAMIC SPEAKER] {stage_tag}: {dynamic_pool}")

        if stage_tag == "END_ROUTER":
            self._auto_determine_ending(state)

        if scenario_module and hasattr(scenario_module, "on_stage_enter"):
            try:
                scenario_module.on_stage_enter(state, stage, scenario)
            except Exception as exc:  # pragma: no cover - defensive
                log("parent", f"on_stage_enter failed: {exc}", stage=stage_tag)
        state_tools.mark_stage_entered(state, stage_tag)

    def _prepare_fallback(self, state: Dict[str, Any], stage: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        atmosphere = (stage.get("atmosphere") or "").lower()
        if atmosphere != "urgent":
            return None
        if state.get("stage_turn", 0) == 0:
            log("codex_fix", "Skip fallback on first turn", stage=stage.get("tag"))
            return None
        if not state.get("user_input"):
            log("codex_fix", "Skip fallback: no user input yet", stage=stage.get("tag"))
            return None
        if state.get("temp_data", {}).get("auto_resume_active"):
            log("codex_fix", "Skip fallback during auto-resume", stage=stage.get("tag"))
            return None
        return trigger_fallback(state, stage, reason="urgent_atmosphere")

    def _mark_stage_complete(self, state: Dict[str, Any], stage_tag: str, next_stage: Optional[str]) -> None:
        temp = state_tools.get_temp_data(state)
        temp["completed_stage"] = stage_tag
        state_tools.mark_pending_stage(state, next_stage)
        state_tools.mark_stage_completed(state, stage_tag)

    def _consume_completed_stage(self, state: Dict[str, Any]) -> Optional[str]:
        temp = state_tools.get_temp_data(state)
        return temp.pop("completed_stage", None)

    def _auto_continue(self, state: Dict[str, Any]) -> Dict[str, Any]:
        previous_dialogues = list(
            (state.get("output") or {}).get("dialogues", [])
        )

        auto_state = self._build_auto_continue_state(state)

        from src.core.workflow import get_workflow

        workflow = get_workflow()
        auto_result = workflow.invoke(auto_state)

        if previous_dialogues:
            auto_output = auto_result.setdefault("output", {})
            auto_dialogues = auto_output.get("dialogues") or []
            auto_output["dialogues"] = previous_dialogues + auto_dialogues

        auto_temp_result = state_tools.get_temp_data(auto_result)
        auto_temp_result.pop("force_story_resume", None)
        auto_temp_result.pop("skip_parent_after_dialogue", None)
        auto_temp_result.pop("auto_resume_active", None)
        auto_result["system_blocked"] = state.get("system_blocked", False)
        if not auto_result.get("system_blocked"):
            auto_result.pop("blocked_until", None)
        auto_result.pop("stage_forced_complete", None)

        log("parent", "Auto continue triggered after guardrail intervention")
        return auto_result

    def _build_auto_continue_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        auto_state: Dict[str, Any] = dict(state)

        def clone(key: str, default):
            value = state.get(key, default)
            try:
                auto_state[key] = deepcopy(value)
            except Exception:
                auto_state[key] = value

        clone("scene", {})
        clone("temp_data", {})
        clone("output", {})
        clone("agent_responses", [])
        clone("agent_inputs", {})
        clone("children_ctx", {})
        clone("message_history", [])
        clone("stage_states", {})
        clone("stage_history", [])
        clone("routing_result", {})
        clone("paths", {})

        auto_state["user_input"] = "__AUTO_CONTINUE__"
        auto_state["agent_responses"] = []
        auto_state["has_more_dialogues"] = False

        auto_temp = state_tools.get_temp_data(auto_state)
        auto_temp.pop("skip_parent_after_dialogue", None)
        auto_temp.pop("force_story_resume", None)
        auto_temp["auto_resume_active"] = True

        auto_state["off_topic_count"] = 0
        auto_output = auto_state.setdefault("output", {})
        auto_output["dialogues"] = []
        auto_state["system_blocked"] = False
        auto_state.pop("blocked_until", None)
        auto_state["stage_forced_complete"] = True
        scene = state_tools.get_scene_state(auto_state)
        scene["stage_completed"] = False
        return auto_state

    def _compose_return_to_front_dialogue(self, state: Dict[str, Any]) -> Dict[str, Any]:
        allies = state.get("allies_recruited", [])
        fails = state.get("recruit_failures", [])
        if allies and not fails:
            msg = f"좋아, {'와 '.join(allies)}를 모았어! 이제 렌고쿠 님을 도우러 가자!"
        elif allies and fails:
            msg = f"{'와 '.join(allies)}는 합류했지만, {', '.join(fails)}는 설득하지 못했어... 그래도 서두르자!"
        else:
            msg = "아무도 합류하지 못했어... 그래도 우리라도 어서 돌아가자!"
        return {"speaker": "tanjiro", "text": msg, "fx": "urgent_heartbeat|flame_flash"}

    def _auto_determine_ending(self, state: Dict[str, Any]) -> None:
        order = state.get("recruit_order", [])
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])

        max_attempts = 3
        if not allies:
            state["_outcome"] = "BAD"
            log("parent", "⚠️ reckless path triggered early — bad ending")
        elif order == ["inosuke", "zenitsu"] and \
                attempts.get("inosuke", 99) <= max_attempts and \
                attempts.get("zenitsu", 99) <= max_attempts:
            state["_outcome"] = "HIDDEN"
        else:
            state["_outcome"] = "BASIC"

        log(
            "parent",
            f"[END_ROUTER DECISION] Outcome={state.get('_outcome')}, Allies={allies}",
            attempts=attempts,
        )

    def _get_reaction_config(self, state: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
        config: Dict[str, Any] = {"enabled": True, "max_dialogues": 3}
        meta_value = (scenario.get("meta") or {}).get("reaction_mode")
        if isinstance(meta_value, dict):
            config.update(meta_value)
        elif isinstance(meta_value, bool):
            config["enabled"] = meta_value

        settings = state.get("settings") or {}
        state_reaction = settings.get("reaction_mode")
        if isinstance(state_reaction, dict):
            config.update(state_reaction)
        elif isinstance(state_reaction, bool):
            config["enabled"] = state_reaction
        return config

    def _generate_reaction_dialogue(
        self,
        state: Dict[str, Any],
        scenario: Dict[str, Any],
        reaction_config: Dict[str, Any],
    ) -> None:
        choice = state.get("last_user_choice")
        if not choice:
            return
        state["last_user_choice"] = None

        char_refs = scenario.get("character_refs", {})
        tone_profiles: Dict[str, Any] = {}
        base_dir = Path(__file__).resolve().parents[3]
        for name, rel_path in char_refs.items():
            rel_path_obj = Path(rel_path)
            if not rel_path_obj.is_absolute():
                rel_path_obj = base_dir / rel_path_obj
            tone_profiles[name] = self._load_character_tone(rel_path_obj)

        recent_dialogues = self._recent_dialogue_turns(state, limit=3)
        system_prompt = (
            "당신은 Demon Slayer 시나리오의 선택 반응 생성기입니다.\n"
            f"사용자가 '{choice}' 선택을 했습니다.\n"
            f"현재 시나리오 제목: \"{scenario.get('title', 'Unknown Scenario')}\".\n"
            "tone_profiles 정보를 참고하여 캐릭터들이 상황에 어울리는 감정으로 짧고 강렬하게 반응하도록 하세요.\n"
            "출력은 JSON 형식이어야 하며 아래 구조를 반드시 따르세요."
        )

        user_payload = {
            "tone_profiles": tone_profiles,
            "recent_dialogues": recent_dialogues,
            "choice": choice,
            "max_dialogues": reaction_config.get("max_dialogues", 3),
            "stage": state_tools.get_current_stage(state),
            "speaker_pool": (state.get("scene") or {}).get("speaker_pool"),
        }

        try:
            response = self._llm.call_json(
                system_prompt=system_prompt,
                user_prompt=json.dumps(user_payload, ensure_ascii=False),
                temperature=0.45,
                max_tokens=400,
            )
        except Exception as exc:  # pragma: no cover - defensive
            log("parent", f"[REACTION MODE] LLM call failed: {exc}", level=40)
            return

        if not isinstance(response, dict):
            return
        dialogues = response.get("dialogues")
        if not isinstance(dialogues, list):
            return

        max_count = int(reaction_config.get("max_dialogues", 3) or 3)
        trimmed = [d for d in dialogues if isinstance(d, dict)][:max_count]
        if not trimmed:
            return

        output_dialogues = state.setdefault("output", {}).setdefault("dialogues", [])
        for entry in trimmed:
            speaker = entry.get("speaker")
            text = entry.get("text")
            if not speaker or not text:
                continue
            output_dialogues.append(
                {"speaker": speaker, "text": text, "metadata": {"reaction_mode": True}}
            )
        log("parent", f"[REACTION MODE] {len(trimmed)} reaction lines generated")

    def _load_character_tone(self, path: Path) -> Dict[str, Any]:
        try:
            if not path.exists():
                return {}
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # pragma: no cover - defensive
            return {}

        if isinstance(data, dict):
            if isinstance(data.get("tone_profile"), dict):
                return data["tone_profile"]
            if isinstance(data.get("tone"), dict):
                return data["tone"]
            if isinstance(data.get("style"), dict):
                return data["style"]
            characters = data.get("characters")
            if isinstance(characters, dict):
                for entry in characters.values():
                    if isinstance(entry, dict) and isinstance(entry.get("tone_profile"), dict):
                        return entry["tone_profile"]
        return {}

    def _recent_dialogue_turns(self, state: Dict[str, Any], limit: int = 3) -> List[str]:
        history: List[str] = []
        output_dialogues = (state.get("output") or {}).get("dialogues") or []
        if isinstance(output_dialogues, list):
            for item in output_dialogues[-limit:]:
                if isinstance(item, dict):
                    history.append(f"{item.get('speaker', 'unknown')}: {item.get('text', '')}")

        agent_responses = state.get("agent_responses") or []
        if isinstance(agent_responses, list):
            for item in agent_responses[-limit:]:
                if isinstance(item, dict):
                    history.append(f"{item.get('speaker', 'unknown')}: {item.get('text', '')}")

        message_history = state.get("message_history") or []
        if isinstance(message_history, list):
            for entry in message_history[-limit:]:
                if isinstance(entry, dict):
                    speaker = entry.get("speaker") or entry.get("role")
                    content = entry.get("text") or entry.get("content")
                    if speaker and content:
                        history.append(f"{speaker}: {content}")
        return history[-limit:]

    def _handle_missing_scenario(self, state: Dict[str, Any]) -> Dict[str, Any]:
        log("parent", "Scenario data missing; emitting empty context")
        state_tools.set_children_ctx(state, {
            "stage_tag": "unknown",
            "stage_type": "scene",
            "speaker_pool": [],
            "beats": [],
        })
        state["next_node"] = "state_tools"
        return state

    def _handle_missing_stage(self, state: Dict[str, Any], stage_tag: str) -> Dict[str, Any]:
        log("parent", "Stage definition not found", stage=stage_tag)
        state_tools.set_children_ctx(state, {
            "stage_tag": stage_tag,
            "stage_type": "scene",
            "speaker_pool": [],
            "beats": [],
        })
        state["next_node"] = "state_tools"
        return state


DEFAULT_AGENT = ParentAgent()


def run_parent_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    return DEFAULT_AGENT.run(state)


def parent_after_dialogue(state: Dict[str, Any]) -> Dict[str, Any]:
    return DEFAULT_AGENT.after_dialogue(state)


__all__ = ["ParentAgent", "run_parent_agent", "parent_after_dialogue"]
