"""
Rate Limiting Middleware
slowapi를 사용한 요청 제한
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Rate Limiter 인스턴스 생성
limiter = Limiter(key_func=get_remote_address)

# 기본 Rate Limit 설정
# 예: "5/minute" = 분당 5회, "100/hour" = 시간당 100회
DEFAULT_RATE_LIMIT = "100/minute"
AUTH_RATE_LIMIT = "5/minute"  # 로그인/회원가입은 더 엄격하게


def get_rate_limiter():
    """Rate Limiter 인스턴스 반환"""
    return limiter


def setup_rate_limiting(app):
    """
    FastAPI 앱에 Rate Limiting 설정

    Usage:
        from src.middleware.rate_limiter import setup_rate_limiting
        setup_rate_limiting(app)
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return app
