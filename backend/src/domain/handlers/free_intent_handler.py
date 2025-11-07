# ============================================================
# 🎛️ 자유 의도 핸들러 — 라우터 의도에 따른 분기 처리
# ============================================================
from __future__ import annotations

from typing import Any, Dict, Optional

# ============================================================
# ============================================================

from src.domain.services.orchestration import state_tools
from src.domain.services.orchestration.scene_tools import (
    get_next_stage_tag,
    get_stage_atmosphere,
    get_stage_beats,
    get_stage_type,
    get_speaker_pool,
)
import logging
log = logging.getLogger(__name__)
from . import StageResult


class FreeIntentHandler:
    """Handle choice-heavy stages that depend on router intents."""

    def __init__(self, locale: str = "ko"):
        self.locale = locale

    def handle(self, state: Dict[str, Any], stage: Dict[str, Any], scenario: Dict[str, Any]) -> StageResult:
        # ========================================================
        # ========================================================
        stage_tag = stage.get("tag") or stage.get("id") or "free_intent"
        stage_turn = int(state.get("stage_turn", 0) or 0)
        scene_state = state_tools.get_scene_state(state)
        speaker_pool = get_speaker_pool(stage, scene_state.get("speaker_pool", []))
        beats = get_stage_beats(stage, scenario, locale=self.locale)

        intent = self._extract_intent(state)
        option_result = self._match_action(stage, intent)

        if option_result and option_result.get("set"):
            self._apply_set_operations(state, option_result["set"])

        stage_complete = bool(option_result)
        next_stage = option_result.get("goto") if stage_complete else None

        # 🔥 이지만 선택을 안 한 경우: 선택 재요청 대사만 생성
        if not stage_complete and intent and intent in ["on_topic_generic", "on_topic"] and stage_turn >= 1:
            log("free_intent", "⚠️ On-topic but no choice made → generating choice reminder", stage_tag=stage_tag, intent=intent)
            reminder_beat = self._create_choice_reminder_beat(state, stage)
            ctx = {
                "stage_tag": stage_tag,
                "stage_type": "choice_reminder",  # LLM에게 선택 재요청 모드임을 알림
                "speaker_pool": speaker_pool,
                "beats": [reminder_beat],
                "atmosphere": get_stage_atmosphere(stage),
            }
            return StageResult(children_ctx=ctx, stage_complete=False, next_stage=None)

        if not stage_complete:
            turn_cap = int((stage.get("constraints") or {}).get("max_turns", 0) or 0)
            current_turn = int(state.get("stage_turn", 0) or 0)
            if turn_cap and current_turn >= turn_cap:
                stage_complete = True
                next_stage = get_next_stage_tag(stage)

        ctx = {
            "stage_tag": stage_tag,
            "stage_type": get_stage_type(stage),
            "speaker_pool": speaker_pool,
            "beats": beats,
            "free_intent": {
                "actions": stage.get("llm_actions", []),
                "matched_intent": intent,
            },
            "atmosphere": get_stage_atmosphere(stage),
        }

        if stage_complete and not next_stage:
            next_stage = get_next_stage_tag(stage)

        if stage_complete:
            log("free_intent", "Intent resolved", stage_tag=stage_tag, intent=intent, next_stage=next_stage)
        return StageResult(children_ctx=ctx, stage_complete=stage_complete, next_stage=next_stage)

    def _extract_intent(self, state: Dict[str, Any]) -> Optional[str]:
        # ----------------------------------------
        # ----------------------------------------
        temp = state_tools.get_temp_data(state)
        if temp.get("intent"):
            return str(temp.get("intent")).lower()
        sticky = temp.get("sticky_intent")
        if sticky:
            return str(sticky).lower()
        routing = state.get("routing_result") or {}
        candidate = routing.get("intent") or routing.get("classification")
        if candidate:
            return str(candidate).lower()
        user_intent = state.get("user_intent")
        return str(user_intent).lower() if user_intent else None

    def _match_action(self, stage: Dict[str, Any], intent: Optional[str]) -> Optional[Dict[str, Any]]:
        # ----------------------------------------
        # ----------------------------------------
        if not intent:
            return None

        intent_mapping = stage.get("intent_mapping", {})
        if intent in intent_mapping:
            next_stage = intent_mapping[intent]
            return {"goto": next_stage}

        for entry in stage.get("on_action", []):
            action = entry.get("action")
            if isinstance(action, str) and action.lower() == intent:
                return entry
        return None

    def _create_choice_reminder_beat(self, state: Dict[str, Any], stage: Dict[str, Any]) -> Dict[str, Any]:
        """
        선택을 하지 않은 경우 LLM이 선택을 재요청하는 beat 생성
        """
        user_input = state.get("user_input", "")
        choices = stage.get("choices", [])
        objective = stage.get("objective", "")

        # 선택지 텍스트 추출
        choice_texts = []
        for choice in choices:
            if isinstance(choice, dict):
                text = choice.get("text", "")
                if text:
                    choice_texts.append(text)

        choices_str = " / ".join(choice_texts) if choice_texts else "결정"

        speaker_pool = stage.get("speaker_pool", [])
        main_speaker = speaker_pool[0] if speaker_pool else "tanjiro"

        beat = {
            "goal": (
                f"{{{{user}}}}가 '{user_input}'라고 말했습니다. "
                f"{main_speaker}는 {{{{user}}}}의 말에 먼저 짧게 반응하거나 답변합니다. "
                f"그리고 지금은 빠르게 결정해야 한다며 자연스럽게 선택지로 유도합니다: {choices_str}. "
                f"목표: {objective}"
            ),
            "speaker_hint": [main_speaker],
            "objective": objective,
            "choices": choice_texts,
            "user_context": user_input,  # LLM이 유저 입력을 참고할 수 있도록
        }

        log("free_intent", "📝 Created choice reminder beat", speaker=main_speaker, choices_count=len(choice_texts), user_input=user_input)
        return beat

    def _apply_set_operations(self, state: Dict[str, Any], operations: Dict[str, Any]) -> None:
        # ----------------------------------------
        # ----------------------------------------
        for key, value in operations.items():
            increment = None
            if isinstance(value, dict):
                if "$inc" in value:
                    increment = value.get("$inc")
                elif "${inc}" in value:
                    increment = value.get("${inc}")
            if increment is not None:
                current = state_tools.read_value(state, key, 0)
                try:
                    new_value = float(current) + float(increment)
                except (TypeError, ValueError):
                    new_value = increment
                state_tools.store_value(state, key, new_value)
                continue
            state_tools.store_value(state, key, value)
