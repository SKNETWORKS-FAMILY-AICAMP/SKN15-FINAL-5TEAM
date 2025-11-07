"""
JWT 토큰 생성 및 검증 유틸리티

API 계층에서 사용하는 액세스/리프레시 토큰 생성과
디코딩 로직을 한곳에 모았다.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from jose import JWTError, jwt

# ============================================================
# 설정
# ============================================================
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


# ============================================================
# 토큰 생성
# ============================================================
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    액세스 토큰 생성

    Args:
        data: 토큰에 포함할 데이터 (user_id, username 등)
        expires_delta: 만료 시간 (기본값: ACCESS_TOKEN_EXPIRE_MINUTES)

    Returns:
        JWT 토큰 문자열
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }
    )

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    리프레시 토큰 생성

    Args:
        data: 토큰에 포함할 데이터 (user_id만 포함 권장)

    Returns:
        JWT 리프레시 토큰 문자열
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
    )

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ============================================================
# 토큰 검증
# ============================================================
def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    JWT 토큰 검증 및 디코딩

    Args:
        token: JWT 토큰 문자열
        token_type: 토큰 타입 ("access" 또는 "refresh")

    Returns:
        디코딩된 토큰 페이로드

    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 토큰 타입 확인
        if payload.get("type") != token_type:
            raise credentials_exception

        # 만료 시간 확인
        exp = payload.get("exp")
        if exp is None:
            raise credentials_exception

        if datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰이 만료되었습니다",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except JWTError as exc:
        print(f"JWT 검증 오류: {exc}")
        raise credentials_exception


def get_current_user(token: str) -> Dict[str, Any]:
    """
    현재 사용자 정보 추출

    Args:
        token: JWT 토큰 문자열

    Returns:
        사용자 정보 딕셔너리 (user_id, username 등)
    """
    payload = verify_token(token, token_type="access")

    user_id = payload.get("user_id")
    username = payload.get("username")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자 정보를 찾을 수 없습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user_id,
        "username": username,
        "display_name": payload.get("display_name"),
    }


def refresh_access_token(refresh_token: str) -> str:
    """
    리프레시 토큰으로 새로운 액세스 토큰 발급

    Args:
        refresh_token: 리프레시 토큰 문자열

    Returns:
        새로운 액세스 토큰
    """
    payload = verify_token(refresh_token, token_type="refresh")

    return create_access_token(
        data={
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "display_name": payload.get("display_name"),
        }
    )
