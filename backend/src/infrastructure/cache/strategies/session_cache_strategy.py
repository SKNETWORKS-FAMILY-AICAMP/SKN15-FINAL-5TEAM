"""
Session Cache Strategy - Session 캐싱 전략

Session 데이터를 Redis에 캐싱하는 전략.
"""

import logging
from typing import Optional, Dict, Any

from src.core.interfaces.providers.cache_provider import ICacheProvider

logger = logging.getLogger(__name__)


class SessionCacheStrategy:
    """
    Session 캐싱 전략

    책임:
    - Session 키 생성 규칙
    - Session 캐시 저장/조회/삭제
    - TTL 관리
    """

    # Session 기본 TTL (1시간)
    DEFAULT_SESSION_TTL = 3600

    def __init__(self, cache_provider: ICacheProvider):
        self._cache = cache_provider

    def _make_key(self, session_id: str) -> str:
        """세션 ID를 Redis 키로 변환"""
        return f"session:{session_id}"

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 데이터 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 또는 None
        """
        key = self._make_key(session_id)
        return self._cache.get(key)

    def set_session(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        세션 데이터 저장

        Args:
            session_id: 세션 ID
            session_data: 세션 데이터
            ttl: TTL (초), None이면 기본값 사용

        Returns:
            성공 여부
        """
        key = self._make_key(session_id)
        ttl = ttl if ttl is not None else self.DEFAULT_SESSION_TTL
        return self._cache.set(key, session_data, ttl)

    def invalidate_session(self, session_id: str) -> bool:
        """
        세션 캐시 무효화 (삭제)

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        key = self._make_key(session_id)
        return self._cache.delete(key)

    def extend_session_ttl(self, session_id: str, additional_seconds: int) -> bool:
        """
        세션 TTL 연장

        Args:
            session_id: 세션 ID
            additional_seconds: 추가할 초 수

        Returns:
            성공 여부
        """
        key = self._make_key(session_id)
        return self._cache.extend_ttl(key, additional_seconds)

    def session_exists(self, session_id: str) -> bool:
        """
        세션 존재 여부 확인

        Args:
            session_id: 세션 ID

        Returns:
            존재 여부
        """
        key = self._make_key(session_id)
        return self._cache.exists(key)
