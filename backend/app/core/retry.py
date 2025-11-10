"""
[Core] 비동기 재시도(Retry) 유틸리티 모듈

이 모듈은 외부 API 호출과 같이 일시적인 오류가 발생할 수 있는 비동기 함수에 대해
자동 재시도 로직을 적용하는 기능을 제공합니다.
"Exponential Backoff with Jitter" 전략을 사용하여 안정적인 재시도를 구현합니다.
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

# 제네릭 타입을 위한 TypeVar 정의
T = TypeVar('T')


# ============================================================
# 재시도 설정 클래스
# ============================================================
class RetryConfig:
    """
    재시도 동작을 제어하기 위한 설정 정보를 담는 클래스입니다.
    """

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
        재시도 설정을 초기화합니다.

        Args:
            max_attempts (int): 재시도를 포함한 최대 시도 횟수.
            initial_delay (float): 첫 재시도 전의 초기 대기 시간 (초).
            max_delay (float): 재시도 대기 시간의 최댓값 (초).
            exponential_base (float): 지수 백오프의 밑. 재시도할 때마다 대기 시간이 이 값의 거듭제곱으로 증가합니다.
            jitter (bool): 대기 시간에 랜덤성을 추가할지 여부. True를 강력히 권장합니다.
            retry_on (Tuple[Type[Exception], ...]): 어떤 예외가 발생했을 때 재시도할지를 정의한 튜플.
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on

    def calculate_delay(self, attempt: int) -> float:
        """
        "Exponential Backoff with Jitter" 전략에 따라 다음 재시도까지의 대기 시간을 계산합니다.

        - Exponential Backoff: 재시도를 할수록 대기 시간을 지수적으로 늘리는 전략.
          (예: 1초 -> 2초 -> 4초 -> 8초...)
          이를 통해 일시적인 과부하 상태의 서비스가 복구될 시간을 줍니다.

        - Jitter: 계산된 대기 시간에 약간의 랜덤성을 추가하는 전략.
          만약 여러 클라이언트가 동시에 오류를 겪고 동일한 백오프 로직으로 재시도하면,
          모두가 같은 시간에 다시 요청을 보내 서버에 또 다른 부하를 유발할 수 있습니다(Thundering Herd 문제).
          Jitter는 이 동시 재시도를 분산시켜 시스템 안정성을 높입니다.

        Args:
            attempt (int): 현재 재시도 횟수 (0부터 시작).

        Returns:
            float: 실제 대기할 시간 (초).
        """
        # 지수 백오프 계산
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        # Jitter 추가 (계산된 딜레이의 50% ~ 100% 사이의 랜덤 값)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


# ============================================================
# 핵심 재시도 로직 함수
# ============================================================
async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """
    주어진 비동기 함수에 대해 재시도 로직을 적용하여 실행합니다.

    Args:
        func (Callable): 재시도할 대상 비동기 함수.
        *args: 함수에 전달될 위치 인자.
        config (Optional[RetryConfig]): 재시도 설정. None이면 기본 설정을 사용.
        **kwargs: 함수에 전달될 키워드 인자.

    Returns:
        T: 함수가 성공적으로 실행되었을 때의 반환 값.

    Raises:
        Exception: 최대 재시도 횟수를 초과했거나, 재시도 대상이 아닌 예외가 발생했을 때.
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            logger.debug(
                "retry_async", f"Attempt {attempt + 1}/{config.max_attempts}",
                func_name=func.__name__
            )
            return await func(*args, **kwargs)

        except config.retry_on as e:
            last_exception = e
            if attempt + 1 >= config.max_attempts:
                logger.error(
                    "retry_async", f"All {config.max_attempts} attempts failed for {func.__name__}",
                    error=str(e)
                )
                raise  # 마지막 예외를 다시 발생시킴

            delay = config.calculate_delay(attempt)
            logger.warning(
                "retry_async", f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                func_name=func.__name__, error=str(e)
            )
            await asyncio.sleep(delay)

        except Exception as e:
            # 재시도 대상이 아닌 예외는 즉시 다시 발생시킵니다.
            logger.error(
                "retry_async", f"Non-retryable exception occurred: {e}",
                func_name=func.__name__, error_type=type(e).__name__
            )
            raise

    # 루프가 모두 실패하고 끝났을 경우 (이론적으로는 도달하지 않음)
    if last_exception:
        raise last_exception


# ============================================================
# 재시도 데코레이터
# ============================================================
def with_retry(config: Optional[RetryConfig] = None):
    """
    비동기 함수에 재시도 로직을 적용하는 데코레이터입니다.

    Args:
        config (Optional[RetryConfig]): 사용할 재시도 설정.

    Usage:
        @with_retry(LLM_RETRY_CONFIG)
        async def call_unstable_api():
            ...
    """
    final_config = config if config is not None else RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(func, *args, config=final_config, **kwargs)
        return wrapper
    return decorator


# ============================================================
# 사전 정의된 재시도 설정 (Preset Configs)
# ============================================================
# 자주 사용되는 재시도 시나리오에 대한 설정을 미리 정의해 둡니다.

# LLM API 호출용: Rate Limit 또는 Timeout 발생 시 재시도
LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    retry_on=(LLMRateLimitException, LLMTimeoutException)
)

# LLM 응답 파싱용: 응답 형식이 잘못되었을 때 짧게 재시도
PARSE_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    initial_delay=0.5,
    max_delay=2.0,
    jitter=False,
    retry_on=(LLMInvalidResponseException,)
)

# 일반적인 네트워크 오류용: 연결 오류 등에 대해 더 길게 재시도
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=2.0,
    max_delay=60.0,
    retry_on=(LLMTimeoutException, ConnectionError, TimeoutError)
)
