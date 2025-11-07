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
# FastAPI 예외 핸들러
# ============================================================

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    AppException 핸들러
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Pydantic 검증 실패 핸들러
    """
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
    # 개발 환경에서는 자세한 에러 출력
    import traceback
    print("=" * 60)
    print(f"[ERROR] Unhandled exception: {exc}")
    traceback.print_exc()
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
