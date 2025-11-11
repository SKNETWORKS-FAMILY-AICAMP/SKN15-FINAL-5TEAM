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
                # msg가 dict일 수도 있고 ChatMessage 객체일 수도 있음
                if isinstance(msg, dict):
                    speaker = msg.get("speaker", "Unknown")
                    text = msg.get("text", "")
                else:
                    speaker = msg.speaker
                    text = msg.text
                history_lines.append(f"{speaker}: {text}")
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
            response = await self.llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8  # 창의성 높게
            )

            # 응답 정규화
            dialogues = self._normalize_llm_response(response)

            if not dialogues:
                logger.warning("generate_simple_dialogue", "Empty dialogues from LLM, using fallback")
                return self._get_fallback_response(character_name, user_input, emotion)

            logger.info(
                "generate_simple_dialogue",
                "✅ Dialogue generated",
                character=character_name,
                dialogues_count=len(dialogues)
            )

            return dialogues

        except Exception as e:
            logger.error("generate_simple_dialogue", f"❌ Failed: {e}", character=character_name, error_type=type(e).__name__)
            return self._get_fallback_response(character_name, user_input, emotion, error=e)

    async def generate_with_prompt(
        self,
        prompt: str,
        temperature: float = 0.8,
        max_tokens: int = 2000
    ) -> List[ChatMessage]:
        """
        외부에서 제공한 프롬프트로 대화 생성 (Layer 4)

        Args:
            prompt: 완성된 프롬프트 (PromptService에서 생성)
            temperature: LLM temperature
            max_tokens: 최대 토큰 수

        Returns:
            생성된 대사 리스트
        """
        logger.info("generate_with_prompt", "Generating dialogue with custom prompt",
                   prompt_len=len(prompt))

        try:
            # System prompt (JSON 모드 사용을 위해 "json" 단어 포함 필수)
            system_prompt = "당신은 창의적인 시나리오 작가입니다. 주어진 지시사항을 정확히 따르고 JSON 형식으로 응답하세요."

            # LLM 호출 (JSON 모드)
            response = await self.llm.call_json(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # 응답 정규화
            dialogues = self._normalize_llm_response(response)

            if not dialogues:
                logger.warning("generate_with_prompt", "Empty dialogues from LLM")
                return []

            logger.info("generate_with_prompt", "✅ Dialogue generated",
                       dialogues_count=len(dialogues))

            return dialogues

        except Exception as e:
            logger.error("generate_with_prompt", f"❌ Failed: {e}", exc_info=True)
            return []

    async def generate_beat_dialogue(
        self,
        beats: List[Dict[str, Any]],
        character_name: str,
        user_input: str,
        emotion: str = "neutral",
        personality: str = "친근하고 밝음",
        conversation_history: Optional[List] = None
    ) -> List[ChatMessage]:
        """
        Beat 기반 대사 생성

        Args:
            beats: Beat 리스트 (각 beat은 dict)
            character_name: 캐릭터 이름
            user_input: 사용자 입력
            emotion: 감정 상태
            personality: 성격 설명
            conversation_history: 대화 이력

        Returns:
            생성된 대사 리스트
        """
        logger.info(
            "generate_beat_dialogue",
            "Generating beat-based dialogue",
            beats_count=len(beats),
            character=character_name,
            user_input_len=len(user_input)
        )

        # Beat 설명 결합
        beat_descriptions = []
        for beat in beats:
            if isinstance(beat, dict):
                desc = beat.get("goal") or beat.get("description") or beat.get("text") or str(beat)
                beat_descriptions.append(desc)
            elif isinstance(beat, str):
                beat_descriptions.append(beat)
        beat_text = "\n".join(beat_descriptions) if beat_descriptions else "일반 대화"

        # 대화 이력 포맷팅
        history_text = ""
        if conversation_history:
            history_lines = []
            for msg in conversation_history[-10:]:  # 최근 10개
                # msg가 dict일 수도 있고 ChatMessage 객체일 수도 있음
                if isinstance(msg, dict):
                    speaker = msg.get("speaker", "Unknown")
                    text = msg.get("text", "")
                else:
                    speaker = msg.speaker
                    text = msg.text
                history_lines.append(f"{speaker}: {text}")
            history_text = "\n".join(history_lines)

        # 프롬프트 생성 (beat 기반)
        system_prompt, user_prompt = get_beat_dialogue_prompt(
            beat_description=beat_text,
            characters_info=f"- {character_name}: {personality}",
            user_input=user_input,
            conversation_history=history_text
        )

        try:
            # LLM 호출 (JSON 모드)
            response = await self.llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                max_tokens=2000
            )

            # 응답 정규화
            dialogues = self._normalize_llm_response(response)

            if not dialogues:
                logger.warning("generate_beat_dialogue", "Empty dialogues from LLM, using fallback")
                return self._get_fallback_response(character_name, user_input, emotion)

            logger.info(
                "generate_beat_dialogue",
                "✅ Beat dialogue generated",
                dialogues_count=len(dialogues)
            )

            return dialogues

        except Exception as e:
            logger.error("generate_beat_dialogue", f"❌ Failed: {e}", error_type=type(e).__name__)
            return self._get_fallback_response(character_name, user_input, emotion, error=e)

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

    def _get_fallback_response(
        self,
        character_name: str,
        user_input: str,
        emotion: str = "neutral",
        error: Optional[Exception] = None
    ) -> List[ChatMessage]:
        """
        LLM 실패 시 Fallback 응답 생성

        사용자 입력에 맞춰 contextual한 응답 제공

        Args:
            character_name: 캐릭터 이름
            user_input: 사용자 입력
            emotion: 감정 상태
            error: 발생한 에러 (있는 경우)

        Returns:
            Fallback 대사 리스트
        """
        from app.core.errors import LLMRateLimitException, LLMTimeoutException

        user_input_lower = user_input.lower().strip()

        # 에러 타입별 특별 메시지
        if isinstance(error, LLMRateLimitException):
            text = "잠시만 기다려주세요. 지금 많은 분들이 대화 중이에요."
        elif isinstance(error, LLMTimeoutException):
            text = "응답이 조금 늦어지고 있어요. 다시 말씀해주시겠어요?"
        # 사용자 입력 패턴별 응답
        elif any(greeting in user_input_lower for greeting in ["안녕", "하이", "헬로", "hello", "hi"]):
            text = f"안녕하세요! 저는 {character_name}입니다. 어떻게 도와드릴까요?"
        elif any(question in user_input_lower for question in ["어떻게", "왜", "무엇", "언제", "어디", "누구"]):
            text = "음... 좋은 질문이네요! 제가 생각해볼게요."
        elif any(word in user_input_lower for word in ["좋아", "감사", "고마워", "thanks", "thank"]):
            text = "감사합니다! 더 도와드릴 것이 있을까요?"
        elif any(word in user_input_lower for word in ["싫어", "아니", "no", "안 돼"]):
            text = "알겠습니다. 다른 방법을 찾아볼까요?"
        else:
            # 기본 fallback
            text = f"말씀하신 내용에 대해 조금 더 생각해볼 시간이 필요할 것 같아요."

        logger.info(
            "_get_fallback_response",
            "Using fallback response",
            character=character_name,
            error_type=type(error).__name__ if error else None
        )

        return [
            ChatMessage(
                speaker=character_name,
                text=text,
                emotion=emotion
            )
        ]

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
