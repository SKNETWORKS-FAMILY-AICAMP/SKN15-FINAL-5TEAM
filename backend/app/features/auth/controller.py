"""
Auth Controller
로그인/로그아웃 엔드포인트
Layer 1: Controller
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.shared.exceptions import BusinessException
from .schemas import LoginRequest, LoginResponse
from .repository import AuthRepository
from .usecase import AuthUseCase

router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================
# 의존성 주입
# ============================================================

def get_auth_repository(db: AsyncSession = Depends(get_db)) -> AuthRepository:
    """AuthRepository 의존성"""
    return AuthRepository(db)


def get_auth_usecase(
    repository: AuthRepository = Depends(get_auth_repository)
) -> AuthUseCase:
    """AuthUseCase 의존성"""
    return AuthUseCase(repository)


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
            user_id=result.user_id,
            username=result.username,
            role=result.role
        )

    except BusinessException as e:
        raise HTTPException(status_code=401, detail=e.message)
