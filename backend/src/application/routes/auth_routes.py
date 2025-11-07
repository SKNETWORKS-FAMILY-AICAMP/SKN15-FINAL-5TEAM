"""
인증 라우터
- 회원가입, 로그인, 토큰 갱신, 비밀번호 재설정을 제공한다.
"""

# ============================================================
# 🔑 인증 라우터 — 회원가입·로그인·토큰 갱신
# ============================================================
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status

# 4-layer 아키텍처 imports
from ..dependencies.auth_deps import require_auth
from ..security.jwt_utils import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
)
from ..middleware import limiter, AUTH_RATE_LIMIT
from ..dependencies.api_deps import get_db_manager
from ..schemas.api_models import (
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from src.infrastructure.database.db_manager import DatabaseManager

# ============================================================
# 라우터 생성
# ============================================================
router = APIRouter()

# ============================================================
# 🚦 엔드포인트 정의
# ============================================================

@router.post("/register", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(
    req: RegisterRequest,
    request: Request,
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    회원가입 엔드포인트

    Args:
        req: RegisterRequest (username, password, email, display_name)

    Returns:
        AuthResponse (success, message, user_id, username, display_name)
    """
    try:
        # 사용자명 중복 체크
        existing_user = db.get_user_by_username(req.username)
        if existing_user:
            return AuthResponse(
                success=False,
                message="이미 존재하는 사용자명입니다.",
                token_type="bearer"
            )

        # 이메일 중복 체크 (이메일이 제공된 경우)
        if req.email:
            existing_email = db.get_user_by_email(req.email)
            if existing_email:
                return AuthResponse(
                    success=False,
                    message="이미 존재하는 이메일입니다.",
                    token_type="bearer"
                )

        # 비밀번호 해시 생성
        password_hash = bcrypt.hashpw(
            req.password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # 사용자 생성
        user_id = db.create_user(
            username=req.username,
            password_hash=password_hash,
            email=req.email,
            display_name=req.display_name or req.username
        )

        if user_id:
            # 진행도 초기화 (랭크·장비·세션 통계 초기 상태로 설정)
            try:
                db.initialize_user_progression(user_id)
            except Exception as e:
                print(f"⚠️  Warning: Failed to initialize progression for user {user_id}: {e}")
                # 진행도 초기화 실패해도 계정은 생성됨 (나중에 수동 초기화 가능)

            token_data = {
                "user_id": user_id,
                "username": req.username,
                "display_name": req.display_name or req.username
            }
            access_token = create_access_token(data=token_data)
            refresh_token = create_refresh_token(data={"user_id": user_id})

            return AuthResponse(
                success=True,
                message="회원가입이 완료되었습니다.",
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token
            )
        else:
            return AuthResponse(
                success=False,
                message="회원가입 중 오류가 발생했습니다.",
                token_type="bearer"
            )

    except Exception as e:
        print(f"❌ Error in register endpoint: {e}")
        import traceback
        traceback.print_exc()
        return AuthResponse(
            success=False,
            message=f"서버 오류: {str(e)}",
            token_type="bearer"
        )

@router.post("/login", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    req: LoginRequest,
    request: Request,
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    로그인 엔드포인트

    Args:
        req: LoginRequest (username, password)

    Returns:
        AuthResponse (success, message, user_id, username, display_name)
    """
    try:
        # 사용자 인증
        user = db.verify_user_password(
            username=req.username,
            password=req.password
        )

        if user:
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
                access_token=access_token,
                refresh_token=refresh_token
            )
        else:
            return AuthResponse(
                success=False,
                message="사용자명 또는 비밀번호가 올바르지 않습니다.",
                token_type="bearer"
            )

    except Exception as e:
        print(f"❌ Error in login endpoint: {e}")
        import traceback
        traceback.print_exc()
        return AuthResponse(
            success=False,
            message=f"서버 오류: {str(e)}",
            token_type="bearer"
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
async def get_me(user: Dict = Depends(require_auth)):
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
async def request_password_reset(
    req: PasswordResetRequest,
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    비밀번호 재설정 요청 - 이메일로 재설정 링크 전송

    Args:
        req: PasswordResetRequest (email)

    Returns:
        성공 메시지
    """
    try:
        from src.domain.services.notification.email_sender import send_email, generate_password_reset_email
        # 이메일로 사용자 찾기
        user = db.get_user_by_username(req.email)
        if not user:
            # 보안상 사용자가 없어도 성공 응답 (이메일 존재 여부 노출 방지)
            return {"success": True, "message": "비밀번호 재설정 이메일이 전송되었습니다."}

        user_id = str(user['user_id'])

        # 재설정 토큰 생성 (보안 랜덤 문자열)
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)  # 1시간 유효

        # 데이터베이스에 토큰 저장
        token_id = db.create_password_reset_token(
            user_id, reset_token, expires_at.isoformat()
        )

        if not token_id:
            raise HTTPException(status_code=500, detail="토큰 생성 실패")

        # 재설정 링크 생성
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"

        # 이메일 전송
        html_content, text_content = generate_password_reset_email(
            reset_link,
            user.get("display_name", user["username"])
        )

        email_sent = await send_email(
            to_email=user.get("email", req.email),
            subject="[KIME Chat] 비밀번호 재설정 요청",
            html_content=html_content,
            text_content=text_content
        )

        if not email_sent:
            # 이메일 전송 실패해도 클라이언트에는 성공 응답 (보안)
            print(f"⚠️  Failed to send password reset email to {req.email}")

        return {
            "success": True,
            "message": "비밀번호 재설정 이메일이 전송되었습니다. 이메일을 확인해주세요."
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Password reset request error: {e}")
        raise HTTPException(
            status_code=500,
            detail="비밀번호 재설정 요청 처리 중 오류가 발생했습니다"
        )

@router.post("/password-reset/confirm")
async def confirm_password_reset(
    req: PasswordResetConfirm,
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    비밀번호 재설정 확인 - 새 비밀번호 설정

    Args:
        req: PasswordResetConfirm (token, new_password)

    Returns:
        성공 메시지
    """
    try:
        # 토큰 검증
        token_data = db.get_password_reset_token(req.token)
        if not token_data:
            raise HTTPException(
                status_code=400,
                detail="유효하지 않거나 만료된 토큰입니다"
            )

        user_id = token_data["user_id"]

        # 새 비밀번호 해싱
        new_password_hash = bcrypt.hashpw(
            req.new_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # 비밀번호 업데이트
        if not db.update_user_password(user_id, new_password_hash):
            raise HTTPException(status_code=500, detail="비밀번호 업데이트 실패")

        # 토큰 사용 처리
        db.mark_password_reset_token_as_used(req.token)

        return {
            "success": True,
            "message": "비밀번호가 성공적으로 변경되었습니다"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Password reset confirm error: {e}")
        raise HTTPException(
            status_code=500,
            detail="비밀번호 재설정 처리 중 오류가 발생했습니다"
        )
