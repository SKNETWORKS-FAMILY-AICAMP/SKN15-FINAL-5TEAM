'''
🧍 User Input
   ↓
🛡️ GuardrailAgent
   ├─ [성적/폭력 표현] → 시스템 경고 (1회) / 차단 (2회) (차단은 프론트 단에서 대화창 비활성화)
   ├─ [오프토픽] → off_topic_count++
   │     ├─ (허용 범위 이내) → fallback LLM으로 보냄 -> 자연스러운 대화하면서 스토리로 유도
   │     └─ (허용 초과) → “⚠️ 집중하세요. 시나리오로 복귀합니다.” 출력 -> 강제 선택(auto_choice)
   └─ [정상 입력] → Router로 전달 (on_topic)
   '''

from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

from .utils.fallback_llm import generate_off_topic_response
from .utils.logger import log


class GuardrailAgent:
    """Context-aware guardrail with character-driven fallbacks."""

    def __init__(self) -> None:
        self._prohibited_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in [
                "자살",
                "죽여",
                "강간",
                "음란",
                "sexual",
                "kill myself",
            ]
        ]
        self._off_topic_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in [
                "숙제",
                "게임",
                "학교",
            ]
        ]

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_input = (state.get("user_input") or "").strip()

        if user_input.startswith("__AUTO_CONTINUE__"):
            return self._pass(state, reset_off_topic=True)

        if self._is_currently_blocked(state):
            return self._enforce_block(state)

        if self._contains_prohibited(user_input):
            return self._handle_prohibited(state)

        if self._is_off_topic(user_input):
            return self._handle_off_topic(state, user_input)

        return self._pass(state, reset_off_topic=True)

    # ------------------------------------------------------------------ helpers
    def _ensure_temp(self, state: Dict[str, Any]) -> Dict[str, Any]:
        temp = state.get("temp_data")
        if isinstance(temp, dict):
            return temp
        state["temp_data"] = {}
        return state["temp_data"]

    def _ensure_routing(self, state: Dict[str, Any], *, intent: str) -> Dict[str, Any]:
        routing = state.get("routing_result")
        if not isinstance(routing, dict):
            routing = {}
            state["routing_result"] = routing
        routing["intent"] = intent
        routing["classification"] = "on_topic"
        return routing

    def _is_currently_blocked(self, state: Dict[str, Any]) -> bool:
        if not state.get("system_blocked"):
            return False
        blocked_until = float(state.get("blocked_until") or 0.0)
        if blocked_until <= time.time():
            state["system_blocked"] = False
            state.pop("blocked_until", None)
            return False
        return True

    def _enforce_block(self, state: Dict[str, Any]) -> Dict[str, Any]:
        message = "⛔️ 부적절한 발언으로 10분 동안 대화가 제한됩니다."
        self._inject_dialogue(state, speaker="system", text=message)
        self._ensure_temp(state)["skip_parent_after_dialogue"] = True
        state["guardrail_result"] = {"status": "blocked", "reason": "timeout"}
        state["system_message"] = message
        log("guardrail", "User input rejected (timer active)")
        return state

    def _handle_prohibited(self, state: Dict[str, Any]) -> Dict[str, Any]:
        warnings = int(state.get("prohibited_warning_count", 0))
        now = time.time()
        if warnings == 0:
            message = "🚨 부적절한 표현입니다. 이번만 경고합니다."
            state["prohibited_warning_count"] = 1
            self._inject_dialogue(state, speaker="system", text=message)
            self._ensure_temp(state)["skip_parent_after_dialogue"] = True
            state["guardrail_result"] = {"status": "warning", "reason": "prohibited"}
            state["system_message"] = message
            log("guardrail", "Prohibited content warning issued")
            return state

        message = "⛔️ 부적절한 발언으로 10분 동안 대화가 제한됩니다."
        state["system_blocked"] = True
        state["blocked_until"] = now + 600
        state["prohibited_warning_count"] = warnings + 1
        self._inject_dialogue(state, speaker="system", text=message)
        self._ensure_temp(state)["skip_parent_after_dialogue"] = True
        state["guardrail_result"] = {"status": "blocked", "reason": "prohibited"}
        state["system_message"] = message
        log(
            "guardrail",
            "User blocked for prohibited content",
            blocked_until=state["blocked_until"],
        )
        return state

    def _handle_off_topic(self, state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        count = int(state.get("off_topic_count", 0)) + 1
        state["off_topic_count"] = count

        scene = state.get("scene") or {}
        atmosphere = (scene.get("atmosphere") or "normal").lower()
        max_allowed = 3 if atmosphere == "normal" else 1

        log("guardrail", "off_topic_detected", count=count, atmosphere=atmosphere)

        if count <= max_allowed:
            fallback_response = generate_off_topic_response(state, user_input)
            if fallback_response:
                self._inject_dialogue(
                    state,
                    speaker=fallback_response.get("speaker", "system"),
                    text=fallback_response.get("text", ""),
                    metadata=fallback_response,
                )
            else:
                self._inject_dialogue(
                    state,
                    speaker="system",
                    text="지금은 임무에 집중해야 해요. 이야기는 나중에 이어가요.",
                )
            state["guardrail_result"] = {"status": "handled", "reason": "off_topic"}
            temp = self._ensure_temp(state)
            temp["skip_parent_after_dialogue"] = True
            return state

        # Exceeded allowance
        state["off_topic_count"] = 0
        message = "⚠️ 집중하세요. 시나리오로 복귀합니다."
        self._inject_dialogue(state, speaker="system", text=message)
        state["guardrail_result"] = {"status": "force_resume", "reason": "off_topic_limit"}
        state["system_message"] = message
        self._ensure_routing(state, intent="on_topic")
        temp = self._ensure_temp(state)
        temp["skip_parent_after_dialogue"] = False
        temp["force_story_resume"] = True
        log("guardrail", "Off-topic limit exceeded; forcing resume")
        return state

    def _pass(self, state: Dict[str, Any], *, reset_off_topic: bool = False) -> Dict[str, Any]:
        if reset_off_topic:
            state["off_topic_count"] = 0
        state.pop("agent_responses", None)
        temp = self._ensure_temp(state)
        temp.pop("skip_parent_after_dialogue", None)
        state["guardrail_result"] = {"status": "passed", "reason": "clean"}
        state["next_node"] = "router"
        log("guardrail", "Input passed")
        return state

    def _contains_prohibited(self, text: str) -> bool:
        if not text:
            return False
        return any(pattern.search(text) for pattern in self._prohibited_patterns)

    def _is_off_topic(self, text: str) -> bool:
        if not text:
            return False
        return any(pattern.search(text) for pattern in self._off_topic_patterns)

    def _inject_dialogue(
        self,
        state: Dict[str, Any],
        *,
        speaker: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "speaker": speaker,
            "text": text,
            "order": 0,
        }
        if metadata:
            for key, value in metadata.items():
                payload.setdefault(key, value)

        state["agent_responses"] = [payload]
        state["has_more_dialogues"] = False
        state["next_node"] = "dialogue_agent"
        temp = self._ensure_temp(state)
        temp.setdefault("skip_parent_after_dialogue", False)


DEFAULT_AGENT = GuardrailAgent()


def run_guardrail_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    return DEFAULT_AGENT.run(state)


__all__ = ["GuardrailAgent", "run_guardrail_agent"]
