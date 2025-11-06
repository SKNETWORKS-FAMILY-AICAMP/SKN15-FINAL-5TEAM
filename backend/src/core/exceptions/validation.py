"""
Validation Exceptions - 검증 예외

입력 검증, 인증, 권한 검증 등에서 발생하는 예외들.
"""

from typing import Optional, Dict, Any, List
from .base import KimeBaseException, KimeErrorCode


class ValidationError(KimeBaseException):
    """입력 검증 실패"""

    def __init__(
        self,
        field: Optional[str] = None,
        message: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, str]]] = None
    ):
        message = message or "Validation failed"
        details: Dict[str, Any] = {}

        if field:
            details["field"] = field
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(
            error_code=KimeErrorCode.VALIDATION_ERROR,
            message=message,
            details=details
        )


class AuthenticationError(KimeBaseException):
    """인증 실패"""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=KimeErrorCode.AUTHENTICATION_ERROR,
            message=message,
            details=details
        )


class AuthorizationError(KimeBaseException):
    """권한 없음"""

    def __init__(
        self,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        message: Optional[str] = None
    ):
        message = message or "Authorization failed"
        details: Dict[str, Any] = {}

        if resource:
            details["resource"] = resource
        if action:
            details["action"] = action

        super().__init__(
            error_code=KimeErrorCode.AUTHORIZATION_ERROR,
            message=message,
            details=details
        )


class InvalidInputError(KimeBaseException):
    """잘못된 입력"""

    def __init__(
        self,
        parameter: Optional[str] = None,
        value: Optional[Any] = None,
        message: Optional[str] = None
    ):
        message = message or "Invalid input"
        details: Dict[str, Any] = {}

        if parameter:
            details["parameter"] = parameter
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            error_code=KimeErrorCode.INVALID_INPUT,
            message=message,
            details=details
        )
