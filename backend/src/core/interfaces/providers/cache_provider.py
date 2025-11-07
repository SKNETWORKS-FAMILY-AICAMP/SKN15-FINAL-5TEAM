"""
Cache Provider Interface

캐시 서비스 접근을 위한 Port 정의.
Redis 등 다양한 캐시 시스템으로 교체 가능.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class ICacheProvider(ABC):
    """Cache Provider Interface (Port)"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        캐시 조회

        Args:
            key: 캐시 키

        Returns:
            캐시 값 또는 None
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        캐시 저장

        Args:
            key: 캐시 키
            value: 캐시 값
            ttl: Time-to-live (초), None이면 기본값 사용

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        캐시 삭제

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        캐시 존재 여부 확인

        Args:
            key: 캐시 키

        Returns:
            존재 여부
        """
        pass

    @abstractmethod
    def get_ttl(self, key: str) -> int:
        """
        캐시의 남은 TTL 조회

        Args:
            key: 캐시 키

        Returns:
            남은 TTL (초), -1: TTL 없음, -2: 키 없음
        """
        pass

    @abstractmethod
    def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """
        캐시 TTL 연장

        Args:
            key: 캐시 키
            additional_seconds: 추가할 초 수

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        캐시 시스템 연결 확인

        Returns:
            연결 상태
        """
        pass
