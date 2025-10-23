from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.utils.llm_client import get_llm_client

from ..scene_tools import (
    get_i18n_entries,
    get_next_stage_tag,
    get_stage_type,
    get_speaker_pool,
)
from ..utils.fallback import trigger_fallback
from ..utils.logger import log
from ..utils.text_matcher import detect_mission_target
from . import StageResult


class MissionHandler:
    """LLM 기반 동료 영입 미션 처리기"""

    MAX_ATTEMPTS = 3

    def __init__(self, locale: str = "ko", llm: Any = None):
        self.locale = locale
        self._llm = llm

    def handle(self, state: Dict[str, Any], stage: Dict[str, Any], scenario: Dict[str, Any]) -> StageResult:
        stage_tag = stage.get("tag") or stage.get("id") or "mission"
        speaker_pool = get_speaker_pool(stage, stage.get("speaker_pool", []))
        user_input = (state.get("user_input") or "").strip()

        target = detect_mission_target(user_input)
        if target not in ("inosuke", "zenitsu"):
            fallback_payload = trigger_fallback(state, stage, reason="invalid_target")
            beats_smell = self._to_dialogues(
                get_i18n_entries(scenario, "beats_smell", locale=self.locale)
            )
            fallback_dialogues = fallback_payload.setdefault("dialogues", [])
            fallback_dialogues.extend(beats_smell)
            children_ctx = {
                "stage_tag": stage_tag,
                "stage_type": get_stage_type(stage),
                "speaker_pool": speaker_pool,
                "beats": [],
                "fallback": {"dialogues": fallback_dialogues},
                "atmosphere": stage.get("atmosphere"),
            }
            log("mission", f"[FALLBACK] ambiguous target on {stage_tag}", user_input=user_input)
            return StageResult(children_ctx=children_ctx, fallback_payload=fallback_payload)

        self._increment_attempt(state, target)
        success = self._evaluate_recruit_attempt_llm(state, target)
        self._update_recruit_result(state, target, success)

        feedback_beats = self._build_feedback_beats(state, target, success, scenario)
        children_ctx = {
            "stage_tag": stage_tag,
            "stage_type": get_stage_type(stage),
            "speaker_pool": speaker_pool,
            "beats": feedback_beats,
            "atmosphere": stage.get("atmosphere"),
            "mission": {
                "target": target,
                "success": success,
                "attempts": state.get("recruit_attempts", {}).get(target, 0),
            },
        }

        stage_complete = self._all_missions_resolved(state)
        next_stage = None
        if stage_complete:
            next_stage = stage.get("next") or get_next_stage_tag(stage) or "RETURN_TO_FRONT"
            log(
                "mission",
                f"[RESOLVED] stage={stage_tag}, next={next_stage}",
                recruited=state.get("allies_recruited"),
                attempts=state.get("recruit_attempts"),
            )
        else:
            log(
                "codex_fix",
                "Mission still in progress",
                stage=stage_tag,
                target=target,
            )

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage,
        )

    # ------------------------------------------------------------------ helpers
    def _increment_attempt(self, state: Dict[str, Any], character: str) -> None:
        attempts = state.setdefault("recruit_attempts", {})
        attempts[character] = attempts.get(character, 0) + 1

        order = state.setdefault("recruit_order", [])
        if character not in order:
            order.append(character)

# 임베딩, 키워드 매핑보다 llm 붙임
    def _evaluate_recruit_attempt_llm(self, state: Dict[str, Any], target: str) -> bool:
        client = self._llm or get_llm_client()
        user_text = state.get("user_input", "")
        system_prompt = (
            "You are a mission adjudicator for a Demon Slayer interactive story. "
            "Return only True or False to indicate whether the recruitment attempt succeeded."
        )
        user_prompt = f"""
현재 캐릭터는 '{target}'을 설득하려고 한다.

플레이어의 대사: "{user_text}"

판정 기준:
- 젠이츠(Zenitsu)는 '네즈코', '사랑', '지켜야 해', '위험해' 같은 감정적 키워드나 설득 문맥이 포함되면 성공.
- 이노스케(Inosuke)는 '겁쟁이', '약하다', '싸우자', '도전해' 같은 도발성 발화가 있으면 성공.
- 그 외엔 실패.

성공이면 True, 실패면 False 만 출력해.
"""
        try:
            result = client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0,
                max_tokens=5,
            )
            decision = "true" in (result or "").lower()
            log("mission", f"[LLM DECISION] target={target} → {'SUCCESS' if decision else 'FAIL'}")
            return decision
        except Exception as exc:  # pragma: no cover - defensive
            log("mission", f"[LLM ERROR] fallback heuristic used: {exc}", level=40)
            return self._heuristic_fallback(user_text, target)

    def _heuristic_fallback(self, text: str, target: str) -> bool:
        lowered = (text or "").lower()
        if target == "zenitsu":
            return any(keyword in lowered for keyword in ["네즈코", "사랑", "지켜", "위험"])
        if target == "inosuke":
            return any(keyword in lowered for keyword in ["겁쟁", "약하", "싸우", "도전", "멧돼"])
        return False

    def _update_recruit_result(self, state: Dict[str, Any], character: str, success: bool) -> None:
        attempts = state.get("recruit_attempts", {}).get(character, 0)
        remaining = max(0, self.MAX_ATTEMPTS - attempts)

        if success:
            allies = state.setdefault("allies_recruited", [])
            if character not in allies:
                allies.append(character)
        else:
            fails = state.setdefault("recruit_failures", [])
            if character not in fails:
                fails.append(character)

        sys_text = (
            f"{character} 설득 성공!"
            if success
            else f"{character} 설득 실패... 남은 시도 {remaining}회"
        )
        state.setdefault("temp_data", {})["last_mission_status"] = {
            "target": character,
            "success": success,
            "remaining": remaining,
        }
        log(
            "mission",
            f"[RESULT] {character} → {'SUCCESS' if success else 'FAIL'}",
            attempts=state.get("recruit_attempts"),
            allies=state.get("allies_recruited"),
            failures=state.get("recruit_failures"),
        )

    def _build_feedback_beats(
        self,
        state: Dict[str, Any],
        character: str,
        success: bool,
        scenario: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        temp_status = state.get("temp_data", {}).get("last_mission_status") or {}
        remaining = temp_status.get("remaining")
        sys_entry: Dict[str, Any] = {
            "text": (
                f"{character.capitalize()} 설득 성공!"
                if success
                else f"{character.capitalize()} 설득 실패... 남은 시도 {remaining}회"
            ),
            "speaker": "system",
            "fx": "ui_confirm|success_chime" if success else "ui_alert|heartbeat_slow",
        }

        feedback_key = (
            f"beats_feedback_success_{character}"
            if success
            else f"beats_feedback_fail_{character}"
        )
        feedback_beats = self._to_dialogues(
            get_i18n_entries(scenario, feedback_key, locale=self.locale)
        )
        dialogues = [sys_entry] + feedback_beats
        if remaining is not None:
            if remaining > 0:
                dialogues.append(
                    {"speaker": "system", "text": f"남은 시도 횟수: {remaining}회"}
                )
                log("codex_fix", "Mission attempts remaining", character=character, remaining=remaining)
            else:
                dialogues.append(
                    {"speaker": "system", "text": "모든 시도를 소진했습니다. 임무 종료로 전환합니다."}
                )
                log("codex_fix", "Mission attempts exhausted", character=character)
        return dialogues

    def _to_dialogues(self, beats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        dialogues: List[Dict[str, Any]] = []
        for beat in beats:
            if isinstance(beat, dict):
                text = beat.get("text") or beat.get("goal") or ""
                if not text:
                    continue
                speaker = beat.get("speaker")
                if not speaker:
                    hints = beat.get("speaker_hint")
                    if isinstance(hints, list) and hints:
                        speaker = hints[0]
                dialogues.append(
                    {
                        "text": text,
                        "speaker": speaker or "narr",
                        **{k: v for k, v in beat.items() if k == "fx"},
                    }
                )
            else:
                dialogues.append({"text": str(beat), "speaker": "narr"})
        return dialogues

    def _all_missions_resolved(self, state: Dict[str, Any]) -> bool:
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])
        for character in ("inosuke", "zenitsu"):
            if character in allies:
                continue
            if attempts.get(character, 0) >= self.MAX_ATTEMPTS:
                continue
            return False
        return True
