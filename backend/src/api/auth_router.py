"""
Authentication API Router

인증 관련 모든 엔드포인트를 관리합니다:
- 회원가입, 로그인, 토큰 갱신
- OAuth (Google, Kakao)
- 비밀번호 재설정
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel
import bcrypt

# Import dependencies
from src.auth.dependencies import require_auth
from src.middleware import AUTH_RATE_LIMIT, limiter

# Router 생성
router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ============================================================
# Pydantic Models
# ============================================================


class LoginRequest(BaseModel):
    """로그인 요청"""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """회원가입 요청"""
    username: str
    password: str
    email: Optional[str] = None
    display_name: Optional[str] = None


class AuthResponse(BaseModel):
    """인증 응답"""
    success: bool
    message: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """토큰 갱신 요청"""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """토큰 갱신 응답"""
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    """비밀번호 재설정 요청"""
    email: str


class PasswordResetConfirm(BaseModel):
    """비밀번호 재설정 확인"""
    token: str
    new_password: str


# ============================================================
# Database Manager Dependency
# ============================================================
# Note: db_manager will be injected from main api_server.py
db_manager = None


def set_db_manager(manager):
    """DB Manager를 설정합니다 (main에서 호출)"""
    global db_manager
    db_manager = manager


# ============================================================
# Authentication Endpoints
# ============================================================


@router.post("/register", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(req: RegisterRequest, request: Request):
    """
    회원가입 엔드포인트

    Args:
        req: RegisterRequest (username, password, email, display_name)

    Returns:
        AuthResponse (success, message, user_id, username, display_name)
    """
    try:
        # 사용자명 중복 체크
        existing_user = db_manager.get_user_by_username(req.username)
        if existing_user:
            return AuthResponse(
                success=False,
                message="이미 사용 중인 사용자명입니다."
            )

        # 이메일 중복 체크 (이메일이 제공된 경우)
        if req.email:
            existing_email = db_manager.get_user_by_email(req.email)
            if existing_email:
                return AuthResponse(
                    success=False,
                    message="이미 사용 중인 이메일입니다."
                )

        # 비밀번호 해싱
        password_hash = bcrypt.hashpw(
            req.password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # 사용자 생성
        user_id = db_manager.create_user(
            username=req.username,
            password_hash=password_hash,
            email=req.email,
            provider='email',
            display_name=req.display_name or req.username
        )

        if user_id:
            # JWT 토큰 생성
            from src.auth.jwt_utils import create_access_token, create_refresh_token

            token_data = {
                "user_id": user_id,
                "username": req.username,
                "display_name": req.display_name or req.username
            }
            access_token = create_access_token(data=token_data)
            refresh_token = create_refresh_token(data={"user_id": user_id})

            return AuthResponse(
                success=True,
                message="회원가입 성공",
                user_id=user_id,
                username=req.username,
                display_name=req.display_name or req.username,
                access_token=access_token,
                refresh_token=refresh_token
            )
        else:
            return AuthResponse(
                success=False,
                message="회원가입 중 오류가 발생했습니다."
            )

    except Exception as e:
        print(f"❌ Error in register endpoint: {e}")
        import traceback
        traceback.print_exc()
        return AuthResponse(
            success=False,
            message=f"서버 오류: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(req: LoginRequest, request: Request):
    """
    로그인 엔드포인트

    Args:
        req: LoginRequest (username, password)

    Returns:
        AuthResponse (success, message, user_id, username, display_name)
    """
    try:
        # 사용자 인증
        user = db_manager.verify_user_password(
            username=req.username,
            password=req.password
        )

        if user:
            # JWT 토큰 생성
            from src.auth.jwt_utils import create_access_token, create_refresh_token

            user_id = str(user["user_id"])
            token_data = {
                "user_id": user_id,
                "username": user["username"],
                "display_name": user.get("display_name") or user["username"]
            }
            access_token = create_access_token(data=token_data)
            refresh_token = create_refresh_token(data={"user_id": user_id})

            return AuthResponse(
                success=True,
                message="로그인 성공",
                user_id=user_id,
                username=user["username"],
                display_name=user.get("display_name") or user["username"],
                access_token=access_token,
                refresh_token=refresh_token
            )
        else:
            return AuthResponse(
                success=False,
                message="사용자명 또는 비밀번호가 올바르지 않습니다."
            )

    except Exception as e:
        print(f"❌ Error in login endpoint: {e}")
        import traceback
        traceback.print_exc()
        return AuthResponse(
            success=False,
            message=f"서버 오류: {str(e)}"
        )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(request: TokenRefreshRequest):
    """
    토큰 갱신 엔드포인트

    Args:
        request: TokenRefreshRequest (refresh_token)

    Returns:
        TokenRefreshResponse (new access_token)
    """
    from src.auth.jwt_utils import refresh_access_token

    try:
        new_access_token = refresh_access_token(request.refresh_token)
        return TokenRefreshResponse(access_token=new_access_token)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Error in refresh endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 갱신에 실패했습니다",
        )


@router.get("/me")
async def get_me(user: dict = Depends(require_auth)):
    """
    현재 사용자 정보 조회 (보호된 라우트)

    Args:
        user: 인증된 사용자 정보 (JWT 토큰에서 추출)

    Returns:
        사용자 정보
    """
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user.get("display_name")
    }


@router.post("/password-reset/request")
@limiter.limit(AUTH_RATE_LIMIT)
async def request_password_reset(req: PasswordResetRequest, request: Request):
    """
    비밀번호 재설정 요청 엔드포인트

    Args:
        req: PasswordResetRequest (email)

    Returns:
        성공 메시지
    """
    # TODO: Implement password reset logic
    # 1. 이메일로 사용자 찾기
    # 2. 재설정 토큰 생성 및 DB 저장
    # 3. 이메일 발송
    return {"message": "비밀번호 재설정 이메일이 발송되었습니다."}


@router.post("/password-reset/confirm")
async def confirm_password_reset(req: PasswordResetConfirm):
    """
    비밀번호 재설정 확인 엔드포인트

    Args:
        req: PasswordResetConfirm (token, new_password)

    Returns:
        성공 메시지
    """
    # TODO: Implement password reset confirmation
    # 1. 토큰 검증
    # 2. 비밀번호 해싱
    # 3. DB 업데이트
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}


# ============================================================
# OAuth Endpoints (Google, Kakao)
# ============================================================
# TODO: OAuth 엔드포인트는 복잡하므로 별도 작업으로 진행
