"""
Galleries Controller
사용자 이미지 갤러리 엔드포인트
Layer 1: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.logging import get_controller_logger
from app.shared.exceptions import BusinessException

from .usecase import GalleryUseCase
from .schemas import (
    ImageListResponse,
    ImageResponse,
    ImageSaveRequest,
    ImageUnlockResponse,
)

logger = get_controller_logger("Gallery")

router = APIRouter(prefix="/gallery", tags=["gallery"])


# ============================================================
# 의존성 주입
# ============================================================

def get_gallery_usecase(db: AsyncSession = Depends(get_db)) -> GalleryUseCase:
    """GalleryUseCase 의존성"""
    return GalleryUseCase(db)


# TODO: 인증 의존성 (임시로 고정 user_id)
async def get_current_user_id() -> str:
    """현재 사용자 ID (임시)"""
    # 실제로는 JWT 토큰에서 추출
    return "temp_user_id"


# ============================================================
# 갤러리 엔드포인트
# ============================================================

@router.get("", response_model=ImageListResponse)
async def list_user_images(
    scenario_id: Optional[str] = Query(None, description="시나리오 ID 필터"),
    limit: int = Query(50, ge=1, le=100, description="페이징 크기"),
    offset: int = Query(0, ge=0, description="페이징 오프셋"),
    user_id: str = Depends(get_current_user_id),
    usecase: GalleryUseCase = Depends(get_gallery_usecase)
):
    """
    사용자 이미지 목록 조회

    Controller → UseCase → Repository
    """
    logger.info("list_user_images", "Listing user images",
               user_id=user_id, scenario_id=scenario_id)

    try:
        images = await usecase.list_user_images(
            user_id=user_id,
            scenario_id=scenario_id,
            limit=limit,
            offset=offset
        )

        return ImageListResponse(
            images=[ImageResponse(**img) for img in images],
            total=len(images)
        )

    except BusinessException as e:
        logger.error("list_user_images", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("list_user_images", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=ImageResponse)
async def save_generated_image(
    request: ImageSaveRequest,
    user_id: str = Depends(get_current_user_id),
    usecase: GalleryUseCase = Depends(get_gallery_usecase)
):
    """
    생성된 이미지 저장

    Controller → UseCase → Repository
    """
    logger.info("save_generated_image", "Saving generated image",
               user_id=user_id, scenario_id=request.scenario_id)

    try:
        image = await usecase.save_generated_image(
            user_id=user_id,
            scenario_id=request.scenario_id,
            session_id=request.session_id,
            stage_tag=request.stage_tag,
            image_url=request.image_url,
            image_type=request.image_type,
            extra_metadata=request.extra_metadata
        )

        return ImageResponse(**image)

    except ValueError as e:
        # 검증 에러 (예: 빈 image_url)
        logger.warning("save_generated_image", f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        logger.error("save_generated_image", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("save_generated_image", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{image_id}/unlock", response_model=ImageUnlockResponse)
async def unlock_image(
    image_id: str,
    scenario_id: str = Query(..., description="시나리오 ID"),
    user_id: str = Depends(get_current_user_id),
    usecase: GalleryUseCase = Depends(get_gallery_usecase)
):
    """
    이미지 언락 (해금)

    Controller → UseCase → Repository
    """
    logger.info("unlock_image", "Unlocking image",
               user_id=user_id, image_id=image_id)

    try:
        unlocked = await usecase.unlock_image(
            user_id=user_id,
            scenario_id=scenario_id,
            image_id=image_id
        )

        return ImageUnlockResponse(**unlocked)

    except BusinessException as e:
        logger.error("unlock_image", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("unlock_image", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/unlocked", response_model=ImageListResponse)
async def get_unlocked_images(
    scenario_id: str = Query(..., description="시나리오 ID"),
    user_id: str = Depends(get_current_user_id),
    usecase: GalleryUseCase = Depends(get_gallery_usecase)
):
    """
    언락한 이미지 목록 조회

    Controller → UseCase → Repository
    """
    logger.info("get_unlocked_images", "Getting unlocked images",
               user_id=user_id, scenario_id=scenario_id)

    try:
        images = await usecase.get_unlocked_images(
            user_id=user_id,
            scenario_id=scenario_id
        )

        return ImageListResponse(
            images=[ImageResponse(**img) for img in images],
            total=len(images)
        )

    except BusinessException as e:
        logger.error("get_unlocked_images", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_unlocked_images", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
