"""
Progression Feature Repository
사용자 진행도 데이터 접근 계층
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, text
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime

from .models import (
    UserInput,
    UserProgression,
    UserScenarioProgress,
    StageProgression,
)
from app.features.users.models.xp_transaction import XPTransaction


class ProgressionRepository:
    """진행도 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== UserInput ====================

    async def save_user_input(
        self,
        session_id: UUID,
        turn_number: int,
        user_input: str
    ) -> UserInput:
        """사용자 입력 저장"""
        input_record = UserInput(
            session_id=session_id,
            turn_number=turn_number,
            user_input=user_input,
            timestamp=datetime.utcnow()
        )
        self.db.add(input_record)
        await self.db.flush()
        return input_record

    async def get_user_inputs(
        self,
        session_id: str,  # ✅ str로 변경 (dialogue_repository와 일관성)
        limit: int = 10
    ) -> List[UserInput]:
        """세션의 사용자 입력 조회"""
        from uuid import UUID
        session_uuid = UUID(session_id) if isinstance(session_id, str) else session_id

        result = await self.db.execute(
            select(UserInput)
            .where(UserInput.session_id == session_uuid)
            .order_by(UserInput.turn_number.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ==================== UserProgression ====================

    async def get_user_progression(self, user_id: UUID) -> Optional[UserProgression]:
        """사용자 진행도 조회"""
        result = await self.db.execute(
            select(UserProgression).where(UserProgression.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_user_progression(self, user_id: UUID) -> UserProgression:
        """사용자 진행도 초기화"""
        progression = UserProgression(
            user_id=user_id,
            rank_code="novice",
            experience_points=0,
            level=1,
            total_messages=0,
            total_sessions=0,
            total_play_minutes=0,
            scenarios_completed=0,
            achievements_count=0
        )
        self.db.add(progression)
        await self.db.flush()
        return progression

    async def award_experience(
        self,
        user_id: UUID,
        xp_amount: int,
        xp_type: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        경험치 지급 및 레벨업 처리

        레벨 공식: FLOOR(SQRT(xp) / 10) + 1

        Returns:
            {
                'user_id': str,
                'experience_points': int,
                'level': int,
                'level_before': int,
                'level_after': int,
                'did_level_up': bool,
                'xp_balance_after': int
            }
        """
        # 현재 상태 조회
        current_progression = await self.get_user_progression(user_id)
        if not current_progression:
            current_progression = await self.create_user_progression(user_id)

        level_before = current_progression.level
        xp_before = current_progression.experience_points

        # 새로운 XP 및 레벨 계산
        new_xp = xp_before + xp_amount
        new_level = int((new_xp ** 0.5) / 10) + 1  # FLOOR(SQRT(xp) / 10) + 1
        new_level = max(1, min(new_level, 99))  # 1~99 범위

        did_level_up = new_level > level_before

        # UserProgression 업데이트
        await self.db.execute(
            update(UserProgression)
            .where(UserProgression.user_id == user_id)
            .values(
                experience_points=new_xp,
                level=new_level,
                updated_at=datetime.utcnow()
            )
        )

        # XPTransaction 기록
        transaction = XPTransaction(
            user_id=user_id,
            xp_amount=xp_amount,
            xp_type=xp_type,
            xp_balance_after=new_xp,
            level_before=level_before,
            level_after=new_level,
            did_level_up=did_level_up,
            description=description,  # Use description field directly
            extra_metadata=metadata or {}  # Python attr name is extra_metadata, DB column is metadata
        )
        self.db.add(transaction)
        await self.db.flush()

        return {
            "user_id": str(user_id),
            "experience_points": new_xp,
            "level": new_level,
            "level_before": level_before,
            "level_after": new_level,
            "did_level_up": did_level_up,
            "xp_balance_after": new_xp
        }

    async def increment_user_stat(
        self,
        user_id: UUID,
        stat_name: str,
        increment_by: int = 1
    ) -> bool:
        """
        사용자 통계 증가

        stat_name: total_messages, total_sessions, total_play_minutes,
                   scenarios_completed, achievements_count
        """
        valid_stats = [
            'total_messages', 'total_sessions', 'total_play_minutes',
            'scenarios_completed', 'achievements_count'
        ]

        if stat_name not in valid_stats:
            raise ValueError(f"Invalid stat name: {stat_name}")

        # 진행도가 없으면 생성
        progression = await self.get_user_progression(user_id)
        if not progression:
            await self.create_user_progression(user_id)

        # 동적 업데이트
        stmt = (
            update(UserProgression)
            .where(UserProgression.user_id == user_id)
            .values(
                **{stat_name: getattr(UserProgression, stat_name) + increment_by},
                updated_at=datetime.utcnow()
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return True

    async def get_xp_transactions(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[XPTransaction]:
        """경험치 거래 내역 조회"""
        result = await self.db.execute(
            select(XPTransaction)
            .where(XPTransaction.user_id == user_id)
            .order_by(XPTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    # ==================== UserScenarioProgress ====================

    async def get_scenario_progress(
        self,
        user_id: UUID,
        scenario_id: str
    ) -> Optional[UserScenarioProgress]:
        """시나리오 진행도 조회"""
        result = await self.db.execute(
            select(UserScenarioProgress).where(
                and_(
                    UserScenarioProgress.user_id == user_id,
                    UserScenarioProgress.scenario_id == scenario_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_scenario_progress(
        self,
        user_id: UUID,
        scenario_id: str,
        progress_data: Dict[str, Any]
    ) -> UserScenarioProgress:
        """시나리오 진행도 업데이트 (UPSERT)"""
        # UPSERT using PostgreSQL's ON CONFLICT
        stmt = insert(UserScenarioProgress).values(
            user_id=user_id,
            scenario_id=scenario_id,
            **progress_data,
            updated_at=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=['user_id', 'scenario_id'],
            set_={
                **progress_data,
                'updated_at': datetime.utcnow()
            }
        )

        await self.db.execute(stmt)
        await self.db.flush()

        return await self.get_scenario_progress(user_id, scenario_id)

    async def toggle_scenario_like(
        self,
        user_id: UUID,
        scenario_id: str
    ) -> Dict[str, Any]:
        """시나리오 좋아요 토글"""
        progress = await self.get_scenario_progress(user_id, scenario_id)

        if not progress:
            # 진행도가 없으면 생성하고 좋아요
            progress = await self.update_scenario_progress(
                user_id,
                scenario_id,
                {
                    "is_liked": True,
                    "liked_at": datetime.utcnow()
                }
            )
            return {"is_liked": True, "was_created": True}

        # 토글
        new_liked = not progress.is_liked

        await self.db.execute(
            update(UserScenarioProgress)
            .where(
                and_(
                    UserScenarioProgress.user_id == user_id,
                    UserScenarioProgress.scenario_id == scenario_id
                )
            )
            .values(
                is_liked=new_liked,
                liked_at=datetime.utcnow() if new_liked else None,
                updated_at=datetime.utcnow()
            )
        )
        await self.db.flush()

        return {"is_liked": new_liked, "was_created": False}

    async def get_all_scenario_progress(
        self,
        user_id: UUID
    ) -> List[UserScenarioProgress]:
        """사용자의 모든 시나리오 진행도 조회"""
        result = await self.db.execute(
            select(UserScenarioProgress)
            .where(UserScenarioProgress.user_id == user_id)
            .order_by(UserScenarioProgress.last_played_at.desc())
        )
        return result.scalars().all()

    # ==================== StageProgression ====================

    async def create_stage_progression(
        self,
        session_id: UUID,
        stage_id: str,
        stage_order: int
    ) -> StageProgression:
        """스테이지 진행 시작"""
        progression = StageProgression(
            session_id=session_id,
            stage_id=stage_id,
            stage_order=stage_order,
            entered_at=datetime.utcnow(),
            dialogue_count=0,
            stage_turn_count=0
        )
        self.db.add(progression)
        await self.db.flush()
        return progression

    async def update_stage_progression(
        self,
        stage_progression_id: int,
        updates: Dict[str, Any]
    ) -> Optional[StageProgression]:
        """스테이지 진행 업데이트"""
        await self.db.execute(
            update(StageProgression)
            .where(StageProgression.id == stage_progression_id)
            .values(**updates)
        )
        await self.db.flush()

        result = await self.db.execute(
            select(StageProgression).where(StageProgression.id == stage_progression_id)
        )
        return result.scalar_one_or_none()

    async def get_session_stage_progressions(
        self,
        session_id: UUID
    ) -> List[StageProgression]:
        """세션의 모든 스테이지 진행 조회"""
        result = await self.db.execute(
            select(StageProgression)
            .where(StageProgression.session_id == session_id)
            .order_by(StageProgression.stage_order)
        )
        return result.scalars().all()

    async def get_current_stage_progression(
        self,
        session_id: UUID
    ) -> Optional[StageProgression]:
        """현재 진행 중인 스테이지 조회 (exited_at이 NULL)"""
        result = await self.db.execute(
            select(StageProgression)
            .where(
                and_(
                    StageProgression.session_id == session_id,
                    StageProgression.exited_at.is_(None)
                )
            )
            .order_by(StageProgression.entered_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
