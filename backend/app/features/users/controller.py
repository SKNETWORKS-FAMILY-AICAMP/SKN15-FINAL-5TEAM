"""
Users Controller
사용자 프로필 및 통계 엔드포인트
Layer 1: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.logging import get_controller_logger
from app.shared.exceptions import BusinessException

from .usecase import UserUseCase
from .schemas import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserStatsResponse,
)

logger = get_controller_logger("User")

router = APIRouter(prefix="/users", tags=["users"])


# ============================================================
# 의존성 주입
# ============================================================

def get_user_usecase(db: AsyncSession = Depends(get_db)) -> UserUseCase:
    """UserUseCase 의존성"""
    return UserUseCase(db)


# TODO: 인증 의존성 (임시로 고정 user_id)
async def get_current_user_id() -> str:
    """현재 사용자 ID (임시)"""
    # 실제로는 JWT 토큰에서 추출
    return "temp_user_id"


# ============================================================
# 프로필 엔드포인트
# ============================================================

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    내 프로필 조회

    Controller → UseCase → Repository
    """
    logger.info("get_my_profile", "Getting user profile", user_id=user_id)

    try:
        profile = await usecase.get_user_profile(user_id)

        if not profile:
            raise HTTPException(status_code=404, detail="User not found")

        return UserProfileResponse(**profile)

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("get_my_profile", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_my_profile", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    request: UserProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    프로필 수정

    Controller → UseCase → Repository
    """
    logger.info("update_my_profile", "Updating user profile", user_id=user_id)

    try:
        profile = await usecase.update_user_profile(
            user_id=user_id,
            display_name=request.display_name,
            email=request.email
        )

        if not profile:
            raise HTTPException(status_code=404, detail="User not found")

        return UserProfileResponse(**profile)

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("update_my_profile", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("update_my_profile", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_my_stats(
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    내 통계 조회

    Controller → UseCase → Repository
    """
    logger.info("get_my_stats", "Getting user stats", user_id=user_id)

    try:
        stats = await usecase.get_user_stats(user_id)

        return UserStatsResponse(**stats)

    except BusinessException as e:
        logger.error("get_my_stats", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_my_stats", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
