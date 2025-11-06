"""
Session Repository Interface

세션 데이터 접근을 위한 Port 정의.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class ISessionRepository(ABC):
    """Session Repository Interface (Port)"""

    @abstractmethod
    def get_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 ID로 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 또는 None
        """
        pass

    @abstractmethod
    def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        활성 세션 조회

        Args:
            user_id: 사용자 ID

        Returns:
            활성 세션 데이터 또는 None
        """
        pass

    @abstractmethod
    def create_session(
        self,
        session_id: str,
        user_id: str,
        scenario_id: str,
        initial_state: Dict[str, Any]
    ) -> Optional[str]:
        """
        새 세션 생성

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            initial_state: 초기 상태

        Returns:
            생성된 세션 ID 또는 None
        """
        pass

    @abstractmethod
    def update_session_state(
        self,
        session_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        세션 상태 업데이트

        Args:
            session_id: 세션 ID
            state: 업데이트할 상태

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def end_session(self, session_id: str) -> bool:
        """
        세션 종료

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def get_user_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        사용자의 세션 목록 조회

        Args:
            user_id: 사용자 ID
            limit: 최대 개수

        Returns:
            세션 목록
        """
        pass
