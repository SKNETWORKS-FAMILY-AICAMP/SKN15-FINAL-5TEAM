"""
Core Errors & Exception Handlers
공통 예외 정의 및 FastAPI 에러 핸들러
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional


# ============================================================
# 공통 예외 클래스
# ============================================================

class AppException(Exception):
    """
    애플리케이션 기본 예외

    모든 커스텀 예외는 이 클래스를 상속
    """
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)


# ============================================================
# 비즈니스 로직 예외
# ============================================================

class BusinessException(AppException):
    """비즈니스 규칙 위반"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code
        )


class NotFoundException(AppException):
    """리소스를 찾을 수 없음"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code
        )


class UnauthorizedException(AppException):
    """인증 실패"""
    def __init__(self, message: str = "Unauthorized", error_code: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code
        )


class ForbiddenException(AppException):
    """권한 없음"""
    def __init__(self, message: str = "Forbidden", error_code: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=error_code
        )


class ConflictException(AppException):
    """리소스 충돌 (예: 낙관적 락 실패)"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code
        )


# ============================================================
# LLM 관련 예외
# ============================================================

class LLMException(AppException):
    """LLM 호출 관련 기본 예외"""
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=error_code
        )
        self.retry_after = retry_after


class LLMRateLimitException(LLMException):
    """LLM API 레이트 리밋"""
    def __init__(self, message: str = "LLM API rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            error_code="LLM_RATE_LIMIT",
            retry_after=retry_after
        )


class LLMTimeoutException(LLMException):
    """LLM API 타임아웃"""
    def __init__(self, message: str = "LLM API timeout"):
        super().__init__(
            message=message,
            error_code="LLM_TIMEOUT"
        )


class LLMInvalidResponseException(LLMException):
    """LLM 응답 파싱 실패"""
    def __init__(self, message: str = "Invalid LLM response format"):
        super().__init__(
            message=message,
            error_code="LLM_INVALID_RESPONSE"
        )


class LLMQuotaExceededException(LLMException):
    """LLM API 할당량 초과"""
    def __init__(self, message: str = "LLM API quota exceeded"):
        super().__init__(
            message=message,
            error_code="LLM_QUOTA_EXCEEDED"
        )


# ============================================================
# FastAPI 예외 핸들러
# ============================================================

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    AppException 핸들러
    """
    from app.core.logging import get_parent_logger
    logger = get_parent_logger("ErrorHandler")

    # LLM 예외는 WARNING, 그 외는 ERROR
    if isinstance(exc, LLMException):
        logger.warning(
            "app_exception_handler",
            f"LLM Error: {exc.message}",
            error_code=exc.error_code,
            path=str(request.url.path)
        )
    else:
        logger.error(
            "app_exception_handler",
            f"App Error: {exc.message}",
            error_code=exc.error_code,
            status_code=exc.status_code,
            path=str(request.url.path)
        )

    response_content = {
        "detail": exc.message,
        "error_code": exc.error_code
    }

    # LLM 예외의 경우 retry_after 정보 포함
    if isinstance(exc, LLMException) and exc.retry_after:
        response_content["retry_after"] = exc.retry_after

    return JSONResponse(
        status_code=exc.status_code,
        content=response_content
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Pydantic 검증 실패 핸들러
    """
    from app.core.logging import get_parent_logger
    logger = get_parent_logger("ErrorHandler")

    logger.warning(
        "validation_exception_handler",
        "Validation failed",
        path=str(request.url.path),
        errors=exc.errors()
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "errors": exc.errors()
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    일반 예외 핸들러 (500 에러)
    """
    from app.core.logging import get_parent_logger
    import traceback

    logger = get_parent_logger("ErrorHandler")

    # 전체 traceback 로깅
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    logger.critical(
        "generic_exception_handler",
        f"Unhandled exception: {exc}",
        path=str(request.url.path),
        method=request.method,
        traceback=tb_str
    )

    # 개발 환경에서는 콘솔에도 출력
    print("=" * 60)
    print(f"[CRITICAL ERROR] Unhandled exception at {request.method} {request.url.path}")
    print(tb_str)
    print("=" * 60)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )


def register_exception_handlers(app):
    """
    FastAPI 앱에 예외 핸들러 등록

    Usage:
        from app.core.errors import register_exception_handlers
        app = FastAPI()
        register_exception_handlers(app)
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
