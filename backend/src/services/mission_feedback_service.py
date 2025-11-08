"""
============================================================
💬 Mission Feedback Service — 미션 피드백 생성
============================================================
미션 결과에 대한 피드백 메시지와 전환 대사를 생성합니다.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.tools.scene_tools import get_i18n_entries
from src.utils.logger import log


class MissionFeedbackService:
    """
    미션 피드백 서비스

    책임:
    - 피드백 beats 생성
    - 전환 대사 생성
    - 완료 메시지 생성
    """

    MAX_ATTEMPTS = 3
    VALID_TARGETS = ("inosuke", "zenitsu")
    CHARACTER_NAMES_KR = {
        "inosuke": "이노스케",
        "zenitsu": "젠이츠",
        "tanjiro": "탄지로",
        "nezuko": "네즈코",
    }

    def __init__(self, locale: str = "ko"):
        """
        Args:
            locale: 로케일 (기본값: "ko")
        """
        self.locale = locale

    def build_feedback_beats(
        self,
        state: Dict[str, Any],
        character: str,
        success: bool,
        scenario: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        피드백 beats 생성

        Args:
            state: 전체 state 객체
            character: 캐릭터 ID
            success: 설득 성공 여부
            scenario: 시나리오 데이터

        Returns:
            피드백 beats 리스트
        """
        char_display = self.CHARACTER_NAMES_KR.get(character.lower(), character.capitalize())

        temp_status = state.get("temp_data", {}).get("last_mission_status") or {}
        attempts_map = state.get("recruit_attempts", {})
        current_attempt = attempts_map.get(character, 0)
        remaining = temp_status.get("remaining")
        if remaining is None:
            remaining = max(0, self.MAX_ATTEMPTS - current_attempt)

        attempt_ratio = f"{current_attempt}/{self.MAX_ATTEMPTS}"

        # 시스템 메시지 생성
        if success:
            sys_text = f"{char_display} 🎉 설득 성공! 🎉 ({attempt_ratio})"
            fx = "ui_confirm|success_chime"
        else:
            remaining_note = f" 남은 시도 {remaining}회" if remaining is not None else ""
            sys_text = f"⏰ {char_display} 설득 실패... ({attempt_ratio}){remaining_note}"
            fx = "ui_alert|heartbeat_slow"

        sys_entry = {
            "text": sys_text,
            "goal": sys_text,
            "speaker": "system",
            "fx": fx,
        }

        # 피드백 beats 로드
        feedback_key = (
            f"beats_feedback_success_{character}"
            if success
            else f"beats_feedback_fail_{character}"
        )

        if not success and remaining == 0:
            alt_key = f"beats_feedback_fail_{character}_end"
            alt_beats = get_i18n_entries(scenario, alt_key, locale=self.locale)
            if alt_beats:
                feedback_key = alt_key

        feedback_beats = self._to_dialogues(
            get_i18n_entries(scenario, feedback_key, locale=self.locale)
        )

        dialogues = list(feedback_beats)
        dialogues.append(sys_entry)

        # 최대 시도 소진 시 추가 메시지
        if not success and remaining == 0:
            exhaustion = {
                "speaker": "system",
                "text": "⚠️ 모든 시도를 소진했습니다. 다른 방법을 찾아야 합니다.",
                "goal": "⚠️ 모든 시도를 소진했습니다. 다른 방법을 찾아야 합니다.",
            }
            dialogues.append(exhaustion)
            log("mission_feedback", "Mission attempts exhausted", character=character)

        # 전환 대사 추가: 캐릭터 미션이 완전히 끝났을 때만 출력
        final_transition_needed = success or (not success and remaining == 0)
        if final_transition_needed:
            # 다음 타겟을 위해 외부에서 제공되어야 함
            # 여기서는 None으로 설정하고, Handler에서 추가 처리
            pass

        return dialogues

    def build_transition_line(
        self,
        mission_result: str,
        completed_ally: str,
        next_target: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        전환 대사 생성

        Args:
            mission_result: "success" 또는 "fail"
            completed_ally: 완료된 캐릭터 표시 이름
            next_target: 다음 타겟 표시 이름

        Returns:
            전환 대사 dict 또는 None
        """
        if mission_result not in {"success", "fail"}:
            return None

        if next_target:
            if mission_result == "success":
                text = f"탄지로: {completed_ally}를 데려오는 데 성공했어! 이제 {next_target}를 찾으러 가자."
            else:
                text = f"탄지로: {completed_ally}를 설득하지 못했어... 그래도 포기할 순 없어. 이번엔 {next_target}를 찾아보자."
        else:
            if mission_result == "success":
                text = f"탄지로: {completed_ally}를 데려오는 데 성공했어! 이제 전장으로 돌아가자."
            else:
                text = f"탄지로: {completed_ally}를 설득하지 못했어... 그래도 포기할 순 없어. 다른 길을 찾아보자."

        log("mission_feedback", text)
        return {
            "speaker": "tanjiro",
            "text": text,
            "goal": text,
        }

    def generate_mission_complete_message(self, allies: List[str]) -> str:
        """
        미션 완료 메시지 생성

        Args:
            allies: 합류한 동료 리스트

        Returns:
            완료 메시지
        """
        if not allies:
            return "동료를 더 설득할 시간이 없습니다. 곧바로 전장으로 돌아가야 해요!"

        converted_names = [self.CHARACTER_NAMES_KR.get(name, name) for name in allies]

        if len(converted_names) == 1:
            ally_text = converted_names[0]
        elif len(converted_names) == 2:
            ally_text = f"{converted_names[0]}와 {converted_names[1]}"
        else:
            ally_text = ", ".join(converted_names[:-1]) + f" 그리고 {converted_names[-1]}"

        return f"{ally_text}가 모두 합류했어요! 이제 바로 전장으로 돌아가 렌고쿠 님을 도와요!"

    def _to_dialogues(self, beats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Beats를 대화 형식으로 변환

        Args:
            beats: Beats 리스트

        Returns:
            대화 리스트
        """
        dialogues = []
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

                entry = dict(beat)
                entry["text"] = text
                entry["speaker"] = speaker or "narr"
                entry.setdefault("goal", beat.get("goal") or text)
                dialogues.append(entry)
            else:
                text = str(beat)
                dialogues.append({"text": text, "speaker": "narr", "goal": text})

        return dialogues


__all__ = ["MissionFeedbackService"]
