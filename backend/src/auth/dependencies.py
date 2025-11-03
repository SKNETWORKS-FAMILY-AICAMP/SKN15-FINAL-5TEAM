"""
FastAPI Dependencies for authentication
"""

from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .jwt_utils import get_current_user

# Bearer 토큰 스키마
security = HTTPBearer()
# 선택적 인증용 (auto_error=False로 설정)
optional_security = HTTPBearer(auto_error=False)


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    인증 필수 의존성

    JWT 토큰을 검증하고 현재 사용자 정보를 반환합니다.

    Usage:
        @app.get("/protected")
        async def protected_route(user: Dict = Depends(require_auth)):
            return {"user": user}

    Args:
        credentials: HTTP Authorization 헤더의 Bearer 토큰

    Returns:
        현재 사용자 정보 딕셔너리

    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 제공되지 않았습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        user = get_current_user(token)
        return user
    except HTTPException:
        raise
    except Exception as e:
        print(f"인증 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증에 실패했습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> Optional[Dict[str, Any]]:
    """
    선택적 인증 의존성

    JWT 토큰이 있으면 검증하고, 없으면 None을 반환합니다.
    익명 사용자와 인증된 사용자 모두 접근 가능한 엔드포인트에 사용합니다.

    Usage:
        @app.post("/api/chat")
        async def chat(user: Optional[Dict] = Depends(optional_auth)):
            if user:
                print(f"Authenticated user: {user['user_id']}")
            else:
                print("Anonymous user")

    Args:
        credentials: HTTP Authorization 헤더의 Bearer 토큰 (선택적)

    Returns:
        현재 사용자 정보 딕셔너리 또는 None (익명)
    """
    if not credentials:
        return None

    token = credentials.credentials

    try:
        user = get_current_user(token)
        return user
    except Exception as e:
        # 토큰이 유효하지 않으면 익명으로 처리 (에러 발생 안 함)
        print(f"선택적 인증 실패 (익명으로 처리): {e}")
        return None
