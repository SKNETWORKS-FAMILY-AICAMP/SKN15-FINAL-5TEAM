"""
LLM Factory - LLM Provider 생성을 위한 Factory Pattern

환경변수 또는 설정에 따라 적절한 LLM Provider를 생성.
"""

import logging
from typing import Optional

from src.core.interfaces.providers.llm_provider import ILLMProvider
from src.core.config.settings import get_settings
from infrastructure.llm.providers.openai_llm_provider import OpenAILLMProvider

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    LLM Provider Factory

    지원 Provider:
    - OpenAI
    - Anthropic (향후 추가)
    - Mock (테스트용)
    """

    @staticmethod
    def create_provider(
        provider_type: str,
        api_key: str,
        model: str,
        **kwargs
    ) -> ILLMProvider:
        """
        LLM Provider 생성

        Args:
            provider_type: Provider 타입 ("openai", "anthropic", "mock")
            api_key: API 키
            model: 모델 이름
            **kwargs: 추가 설정

        Returns:
            ILLMProvider 구현체

        Raises:
            ValueError: 지원하지 않는 Provider 타입
        """
        provider_type = provider_type.lower()

        if provider_type == "openai":
            return OpenAILLMProvider(api_key=api_key, model=model)

        elif provider_type == "anthropic":
            # 향후 구현
            raise NotImplementedError("Anthropic provider not implemented yet")

        elif provider_type == "mock":
            # 향후 구현 (테스트용)
            raise NotImplementedError("Mock provider not implemented yet")

        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider_type}. "
                f"Supported: openai, anthropic, mock"
            )

    @staticmethod
    def create_from_env() -> ILLMProvider:
        """
        환경변수에서 LLM Provider 생성

        환경변수:
        - LLM_PROVIDER (default: "openai")
        - OPENAI_API_KEY
        - OPENAI_MODEL (default: "gpt-4o-mini")

        Returns:
            ILLMProvider 구현체
        """
        settings = get_settings()
        llm_config = settings.llm

        logger.info(
            f"🔧 Creating LLM Provider: {llm_config.provider} ({llm_config.model})"
        )

        return LLMFactory.create_provider(
            provider_type=llm_config.provider,
            api_key=llm_config.api_key,
            model=llm_config.model
        )
