"""
Game Feature Controller
게임 요소 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from sqlalchemy.ext.asyncio import AsyncSession

from .repository import GameRepository
from .usecase import GameUseCase
from .schemas import (
    UserEquipmentResponse,
    UserEquipmentUpdateRequest,
    UnlockedImageResponse,
    UnlockImageRequest,
    UnlockImageResponse,
    GalleryStatsResponse,
    RankDefinitionResponse,
    GameEventResponse,
    CreateGameEventRequest,
    MissionRecordResponse,
    CreateMissionRecordRequest,
    MissionStatsResponse
)

router = APIRouter(prefix="/game", tags=["game"])


def get_game_usecase(db: AsyncSession = Depends(get_db)) -> GameUseCase:
    """GameUseCase 의존성 주입"""
    repository = GameRepository(db)
    return GameUseCase(repository)


# ==================== Equipment Endpoints ====================

@router.get("/equipment", response_model=UserEquipmentResponse)
async def get_my_equipment(
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    내 장비 상태 조회

    - 칼, 제복, 까마귀 상태
    - 없으면 자동 초기화
    """
    equipment = await usecase.get_user_equipment(UUID(current_user.user_id))
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )
    return equipment


@router.put("/equipment", response_model=UserEquipmentResponse)
async def update_my_equipment(
    update_data: UserEquipmentUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    내 장비 상태 업데이트

    - 칼 상태: excellent, good, fair, poor, broken
    - 제복 상태: pristine, worn, equipped, damaged, torn
    - 까마귀 상태: waiting, active, resting, absent
    """
    try:
        equipment = await usecase.update_user_equipment(UUID(current_user.user_id), update_data)
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        return equipment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== Image Unlock Endpoints ====================

@router.post("/images/unlock", response_model=UnlockImageResponse)
async def unlock_image(
    unlock_data: UnlockImageRequest,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    이미지 획득 처리

    - 스토리 진행, 미션 완료 등으로 이미지 획득
    - 이미 획득한 경우 newly_unlocked=false 반환
    """
    result = await usecase.unlock_image(UUID(current_user.user_id), unlock_data)
    return result


@router.get("/images/unlocked", response_model=List[UnlockedImageResponse])
async def get_my_unlocked_images(
    scenario_id: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    내가 획득한 이미지 목록

    - scenario_id로 필터링 가능
    - 최근 획득 순 정렬
    """
    images = await usecase.get_unlocked_images(UUID(current_user.user_id), scenario_id)
    return images


@router.get("/images/stats", response_model=GalleryStatsResponse)
async def get_gallery_stats(
    scenario_id: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    갤러리 통계

    - 획득한 이미지 수 / 전체 이미지 수
    - 획득 비율
    """
    stats = await usecase.get_gallery_stats(UUID(current_user.user_id), scenario_id)
    return stats


@router.get("/images/{image_id}/check", response_model=bool)
async def check_image_unlocked(
    image_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    특정 이미지 획득 여부 확인

    - True: 획득함
    - False: 미획득
    """
    unlocked = await usecase.check_image_unlocked(UUID(current_user.user_id), image_id)
    return unlocked


# ==================== Rank Endpoints ====================

@router.get("/ranks", response_model=List[RankDefinitionResponse])
async def get_all_ranks(
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    모든 랭크 정의 조회

    - 계급 시스템 (갑, 을, 병, 정 등)
    - 레벨 범위 및 필요 XP
    """
    ranks = await usecase.get_all_ranks()
    return ranks


@router.get("/ranks/{rank_code}", response_model=RankDefinitionResponse)
async def get_rank_by_code(
    rank_code: str,
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    랭크 코드로 랭크 조회

    - 특정 랭크의 상세 정보
    """
    rank = await usecase.get_rank_by_code(rank_code)
    if not rank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rank '{rank_code}' not found"
        )
    return rank


@router.get("/ranks/by-level/{level}", response_model=RankDefinitionResponse)
async def get_rank_by_level(
    level: int,
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    레벨에 맞는 랭크 조회

    - 레벨에 해당하는 랭크 반환
    """
    rank = await usecase.get_rank_by_level(level)
    if not rank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No rank found for level {level}"
        )
    return rank


# ==================== Game Event Endpoints ====================

@router.post("/sessions/{session_id}/events", response_model=GameEventResponse)
async def record_game_event(
    session_id: UUID,
    event_data: CreateGameEventRequest,
    turn_number: int = 1,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    게임 이벤트 기록

    - mission_start, mission_complete, rank_up, item_acquired 등
    - 주요 게임 이벤트 로깅
    """
    event = await usecase.record_game_event(session_id, turn_number, event_data)
    return event


@router.get("/sessions/{session_id}/events", response_model=List[GameEventResponse])
async def get_session_events(
    session_id: UUID,
    event_type: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    세션의 게임 이벤트 조회

    - event_type으로 필터링 가능
    - 턴 순서대로 정렬
    """
    events = await usecase.get_session_events(session_id, event_type)
    return events


# ==================== Mission Endpoints ====================

@router.post("/sessions/{session_id}/missions", response_model=MissionRecordResponse)
async def record_mission(
    session_id: UUID,
    mission_data: CreateMissionRecordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    미션 완료 기록

    - persuade, investigate, battle, protect 등
    - 성공/실패 여부 및 시도 횟수 기록
    """
    record = await usecase.record_mission(session_id, mission_data)
    return record


@router.get("/sessions/{session_id}/missions", response_model=List[MissionRecordResponse])
async def get_session_missions(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    세션의 미션 기록 조회

    - 완료 시간 순 정렬
    """
    missions = await usecase.get_session_missions(session_id)
    return missions


@router.get("/missions/stats", response_model=MissionStatsResponse)
async def get_my_mission_stats(
    mission_type: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: GameUseCase = Depends(get_game_usecase)
):
    """
    내 미션 통계

    - 전체 미션 수, 성공/실패 수, 성공률
    - mission_type으로 필터링 가능
    """
    stats = await usecase.get_mission_stats(UUID(current_user.user_id), mission_type)
    return stats
