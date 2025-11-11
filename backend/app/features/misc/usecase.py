"""
Misc Feature UseCase
기타 기능 비즈니스 로직 계층
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from .repository import MiscRepository
from .schemas import (
    SessionSnapshotResponse,
    ScenarioStatisticsResponse,
    CreateFeedbackRequest,
    UserFeedbackResponse
)


class MiscUseCase:
    """기타 기능 UseCase"""

    def __init__(self, repository: MiscRepository):
        self.repository = repository

    # ==================== SessionSnapshot ====================

    async def create_snapshot(
        self,
        session_id: UUID,
        turn_number: int,
        state_json: Dict[str, Any]
    ) -> SessionSnapshotResponse:
        """세션 스냅샷 생성"""
        snapshot = await self.repository.create_snapshot(
            session_id, turn_number, state_json
        )
        return SessionSnapshotResponse.model_validate(snapshot)

    async def get_session_snapshots(
        self,
        session_id: UUID,
        limit: int = 10
    ) -> List[SessionSnapshotResponse]:
        """세션 스냅샷 목록"""
        snapshots = await self.repository.get_session_snapshots(session_id, limit)
        return [SessionSnapshotResponse.model_validate(s) for s in snapshots]

    # ==================== ScenarioStatistics ====================

    async def get_scenario_stats(self, scenario_id: str) -> Optional[ScenarioStatisticsResponse]:
        """시나리오 통계 조회"""
        stats = await self.repository.get_scenario_stats(scenario_id)
        return ScenarioStatisticsResponse.model_validate(stats) if stats else None

    async def increment_stat(
        self,
        scenario_id: str,
        stat_name: str,
        increment_by: int = 1
    ) -> bool:
        """통계 증가"""
        return await self.repository.increment_scenario_stat(
            scenario_id, stat_name, increment_by
        )

    async def get_all_stats(self) -> List[ScenarioStatisticsResponse]:
        """모든 통계"""
        stats = await self.repository.get_all_scenario_stats()
        return [ScenarioStatisticsResponse.model_validate(s) for s in stats]

    # ==================== UserFeedback ====================

    async def create_feedback(
        self,
        request: CreateFeedbackRequest,
        user_id: Optional[str] = None
    ) -> UserFeedbackResponse:
        """피드백 생성"""
        feedback = await self.repository.create_feedback(
            feedback_type=request.feedback_type,
            feedback_text=request.feedback_text,
            user_id=user_id,
            training_log_id=request.training_log_id
        )
        return UserFeedbackResponse.model_validate(feedback)

    async def get_all_feedback(
        self,
        feedback_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[UserFeedbackResponse]:
        """피드백 목록"""
        feedbacks = await self.repository.get_all_feedback(
            feedback_type, limit, offset
        )
        return [UserFeedbackResponse.model_validate(f) for f in feedbacks]
