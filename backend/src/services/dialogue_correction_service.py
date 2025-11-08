"""
============================================================
✏️ Dialogue Correction Service — 대사 수정
============================================================
LLM을 사용해 검증 실패한 대사를 자동으로 수정합니다.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.graph_state import Dialogue, AgentState
from src.utils.llm_client import LLMClient, get_llm_client
from src.utils.config_loader import get_config_loader

_PROMPTS = get_config_loader().get_prompts()
_DIALOGUE_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("dialogue") or {})
_DIALOGUE_CORRECTION_TEMPLATE = (_DIALOGUE_PROMPTS.get("correction_template") or "").strip()

if not _DIALOGUE_CORRECTION_TEMPLATE:
    raise ValueError("DialogueAgent correction_template missing in configs/prompts.yaml")


class DialogueCorrectionService:
    """
    대사 수정 서비스

    책임:
    - LLM 기반 대사 수정
    - 검증 결과 기반 수정 프롬프트 생성
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
        """
        self._llm = llm_client

    def correct_dialogue(
        self,
        dialogue: Dialogue,
        state: AgentState,
        validation_result: Dict
    ) -> Optional[Dialogue]:
        """
        대사 자동 수정

        Args:
            dialogue: 수정할 대사
            state: 전체 state 객체
            validation_result: 검증 결과 dict

        Returns:
            수정된 Dialogue 객체 또는 None (실패 시)
        """
        if not self._llm:
            return None

        try:
            issues = validation_result.get("issues", [])
            suggestions = validation_result.get("suggestions") or "대사를 상황에 맞게 다듬어 주세요."

            issues_block = "\n".join(f"- {issue}" for issue in issues) if issues else "- 자연스럽게 다듬어 주세요."
            system_prompt = _DIALOGUE_CORRECTION_TEMPLATE.format(
                speaker=dialogue.speaker,
                issues_block=issues_block,
                suggestions=suggestions,
            )

            character_info = self._get_character_info(dialogue.speaker)

            user_prompt = f"""원본 대사: "{dialogue.content}"
캐릭터 성격: {character_info.get('personality', '')}
감정: {dialogue.emotion}
씬: {state.scene.current_scene}

수정된 대사만 출력하세요 (따옴표 없이):"""

            correction_temperature = self._llm.get_agent_setting(
                "dialogue",
                "correction_temperature",
                self._llm.get_agent_setting("dialogue", "temperature", 0.7),
            )
            correction_max_tokens = self._llm.get_agent_setting("dialogue", "correction_max_tokens", 100)

            corrected_content = self._llm.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=correction_temperature,
                max_tokens=correction_max_tokens,
                agent="dialogue",
            )

            # 새 Dialogue 객체 생성
            return Dialogue(
                speaker=dialogue.speaker,
                content=corrected_content.strip().strip('"').strip("'"),
                emotion=dialogue.emotion,
                emotion_intensity=dialogue.emotion_intensity,
                affinity_level=dialogue.affinity_level
            )

        except Exception as e:
            print(f"대사 수정 실패: {str(e)}")
            return None

    def _get_character_info(self, speaker: str) -> Dict:
        """
        캐릭터 정보 가져오기

        Args:
            speaker: 캐릭터 이름

        Returns:
            캐릭터 정보 dict
        """
        # 간단한 캐릭터 정보 (실제로는 DB에서 가져옴)
        characters = {
            "탄지로": {
                "personality": "정직하고 배려심 깊음. 동료애가 강함"
            },
            "이노스케": {
                "personality": "자유분방하고 호승심이 강함"
            },
            "젠이츠": {
                "personality": "겁이 많지만 용기를 보임"
            },
            "렌고쿠": {
                "personality": "열정적이고 정의로움"
            }
        }
        return characters.get(speaker, {})


__all__ = ["DialogueCorrectionService"]
