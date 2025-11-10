"""
[Core/LLM] LLM API 클라이언트 모듈

이 모듈은 OpenAI와 같은 외부 LLM(Large Language Model) API와 상호작용하기 위한
고수준 클라이언트를 제공합니다. 재시도, 캐싱, 속도 제한 등 외부 API 연동에
필수적인 기능들을 캡슐화하여 안정성을 높입니다.
"""
import json
import hashlib
import time
import asyncio
from typing import Dict, List, Optional, Any
from collections import deque
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
from app.core.config import get_settings
from app.core.logging import get_parent_logger
from app.core.errors import (
    LLMRateLimitException,
    LLMTimeoutException,
    LLMInvalidResponseException,
    LLMException
)
from app.core.retry import with_retry, LLM_RETRY_CONFIG

settings = get_settings()
logger = get_parent_logger("LLMClient")


# ============================================================
# API 호출 속도 제한 클래스 (Rate Limiter)
# ============================================================
class RateLimiter:
    """
    Sliding Window 알고리즘을 사용한 간단한 API 호출 속도 제한 클래스입니다.
    지정된 시간(time_window) 동안의 최대 요청 수(max_requests)를 관리합니다.
    """
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    async def acquire(self):
        """
        요청을 수행할 권한을 획득합니다. 제한에 도달하면 필요 시간만큼 비동기적으로 대기합니다.

        NOTE: (수정됨) 기존의 time.sleep()은 동기 함수로, 전체 이벤트 루프를 차단하는
              심각한 성능 문제를 유발했습니다. 비동기 환경에 맞는 await asyncio.sleep()으로 수정되었습니다.
        """
        now = time.time()

        # 시간 윈도우를 벗어난 오래된 요청 타임스탬프를 제거합니다.
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()

        # 현재 윈도우 내의 요청 수가 최대치를 초과했는지 확인합니다.
        if len(self.requests) >= self.max_requests:
            # 가장 오래된 요청 시간을 기준으로 대기해야 할 시간을 계산합니다.
            sleep_time = self.requests[0] + self.time_window - now
            if sleep_time > 0:
                logger.warning("rate_limiter", f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                # 대기 후 다시 acquire를 호출하여 상태를 재확인합니다.
                return await self.acquire()

        self.requests.append(now)


# ============================================================
# LLM 클라이언트 클래스
# ============================================================
class LLMClient:
    """
    OpenAI LLM API와 상호작용하기 위한 주 클라이언트 클래스입니다.

    주요 기능:
    - OpenAI API 호출 (텍스트 및 JSON 모드)
    - API 호출 속도 제한 (Rate Limiting)
    - 응답 캐싱 (In-memory 또는 Redis)
    - 지수 백오프를 사용한 자동 재시도
    - 구조화된 오류 처리
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_caching: bool = True,
        max_requests_per_minute: int = 60
    ):
        """
        LLM 클라이언트를 초기화합니다.

        Args:
            api_key (Optional[str]): OpenAI API 키. None이면 설정 파일에서 가져옵니다.
            model (Optional[str]): 사용할 모델. None이면 설정 파일에서 가져옵니다.
            enable_caching (bool): 응답 캐싱 활성화 여부.
            max_requests_per_minute (int): 분당 최대 요청 수.
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.temperature = settings.OPENAI_TEMPERATURE
        self.max_tokens = settings.OPENAI_MAX_TOKENS

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

        self.client = OpenAI(api_key=self.api_key)
        self.enable_caching = enable_caching
        self.rate_limiter = RateLimiter(max_requests=max_requests_per_minute, time_window=60)
        self.call_count = 0

        # NOTE: 아래 캐시는 동시성 문제가 있습니다.
        #       여러 코루틴이 동시에 접근할 경우 Race Condition이 발생할 수 있습니다.
        #       asyncio.Lock으로 보호하거나, 더 나은 방법으로 Redis를 사용하는 것을 권장합니다.
        self.cache: Dict[str, tuple[str, float]] = {}  # {key: (response, expiry_time)}
        self._cache_lock = asyncio.Lock()  # 동시성 제어를 위한 Lock
        self.cache_ttl = 3600  # 캐시 만료 시간 (1시간)

        logger.info("__init__", "LLMClient initialized", model=self.model, cache_ttl=self.cache_ttl)

    def _get_cache_key(
        self, system_prompt: str, user_prompt: str, temperature: float, model: str
    ) -> str:
        """API 요청 파라미터를 기반으로 고유한 캐시 키를 생성합니다."""
        cache_str = f"{system_prompt}|{user_prompt}|{temperature}|{model}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    async def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """
        만료 시간(TTL)을 고려하여 캐시에서 응답을 조회합니다.
        NOTE: 동시성 안전을 위해 asyncio.Lock으로 보호됩니다.
        """
        async with self._cache_lock:
            if cache_key not in self.cache:
                return None

            cached_response, expiry_time = self.cache[cache_key]
            if time.time() > expiry_time:
                del self.cache[cache_key]
                logger.debug("_get_from_cache", "Cache expired", cache_key=cache_key[:8])
                return None

            logger.info("_get_from_cache", "✅ Cache hit", cache_key=cache_key[:8])
            return cached_response

    async def _save_to_cache(self, cache_key: str, response: str):
        """
        응답을 캐시에 저장합니다.
        NOTE: 동시성 안전을 위해 asyncio.Lock으로 보호됩니다.
        """
        async with self._cache_lock:
            expiry_time = time.time() + self.cache_ttl
            self.cache[cache_key] = (response, expiry_time)
            logger.debug("_save_to_cache", "Cached response", cache_key=cache_key[:8], ttl=self.cache_ttl)

    @with_retry(LLM_RETRY_CONFIG)
    async def _call_api_with_retry(self, **kwargs) -> Any:
        """
        `@with_retry` 데코레이터가 적용된 OpenAI API 실제 호출 함수입니다.
        RateLimit, Timeout 등의 오류 발생 시 자동으로 재시도합니다.
        """
        try:
            return self.client.chat.completions.create(**kwargs)
        except RateLimitError as e:
            raise LLMRateLimitException(str(e))
        except (APITimeoutError, TimeoutError) as e:
            raise LLMTimeoutException(str(e))
        except APIConnectionError as e:
            raise LLMException(f"Connection failed: {e}")
        except Exception as e:
            logger.error("_call_api_with_retry", f"Unhandled API call failed: {e}", exc_info=True)
            raise LLMException(f"LLM API error: {e}")

    async def call(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> str:
        """
        LLM API를 호출하여 텍스트 응답을 받습니다.

        Args:
            system_prompt (str): 시스템 프롬프트.
            user_prompt (str): 사용자 프롬프트.
            **kwargs: temperature, max_tokens, model, use_cache 등 추가 옵션.

        Returns:
            str: LLM이 생성한 텍스트 응답.
        """
        use_cache = kwargs.get("use_cache", True)
        target_model = kwargs.get("model", self.model)
        resolved_temp = kwargs.get("temperature", self.temperature)
        
        cache_key = None
        if self.enable_caching and use_cache:
            cache_key = self._get_cache_key(system_prompt, user_prompt, resolved_temp, target_model)
            if (cached_response := await self._get_from_cache(cache_key)):
                return cached_response

        await self.rate_limiter.acquire()

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        api_kwargs = {
            "model": target_model,
            "messages": messages,
            "temperature": resolved_temp,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        logger.info("call", "🤖 Calling LLM", **api_kwargs)

        response = await self._call_api_with_retry(**api_kwargs)
        content = response.choices[0].message.content or ""
        self.call_count += 1

        if self.enable_caching and use_cache and cache_key:
            await self._save_to_cache(cache_key, content)

        logger.info("call", "✅ LLM response received", response_len=len(content))
        return content

    async def call_json(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> Dict[str, Any]:
        """
        LLM API를 호출하여 JSON 형식의 응답을 받습니다. (JSON 모드 사용)

        Args:
            system_prompt (str): 시스템 프롬프트.
            user_prompt (str): 사용자 프롬프트.
            **kwargs: temperature, max_tokens, model, use_cache 등 추가 옵션.

        Returns:
            Dict[str, Any]: LLM이 생성하고 파싱된 JSON 객체.
        """
        use_cache = kwargs.get("use_cache", True)
        target_model = kwargs.get("model", self.model)
        resolved_temp = kwargs.get("temperature", self.temperature)

        cache_key = None
        if self.enable_caching and use_cache:
            cache_key = self._get_cache_key(system_prompt, user_prompt, resolved_temp, target_model) + "_json"
            if (cached_response := await self._get_from_cache(cache_key)):
                return json.loads(cached_response)

        await self.rate_limiter.acquire()

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        api_kwargs = {
            "model": target_model,
            "messages": messages,
            "temperature": resolved_temp,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "response_format": {"type": "json_object"},
        }
        logger.info("call_json", "🤖 Calling LLM (JSON mode)", **api_kwargs)

        response = await self._call_api_with_retry(**api_kwargs)
        content = response.choices[0].message.content or "{}"
        self.call_count += 1

        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("call_json", f"❌ JSON parsing failed: {e}", content_preview=content[:200])
            raise LLMInvalidResponseException(f"Failed to parse JSON response: {e}")

        if self.enable_caching and use_cache and cache_key:
            await self._save_to_cache(cache_key, content)

        logger.info("call_json", "✅ LLM JSON response received", keys=list(result.keys()))
        return result

    async def clear_cache(self):
        """인메모리 캐시를 모두 지웁니다."""
        async with self._cache_lock:
            self.cache.clear()
        logger.info("clear_cache", "In-memory cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """클라이언트의 현재 통계 정보를 반환합니다."""
        return {
            "call_count": self.call_count,
            "cache_size": len(self.cache),
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
