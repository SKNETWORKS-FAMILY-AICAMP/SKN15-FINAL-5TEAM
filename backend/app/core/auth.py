"""
Authentication Dependencies
JWT 토큰 검증 및 현재 사용자 정보 추출
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional
from app.core.config import get_settings
from app.core.logging import get_parent_logger

logger = get_parent_logger("AuthDependency")
settings = get_settings()

# HTTP Bearer 토큰 스키마
security = HTTPBearer()


class CurrentUser:
    """현재 인증된 사용자 정보"""
    def __init__(self, user_id: str, username: str, role: str):
        self.user_id = user_id
        self.username = username
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    JWT 토큰에서 현재 사용자 정보 추출

    Args:
        credentials: HTTP Bearer 토큰

    Returns:
        CurrentUser 객체

    Raises:
        HTTPException: 인증 실패 시 401 Unauthorized
    """
    token = credentials.credentials

    try:
        # JWT 토큰 디코딩
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # 필수 필드 추출
        user_id: Optional[str] = payload.get("user_id")
        username: Optional[str] = payload.get("username")
        role: Optional[str] = payload.get("role")

        if not user_id or not username or not role:
            logger.warning("get_current_user", "Invalid token payload: missing fields")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug("get_current_user", "User authenticated", user_id=user_id, username=username)
        return CurrentUser(user_id=user_id, username=username, role=role)

    except JWTError as e:
        logger.warning("get_current_user", f"JWT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    current_user: CurrentUser = Depends(get_current_user)
) -> str:
    """
    현재 사용자 ID 추출 (편의 함수)

    Args:
        current_user: 인증된 사용자 정보

    Returns:
        사용자 ID
    """
    return current_user.user_id


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[CurrentUser]:
    """
    선택적 인증 (토큰이 없어도 에러 발생하지 않음)

    Args:
        credentials: HTTP Bearer 토큰 (선택)

    Returns:
        CurrentUser 또는 None
    """
    if not credentials:
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id = payload.get("user_id")
        username = payload.get("username")
        role = payload.get("role")

        if user_id and username and role:
            return CurrentUser(user_id=user_id, username=username, role=role)

    except JWTError:
        pass

    return None


def require_role(*allowed_roles: str):
    """
    특정 역할 요구 데코레이터

    Usage:
        @router.get("/admin")
        async def admin_only(user: CurrentUser = Depends(require_role("admin"))):
            ...

    Args:
        allowed_roles: 허용된 역할 목록

    Returns:
        의존성 함수
    """
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            logger.warning(
                "require_role",
                f"Access denied for role {current_user.role}",
                user_id=current_user.user_id,
                required_roles=allowed_roles
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker
