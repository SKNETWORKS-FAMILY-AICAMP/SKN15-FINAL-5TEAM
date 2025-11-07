"""
인증 관련 FastAPI Depends.

핵심 원칙:
1. 라우터에서는 이 모듈의 factory를 통해서만 인증 정보를 얻는다.
2. Bearer 토큰 미제공, 만료 등 모든 실패 케이스를 명시적으로 로깅한다.
3. Optional 흐름은 실패하더라도 예외를 던지지 않고 `None`을 반환해
   익명 사용자를 허용할 수 있게 한다.
"""

# ============================================================
# ============================================================
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..security.jwt_utils import get_current_user

logger = logging.getLogger(__name__)

# ============================================================
# ============================================================
# 필수 인증에서 사용한다.
security = HTTPBearer()

# 익명 접근을 허용해야 하는 경우 사용되는 스키마.
optional_security = HTTPBearer(auto_error=False)


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    보호된 라우트에서 사용하는 필수 인증 의존성.

    Returns:
        현재 사용자 페이로드(dict). JWT 페이로드 포맷은 `jwt_utils.get_current_user` 참고.

    Raises:
        HTTPException 401: 토큰 미제공, 검증 실패, 만료 등의 사유.
    """

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 제공되지 않았습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        return get_current_user(token)
    except HTTPException:
        # 하위 함수에서 이미 적절한 메시지/헤더를 세팅했으므로 재전달한다.
        raise
    except Exception as exc:  # pragma: no cover - 예외 상황 로깅
        logger.exception("Unhandled authentication error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증에 실패했습니다",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[Dict[str, Any]]:
    """
    선택적 인증. 예: 로그인 여부와 상관없이 접근 가능한 엔드포인트.

    Returns:
        JWT 검증 성공 시 사용자 정보 dict, 실패/미제공 시 None.
    """

    if not credentials:
        return None

    token = credentials.credentials
    try:
        return get_current_user(token)
    except Exception as exc:  # pragma: no cover - 디버깅용 로깅
        logger.warning("Optional auth failed; treat as anonymous: %s", exc)
        return None
