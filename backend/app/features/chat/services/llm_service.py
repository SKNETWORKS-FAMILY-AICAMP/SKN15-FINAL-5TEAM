"""
LLM Service - 대사 생성 서비스
캐릭터 대사 생성, Beat 처리, 응답 정규화
"""
import json
from typing import Dict, List, Any, Optional
from app.core.llm import LLMClient, PromptTemplate
from app.core.llm.prompts import get_dialogue_prompt, get_beat_dialogue_prompt
from app.core.logging import get_parent_logger
from ..schemas import ChatMessage

logger = get_parent_logger("LLMService")


class LLMService:
    """
    LLM 대사 생성 서비스

    책임:
    - 캐릭터 대사 생성
    - Beat 기반 대화 생성
    - LLM 응답 정규화
    - 에러 핸들링 및 Fallback
    """

    def __init__(self):
        """LLMService 초기화"""
        self.llm = LLMClient()
        logger.info("__init__", "LLMService initialized")

    async def generate_simple_dialogue(
        self,
        character_name: str,
        user_input: str,
        emotion: str = "neutral",
        personality: str = "친근하고 밝음",
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> List[ChatMessage]:
        """
        간단한 대사 생성 (Beat 없이)

        Args:
            character_name: 캐릭터 이름
            user_input: 사용자 입력
            emotion: 감정 상태
            personality: 성격 설명
            conversation_history: 대화 이력

        Returns:
            생성된 대사 리스트
        """
        logger.info(
            "generate_simple_dialogue",
            "Generating dialogue",
            character=character_name,
            user_input_len=len(user_input),
            emotion=emotion
        )

        # 대화 이력 포맷팅
        history_text = ""
        if conversation_history:
            history_lines = []
            for msg in conversation_history[-5:]:  # 최근 5개만
                history_lines.append(f"{msg.speaker}: {msg.text}")
            history_text = "\n".join(history_lines)

        # 프롬프트 생성
        system_prompt, user_prompt = get_dialogue_prompt(
            character_name=character_name,
            user_input=user_input,
            emotion=emotion,
            personality=personality,
            conversation_history=history_text
        )

        try:
            # LLM 호출 (JSON 모드)
            response = self.llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8  # 창의성 높게
            )

            # 응답 정규화
            dialogues = self._normalize_llm_response(response)

            logger.info(
                "generate_simple_dialogue",
                "✅ Dialogue generated",
                character=character_name,
                dialogues_count=len(dialogues)
            )

            return dialogues

        except Exception as e:
            logger.error("generate_simple_dialogue", f"❌ Failed: {e}", character=character_name)
            # Fallback: 더미 응답
            return [
                ChatMessage(
                    speaker=character_name,
                    text=f"안녕하세요! (대사 생성 실패: {str(e)[:50]})",
                    emotion=emotion
                )
            ]

    async def generate_beat_dialogue(
        self,
        beat_description: str,
        characters_info: Dict[str, str],
        user_input: str,
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> List[ChatMessage]:
        """
        Beat 기반 대사 생성

        Args:
            beat_description: Beat 설명
            characters_info: 캐릭터 정보 dict (name → description)
            user_input: 사용자 입력
            conversation_history: 대화 이력

        Returns:
            생성된 대사 리스트
        """
        logger.info(
            "generate_beat_dialogue",
            "Generating beat-based dialogue",
            beat_len=len(beat_description),
            characters=list(characters_info.keys()),
            user_input_len=len(user_input)
        )

        # 캐릭터 정보 포맷팅
        chars_text = "\n".join([
            f"- {name}: {desc}"
            for name, desc in characters_info.items()
        ])

        # 대화 이력 포맷팅
        history_text = ""
        if conversation_history:
            history_lines = []
            for msg in conversation_history[-10:]:  # 최근 10개
                history_lines.append(f"{msg.speaker}: {msg.text}")
            history_text = "\n".join(history_lines)

        # 프롬프트 생성
        system_prompt, user_prompt = get_beat_dialogue_prompt(
            beat_description=beat_description,
            characters_info=chars_text,
            user_input=user_input,
            conversation_history=history_text
        )

        try:
            # LLM 호출 (JSON 모드)
            response = self.llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                max_tokens=2000
            )

            # 응답 정규화
            dialogues = self._normalize_llm_response(response)

            logger.info(
                "generate_beat_dialogue",
                "✅ Beat dialogue generated",
                dialogues_count=len(dialogues)
            )

            return dialogues

        except Exception as e:
            logger.error("generate_beat_dialogue", f"❌ Failed: {e}")
            # Fallback
            first_character = list(characters_info.keys())[0] if characters_info else "narrator"
            return [
                ChatMessage(
                    speaker=first_character,
                    text=f"(대사 생성 실패: {str(e)[:50]})",
                    emotion="neutral"
                )
            ]

    def _normalize_llm_response(self, response: Dict[str, Any]) -> List[ChatMessage]:
        """
        LLM 응답을 ChatMessage 리스트로 정규화

        지원하는 응답 형식:
        1. {"dialogues": [{"speaker": "...", "text": "...", "emotion": "..."}, ...]}
        2. {"scene": {"dialogues": [...]}}
        3. {"scene": [{"character": "...", "dialogue": "..."}, ...]}
        4. {"response": "..."}  # 단일 텍스트

        Args:
            response: LLM JSON 응답

        Returns:
            정규화된 ChatMessage 리스트
        """
        try:
            # 1. dialogues 키가 있는 경우
            if "dialogues" in response:
                dialogues_list = response["dialogues"]
                if isinstance(dialogues_list, list):
                    return self._parse_dialogue_list(dialogues_list)

            # 2. scene 키가 있는 경우
            if "scene" in response:
                scene = response["scene"]

                # 2-1. scene이 list인 경우
                if isinstance(scene, list):
                    return self._parse_dialogue_list(scene)

                # 2-2. scene이 dict인 경우
                if isinstance(scene, dict):
                    if "dialogues" in scene:
                        return self._parse_dialogue_list(scene["dialogues"])
                    if "dialogue" in scene:
                        return self._parse_dialogue_list(scene["dialogue"])

            # 3. response 키가 있는 경우 (단일 텍스트)
            if "response" in response:
                text = response["response"]
                if isinstance(text, str) and text.strip():
                    return [ChatMessage(speaker="narrator", text=text, emotion="neutral")]

            # 4. 파싱 실패 시 빈 리스트
            logger.warning("_normalize_llm_response", "❌ Unknown response format", keys=list(response.keys()))
            return []

        except Exception as e:
            logger.error("_normalize_llm_response", f"❌ Normalization failed: {e}")
            return []

    def _parse_dialogue_list(self, dialogues_list: List[Any]) -> List[ChatMessage]:
        """
        대화 리스트를 ChatMessage로 변환

        Args:
            dialogues_list: 대화 데이터 리스트

        Returns:
            ChatMessage 리스트
        """
        messages = []

        for item in dialogues_list:
            if not isinstance(item, dict):
                continue

            # speaker 추출 (여러 필드 시도)
            speaker = (
                item.get("speaker")
                or item.get("character")
                or item.get("name")
                or "narrator"
            )

            # text 추출 (여러 필드 시도)
            text = (
                item.get("text")
                or item.get("dialogue")
                or item.get("content")
                or item.get("line")
                or ""
            )

            # emotion 추출
            emotion = item.get("emotion") or item.get("mood") or "neutral"

            if text.strip():
                messages.append(
                    ChatMessage(
                        speaker=speaker,
                        text=text,
                        emotion=emotion
                    )
                )

        return messages

    def get_stats(self) -> Dict[str, Any]:
        """
        서비스 통계 정보

        Returns:
            통계 dict
        """
        return {
            "llm_stats": self.llm.get_stats(),
            "service": "LLMService"
        }
