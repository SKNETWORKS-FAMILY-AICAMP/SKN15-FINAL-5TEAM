"""
Progression Feature Controller
진행도 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from sqlalchemy.ext.asyncio import AsyncSession

from .repository import ProgressionRepository
from .usecase import ProgressionUseCase
from .schemas import (
    UserInputResponse,
    UserProgressionResponse,
    AwardXPRequest,
    AwardXPResponse,
    XPTransactionResponse,
    IncrementStatRequest,
    ScenarioProgressResponse,
    UpdateScenarioProgressRequest,
    ToggleLikeResponse,
    StageProgressionResponse,
    CreateStageProgressionRequest,
    UpdateStageProgressionRequest,
    UserProgressionWithRankResponse,
    UserStatsResponse
)

router = APIRouter(prefix="/progression", tags=["progression"])


def get_progression_usecase(db: AsyncSession = Depends(get_db)) -> ProgressionUseCase:
    """ProgressionUseCase 의존성 주입"""
    repository = ProgressionRepository(db)
    return ProgressionUseCase(repository)


# ==================== User Progression Endpoints ====================

@router.get("/me", response_model=UserProgressionResponse)
async def get_my_progression(
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    내 진행도 조회

    - 레벨, XP, 랭크
    - 통계 (메시지, 세션, 플레이 시간 등)
    """
    progression = await usecase.get_user_progression(UUID(current_user.user_id))
    if not progression:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progression not found"
        )
    return progression


@router.get("/me/with-rank", response_model=UserProgressionWithRankResponse)
async def get_my_progression_with_rank(
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    내 진행도 + 랭크 정보 조회

    - 진행도 정보
    - 랭크 이름, 아이콘
    """
    return await usecase.get_progression_with_rank(UUID(current_user.user_id))


@router.post("/me/award-xp", response_model=AwardXPResponse)
async def award_my_xp(
    request: AwardXPRequest,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    경험치 지급

    - 자동 레벨업 계산
    - XP 거래 내역 기록
    """
    try:
        return await usecase.award_xp(UUID(current_user.user_id), request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/me/increment-stat")
async def increment_my_stat(
    request: IncrementStatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    통계 증가

    - total_messages, total_sessions, total_play_minutes
    - scenarios_completed, achievements_count
    """
    try:
        success = await usecase.increment_stat(UUID(current_user.user_id), request)
        return {"success": success}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me/xp-transactions", response_model=List[XPTransactionResponse])
async def get_my_xp_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    내 경험치 거래 내역

    - 최근 거래 내역 조회
    - 페이지네이션
    """
    return await usecase.get_xp_transactions(
        UUID(current_user.user_id), limit, offset
    )


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_my_stats(
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    내 통계 종합

    - 진행도
    - 최근 XP 거래
    - 시나리오 진행 수
    - 좋아요 수
    """
    return await usecase.get_user_stats(UUID(current_user.user_id))


# ==================== Scenario Progress Endpoints ====================

@router.get("/scenarios", response_model=List[ScenarioProgressResponse])
async def get_my_scenarios(
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    내 모든 시나리오 진행도

    - 플레이한 모든 시나리오
    - 완료 여부, 진행률, 좋아요
    """
    return await usecase.get_all_scenario_progress(UUID(current_user.user_id))


@router.get("/scenarios/{scenario_id}", response_model=ScenarioProgressResponse)
async def get_scenario_progress(
    scenario_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    특정 시나리오 진행도 조회

    - 완료 여부
    - 진행률
    - 플레이 시간
    """
    progress = await usecase.get_scenario_progress(
        UUID(current_user.user_id), scenario_id
    )
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario progress not found"
        )
    return progress


@router.put("/scenarios/{scenario_id}", response_model=ScenarioProgressResponse)
async def update_scenario_progress(
    scenario_id: str,
    request: UpdateScenarioProgressRequest,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    시나리오 진행도 업데이트

    - 완료 처리
    - 진행률 업데이트
    """
    return await usecase.update_scenario_progress(
        UUID(current_user.user_id), scenario_id, request
    )


@router.post("/scenarios/{scenario_id}/like", response_model=ToggleLikeResponse)
async def toggle_scenario_like(
    scenario_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    시나리오 좋아요 토글

    - 좋아요 추가/제거
    - 통계 업데이트
    """
    return await usecase.toggle_scenario_like(
        UUID(current_user.user_id), scenario_id
    )


# ==================== Stage Progression Endpoints ====================

@router.post("/sessions/{session_id}/stages", response_model=StageProgressionResponse)
async def start_stage(
    session_id: UUID,
    request: CreateStageProgressionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    스테이지 진행 시작

    - 스테이지 진입 기록
    - 진입 시간 저장
    """
    return await usecase.start_stage(session_id, request)


@router.put("/stages/{stage_id}", response_model=StageProgressionResponse)
async def update_stage(
    stage_id: int,
    request: UpdateStageProgressionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    스테이지 진행 업데이트

    - 이탈 시간 기록
    - 대화 수, 턴 수 업데이트
    """
    progression = await usecase.update_stage(stage_id, request)
    if not progression:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage progression not found"
        )
    return progression


@router.get("/sessions/{session_id}/stages", response_model=List[StageProgressionResponse])
async def get_session_stages(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    세션의 모든 스테이지 진행

    - 진행한 스테이지 목록
    - 시간, 대화 수 통계
    """
    return await usecase.get_session_stages(session_id)


@router.get("/sessions/{session_id}/current-stage", response_model=Optional[StageProgressionResponse])
async def get_current_stage(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    현재 진행 중인 스테이지

    - exited_at이 NULL인 스테이지
    """
    return await usecase.get_current_stage(session_id)


# ==================== User Input Endpoints ====================

@router.post("/sessions/{session_id}/inputs", response_model=UserInputResponse)
async def save_user_input(
    session_id: UUID,
    user_input: str,
    turn_number: int,
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    사용자 입력 저장

    - 대화 히스토리
    - 학습 데이터 수집
    """
    return await usecase.save_user_input(session_id, turn_number, user_input)


@router.get("/sessions/{session_id}/inputs", response_model=List[UserInputResponse])
async def get_session_inputs(
    session_id: UUID,
    limit: int = Query(10, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    usecase: ProgressionUseCase = Depends(get_progression_usecase)
):
    """
    세션의 사용자 입력 조회

    - 최근 입력 내역
    - 컨텍스트 빌딩용
    """
    return await usecase.get_user_inputs(session_id, limit)
