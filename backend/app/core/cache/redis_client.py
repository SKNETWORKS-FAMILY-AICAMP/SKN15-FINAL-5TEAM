"""
Redis Client
세션 캐시 및 Hot Storage
"""
import redis.asyncio as redis
from typing import Optional
from app.core.config import get_settings
from app.core.logging import get_repository_logger

settings = get_settings()
logger = get_repository_logger("Redis")


class RedisClient:
    """
    Redis 클라이언트 싱글톤
    """
    _instance: Optional[redis.Redis] = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """
        Redis 클라이언트 인스턴스 반환

        Returns:
            Redis 클라이언트
        """
        if cls._instance is None:
            logger.info("get_client", "Creating new Redis client")
            cls._instance = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
            )
            logger.info("get_client", "Redis client created")

        return cls._instance

    @classmethod
    async def close(cls):
        """Redis 연결 종료"""
        if cls._instance:
            logger.info("close", "Closing Redis client")
            await cls._instance.close()
            cls._instance = None
            logger.info("close", "Redis client closed")


async def get_redis() -> redis.Redis:
    """
    FastAPI 의존성 주입용 Redis 클라이언트

    Usage:
        @router.get("/test")
        async def test(redis: Redis = Depends(get_redis)):
            await redis.set("key", "value")
    """
    return await RedisClient.get_client()
