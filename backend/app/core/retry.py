"""
Retry Utilities - LLM 호출 재시도 로직
Exponential backoff with jitter
"""
import asyncio
import random
from typing import TypeVar, Callable, Optional, Type, Tuple
from functools import wraps

from app.core.logging import get_parent_logger
from app.core.errors import (
    LLMException,
    LLMRateLimitException,
    LLMTimeoutException,
    LLMInvalidResponseException
)

logger = get_parent_logger("Retry")

T = TypeVar('T')


class RetryConfig:
    """재시도 설정"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on: Tuple[Type[Exception], ...] = (LLMRateLimitException, LLMTimeoutException)
    ):
        """
        Args:
            max_attempts: 최대 시도 횟수
            initial_delay: 초기 지연 시간 (초)
            max_delay: 최대 지연 시간 (초)
            exponential_base: 지수 백오프 베이스 (2 = 1s, 2s, 4s, 8s...)
            jitter: 랜덤 지터 활성화 (True 권장)
            retry_on: 재시도할 예외 타입들
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on

    def calculate_delay(self, attempt: int) -> float:
        """
        백오프 지연 시간 계산

        Args:
            attempt: 현재 시도 횟수 (0부터 시작)

        Returns:
            지연 시간 (초)
        """
        # Exponential backoff: delay = initial_delay * (base ** attempt)
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        # Jitter: 랜덤성 추가 (thundering herd 방지)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)  # 50-100% 사이

        return delay


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """
    비동기 함수 재시도 (일반 함수용)

    Args:
        func: 재시도할 비동기 함수
        *args: 함수 인자
        config: 재시도 설정
        **kwargs: 함수 키워드 인자

    Returns:
        함수 실행 결과

    Raises:
        마지막 시도의 예외
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            logger.debug(
                "retry_async",
                f"Attempt {attempt + 1}/{config.max_attempts}",
                func_name=func.__name__
            )
            return await func(*args, **kwargs)

        except config.retry_on as e:
            last_exception = e
            last_exception = e

            if attempt + 1 >= config.max_attempts:
                logger.error(
                    "retry_async",
                    f"All {config.max_attempts} attempts failed",
                    func_name=func.__name__,
                    error=str(e)
                )
                raise

            delay = config.calculate_delay(attempt)

            logger.warning(
                "retry_async",
                f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                func_name=func.__name__,
                error=str(e),
                delay=delay
            )

            await asyncio.sleep(delay)

        except Exception as e:
            # 재시도 대상이 아닌 예외는 즉시 raise
            logger.error(
                "retry_async",
                f"Non-retryable exception: {e}",
                func_name=func.__name__,
                error_type=type(e).__name__
            )
            raise

    # Unreachable (안전장치)
    if last_exception:
        raise last_exception


def with_retry(config: Optional[RetryConfig] = None):
    """
    재시도 데코레이터 (비동기 함수용)

    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        async def call_llm_api():
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(func, *args, config=config, **kwargs)

        return wrapper

    return decorator


# ============================================================
# Preset Configs
# ============================================================

# LLM API 호출용 (rate limit, timeout 재시도)
LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True,
    retry_on=(LLMRateLimitException, LLMTimeoutException)
)

# 응답 파싱 재시도 (빠른 재시도, 짧은 지연)
PARSE_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    initial_delay=0.5,
    max_delay=2.0,
    exponential_base=2.0,
    jitter=False,
    retry_on=(LLMInvalidResponseException,)
)

# 네트워크 재시도 (긴 지연)
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
    retry_on=(LLMTimeoutException, ConnectionError, TimeoutError)
)
