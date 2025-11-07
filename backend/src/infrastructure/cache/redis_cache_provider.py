"""
Redis Cache Provider - ICacheProvider 구현체

Redis를 사용한 캐시 시스템 Adapter.
"""

import json
import logging
from typing import Optional, Any

from src.core.interfaces.providers.cache_provider import ICacheProvider
from src.core.config.settings import get_settings
from src.core.exceptions import CacheOperationError
from infrastructure.cache.redis_connection import RedisConnection

logger = logging.getLogger(__name__)


class RedisCacheProvider(ICacheProvider):
    """
    Redis Cache Provider 구현체

    의존성: RedisConnection
    """

    def __init__(self, redis_connection: RedisConnection):
        self._redis = redis_connection.get_client()
        settings = get_settings()
        self._default_ttl = settings.redis.default_ttl

    def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        try:
            data = self._redis.get(key)
            if data:
                logger.debug(f"✅ Cache HIT: {key}")
                return json.loads(data)
            else:
                logger.debug(f"⚠️  Cache MISS: {key}")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to get cache: {e}")
            raise CacheOperationError(
                operation="get",
                key=key,
                message=f"Failed to get cache: {str(e)}"
            )

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시 저장"""
        try:
            ttl = ttl if ttl is not None else self._default_ttl
            json_data = json.dumps(value, ensure_ascii=False, default=str)

            self._redis.setex(key, ttl, json_data)
            logger.debug(f"✅ Cache SET: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to set cache: {e}")
            raise CacheOperationError(
                operation="set",
                key=key,
                message=f"Failed to set cache: {str(e)}"
            )

    def delete(self, key: str) -> bool:
        """캐시 삭제"""
        try:
            deleted = self._redis.delete(key)
            logger.debug(f"✅ Cache DELETE: {key}")
            return deleted > 0

        except Exception as e:
            logger.error(f"❌ Failed to delete cache: {e}")
            raise CacheOperationError(
                operation="delete",
                key=key,
                message=f"Failed to delete cache: {str(e)}"
            )

    def exists(self, key: str) -> bool:
        """캐시 존재 여부 확인"""
        try:
            return self._redis.exists(key) > 0
        except Exception as e:
            logger.error(f"❌ Failed to check cache existence: {e}")
            return False

    def get_ttl(self, key: str) -> int:
        """캐시의 남은 TTL 조회"""
        try:
            return self._redis.ttl(key)
        except Exception as e:
            logger.error(f"❌ Failed to get TTL: {e}")
            return -2

    def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """캐시 TTL 연장"""
        try:
            current_ttl = self._redis.ttl(key)

            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                self._redis.expire(key, new_ttl)
                logger.debug(f"✅ TTL extended: {key} (+{additional_seconds}s)")
                return True
            else:
                logger.warning(f"⚠️  Cannot extend TTL for non-existent key: {key}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to extend TTL: {e}")
            raise CacheOperationError(
                operation="extend_ttl",
                key=key,
                message=f"Failed to extend TTL: {str(e)}"
            )

    def health_check(self) -> bool:
        """캐시 시스템 연결 확인"""
        try:
            return self._redis.ping()
        except Exception as e:
            logger.error(f"❌ Cache health check failed: {e}")
            return False
