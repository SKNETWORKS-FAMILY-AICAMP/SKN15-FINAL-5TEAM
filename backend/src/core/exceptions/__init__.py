"""
Core Exceptions - 커스텀 예외 계층

계층별 예외 정의:
- base: 기본 예외 클래스
- domain: 도메인 계층 예외
- infrastructure: 인프라 계층 예외
- validation: 검증 예외
"""

from .base import KimeBaseException, KimeErrorCode

# Domain Exceptions
from .domain import (
    InvalidStateError,
    BusinessRuleViolationError,
    InsufficientCreditsError,
    SessionExpiredError,
    InvalidStageTransitionError
)

# Infrastructure Exceptions
from .infrastructure import (
    DatabaseConnectionError,
    DatabaseQueryError,
    CacheConnectionError,
    CacheOperationError,
    LLMProviderError,
    RateLimitExceededError
)

# Validation Exceptions
from .validation import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    InvalidInputError
)

__all__ = [
    # Base
    "KimeBaseException",
    "KimeErrorCode",

    # Domain
    "InvalidStateError",
    "BusinessRuleViolationError",
    "InsufficientCreditsError",
    "SessionExpiredError",
    "InvalidStageTransitionError",

    # Infrastructure
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "CacheConnectionError",
    "CacheOperationError",
    "LLMProviderError",
    "RateLimitExceededError",

    # Validation
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "InvalidInputError",
]
