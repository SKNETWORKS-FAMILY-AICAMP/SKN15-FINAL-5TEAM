"""
Misc Feature Repository
기타 기능 데이터 접근 계층
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from datetime import datetime

from .models import SessionSnapshot, ScenarioStatistics, UserFeedback


class MiscRepository:
    """기타 기능 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== SessionSnapshot ====================

    async def create_snapshot(
        self,
        session_id: UUID,
        turn_number: int,
        state_json: Dict[str, Any]
    ) -> SessionSnapshot:
        """세션 스냅샷 생성"""
        snapshot = SessionSnapshot(
            session_id=session_id,
            turn_number=turn_number,
            state_json=state_json
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def get_session_snapshots(
        self,
        session_id: UUID,
        limit: int = 10
    ) -> List[SessionSnapshot]:
        """세션의 스냅샷 조회"""
        result = await self.db.execute(
            select(SessionSnapshot)
            .where(SessionSnapshot.session_id == session_id)
            .order_by(SessionSnapshot.turn_number.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ==================== ScenarioStatistics ====================

    async def get_scenario_stats(self, scenario_id: str) -> Optional[ScenarioStatistics]:
        """시나리오 통계 조회"""
        result = await self.db.execute(
            select(ScenarioStatistics).where(ScenarioStatistics.scenario_id == scenario_id)
        )
        return result.scalar_one_or_none()

    async def increment_scenario_stat(
        self,
        scenario_id: str,
        stat_name: str,
        increment_by: int = 1
    ) -> bool:
        """시나리오 통계 증가"""
        valid_stats = [
            'total_likes', 'total_comments', 'total_views',
            'total_completions', 'total_sessions'
        ]

        if stat_name not in valid_stats:
            raise ValueError(f"Invalid stat_name. Must be one of {valid_stats}")

        # UPSERT: 없으면 생성, 있으면 업데이트
        from sqlalchemy.dialects.postgresql import insert

        stmt = insert(ScenarioStatistics).values(
            scenario_id=scenario_id,
            **{stat_name: increment_by},
            last_updated=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=['scenario_id'],
            set_={
                stat_name: getattr(ScenarioStatistics, stat_name) + increment_by,
                'last_updated': datetime.utcnow()
            }
        )

        await self.db.execute(stmt)
        await self.db.flush()
        return True

    async def get_all_scenario_stats(self) -> List[ScenarioStatistics]:
        """모든 시나리오 통계 조회"""
        result = await self.db.execute(
            select(ScenarioStatistics).order_by(ScenarioStatistics.total_views.desc())
        )
        return result.scalars().all()

    # ==================== UserFeedback ====================

    async def create_feedback(
        self,
        feedback_type: str,
        feedback_text: Optional[str] = None,
        user_id: Optional[str] = None,
        training_log_id: Optional[int] = None
    ) -> UserFeedback:
        """사용자 피드백 생성"""
        feedback = UserFeedback(
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            user_id=user_id,
            training_log_id=training_log_id
        )
        self.db.add(feedback)
        await self.db.flush()
        return feedback

    async def get_all_feedback(
        self,
        feedback_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[UserFeedback]:
        """피드백 목록 조회"""
        query = select(UserFeedback)

        if feedback_type:
            query = query.where(UserFeedback.feedback_type == feedback_type)

        query = query.order_by(UserFeedback.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()
