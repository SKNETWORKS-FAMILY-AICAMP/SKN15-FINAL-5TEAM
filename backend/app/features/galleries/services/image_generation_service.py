"""
Image Generation Service
AI 이미지 생성 서비스 (DALL-E, Stable Diffusion 등)
"""
from typing import Dict, Any, Optional, List
from app.core.logging import get_parent_logger
from app.core.config import get_settings
from app.core.llm.client import LLMClient

logger = get_parent_logger("ImageGeneration")
settings = get_settings()


class ImageGenerationService:
    """
    이미지 생성 서비스

    책임:
    - AI 이미지 생성 (DALL-E)
    - 프롬프트 빌더
    - 이미지 스타일 관리
    """

    def __init__(self):
        """ImageGenerationService 초기화"""
        self.llm_client = LLMClient()
        logger.info("__init__", "ImageGenerationService initialized")

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        AI 이미지 생성

        Args:
            prompt: 이미지 생성 프롬프트
            size: 이미지 크기 (1024x1024, 1024x1792, 1792x1024)
            quality: 품질 (standard, hd)
            style: 스타일 (vivid, natural)

        Returns:
            생성 결과
            {
                "url": str,  # 생성된 이미지 URL
                "revised_prompt": str,  # OpenAI가 수정한 프롬프트
                "model": str,  # 사용된 모델명
            }
        """
        logger.info("generate_image", "Generating image", prompt=prompt[:100])

        try:
            # OpenAI DALL-E API 호출
            result = await self.llm_client.generate_image(
                prompt=prompt,
                size=size,
                quality=quality,
                style=style
            )

            logger.info("generate_image", "✅ Image generated successfully")
            return result

        except Exception as e:
            logger.error("generate_image", f"❌ Image generation failed: {e}")
            raise

    def build_scene_prompt(
        self,
        scenario_id: str,
        stage_tag: str,
        character_name: Optional[str] = None,
        scene_description: Optional[str] = None,
        style_preset: str = "anime"
    ) -> str:
        """
        씬 기반 이미지 생성 프롬프트 빌더

        Args:
            scenario_id: 시나리오 ID
            stage_tag: 스테이지 태그
            character_name: 캐릭터 이름 (선택적)
            scene_description: 씬 설명 (선택적)
            style_preset: 스타일 프리셋 (anime, realistic, fantasy 등)

        Returns:
            생성 프롬프트 문자열
        """
        # 스타일 프리셋
        style_templates = {
            "anime": "高品質のアニメスタイル、詳細な背景、美しい照明",
            "realistic": "photorealistic, highly detailed, cinematic lighting",
            "fantasy": "fantasy art, detailed illustration, vibrant colors",
            "watercolor": "watercolor painting style, soft colors, artistic",
        }

        style_suffix = style_templates.get(style_preset, style_templates["anime"])

        # 기본 프롬프트
        prompt_parts = []

        # 씬 설명
        if scene_description:
            prompt_parts.append(scene_description)

        # 캐릭터
        if character_name:
            prompt_parts.append(f"featuring {character_name}")

        # 스타일
        prompt_parts.append(style_suffix)

        prompt = ", ".join(prompt_parts)

        logger.info("build_scene_prompt", f"Built prompt for {scenario_id}/{stage_tag}",
                   prompt=prompt[:100])

        return prompt

    def build_character_portrait_prompt(
        self,
        character_name: str,
        character_description: str,
        emotion: str = "neutral",
        style_preset: str = "anime"
    ) -> str:
        """
        캐릭터 초상화 프롬프트 빌더

        Args:
            character_name: 캐릭터 이름
            character_description: 캐릭터 설명
            emotion: 감정 (neutral, happy, sad, angry, surprised 등)
            style_preset: 스타일 프리셋

        Returns:
            생성 프롬프트 문자열
        """
        # 감정 표현
        emotion_map = {
            "neutral": "calm expression",
            "happy": "smiling, joyful expression",
            "sad": "melancholic expression",
            "angry": "intense, determined expression",
            "surprised": "wide-eyed, surprised expression",
        }

        emotion_desc = emotion_map.get(emotion, "neutral expression")

        # 스타일
        style_templates = {
            "anime": "anime character portrait, highly detailed face, vibrant colors",
            "realistic": "realistic portrait, detailed facial features, professional lighting",
        }

        style = style_templates.get(style_preset, style_templates["anime"])

        # 프롬프트 조합
        prompt = f"{character_description}, {emotion_desc}, {style}"

        logger.info("build_character_portrait_prompt",
                   f"Built portrait prompt for {character_name}",
                   prompt=prompt[:100])

        return prompt

    async def generate_scene_image(
        self,
        scenario_id: str,
        stage_tag: str,
        scene_description: str,
        character_name: Optional[str] = None,
        style_preset: str = "anime"
    ) -> Dict[str, Any]:
        """
        씬 이미지 생성 (프롬프트 빌더 + AI 생성)

        Args:
            scenario_id: 시나리오 ID
            stage_tag: 스테이지 태그
            scene_description: 씬 설명
            character_name: 캐릭터 이름
            style_preset: 스타일 프리셋

        Returns:
            생성 결과 (URL, 프롬프트 등)
        """
        # 프롬프트 빌드
        prompt = self.build_scene_prompt(
            scenario_id=scenario_id,
            stage_tag=stage_tag,
            character_name=character_name,
            scene_description=scene_description,
            style_preset=style_preset
        )

        # 이미지 생성
        result = await self.generate_image(prompt)

        # 메타데이터 추가
        result["generation_metadata"] = {
            "scenario_id": scenario_id,
            "stage_tag": stage_tag,
            "character_name": character_name,
            "style_preset": style_preset,
            "original_prompt": prompt
        }

        return result

    async def generate_character_portrait(
        self,
        character_name: str,
        character_description: str,
        emotion: str = "neutral",
        style_preset: str = "anime"
    ) -> Dict[str, Any]:
        """
        캐릭터 초상화 생성

        Args:
            character_name: 캐릭터 이름
            character_description: 캐릭터 설명
            emotion: 감정
            style_preset: 스타일 프리셋

        Returns:
            생성 결과 (URL, 프롬프트 등)
        """
        # 프롬프트 빌드
        prompt = self.build_character_portrait_prompt(
            character_name=character_name,
            character_description=character_description,
            emotion=emotion,
            style_preset=style_preset
        )

        # 이미지 생성
        result = await self.generate_image(prompt)

        # 메타데이터 추가
        result["generation_metadata"] = {
            "character_name": character_name,
            "emotion": emotion,
            "style_preset": style_preset,
            "original_prompt": prompt
        }

        return result
