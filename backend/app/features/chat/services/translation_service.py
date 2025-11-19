"""
Translation Service - 다국어 번역 서비스
LLM 기반 실시간 번역 (한국어 ↔ 영어/일본어)
"""
from typing import List, Dict, Any, Optional
from app.core.llm import LLMClient
from app.core.logging import get_parent_logger

logger = get_parent_logger("TranslationService")


class TranslationService:
    """
    LLM 기반 번역 서비스

    책임:
    - 사용자 입력 번역 (외국어 → 한국어)
    - AI 대화 번역 (한국어 → 외국어)
    - 캐릭터 톤&매너 유지
    - 번역 캐싱
    """

    # 지원 언어 코드
    SUPPORTED_LANGUAGES = {
        "ko": "Korean",
        "en": "English",
        "ja": "Japanese"
    }

    def __init__(self):
        """TranslationService 초기화"""
        self.llm = LLMClient()
        logger.info("__init__", "TranslationService initialized")

    async def translate_user_input(
        self,
        text: str,
        from_lang: str = "auto",
        to_lang: str = "ko"
    ) -> str:
        """
        사용자 입력 번역 (외국어 → 한국어)

        Args:
            text: 번역할 텍스트
            from_lang: 원본 언어 (auto=자동감지)
            to_lang: 목표 언어 (기본: 한국어)

        Returns:
            번역된 텍스트
        """
        # 이미 한국어면 번역 스킵
        if from_lang == "ko" and to_lang == "ko":
            return text

        logger.info(
            "translate_user_input",
            f"Translating user input: {from_lang} → {to_lang}",
            text_len=len(text)
        )

        target_language = self.SUPPORTED_LANGUAGES.get(to_lang, "Korean")

        system_prompt = f"""You are a professional translator specializing in natural conversation translation.
Translate the user's message to {target_language} while preserving:
- Natural conversational tone
- Emotional nuance
- Intent and context

Return ONLY the translated text without explanations."""

        user_prompt = f"Translate this to {target_language}:\n\n{text}"

        try:
            response = await self.llm.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3  # 일관성 있는 번역
            )

            translated = response.strip()
            logger.info(
                "translate_user_input",
                "✅ User input translated",
                from_lang=from_lang,
                to_lang=to_lang,
                original_len=len(text),
                translated_len=len(translated)
            )
            return translated

        except Exception as e:
            logger.error(
                "translate_user_input",
                f"Translation failed: {e}",
                exc_info=True
            )
            # 번역 실패 시 원문 반환
            return text

    async def translate_dialogue(
        self,
        text: str,
        to_lang: str,
        speaker: str = "narr",
        emotion: str = "neutral"
    ) -> str:
        """
        AI 대화 번역 (한국어 → 외국어)
        캐릭터 톤&매너 유지

        Args:
            text: 번역할 텍스트 (한국어)
            to_lang: 목표 언어
            speaker: 화자 (캐릭터명)
            emotion: 감정 상태

        Returns:
            번역된 텍스트
        """
        # 이미 목표 언어면 번역 스킵
        if to_lang == "ko":
            return text

        logger.info(
            "translate_dialogue",
            f"Translating dialogue: ko → {to_lang}",
            speaker=speaker,
            emotion=emotion,
            text_len=len(text)
        )

        target_language = self.SUPPORTED_LANGUAGES.get(to_lang, "English")

        # 캐릭터 톤 유지 지침
        tone_instructions = {
            "narr": "Maintain narrative, descriptive tone.",
            "시스템": "Use clear, informative system message style.",
        }
        tone_guide = tone_instructions.get(speaker, f"Maintain {speaker}'s speaking style and personality.")

        # 감정 반영 지침
        emotion_guide = f"The emotion is '{emotion}' - reflect this in word choice and tone."

        system_prompt = f"""You are a professional translator for interactive visual novel dialogue.
Translate Korean dialogue to {target_language} while:
- {tone_guide}
- {emotion_guide}
- Preserving speaker's personality and manner of speaking
- Keeping the same level of formality/politeness
- Maintaining emotional intensity
- Using natural, engaging language

Return ONLY the translated dialogue without explanations or quotes."""

        user_prompt = f"Translate this dialogue to {target_language}:\n\n{text}"

        try:
            response = await self.llm.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4  # 창의성과 일관성 균형
            )

            translated = response.strip()

            # 불필요한 따옴표 제거
            if translated.startswith('"') and translated.endswith('"'):
                translated = translated[1:-1]
            if translated.startswith("'") and translated.endswith("'"):
                translated = translated[1:-1]

            logger.info(
                "translate_dialogue",
                "✅ Dialogue translated",
                to_lang=to_lang,
                speaker=speaker,
                original_len=len(text),
                translated_len=len(translated)
            )
            return translated

        except Exception as e:
            logger.error(
                "translate_dialogue",
                f"Translation failed: {e}",
                exc_info=True
            )
            # 번역 실패 시 원문 반환
            return text

    async def translate_dialogues(
        self,
        dialogues: List[Dict[str, Any]],
        to_lang: str
    ) -> List[Dict[str, Any]]:
        """
        대화 리스트 일괄 번역

        Args:
            dialogues: 번역할 대화 리스트
            to_lang: 목표 언어

        Returns:
            번역된 대화 리스트
        """
        if to_lang == "ko":
            return dialogues

        logger.info(
            "translate_dialogues",
            f"Translating {len(dialogues)} dialogues to {to_lang}"
        )

        translated_dialogues = []

        for dialogue in dialogues:
            translated_dialogue = dialogue.copy()

            # 텍스트 번역
            original_text = dialogue.get("text", "")
            if original_text:
                translated_text = await self.translate_dialogue(
                    text=original_text,
                    to_lang=to_lang,
                    speaker=dialogue.get("speaker", "narr"),
                    emotion=dialogue.get("emotion", "neutral")
                )
                translated_dialogue["text"] = translated_text

            translated_dialogues.append(translated_dialogue)

        logger.info(
            "translate_dialogues",
            f"✅ {len(translated_dialogues)} dialogues translated"
        )

        return translated_dialogues

    def is_language_supported(self, lang_code: str) -> bool:
        """
        언어 코드가 지원되는지 확인

        Args:
            lang_code: 언어 코드 (ko/en/ja)

        Returns:
            지원 여부
        """
        return lang_code in self.SUPPORTED_LANGUAGES
