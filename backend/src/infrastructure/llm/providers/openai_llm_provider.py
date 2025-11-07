"""
OpenAI LLM Provider - ILLMProvider 구현체

OpenAI API를 사용한 LLM Provider Adapter.
"""

import logging
from typing import List, Dict, Optional
import tiktoken
from openai import AsyncOpenAI

from src.core.interfaces.providers.llm_provider import ILLMProvider
from src.core.exceptions import LLMProviderError, RateLimitExceededError

logger = logging.getLogger(__name__)


class OpenAILLMProvider(ILLMProvider):
    """
    OpenAI LLM Provider 구현체

    지원 모델:
    - gpt-4o
    - gpt-4o-mini
    - gpt-4-turbo
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._encoding = tiktoken.encoding_for_model(model)

        logger.info(f"✅ OpenAI LLM Provider initialized: {model}")

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """텍스트 생성 (단일 prompt)"""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            generated_text = response.choices[0].message.content
            logger.debug(f"✅ OpenAI generate_text: {len(generated_text)} chars")
            return generated_text

        except Exception as e:
            error_message = str(e)

            # Rate limit 오류 처리
            if "429" in error_message or "rate_limit" in error_message.lower():
                logger.error(f"❌ OpenAI rate limit exceeded: {e}")
                raise RateLimitExceededError(
                    service="OpenAI",
                    message="OpenAI API rate limit exceeded"
                )

            logger.error(f"❌ OpenAI API error: {e}")
            raise LLMProviderError(
                provider="OpenAI",
                message=f"Failed to generate text: {error_message}"
            )

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """채팅 생성 (대화 형식)"""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            generated_text = response.choices[0].message.content
            logger.debug(f"✅ OpenAI generate_chat: {len(generated_text)} chars")
            return generated_text

        except Exception as e:
            error_message = str(e)

            if "429" in error_message or "rate_limit" in error_message.lower():
                logger.error(f"❌ OpenAI rate limit exceeded: {e}")
                raise RateLimitExceededError(
                    service="OpenAI",
                    message="OpenAI API rate limit exceeded"
                )

            logger.error(f"❌ OpenAI API error: {e}")
            raise LLMProviderError(
                provider="OpenAI",
                message=f"Failed to generate chat: {error_message}"
            )

    def count_tokens(self, text: str) -> int:
        """텍스트의 토큰 수 계산"""
        try:
            tokens = self._encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"❌ Failed to count tokens: {e}")
            # Fallback: 대략적인 추정 (4 chars = 1 token)
            return len(text) // 4

    def get_model_name(self) -> str:
        """현재 사용 중인 모델 이름 반환"""
        return self._model
