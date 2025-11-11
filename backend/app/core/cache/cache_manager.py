"""
CacheManager - Redis 연동 (현재 아키텍처 맞춤)
"""
import os
import json
from typing import Optional, Dict, Any
import redis
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheManager:
    """Redis 기반 캐시 관리자 (간소화된 버전)"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = None
    ):
        """
        Args:
            host: Redis 호스트
            port: Redis 포트
            db: Redis DB 번호
            password: Redis 비밀번호
            default_ttl: 기본 TTL (초)
        """
        # 환경변수 또는 설정에서 읽기
        host = host or os.getenv('REDIS_HOST', 'localhost')
        port = port or int(os.getenv('REDIS_PORT', '6379'))
        password = password or os.getenv('REDIS_PASSWORD')
        default_ttl = default_ttl or int(os.getenv('SESSION_TTL', '3600'))

        # Redis 연결 설정
        redis_config = {
            'host': host,
            'port': port,
            'db': db,
            'decode_responses': True,
            'socket_connect_timeout': 2,
            'socket_timeout': 5
        }

        if password and password.strip():
            redis_config['password'] = password

        try:
            self.redis_client = redis.Redis(**redis_config)
            self.redis_client.ping()
            logger.info(f"CacheManager initialized: {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Redis 없이도 동작하도록 (캐시 없이)
            self.redis_client = None

        self.default_ttl = default_ttl

        # 통계
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }

    def _make_key(self, prefix: str, identifier: str) -> str:
        """키 생성"""
        return f"{prefix}:{identifier}"

    # ========================================
    # 세션 캐싱
    # ========================================

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 데이터 조회"""
        if not self.redis_client:
            return None

        try:
            key = self._make_key("session", session_id)
            data = self.redis_client.get(key)

            if data:
                self.stats["hits"] += 1
                return json.loads(data)
            else:
                self.stats["misses"] += 1
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
        """세션 데이터 저장"""
        if not self.redis_client:
            return False

        try:
            key = self._make_key("session", session_id)
            ttl = ttl if ttl is not None else self.default_ttl

            json_data = json.dumps(session_data, ensure_ascii=False, default=str)
            self.redis_client.setex(key, ttl, json_data)

            self.stats["sets"] += 1
            return True

        except Exception as e:
            logger.error(f"Failed to set session in cache: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """세션 데이터 삭제"""
        if not self.redis_client:
            return False

        try:
            key = self._make_key("session", session_id)
            self.redis_client.delete(key)
            self.stats["deletes"] += 1
            return True

        except Exception as e:
            logger.error(f"Failed to delete session from cache: {e}")
            return False

    # ========================================
    # 시나리오 캐싱
    # ========================================

    def get_scenario_cached(self, scenario_id: str) -> Optional[dict]:
        """시나리오 캐싱 조회 (10분 TTL)"""
        if not self.redis_client:
            return None

        try:
            key = self._make_key("scenario", scenario_id)
            cached = self.redis_client.get(key)

            if cached:
                return json.loads(cached)
            return None

        except Exception as e:
            logger.error(f"Failed to get scenario from cache: {e}")
            return None

    def set_scenario_cached(self, scenario_id: str, scenario: dict, ttl: int = 600) -> bool:
        """시나리오 캐싱 저장"""
        if not self.redis_client:
            return False

        try:
            key = self._make_key("scenario", scenario_id)
            json_data = json.dumps(scenario, ensure_ascii=False, default=str)
            self.redis_client.setex(key, ttl, json_data)
            return True

        except Exception as e:
            logger.error(f"Failed to set scenario in cache: {e}")
            return False

    # ========================================
    # 유틸리티
    # ========================================

    def ping(self) -> bool:
        """Redis 연결 확인"""
        if not self.redis_client:
            return False
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
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

    def close(self):
        """Redis 연결 종료"""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Failed to close Redis connection: {e}")


# 싱글톤 인스턴스
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """CacheManager 싱글톤"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
