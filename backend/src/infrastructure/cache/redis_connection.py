"""
Redis Connection - Redis Client 관리

단일 책임: Redis Connection만 관리
"""

import logging
import redis
from typing import Optional

from core.config.settings import get_settings
from core.exceptions import CacheConnectionError

logger = logging.getLogger(__name__)


class RedisConnection:
    """
    Redis Connection 관리자

    책임:
    - Redis Client 생성 및 관리
    - Health Check
    - Connection 종료
    """

    def __init__(self):
        """환경변수에서 설정을 읽어 Redis Client 생성"""
        settings = get_settings()
        redis_config = settings.redis

        try:
            self._client = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                decode_responses=True,  # 자동 문자열 디코딩
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # 연결 테스트
            self._client.ping()

            logger.info(
                f"✅ Redis Connection initialized: "
                f"{redis_config.host}:{redis_config.port}/{redis_config.db}"
            )

        except redis.ConnectionError as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise CacheConnectionError(
                message=f"Failed to connect to Redis: {str(e)}",
                details={
                    "host": redis_config.host,
                    "port": redis_config.port
                }
            )

    def get_client(self) -> redis.Redis:
        """
        Redis Client 반환

        Returns:
            Redis client instance
        """
        return self._client

    def health_check(self) -> bool:
        """
        Redis 연결 상태 확인

        Returns:
            연결 정상 여부
        """
        try:
            return self._client.ping()
        except Exception as e:
            logger.error(f"❌ Redis health check failed: {e}")
            return False

    def close(self):
        """Redis 연결 종료"""
        try:
            if self._client:
                self._client.close()
                logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"❌ Failed to close Redis connection: {e}")

    def __del__(self):
        """소멸자: Redis Connection 자동 종료"""
        self.close()
