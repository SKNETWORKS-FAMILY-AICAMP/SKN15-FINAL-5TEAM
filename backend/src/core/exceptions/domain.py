"""
Domain Exceptions - 도메인 계층 예외

비즈니스 로직 수행 중 발생하는 예외들.
"""

from typing import Optional, Dict, Any
from .base import KimeBaseException, KimeErrorCode


class InvalidStateError(KimeBaseException):
    """상태 전이 오류 (잘못된 State 접근/수정)"""

    def __init__(
        self,
        message: str = "Invalid state transition",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=KimeErrorCode.INVALID_STATE,
            message=message,
            details=details
        )


class BusinessRuleViolationError(KimeBaseException):
    """비즈니스 규칙 위반"""

    def __init__(
        self,
        message: str = "Business rule violation",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=KimeErrorCode.BUSINESS_RULE_VIOLATION,
            message=message,
            details=details
        )


class InsufficientCreditsError(KimeBaseException):
    """크레딧 부족"""

    def __init__(
        self,
        required_credits: int,
        current_credits: int,
        message: Optional[str] = None
    ):
        message = message or f"Insufficient credits: required {required_credits}, have {current_credits}"
        super().__init__(
            error_code=KimeErrorCode.INSUFFICIENT_CREDITS,
            message=message,
            details={
                "required_credits": required_credits,
                "current_credits": current_credits
            }
        )


class SessionExpiredError(KimeBaseException):
    """세션 만료"""

    def __init__(
        self,
        session_id: str,
        message: Optional[str] = None
    ):
        message = message or f"Session expired: {session_id}"
        super().__init__(
            error_code=KimeErrorCode.SESSION_EXPIRED,
            message=message,
            details={"session_id": session_id}
        )


class InvalidStageTransitionError(KimeBaseException):
    """스테이지 전이 오류"""

    def __init__(
        self,
        from_stage: str,
        to_stage: str,
        message: Optional[str] = None
    ):
        message = message or f"Invalid stage transition: {from_stage} -> {to_stage}"
        super().__init__(
            error_code=KimeErrorCode.INVALID_STAGE_TRANSITION,
            message=message,
            details={"from_stage": from_stage, "to_stage": to_stage}
        )
