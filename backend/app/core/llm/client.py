"""
LLM Client - OpenAI API 통합
4-Layer 아키텍처용 간소화 버전
"""
import json
import hashlib
import time
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
        self.cache: Dict[str, tuple[str, float]] = {}  # {key: (response, expiry_time)}
        self.cache_ttl = 3600  # 1시간 TTL
        self.rate_limiter = RateLimiter(max_requests=max_requests_per_minute, time_window=60)
        self.call_count = 0

        logger.info("__init__", "LLMClient initialized", model=self.model, cache_ttl=self.cache_ttl)

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

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """
        TTL 기반 캐시 조회

        Args:
            cache_key: 캐시 키

        Returns:
            캐시된 응답 (없거나 만료되면 None)
        """
        if cache_key not in self.cache:
            return None

        cached_response, expiry_time = self.cache[cache_key]
        current_time = time.time()

        # TTL 만료 체크
        if current_time > expiry_time:
            # 만료된 캐시 제거
            del self.cache[cache_key]
            logger.debug("_get_from_cache", "Cache expired", cache_key=cache_key[:8])
            return None

        logger.info("_get_from_cache", "✅ Cache hit", cache_key=cache_key[:8])
        return cached_response

    def _save_to_cache(self, cache_key: str, response: str):
        """
        TTL 기반 캐시 저장

        Args:
            cache_key: 캐시 키
            response: 응답 문자열
        """
        expiry_time = time.time() + self.cache_ttl
        self.cache[cache_key] = (response, expiry_time)
        logger.debug("_save_to_cache", "Cached response", cache_key=cache_key[:8], ttl=self.cache_ttl)

    @with_retry(LLM_RETRY_CONFIG)
    async def _call_api_with_retry(self, **kwargs) -> Any:
        """
        OpenAI API 호출 (재시도 로직 포함)

        Args:
            **kwargs: create() 메서드에 전달할 인자

        Returns:
            API 응답

        Raises:
            LLMRateLimitException: Rate limit 초과
            LLMTimeoutException: 타임아웃
            LLMException: 기타 LLM 에러
        """
        try:
            response = self.client.chat.completions.create(**kwargs)
            return response

        except RateLimitError as e:
            # Rate limit 에러 → 재시도 대상
            logger.warning("_call_api_with_retry", f"Rate limit hit: {e}")
            raise LLMRateLimitException(str(e))

        except (APITimeoutError, TimeoutError) as e:
            # Timeout 에러 → 재시도 대상
            logger.warning("_call_api_with_retry", f"API timeout: {e}")
            raise LLMTimeoutException(str(e))

        except APIConnectionError as e:
            # Connection 에러 → 재시도 대상
            logger.warning("_call_api_with_retry", f"Connection error: {e}")
            raise LLMTimeoutException(f"Connection failed: {e}")

        except Exception as e:
            # 기타 에러 → 재시도 안 함
            logger.error("_call_api_with_retry", f"API call failed: {e}")
            raise LLMException(f"LLM API error: {e}")

    async def call(
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
        cache_key = None
        if self.enable_caching and use_cache:
            cache_key = self._get_cache_key(system_prompt, user_prompt, resolved_temp, target_model)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                return cached_response

        # Rate limiting
        self.rate_limiter.acquire()

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

        # API 호출 (재시도 로직 포함)
        response = await self._call_api_with_retry(**kwargs)

        content = response.choices[0].message.content or ""
        self.call_count += 1

        # 캐시 저장
        if self.enable_caching and use_cache and cache_key:
            self._save_to_cache(cache_key, content)

        logger.info(
            "call",
            "✅ LLM response received",
            model=target_model,
            response_len=len(content),
            call_count=self.call_count
        )

        return content

    async def call_json(
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
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                return json.loads(cached_response)

        # Rate limiting
        self.rate_limiter.acquire()

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

        # API 호출 (재시도 로직 포함)
        response = await self._call_api_with_retry(**kwargs)

        content = response.choices[0].message.content or "{}"
        self.call_count += 1

        # JSON 파싱
        try:
            result = json.loads(content)
        except json.JSONDecodeError as je:
            logger.error("call_json", f"❌ JSON parsing failed: {je}", content_preview=content[:200])
            raise LLMInvalidResponseException(f"Failed to parse JSON response: {je}")

        # 캐시 저장
        if self.enable_caching and use_cache and cache_key:
            self._save_to_cache(cache_key, content)

        logger.info(
            "call_json",
            "✅ LLM JSON response received",
            model=target_model,
            keys=list(result.keys()) if isinstance(result, dict) else None,
            call_count=self.call_count
        )

        return result

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: Optional[str] = None,
        model: str = "dall-e-3"
    ) -> Dict[str, Any]:
        """
        이미지 생성 (DALL-E)

        Args:
            prompt: 이미지 생성 프롬프트
            size: 이미지 크기 (1024x1024, 1024x1792, 1792x1024)
            quality: 품질 (standard, hd)
            style: 스타일 (vivid, natural)
            model: 모델명 (dall-e-2, dall-e-3)

        Returns:
            생성 결과
            {
                "url": str,  # 생성된 이미지 URL
                "revised_prompt": str,  # OpenAI가 수정한 프롬프트
                "model": str,  # 사용된 모델명
            }
        """
        logger.info("generate_image", "🎨 Generating image with DALL-E",
                   model=model, size=size, quality=quality)

        # Rate limiting
        self.rate_limiter.acquire()

        try:
            # OpenAI Image Generation API 호출
            kwargs = {
                "model": model,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "n": 1,
            }

            if style and model == "dall-e-3":
                kwargs["style"] = style

            response = self.client.images.generate(**kwargs)

            # 결과 추출
            image_data = response.data[0]
            result = {
                "url": image_data.url,
                "revised_prompt": getattr(image_data, "revised_prompt", prompt),
                "model": model
            }

            self.call_count += 1

            logger.info("generate_image", "✅ Image generated successfully",
                       model=model, call_count=self.call_count)

            return result

        except RateLimitError as e:
            logger.error("generate_image", f"❌ Rate limit exceeded: {e}")
            raise LLMRateLimitException(f"Image generation rate limit exceeded: {e}")
        except APITimeoutError as e:
            logger.error("generate_image", f"❌ API timeout: {e}")
            raise LLMTimeoutException(f"Image generation timeout: {e}")
        except Exception as e:
            logger.error("generate_image", f"❌ Image generation failed: {e}")
            raise LLMException(f"Image generation failed: {e}")

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
