"""
CacheManager - Redis 연동
세션 데이터 캐싱 및 TTL 관리
"""

import os
import json
from typing import Optional, Dict, Any
import redis
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis 기반 세션 캐시 관리자"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        default_ttl: int = 3600
    ):
        """
        Args:
            host: Redis 호스트
            port: Redis 포트
            db: Redis DB 번호
            password: Redis 비밀번호 (optional)
            default_ttl: 기본 TTL (초 단위, 기본 1시간)
        """
        host = host or os.getenv("REDIS_HOST", "localhost")
        port = int(port if port is not None else os.getenv("REDIS_PORT", "6379"))
        db = int(db if db is not None else os.getenv("REDIS_DB", "0"))
        password = password if password is not None else os.getenv("REDIS_PASSWORD")

        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,  # 자동으로 문자열 디코딩
            socket_connect_timeout=5,
            socket_timeout=5
        )
        self.default_ttl = default_ttl

        # 연결 테스트
        try:
            self.redis_client.ping()
            logger.info(f"CacheManager initialized: {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        # 통계 추적
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }

    def _make_key(self, session_id: str) -> str:
        """세션 ID를 Redis 키로 변환"""
        return f"session:{session_id}"

    # ========================================
    # 기본 캐시 작업
    # ========================================

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 데이터 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 (dict) 또는 None
        """
        try:
            key = self._make_key(session_id)
            data = self.redis_client.get(key)

            if data:
                self.stats["hits"] += 1
                logger.debug(f"Cache HIT: {session_id}")
                return json.loads(data)
            else:
                self.stats["misses"] += 1
                logger.debug(f"Cache MISS: {session_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to get session from cache: {e}")
            self.stats["misses"] += 1
            return None

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
            session_data: 세션 데이터 (dict)
            ttl: TTL (초 단위, None이면 default_ttl 사용)

        Returns:
            성공 여부
        """
        try:
            key = self._make_key(session_id)
            ttl = ttl if ttl is not None else self.default_ttl

            # JSON 직렬화
            json_data = json.dumps(session_data, ensure_ascii=False, default=str)

            # Redis에 저장 (TTL 설정)
            self.redis_client.setex(key, ttl, json_data)

            self.stats["sets"] += 1
            logger.debug(f"Cache SET: {session_id} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to set session in cache: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        세션 데이터 삭제

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        try:
            key = self._make_key(session_id)
            deleted = self.redis_client.delete(key)

            self.stats["deletes"] += 1
            logger.debug(f"Cache DELETE: {session_id}")
            return deleted > 0

        except Exception as e:
            logger.error(f"Failed to delete session from cache: {e}")
            return False

    def exists(self, session_id: str) -> bool:
        """세션이 캐시에 존재하는지 확인"""
        try:
            key = self._make_key(session_id)
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check session existence: {e}")
            return False

    def get_ttl(self, session_id: str) -> int:
        """
        세션의 남은 TTL 조회

        Returns:
            남은 TTL (초), -1: 키 존재하나 TTL 없음, -2: 키 없음
        """
        try:
            key = self._make_key(session_id)
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Failed to get TTL: {e}")
            return -2

    def extend_ttl(self, session_id: str, additional_seconds: int) -> bool:
        """
        세션 TTL 연장

        Args:
            session_id: 세션 ID
            additional_seconds: 추가할 초 수

        Returns:
            성공 여부
        """
        try:
            key = self._make_key(session_id)
            current_ttl = self.redis_client.ttl(key)

            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                self.redis_client.expire(key, new_ttl)
                logger.debug(f"TTL extended: {session_id} (+{additional_seconds}s)")
                return True
            else:
                logger.warning(f"Cannot extend TTL for non-existent key: {session_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to extend TTL: {e}")
            return False

    # ========================================
    # 통계 및 유틸리티
    # ========================================

    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            {
                "hits": int,
                "misses": int,
                "sets": int,
                "deletes": int,
                "hit_rate": float (0.0 ~ 1.0)
            }
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total_requests
            if total_requests > 0
            else 0.0
        )

        return {
            **self.stats,
            "hit_rate": round(hit_rate, 3)
        }

    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
        logger.info("Cache stats reset")

    def clear_all_sessions(self) -> int:
        """
        모든 세션 캐시 삭제 (주의: 개발용)

        Returns:
            삭제된 키 개수
        """
        try:
            pattern = "session:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.warning(f"Cleared {deleted} session keys")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Failed to clear all sessions: {e}")
            return 0

    def get_all_session_ids(self) -> list[str]:
        """
        모든 캐시된 세션 ID 조회 (디버깅용)

        Returns:
            세션 ID 리스트
        """
        try:
            pattern = "session:*"
            keys = self.redis_client.keys(pattern)
            # "session:" 접두사 제거
            return [key.replace("session:", "") for key in keys]
        except Exception as e:
            logger.error(f"Failed to get session IDs: {e}")
            return []

    def ping(self) -> bool:
        """Redis 연결 확인"""
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def close(self):
        """Redis 연결 종료"""
        try:
            self.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Failed to close Redis connection: {e}")


# 환경변수 기반 싱글톤 인스턴스 생성 헬퍼
def create_cache_manager_from_env() -> CacheManager:
    """환경변수에서 설정을 읽어 CacheManager 인스턴스 생성"""
    return CacheManager(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD"),
        default_ttl=int(os.getenv("SESSION_TTL", "3600"))
    )
