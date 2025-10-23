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
import time
from typing import Dict, Optional, Sequence

from .utils.embedding_matcher import EmbeddingMatcher, EmbeddingClient, get_embedding_client
from .utils.logger import log
from src.utils.spellcheck import get_spell_checker, SpellChecker


class GuardrailAgent:
    """Context-aware guardrail with character-driven fallbacks."""

    def __init__(self) -> None:
        self._embedding_client: EmbeddingClient = get_embedding_client()
        self._prohibited_matcher = EmbeddingMatcher(
            {
                "self_harm": ["자살", "자해"],
                "sexual": ["강간", "성폭행", "음란", "sex", "섹스", "자지", "보지"],
                "system_intrusion": ["시스템 : ","관리자","system override", "보안 해제"],
            },
            threshold=0.85,
            embedding_client=self._embedding_client,
        )
        self._spell_checker: SpellChecker = get_spell_checker()

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_input = (state.get("user_input") or "").strip()

        if user_input.startswith("__AUTO_CONTINUE__"):
            return self._pass(state)

        if self._is_currently_blocked(state):
            return self._enforce_block(state)

        user_input = self._run_spellcheck(state, user_input)
        user_embedding = self._get_user_embedding(state, user_input)

        if self._contains_prohibited(state, user_input, embedding=user_embedding):
            return self._handle_prohibited(state)

        return self._pass(state)

    # ------------------------------------------------------------------ helpers
    def _ensure_temp(self, state: Dict[str, Any]) -> Dict[str, Any]:
        temp = state.get("temp_data")
        if isinstance(temp, dict):
            return temp
        state["temp_data"] = {}
        return state["temp_data"]

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
        message = "[꺾쇠 까마귀]⛔️ 부적절한 발언으로 10분 동안 대화가 제한됩니다."
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
            message = "[꺾쇠 까마귀]🚨 부적절한 표현입니다. 이번만 경고합니다."
            state["prohibited_warning_count"] = 1
            self._inject_dialogue(state, speaker="system", text=message)
            self._ensure_temp(state)["skip_parent_after_dialogue"] = True
            state["guardrail_result"] = {"status": "warning", "reason": "prohibited"}
            state["system_message"] = message
            log("guardrail", "Prohibited content warning issued")
            return state

        message = "[꺾쇠 까마귀]⛔️ 부적절한 발언으로 10분 동안 대화가 제한됩니다."
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

    def _pass(self, state: Dict[str, Any]) -> Dict[str, Any]:
        state.pop("agent_responses", None)
        temp = self._ensure_temp(state)
        temp.pop("skip_parent_after_dialogue", None)
        state["guardrail_result"] = {"status": "passed", "reason": "clean"}
        state["next_node"] = "router"
        log("guardrail", "Input passed")
        return state

    def _run_spellcheck(self, state: Dict[str, Any], text: str) -> str:
        if not text:
            state["user_input"] = ""
            state["spellcheck_result"] = {"has_typo": False, "corrected": None, "notes": None}
            return ""

        result = self._spell_checker.check(text)
        state["spellcheck_result"] = result

        corrected = (result.get("corrected") or "").strip() if isinstance(result, dict) else ""
        if result.get("has_typo") and corrected:
            state.setdefault("spellcheck_original", text)
            state["user_input"] = corrected
            log("guardrail", "typo_corrected", original=text, corrected=corrected)
            return corrected

        # 보정이 없으면 원본을 그대로 사용 (불필요한 공백 제거)
        normalized = text.strip()
        state["user_input"] = normalized
        if result.get("has_typo"):
            log("guardrail", "typo_detected", corrected=result.get("corrected"))
        return normalized

    def _get_user_embedding(self, state: Dict[str, Any], text: str) -> Optional[Sequence[float]]:
        cache = state.setdefault("_embedding_cache", {})
        cached_text = cache.get("text")
        cached_vector = cache.get("vector")
        if cached_text == text and cached_vector:
            return cached_vector
        vector = self._embedding_client.embed(text)
        cache["text"] = text
        cache["vector"] = vector
        return vector

    def _contains_prohibited(
        self,
        state: Dict[str, Any],
        text: str,
        *,
        embedding: Optional[Sequence[float]] = None,
    ) -> bool:
        if not text:
            return False
        result = self._prohibited_matcher.match(text, embedding=embedding)
        if result.label:
            state.setdefault("guardrail_debug", {})["prohibited_match"] = {
                "label": result.label,
                "score": round(result.score, 4),
            }
            log(
                "guardrail",
                "Prohibited match detected",
                label=result.label,
                score=round(result.score, 4),
                threshold=self._prohibited_matcher.threshold,
            )
            return True
        return False

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
