"""
Memory Repository Interface (Port)

대화 메모리 및 요약 데이터 접근을 위한 포트 정의
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class IMemoryRepository(ABC):
    """메모리 리포지토리 인터페이스"""

    @abstractmethod
    def get_conversation_summary(
        self,
        session_id: str,
        character_name: Optional[str] = None
    ) -> Optional[str]:
        """
        세션의 대화 요약 조회

        Args:
            session_id: 세션 ID
            character_name: 캐릭터 이름 (선택)

        Returns:
            대화 요약 텍스트 또는 None
        """
        pass

    @abstractmethod
    def save_conversation_summary(
        self,
        session_id: str,
        summary: str,
        character_name: Optional[str] = None
    ) -> bool:
        """
        대화 요약 저장

        Args:
            session_id: 세션 ID
            summary: 요약 텍스트
            character_name: 캐릭터 이름 (선택)

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최근 대화 메시지 조회

        Args:
            session_id: 세션 ID
            limit: 조회할 메시지 개수

        Returns:
            메시지 리스트
        """
        pass

    @abstractmethod
    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        대화 메시지 저장

        Args:
            session_id: 세션 ID
            role: 메시지 역할 (user/assistant/system)
            content: 메시지 내용
            metadata: 메타데이터 (선택)

        Returns:
            메시지 ID
        """
        pass

    @abstractmethod
    def extract_key_memories(
        self,
        session_id: str,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        중요한 기억 추출

        Args:
            session_id: 세션 ID
            threshold: 중요도 임계값

        Returns:
            핵심 기억 리스트
        """
        pass
