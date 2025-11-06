"""
User Repository Interface

사용자 데이터 접근을 위한 Port 정의.
Infrastructure 계층에서 구현체(Adapter)를 제공함.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class IUserRepository(ABC):
    """User Repository Interface (Port)"""

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 ID로 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 데이터 또는 None
        """
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        사용자명으로 조회

        Args:
            username: 사용자명

        Returns:
            사용자 데이터 또는 None
        """
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        이메일로 조회

        Args:
            email: 이메일

        Returns:
            사용자 데이터 또는 None
        """
        pass

    @abstractmethod
    def create_user(
        self,
        username: str,
        password_hash: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> Optional[str]:
        """
        사용자 생성

        Args:
            username: 사용자명
            password_hash: 비밀번호 해시
            email: 이메일 (선택)
            display_name: 표시 이름 (선택)

        Returns:
            생성된 사용자 ID 또는 None (실패 시)
        """
        pass

    @abstractmethod
    def update_password(self, user_id: str, password_hash: str) -> bool:
        """
        비밀번호 업데이트

        Args:
            user_id: 사용자 ID
            password_hash: 새 비밀번호 해시

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def verify_user_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        사용자 인증 (사용자명 + 비밀번호)

        Args:
            username: 사용자명
            password: 비밀번호 (평문)

        Returns:
            인증된 사용자 데이터 또는 None
        """
        pass

    @abstractmethod
    def initialize_user_progression(self, user_id: str) -> bool:
        """
        사용자 진행도 초기화 (ranks, stats, equipment)

        Args:
            user_id: 사용자 ID

        Returns:
            성공 여부
        """
        pass
