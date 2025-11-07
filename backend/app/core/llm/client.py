"""
LLM Client - OpenAI API 통합
4-Layer 아키텍처용 간소화 버전
"""
import json
import hashlib
import time
from typing import Dict, List, Optional, Any
from collections import deque
from openai import OpenAI
from app.core.config import get_settings
from app.core.logging import get_parent_logger

settings = get_settings()
logger = get_parent_logger("LLM")


class RateLimiter:
    """
    API Rate Limiter
    Thread-safe rate limiting for LLM API calls
    """
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    def acquire(self):
        """요청 허가 획득 (필요시 대기)"""
        now = time.time()

        # 오래된 요청 제거
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()

        # Rate limit 체크
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                logger.warning("rate_limiter", f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                return self.acquire()

        self.requests.append(now)


class LLMClient:
    """
    LLM API 클라이언트 (OpenAI)

    Features:
    - OpenAI API 통합
    - Rate limiting
    - Response caching
    - Error handling
    - Structured output (JSON mode)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_caching: bool = True,
        max_requests_per_minute: int = 60
    ):
        """
        LLM 클라이언트 초기화

        Args:
            api_key: OpenAI API 키 (None이면 settings에서 가져옴)
            model: 사용할 모델 (None이면 settings에서 가져옴)
            enable_caching: 응답 캐싱 활성화
            max_requests_per_minute: 분당 최대 요청 수
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.temperature = settings.OPENAI_TEMPERATURE
        self.max_tokens = settings.OPENAI_MAX_TOKENS

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

        self.client = OpenAI(api_key=self.api_key)
        self.enable_caching = enable_caching
        self.cache: Dict[str, str] = {}
        self.rate_limiter = RateLimiter(max_requests=max_requests_per_minute, time_window=60)
        self.call_count = 0

        logger.info("__init__", "LLMClient initialized", model=self.model)

    def _get_cache_key(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        model: str
    ) -> str:
        """캐시 키 생성"""
        cache_str = f"{system_prompt}|{user_prompt}|{temperature}|{model}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        use_cache: bool = True,
    ) -> str:
        """
        LLM 호출 (텍스트 응답)

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 창의성 조절 (0.0~1.0)
            max_tokens: 최대 토큰 수
            model: 사용할 모델 (None이면 기본값)
            use_cache: 캐시 사용 여부

        Returns:
            LLM 응답 텍스트
        """
        target_model = model or self.model
        resolved_temp = temperature if temperature is not None else self.temperature
        resolved_max_tokens = max_tokens or self.max_tokens

        # 캐시 확인
        if self.enable_caching and use_cache:
            cache_key = self._get_cache_key(system_prompt, user_prompt, resolved_temp, target_model)
            if cache_key in self.cache:
                logger.info("call", "✅ Cache hit", model=target_model)
                return self.cache[cache_key]

        # Rate limiting
        self.rate_limiter.acquire()

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            logger.info(
                "call",
                "🤖 Calling LLM",
                model=target_model,
                temp=resolved_temp,
                max_tokens=resolved_max_tokens,
                system_len=len(system_prompt),
                user_len=len(user_prompt)
            )

            kwargs = {
                "model": target_model,
                "messages": messages,
                "temperature": resolved_temp,
            }

            if resolved_max_tokens:
                kwargs["max_tokens"] = resolved_max_tokens

            response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content or ""
            self.call_count += 1

            # 캐시 저장
            if self.enable_caching and use_cache:
                self.cache[cache_key] = content

            logger.info(
                "call",
                "✅ LLM response received",
                model=target_model,
                response_len=len(content),
                call_count=self.call_count
            )

            return content

        except Exception as e:
            logger.error("call", f"❌ LLM API call failed: {e}", model=target_model)
            raise

    def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        LLM 호출 (JSON 응답)

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 창의성 조절
            max_tokens: 최대 토큰 수
            model: 사용할 모델
            use_cache: 캐시 사용 여부

        Returns:
            파싱된 JSON Dict
        """
        target_model = model or self.model
        resolved_temp = temperature if temperature is not None else self.temperature
        resolved_max_tokens = max_tokens or self.max_tokens

        # 캐시 확인
        cache_key = None
        if self.enable_caching and use_cache:
            cache_key = self._get_cache_key(system_prompt, user_prompt, resolved_temp, target_model) + "_json"
            if cache_key in self.cache:
                logger.info("call_json", "✅ Cache hit", model=target_model)
                return json.loads(self.cache[cache_key])

        # Rate limiting
        self.rate_limiter.acquire()

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            logger.info(
                "call_json",
                "🤖 Calling LLM (JSON mode)",
                model=target_model,
                temp=resolved_temp,
                max_tokens=resolved_max_tokens
            )

            kwargs = {
                "model": target_model,
                "messages": messages,
                "temperature": resolved_temp,
                "response_format": {"type": "json_object"}
            }

            if resolved_max_tokens:
                kwargs["max_tokens"] = resolved_max_tokens

            response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content or "{}"
            self.call_count += 1

            # JSON 파싱
            try:
                result = json.loads(content)
            except json.JSONDecodeError as je:
                logger.error("call_json", f"❌ JSON parsing failed: {je}", content_preview=content[:200])
                # Fallback: 빈 딕셔너리 반환
                result = {}

            # 캐시 저장
            if self.enable_caching and use_cache and cache_key:
                self.cache[cache_key] = content

            logger.info(
                "call_json",
                "✅ LLM JSON response received",
                model=target_model,
                keys=list(result.keys()) if isinstance(result, dict) else None,
                call_count=self.call_count
            )

            return result

        except Exception as e:
            logger.error("call_json", f"❌ LLM JSON API call failed: {e}", model=target_model)
            raise

    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
        logger.info("clear_cache", "Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            "call_count": self.call_count,
            "cache_size": len(self.cache),
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
