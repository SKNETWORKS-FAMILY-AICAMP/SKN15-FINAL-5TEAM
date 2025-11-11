"""
Misc Feature Controller
기타 기능 API 엔드포인트
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user_id
from sqlalchemy.ext.asyncio import AsyncSession

from .repository import MiscRepository
from .usecase import MiscUseCase
from .schemas import (
    SessionSnapshotResponse,
    ScenarioStatisticsResponse,
    CreateFeedbackRequest,
    UserFeedbackResponse
)

router = APIRouter(prefix="/misc", tags=["misc"])


def get_misc_usecase(db: AsyncSession = Depends(get_db)) -> MiscUseCase:
    """MiscUseCase 의존성 주입"""
    repository = MiscRepository(db)
    return MiscUseCase(repository)


# ==================== Session Snapshot Endpoints ====================

@router.get("/sessions/{session_id}/snapshots", response_model=List[SessionSnapshotResponse])
async def get_session_snapshots(
    session_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    usecase: MiscUseCase = Depends(get_misc_usecase)
):
    """
    세션 스냅샷 조회

    - 최근 스냅샷부터 정렬
    """
    return await usecase.get_session_snapshots(session_id, limit)


# ==================== Scenario Statistics Endpoints ====================

@router.get("/scenarios/stats", response_model=List[ScenarioStatisticsResponse])
async def get_all_scenario_stats(
    usecase: MiscUseCase = Depends(get_misc_usecase)
):
    """
    모든 시나리오 통계 조회

    - 조회수 순 정렬
    """
    return await usecase.get_all_stats()


@router.get("/scenarios/{scenario_id}/stats", response_model=Optional[ScenarioStatisticsResponse])
async def get_scenario_stats(
    scenario_id: str,
    usecase: MiscUseCase = Depends(get_misc_usecase)
):
    """
    특정 시나리오 통계 조회
    """
    return await usecase.get_scenario_stats(scenario_id)


# ==================== User Feedback Endpoints ====================

@router.post("/feedback", response_model=UserFeedbackResponse)
async def create_feedback(
    request: CreateFeedbackRequest,
    user_id: str = Depends(get_current_user_id),
    usecase: MiscUseCase = Depends(get_misc_usecase)
):
    """
    피드백 제출

    - feedback_type: bug_report, feature_request, general, rating
    """
    return await usecase.create_feedback(request, user_id)


@router.get("/feedback", response_model=List[UserFeedbackResponse])
async def get_feedback(
    feedback_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    usecase: MiscUseCase = Depends(get_misc_usecase)
):
    """
    피드백 목록 조회

    - feedback_type로 필터링 가능
    """
    return await usecase.get_all_feedback(feedback_type, limit, offset)
