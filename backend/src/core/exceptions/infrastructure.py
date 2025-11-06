"""
Infrastructure Exceptions - 인프라 계층 예외

Database, Cache, LLM 등 외부 시스템 연동 중 발생하는 예외들.
"""

from typing import Optional, Dict, Any
from .base import KimeBaseException, KimeErrorCode


class DatabaseConnectionError(KimeBaseException):
    """데이터베이스 연결 실패"""

    def __init__(
        self,
        message: str = "Database connection failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=KimeErrorCode.DATABASE_CONNECTION_ERROR,
            message=message,
            details=details
        )


class DatabaseQueryError(KimeBaseException):
    """데이터베이스 쿼리 실행 실패"""

    def __init__(
        self,
        query: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = message or "Database query failed"
        details = details or {}
        if query:
            details["query"] = query

        super().__init__(
            error_code=KimeErrorCode.DATABASE_QUERY_ERROR,
            message=message,
            details=details
        )


class CacheConnectionError(KimeBaseException):
    """캐시 연결 실패 (Redis 등)"""

    def __init__(
        self,
        message: str = "Cache connection failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=KimeErrorCode.CACHE_CONNECTION_ERROR,
            message=message,
            details=details
        )


class CacheOperationError(KimeBaseException):
    """캐시 작업 실패 (get/set/delete 등)"""

    def __init__(
        self,
        operation: str,
        key: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = message or f"Cache operation failed: {operation}"
        details = details or {}
        details["operation"] = operation
        if key:
            details["key"] = key

        super().__init__(
            error_code=KimeErrorCode.CACHE_OPERATION_ERROR,
            message=message,
            details=details
        )


class LLMProviderError(KimeBaseException):
    """LLM Provider 오류 (OpenAI, Anthropic 등)"""

    def __init__(
        self,
        provider: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = message or f"LLM provider error: {provider}"
        details = details or {}
        details["provider"] = provider

        super().__init__(
            error_code=KimeErrorCode.LLM_PROVIDER_ERROR,
            message=message,
            details=details
        )


class RateLimitExceededError(KimeBaseException):
    """Rate Limit 초과 (API 호출 제한)"""

    def __init__(
        self,
        service: str,
        retry_after: Optional[int] = None,
        message: Optional[str] = None
    ):
        message = message or f"Rate limit exceeded: {service}"
        details: Dict[str, Any] = {"service": service}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            error_code=KimeErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details
        )
