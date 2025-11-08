"""
============================================================
📝 Dialogue Formatter Service — 대사 정규화 및 렌더링
============================================================
다양한 형식의 대사 데이터를 표준 형식으로 정규화하고,
플레이어 이름 등의 변수를 치환하여 최종 대사를 렌더링합니다.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List


class DialogueFormatterService:
    """
    대사 정규화 및 렌더링 서비스

    책임:
    - 다양한 형식의 대사를 표준 형식으로 정규화
    - 플레이어 이름 등의 변수 치환
    - goal 텍스트에서 대사 추출
    """

    def normalize_dialogues(self, entries: List[Any]) -> List[Dict[str, Any]]:
        """
        다양한 형식의 대사 데이터를 표준 형식으로 정규화

        Args:
            entries: 대사 데이터 리스트 (dict, str 등 다양한 형식)

        Returns:
            표준 형식의 대사 리스트 [{"speaker": "...", "text": "...", "fx": ...}, ...]
        """
        normalized: List[Dict[str, Any]] = []
        for entry in entries:
            if isinstance(entry, dict):
                text = (
                    entry.get("text")
                    or entry.get("line")
                    or entry.get("goal")
                    or entry.get("description")
                )
                speaker = entry.get("speaker")
                if not speaker:
                    hints = entry.get("speaker_hint")
                    if isinstance(hints, list) and hints:
                        speaker = hints[0]

                # 🔥 goal에서 따옴표 안의 대사 추출
                if not entry.get("text") and text:
                    text = self.extract_dialogue_from_goal(text, speaker or "narr")

                normalized.append(
                    {
                        "speaker": (speaker or "narr"),
                        "text": text or json.dumps(entry, ensure_ascii=False),
                        "fx": entry.get("fx"),
                    }
                )
            else:
                normalized.append({"speaker": "narr", "text": str(entry)})
        return normalized

    def extract_dialogue_from_goal(self, goal: str, speaker: str) -> str:
        """
        goal 텍스트에서 따옴표 안의 대사를 추출하여 자연스럽게 만듦

        예: "탄지로가 말한다. '이노스케! 지금은 싸움이 아니야!'"
            → "이노스케! 지금은 싸움이 아니야!"

        Args:
            goal: 원본 goal 텍스트
            speaker: 화자 ID

        Returns:
            추출된 대사 또는 원본 텍스트
        """
        # 따옴표 안의 대사 찾기 (', ", 「」 모두 지원)
        quotes_pattern = r"['\"\「]([^'\"」]+)['\"\」]"
        matches = re.findall(quotes_pattern, goal)

        if matches:
            # 대사를 찾았으면 그것을 반환 (여러 개면 합침)
            dialogue = " ".join(matches)

            # narr(내레이션)인 경우 goal 전체 사용 (상황 묘사)
            if speaker == "narr":
                # 【 】 안의 상황 태그 제거
                cleaned = re.sub(r"【[^】]+】\s*", "", goal)
                return cleaned.strip()

            return dialogue.strip()

        # 대사를 못 찾았으면 goal 그대로 반환
        return goal

    def render_dialogues(self, state: Dict[str, Any], entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        대사 리스트의 텍스트를 렌더링 (변수 치환)

        Args:
            state: 전체 state 객체 (user_name 등 포함)
            entries: 렌더링할 대사 리스트

        Returns:
            렌더링된 대사 리스트
        """
        rendered: List[Dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            text = entry.get("text")
            if isinstance(text, str):
                entry["text"] = self.render_text(state, text)
            rendered.append(entry)
        return rendered

    def render_text(self, state: Dict[str, Any], text: str) -> str:
        """
        텍스트 내의 플레이어 이름, 변수 등을 실제 값으로 치환

        Args:
            state: 전체 state 객체
            text: 치환할 텍스트

        Returns:
            치환된 텍스트
        """
        user_name = (
            state.get("user_name")
            or (state.get("temp_data") or {}).get("user_name")
            or "츠구코"
        )

        replacements = {
            "{user}": user_name,
            "{user_name}": user_name,
            "{{user}}": user_name,
        }

        result = text
        for token, value in replacements.items():
            result = result.replace(token, value)
        return result


__all__ = ["DialogueFormatterService"]
