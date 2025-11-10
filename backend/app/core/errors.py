"""
[Core] 공통 예외 클래스 및 전역 예외 핸들러 모듈

이 모듈은 애플리케이션 전반에서 사용될 커스텀 예외 클래스들과,
FastAPI 애플리케이션에 적용될 전역 예외 핸들러들을 정의합니다.

- 커스텀 예외: 도메인별로 의미 있는 예외를 발생시켜 코드의 가독성과
  에러 처리 로직의 명확성을 높입니다.
- 전역 핸들러: 처리되지 않은 예외를 일관된 JSON 형식의 HTTP 응답으로 변환하여
  클라이언트에 반환하고, 서버에 상세한 로그를 남깁니다.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional


# ============================================================
# 기본 예외 클래스 (Base Exception)
# ============================================================
class AppException(Exception):
    """
    애플리케이션의 모든 커스텀 예외가 상속받는 기본 클래스입니다.

    Attributes:
        message (str): 클라이언트에게 전달될 에러 메시지.
        status_code (int): HTTP 상태 코드.
        error_code (str): 클라이언트가 에러 유형을 식별할 수 있는 고유 에러 코드.
    """
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        # error_code가 명시되지 않으면, 예외 클래스의 이름을 코드로 사용합니다.
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)


# ============================================================
# 공통 비즈니스 로직 예외
# ============================================================
class BusinessException(AppException):
    """비즈니스 규칙을 위반했을 때 발생하는 예외. (예: 잘못된 요청 값)"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code
        )


class NotFoundException(AppException):
    """요청한 리소스를 찾을 수 없을 때 발생하는 예외. (예: 존재하지 않는 사용자 ID 조회)"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code
        )


class UnauthorizedException(AppException):
    """인증(Authentication)에 실패했을 때 발생하는 예외. (예: 유효하지 않은 토큰)"""
    def __init__(self, message: str = "Unauthorized", error_code: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code
        )


class ForbiddenException(AppException):
    """인가(Authorization)에 실패했을 때 발생하는 예외. (예: 관리자만 접근 가능한 리소스에 일반 사용자가 접근)"""
    def __init__(self, message: str = "Forbidden", error_code: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=error_code
        )


class ConflictException(AppException):
    """요청이 현재 서버의 상태와 충돌할 때 발생하는 예외. (예: 이미 존재하는 사용자 이름으로 회원가입 시도)"""
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
    """LLM API 호출과 관련된 모든 예외의 기본 클래스."""
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  # LLM 서비스가 일시적으로 사용 불가함을 의미
            error_code=error_code
        )
        self.retry_after = retry_after  # 클라이언트가 재시도해야 할 대기 시간(초)


class LLMRateLimitException(LLMException):
    """LLM API의 분당 요청 제한(Rate Limit)을 초과했을 때 발생."""
    def __init__(self, message: str = "LLM API rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            error_code="LLM_RATE_LIMIT",
            retry_after=retry_after
        )


class LLMTimeoutException(LLMException):
    """LLM API 응답이 지정된 시간 내에 도착하지 않았을 때 발생."""
    def __init__(self, message: str = "LLM API timeout"):
        super().__init__(
            message=message,
            error_code="LLM_TIMEOUT"
        )


class LLMInvalidResponseException(LLMException):
    """LLM의 응답이 예상된 형식(예: JSON)이 아닐 때 발생."""
    def __init__(self, message: str = "Invalid LLM response format"):
        super().__init__(
            message=message,
            error_code="LLM_INVALID_RESPONSE"
        )


class LLMQuotaExceededException(LLMException):
    """LLM API 사용 할당량(Quota)을 초과했을 때 발생."""
    def __init__(self, message: str = "LLM API quota exceeded"):
        super().__init__(
            message=message,
            error_code="LLM_QUOTA_EXCEEDED"
        )


# ============================================================
# FastAPI 전역 예외 핸들러
# ============================================================
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    `AppException` 및 그 서브클래스들을 처리하는 핸들러입니다.
    발생한 예외 정보를 바탕으로 구조화된 JSON 응답을 생성하고 로그를 남깁니다.
    """
    from app.core.logging import get_parent_logger
    logger = get_parent_logger("ErrorHandler")

    # LLM 관련 예외는 일시적인 문제일 수 있으므로 WARNING 레벨로,
    # 그 외의 애플리케이션 예외는 ERROR 레벨로 로깅합니다.
    if isinstance(exc, LLMException):
        logger.warning(
            "app_exception_handler", f"LLM Error: {exc.message}",
            error_code=exc.error_code, path=str(request.url.path)
        )
    else:
        logger.error(
            "app_exception_handler", f"App Error: {exc.message}",
            error_code=exc.error_code, status_code=exc.status_code, path=str(request.url.path)
        )

    response_content = {"detail": exc.message, "error_code": exc.error_code}

    # 재시도 정보가 있는 경우 응답에 포함시킵니다.
    if isinstance(exc, LLMException) and exc.retry_after:
        response_content["retry_after"] = exc.retry_after

    return JSONResponse(status_code=exc.status_code, content=response_content)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Pydantic 모델의 유효성 검증(Validation) 실패 시 발생하는 `RequestValidationError`를 처리합니다.
    어떤 필드에서 어떤 에러가 발생했는지 상세한 정보를 클라이언트에 반환합니다.
    """
    from app.core.logging import get_parent_logger
    logger = get_parent_logger("ErrorHandler")

    logger.warning(
        "validation_exception_handler", "Validation failed",
        path=str(request.url.path), errors=exc.errors()
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "errors": exc.errors()  # Pydantic이 제공하는 상세 에러 정보
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    처리되지 않은 모든 예외(Exception)를 마지막에 처리하는 핸들러입니다. (HTTP 500)
    서버 내부 오류를 클라이언트에 직접 노출하지 않고, 상세한 오류 내용은 서버 로그에만 기록합니다.
    """
    from app.core.logging import get_parent_logger
    import traceback

    logger = get_parent_logger("ErrorHandler")

    # 에러의 전체 스택 트레이스를 문자열로 만들어 로깅합니다.
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.critical(
        "generic_exception_handler", f"Unhandled exception: {exc}",
        path=str(request.url.path), method=request.method, traceback=tb_str
    )

    # NOTE: 아래 print 구문은 개발 환경에서의 디버깅 편의를 위한 것입니다.
    #       프로덕션 환경에서는 로깅 시스템으로만 출력하는 것이 좋습니다.
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
    FastAPI 애플리케이션 인스턴스에 위에 정의된 모든 예외 핸들러를 등록합니다.
    이 함수는 `main.py` 등에서 애플리케이션 초기화 시 호출되어야 합니다.

    Args:
        app (FastAPI): FastAPI 애플리케이션 인스턴스.
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # 가장 일반적인 Exception 핸들러를 마지막에 등록해야 합니다.
    app.add_exception_handler(Exception, generic_exception_handler)
