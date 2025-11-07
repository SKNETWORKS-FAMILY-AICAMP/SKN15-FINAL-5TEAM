"""
Session Manager Interface (Port)

세션 생명주기 관리를 위한 포트 정의
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class ISessionManager(ABC):
    """세션 매니저 인터페이스"""

    @abstractmethod
    def create_session(
        self,
        user_id: str,
        scenario_id: str,
        **kwargs
    ) -> str:
        """
        새 세션 생성

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            **kwargs: 추가 세션 속성

        Returns:
            생성된 세션 ID
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 정보 조회 (DB + Cache 하이브리드)

        Args:
            session_id: 세션 ID

        Returns:
            세션 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        세션 정보 업데이트

        Args:
            session_id: 세션 ID
            updates: 업데이트할 필드

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 상태 조회 (GraphState)

        Args:
            session_id: 세션 ID

        Returns:
            GraphState 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def save_session_state(
        self,
        session_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        세션 상태 저장

        Args:
            session_id: 세션 ID
            state: GraphState 딕셔너리

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def increment_turn_count(self, session_id: str) -> int:
        """
        세션 턴 카운트 증가

        Args:
            session_id: 세션 ID

        Returns:
            새로운 턴 카운트
        """
        pass
