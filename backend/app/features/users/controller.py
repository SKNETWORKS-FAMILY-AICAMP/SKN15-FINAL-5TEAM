"""
Users Controller
사용자 프로필 및 통계 엔드포인트
Layer 1: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.core.logging import get_controller_logger
from app.core.auth import get_current_user_id, CurrentUser, get_current_user
from app.shared.exceptions import BusinessException

from .usecase import UserUseCase
from .schemas import (
    AffinityResponse,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserStatsResponse,
    UserCreditsResponse,
    ConsumeCreditsRequest,
    ConsumeCreditsResponse,
    UserProgressionResponse,
    UserSettingsBase,
    UserSettingsResponse,
)
from app.features.galleries.schemas import ImageResponse, ImageListResponse
from app.features.chat.schemas import MemoryResponse

logger = get_controller_logger("User")

router = APIRouter(prefix="/users", tags=["users"])


# ============================================================
# 의존성 주입
# ============================================================

def get_user_usecase(db: AsyncSession = Depends(get_db)) -> UserUseCase:
    """UserUseCase 의존성"""
    return UserUseCase(db)


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
        logger.info("get_my_profile", f"Profile received: {profile is not None}")

        if not profile:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info("get_my_profile", f"Profile keys: {list(profile.keys()) if profile else 'None'}")

        # Convert affinities dict list to AffinityResponse objects
        affinities_data = profile.pop("affinities", [])
        logger.info("get_my_profile", f"Affinities data count: {len(affinities_data)}")
        logger.info("get_my_profile", f"Affinities data: {affinities_data}")

        affinities = []
        for i, aff in enumerate(affinities_data):
            logger.info("get_my_profile", f"Converting affinity {i}: {aff}")
            try:
                affinity_obj = AffinityResponse(**aff)
                affinities.append(affinity_obj)
                logger.info("get_my_profile", f"Successfully converted affinity {i}")
            except Exception as aff_error:
                logger.error("get_my_profile", f"Error converting affinity {i}: {type(aff_error).__name__}: {aff_error}")
                logger.error("get_my_profile", f"Problematic affinity data: {aff}")
                raise

        logger.info("get_my_profile", f"All affinities converted. Total: {len(affinities)}")
        logger.info("get_my_profile", f"Profile data before UserProfileResponse: {profile}")

        response = UserProfileResponse(**profile, affinities=affinities)
        logger.info("get_my_profile", "UserProfileResponse created successfully")
        return response

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("get_my_profile", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        import traceback
        logger.error("get_my_profile", f"Unexpected error: {type(e).__name__}: {e}")
        logger.error("get_my_profile", f"Traceback: {traceback.format_exc()}")
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


@router.get("/me/credits", response_model=UserCreditsResponse)
async def get_my_credits(
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    내 크레딧 조회

    Controller → UseCase → Repository
    """
    logger.info("get_my_credits", "Getting user credits", user_id=user_id)

    try:
        credits = await usecase.get_user_credits(user_id)
        return UserCreditsResponse(**credits)

    except BusinessException as e:
        logger.error("get_my_credits", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("get_my_credits", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/me/credits/consume", response_model=ConsumeCreditsResponse)
async def consume_my_credits(
    request: ConsumeCreditsRequest,
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    크레딧 소비

    Controller → UseCase → Repository
    """
    logger.info("consume_my_credits", "Consuming credits",
               user_id=user_id, amount=request.amount)

    try:
        result = await usecase.consume_user_credits(
            user_id=user_id,
            amount=request.amount,
            description=request.description
        )

        return ConsumeCreditsResponse(**result)

    except BusinessException as e:
        logger.error("consume_my_credits", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("consume_my_credits", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me/gallery", response_model=ImageListResponse)
async def get_my_gallery_images(
    limit: int = Query(50, ge=1, le=100, description="페이징 크기"),
    offset: int = Query(0, ge=0, description="페이징 오프셋"),
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    내 갤러리 이미지 목록 조회 (마이페이지)

    모든 시나리오의 이미지를 통계 정보와 함께 반환합니다.

    Controller → UseCase → Repository
    """
    logger.info("get_my_gallery_images", "Getting gallery images",
               user_id=user_id, limit=limit, offset=offset)

    try:
        images = await usecase.get_my_gallery_images(
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        return ImageListResponse(
            images=[ImageResponse(**img) for img in images],
            total=len(images)
        )

    except BusinessException as e:
        logger.error("get_my_gallery_images", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_my_gallery_images", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me/progression", response_model=UserProgressionResponse)
async def get_my_progression(
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    내 진행도 조회 (XP/Level/Rank)

    사용자의 레벨, 경험치, 계급 정보를 반환합니다.

    Controller → UseCase → Repository
    """
    logger.info("get_my_progression", "Getting user progression", user_id=user_id)

    try:
        progression = await usecase.get_my_progression(user_id)

        if not progression:
            raise HTTPException(status_code=404, detail="Progression not found")

        return UserProgressionResponse(**progression)

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("get_my_progression", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_my_progression", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me/memories", response_model=List[MemoryResponse])
async def get_my_memories(
    scenario_id: Optional[str] = Query(None, description="시나리오 ID 필터"),
    memory_type: Optional[str] = Query(None, description="기억 유형 필터 (episodic/semantic/procedural)"),
    limit: int = Query(50, ge=1, le=100, description="최대 개수"),
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    내 기억 조회

    사용자의 모든 기억을 조회합니다.
    scenario_id와 memory_type으로 필터링할 수 있습니다.

    Controller → UseCase → ChatRepository
    """
    logger.info("get_my_memories", "Getting user memories",
               user_id=user_id, scenario_id=scenario_id, memory_type=memory_type)

    try:
        memories = await usecase.get_my_memories(
            user_id=user_id,
            scenario_id=scenario_id,
            memory_type=memory_type,
            limit=limit
        )

        return [MemoryResponse(**memory) for memory in memories]

    except BusinessException as e:
        logger.error("get_my_memories", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_my_memories", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_my_settings(
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    내 설정 조회

    사용자의 설정 정보를 조회합니다.
    설정이 없으면 기본값으로 자동 생성됩니다.

    Controller → UseCase → Repository
    """
    logger.info("get_my_settings", "Getting user settings", user_id=user_id)

    try:
        settings = await usecase.get_my_settings(user_id)

        if not settings:
            raise HTTPException(status_code=404, detail="Settings not found")

        return UserSettingsResponse(**settings)

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("get_my_settings", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("get_my_settings", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/me/settings", response_model=UserSettingsResponse)
async def update_my_settings(
    request: UserSettingsBase,
    user_id: str = Depends(get_current_user_id),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    설정 수정

    사용자의 설정 정보를 수정합니다.
    부분 업데이트를 지원합니다 (None이 아닌 필드만 업데이트).

    Controller → UseCase → Repository
    """
    logger.info("update_my_settings", "Updating user settings", user_id=user_id)

    try:
        # None이 아닌 필드만 추출
        settings_update = request.model_dump(exclude_none=True)

        if not settings_update:
            logger.warning("update_my_settings", "No fields to update")
            # 업데이트할 것이 없으면 현재 설정 반환
            settings = await usecase.get_my_settings(user_id)
            return UserSettingsResponse(**settings)

        # 설정 업데이트
        settings = await usecase.update_my_settings(user_id, settings_update)

        if not settings:
            raise HTTPException(status_code=404, detail="Settings not found")

        return UserSettingsResponse(**settings)

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("update_my_settings", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("update_my_settings", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 게임 요소 엔드포인트 (프론트엔드 호환성)
# ============================================================

@router.get("/me/equipment")
async def get_my_equipment(
    current_user: CurrentUser = Depends(get_current_user),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    내 장비 상태 조회 (프론트엔드 호환)

    /api/game/equipment로 프록시
    """
    from uuid import UUID
    from app.features.game.repository import GameRepository
    from app.features.game.usecase import GameUseCase

    logger.info("get_my_equipment", "Getting user equipment", user_id=current_user.user_id)

    try:
        # Game feature UseCase 사용
        db = usecase.db  # UserUseCase의 db 세션 재사용
        game_repo = GameRepository(db)
        game_usecase = GameUseCase(game_repo)

        equipment = await game_usecase.get_user_equipment(UUID(current_user.user_id))

        if not equipment:
            raise HTTPException(status_code=404, detail="Equipment not found")

        return equipment

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_my_equipment", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/me/equipment")
async def update_my_equipment(
    equipment_updates: dict,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    장비 상태 업데이트 (프론트엔드 호환)

    /api/game/equipment로 프록시
    """
    from uuid import UUID
    from app.features.game.repository import GameRepository
    from app.features.game.usecase import GameUseCase
    from app.features.game.schemas import UserEquipmentUpdateRequest

    logger.info("update_my_equipment", "Updating user equipment", user_id=current_user.user_id)

    try:
        # 프론트엔드가 보내는 equipment_updates 키 처리
        updates = equipment_updates.get('equipment_updates', equipment_updates)
        update_request = UserEquipmentUpdateRequest(**updates)

        # Game feature UseCase 사용
        db = usecase.db
        game_repo = GameRepository(db)
        game_usecase = GameUseCase(game_repo)

        equipment = await game_usecase.update_user_equipment(
            UUID(current_user.user_id),
            update_request
        )

        if not equipment:
            raise HTTPException(status_code=404, detail="Equipment not found")

        return {"success": True, "equipment": equipment}

    except ValueError as e:
        logger.error("update_my_equipment", f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_my_equipment", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/me/progression/award-xp")
async def award_my_xp(
    request: dict,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    경험치 지급 (프론트엔드 호환)

    Phase 2 구현 전까지는 임시 응답
    """
    logger.info("award_my_xp", "Awarding XP", user_id=current_user.user_id)

    # TODO: Phase 2에서 실제 구현
    xp_amount = request.get('xp_amount', 0)

    return {
        "user_id": current_user.user_id,
        "experience_points": 0,  # TODO: 실제 XP 조회
        "level": 1,  # TODO: 실제 레벨 조회
        "level_before": 1,
        "level_after": 1,
        "did_level_up": False
    }


@router.get("/me/xp-transactions")
async def get_my_xp_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    usecase: UserUseCase = Depends(get_user_usecase)
):
    """
    경험치 거래 내역 조회 (프론트엔드 호환)

    Phase 2 구현 전까지는 빈 배열 반환
    """
    logger.info("get_my_xp_transactions", "Getting XP transactions", user_id=current_user.user_id)

    # TODO: Phase 2에서 실제 구현
    return []
