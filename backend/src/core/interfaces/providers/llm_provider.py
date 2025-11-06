"""
LLM Provider Interface

LLM 서비스 접근을 위한 Port 정의.
OpenAI, Anthropic 등 다양한 Provider로 교체 가능.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ILLMProvider(ABC):
    """LLM Provider Interface (Port)"""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        텍스트 생성 (단일 prompt)

        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 온도 (0.0 ~ 1.0)
            **kwargs: 추가 파라미터

        Returns:
            생성된 텍스트
        """
        pass

    @abstractmethod
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        채팅 생성 (대화 형식)

        Args:
            messages: 메시지 리스트 [{"role": "user", "content": "..."}]
            max_tokens: 최대 토큰 수
            temperature: 온도
            **kwargs: 추가 파라미터

        Returns:
            생성된 응답
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        텍스트의 토큰 수 계산

        Args:
            text: 입력 텍스트

        Returns:
            토큰 수
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        현재 사용 중인 모델 이름 반환

        Returns:
            모델 이름 (예: "gpt-4o-mini", "claude-sonnet-4")
        """
        pass
