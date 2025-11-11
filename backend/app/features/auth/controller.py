"""
Auth Controller
로그인/로그아웃/회원가입/비밀번호 재설정 엔드포인트
Layer 1: Controller
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.shared.exceptions import BusinessException
from .schemas import (
    LoginRequest, LoginResponse,
    RegisterRequest, RegisterResponse,
    PasswordResetRequest, PasswordResetConfirm, PasswordResetResponse,
    RefreshTokenRequest, RefreshTokenResponse
)
from .repository import AuthRepository
from .usecase import AuthUseCase
from app.features.users.repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================
# 의존성 주입
# ============================================================

def get_auth_repository(db: AsyncSession = Depends(get_db)) -> AuthRepository:
    """AuthRepository 의존성"""
    return AuthRepository(db)


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """UserRepository 의존성"""
    return UserRepository(db)


def get_auth_usecase(
    repository: AuthRepository = Depends(get_auth_repository),
    user_repository: UserRepository = Depends(get_user_repository)
) -> AuthUseCase:
    """AuthUseCase 의존성"""
    return AuthUseCase(repository, user_repository)


# ============================================================
# 엔드포인트
# ============================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    usecase: AuthUseCase = Depends(get_auth_usecase)
):
    """
    로그인 (4-Layer Architecture)
    Controller → UseCase → Repository
    """
    try:
        result = await usecase.authenticate_user(request.username, request.password)

        return LoginResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            user_id=result.user_id,
            username=result.username,
            role=result.role
        )

    except BusinessException as e:
        raise HTTPException(status_code=401, detail=e.message)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    usecase: AuthUseCase = Depends(get_auth_usecase)
):
    """
    회원가입
    Controller → UseCase → Repository
    """
    try:
        result = await usecase.register_user(
            username=request.username,
            password=request.password,
            display_name=request.display_name,
            email=request.email
        )

        return RegisterResponse(
            user_id=result.user_id,
            username=result.username,
            display_name=result.display_name,
            message="Registration successful",
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            role=result.role
        )

    except BusinessException as e:
        if e.error_code == "USERNAME_EXISTS":
            raise HTTPException(status_code=409, detail=e.message)
        elif e.error_code == "EMAIL_EXISTS":
            raise HTTPException(status_code=409, detail=e.message)
        else:
            raise HTTPException(status_code=400, detail=e.message)


@router.post("/password-reset/request", response_model=PasswordResetResponse)
async def request_password_reset(
    request: PasswordResetRequest,
    usecase: AuthUseCase = Depends(get_auth_usecase)
):
    """
    비밀번호 재설정 요청
    이메일로 재설정 링크 전송 (개발 환경에서는 토큰 반환)
    """
    try:
        token = await usecase.request_password_reset(request.email)

        # 개발 환경: 토큰을 응답에 포함 (실제로는 이메일로 전송)
        return PasswordResetResponse(
            message=f"Password reset token (dev only): {token}"
        )

    except BusinessException as e:
        # 보안을 위해 항상 200 OK 반환
        return PasswordResetResponse(
            message="If this email exists, a reset link has been sent"
        )


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
async def confirm_password_reset(
    request: PasswordResetConfirm,
    usecase: AuthUseCase = Depends(get_auth_usecase)
):
    """
    비밀번호 재설정 확인
    토큰을 검증하고 새 비밀번호로 변경
    """
    try:
        await usecase.reset_password(request.token, request.new_password)

        return PasswordResetResponse(
            message="Password has been reset successfully"
        )

    except BusinessException as e:
        if e.error_code in ["INVALID_TOKEN", "TOKEN_USED", "TOKEN_EXPIRED"]:
            raise HTTPException(status_code=400, detail=e.message)
        else:
            raise HTTPException(status_code=500, detail="Password reset failed")


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    usecase: AuthUseCase = Depends(get_auth_usecase)
):
    """
    Refresh 토큰으로 새로운 Access 토큰 발급

    Args:
        request: RefreshTokenRequest (refresh_token)

    Returns:
        RefreshTokenResponse (new access_token)
    """
    try:
        new_access_token = await usecase.refresh_access_token(request.refresh_token)

        return RefreshTokenResponse(
            access_token=new_access_token
        )

    except BusinessException as e:
        if e.error_code in ["INVALID_TOKEN", "TOKEN_EXPIRED", "USER_INACTIVE"]:
            raise HTTPException(status_code=401, detail=e.message)
        else:
            raise HTTPException(status_code=400, detail=e.message)
