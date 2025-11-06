"""
Base Exception - 모든 커스텀 예외의 기본 클래스
"""

from enum import Enum
from typing import Optional, Dict, Any


class KimeErrorCode(Enum):
    """에러 코드 정의"""
    # Domain Errors (1000~1999)
    INVALID_STATE = 1000
    BUSINESS_RULE_VIOLATION = 1001
    INSUFFICIENT_CREDITS = 1002
    SESSION_EXPIRED = 1003
    INVALID_STAGE_TRANSITION = 1004

    # Infrastructure Errors (2000~2999)
    DATABASE_CONNECTION_ERROR = 2000
    DATABASE_QUERY_ERROR = 2001
    CACHE_CONNECTION_ERROR = 2002
    CACHE_OPERATION_ERROR = 2003
    LLM_PROVIDER_ERROR = 2004
    RATE_LIMIT_EXCEEDED = 2005

    # Validation Errors (3000~3999)
    VALIDATION_ERROR = 3000
    AUTHENTICATION_ERROR = 3001
    AUTHORIZATION_ERROR = 3002
    INVALID_INPUT = 3003

    # Unknown Error
    UNKNOWN_ERROR = 9999


class KimeBaseException(Exception):
    """
    KIME Chat의 모든 커스텀 예외의 기본 클래스

    Attributes:
        error_code: 에러 코드 (Enum)
        message: 에러 메시지
        details: 추가 상세 정보
    """

    def __init__(
        self,
        error_code: KimeErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환 (API 응답용)"""
        return {
            "error_code": self.error_code.value,
            "error_name": self.error_code.name,
            "message": self.message,
            "details": self.details
        }

    def __str__(self) -> str:
        return f"[{self.error_code.name}] {self.message}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(error_code={self.error_code}, message='{self.message}')"
