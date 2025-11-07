"""
Conversation Repository Interface (Port)

대화 데이터 접근을 위한 포트 정의
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class IConversationRepository(ABC):
    """대화 리포지토리 인터페이스"""

    @abstractmethod
    def get_dialogue_by_id(
        self,
        dialogue_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        대화 ID로 대화 조회

        Args:
            dialogue_id: 대화 ID

        Returns:
            대화 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def save_dialogue(
        self,
        session_id: str,
        turn_number: int,
        user_input: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        대화 저장

        Args:
            session_id: 세션 ID
            turn_number: 턴 번호
            user_input: 사용자 입력
            agent_response: 에이전트 응답
            metadata: 메타데이터

        Returns:
            dialogue_id
        """
        pass

    @abstractmethod
    def get_session_dialogues(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        세션의 대화 목록 조회

        Args:
            session_id: 세션 ID
            limit: 조회 개수 제한

        Returns:
            대화 리스트
        """
        pass

    @abstractmethod
    def update_dialogue_metadata(
        self,
        dialogue_id: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        대화 메타데이터 업데이트

        Args:
            dialogue_id: 대화 ID
            metadata: 메타데이터

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def get_conversation_summary(
        self,
        session_id: str
    ) -> Optional[str]:
        """
        대화 요약 조회

        Args:
            session_id: 세션 ID

        Returns:
            요약 텍스트 또는 None
        """
        pass

    @abstractmethod
    def save_conversation_summary(
        self,
        session_id: str,
        summary: str,
        turn_count: int
    ) -> bool:
        """
        대화 요약 저장

        Args:
            session_id: 세션 ID
            summary: 요약 텍스트
            turn_count: 턴 카운트

        Returns:
            성공 여부
        """
        pass
