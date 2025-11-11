"""
Game Feature Repository
게임 요소 데이터 접근 계층
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime

from .models import (
    UserEquipment,
    UserUnlockedImage,
    RankDefinition,
    GameEvent,
    MissionRecord
)


class GameRepository:
    """게임 요소 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== UserEquipment ====================

    async def get_user_equipment(self, user_id: UUID) -> Optional[UserEquipment]:
        """사용자 장비 상태 조회"""
        result = await self.db.execute(
            select(UserEquipment).where(UserEquipment.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_user_equipment(self, user_id: UUID) -> UserEquipment:
        """사용자 장비 초기화 (기본값으로 생성)"""
        equipment = UserEquipment(
            user_id=user_id,
            sword_status="good",
            uniform_status="worn",
            crow_status="waiting"
        )
        self.db.add(equipment)
        await self.db.flush()
        return equipment

    async def update_user_equipment(
        self,
        user_id: UUID,
        equipment_updates: Dict[str, str]
    ) -> Optional[UserEquipment]:
        """사용자 장비 상태 업데이트"""
        valid_fields = [
            'sword_status', 'uniform_status', 'crow_status',
            'sword_type', 'uniform_color', 'crow_name'
        ]

        # 유효한 필드만 필터링
        updates = {k: v for k, v in equipment_updates.items() if k in valid_fields}

        if not updates:
            return None

        updates['updated_at'] = datetime.utcnow()

        await self.db.execute(
            update(UserEquipment)
            .where(UserEquipment.user_id == user_id)
            .values(**updates)
        )
        await self.db.flush()

        return await self.get_user_equipment(user_id)

    # ==================== UserUnlockedImage ====================

    async def unlock_image_for_user(
        self,
        user_id: UUID,
        image_id: UUID,
        scenario_id: Optional[str] = None,
        session_id: Optional[UUID] = None,
        stage_id: Optional[str] = None,
        unlock_method: str = "story_progress"
    ) -> bool:
        """
        사용자에게 이미지 획득 처리

        Returns:
            True if newly unlocked, False if already unlocked
        """
        # 이미 획득했는지 확인
        result = await self.db.execute(
            select(UserUnlockedImage).where(
                and_(
                    UserUnlockedImage.user_id == user_id,
                    UserUnlockedImage.image_id == image_id
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return False  # Already unlocked

        # 새로 획득
        unlock = UserUnlockedImage(
            user_id=user_id,
            image_id=image_id,
            scenario_id=scenario_id,
            session_id=session_id,
            stage_id=stage_id,
            unlock_method=unlock_method,
            unlocked_at=datetime.utcnow()
        )
        self.db.add(unlock)
        await self.db.flush()
        return True

    async def get_user_unlocked_images(
        self,
        user_id: UUID,
        scenario_id: Optional[str] = None
    ) -> List[UserUnlockedImage]:
        """사용자가 획득한 이미지 목록 조회"""
        query = select(UserUnlockedImage).where(UserUnlockedImage.user_id == user_id)

        if scenario_id:
            query = query.where(UserUnlockedImage.scenario_id == scenario_id)

        query = query.order_by(UserUnlockedImage.unlocked_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_unlock_count(
        self,
        user_id: UUID,
        scenario_id: Optional[str] = None
    ) -> int:
        """획득한 이미지 개수"""
        query = select(func.count(UserUnlockedImage.unlock_id)).where(
            UserUnlockedImage.user_id == user_id
        )

        if scenario_id:
            query = query.where(UserUnlockedImage.scenario_id == scenario_id)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def check_image_unlocked(
        self,
        user_id: UUID,
        image_id: UUID
    ) -> bool:
        """특정 이미지 획득 여부 확인"""
        result = await self.db.execute(
            select(UserUnlockedImage).where(
                and_(
                    UserUnlockedImage.user_id == user_id,
                    UserUnlockedImage.image_id == image_id
                )
            )
        )
        return result.scalar_one_or_none() is not None

    # ==================== RankDefinition ====================

    async def get_rank_by_code(self, rank_code: str) -> Optional[RankDefinition]:
        """랭크 코드로 랭크 정의 조회"""
        result = await self.db.execute(
            select(RankDefinition).where(RankDefinition.rank_code == rank_code)
        )
        return result.scalar_one_or_none()

    async def get_rank_by_level(self, level: int) -> Optional[RankDefinition]:
        """레벨에 맞는 랭크 조회"""
        result = await self.db.execute(
            select(RankDefinition).where(
                and_(
                    RankDefinition.level_range_start <= level,
                    RankDefinition.level_range_end >= level
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_all_ranks(self) -> List[RankDefinition]:
        """모든 랭크 정의 조회 (레벨 순)"""
        result = await self.db.execute(
            select(RankDefinition).order_by(RankDefinition.level_range_start)
        )
        return result.scalars().all()

    # ==================== GameEvent ====================

    async def create_game_event(
        self,
        session_id: UUID,
        turn_number: int,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> GameEvent:
        """게임 이벤트 기록"""
        event = GameEvent(
            session_id=session_id,
            turn_number=turn_number,
            event_type=event_type,
            event_data=event_data,
            timestamp=datetime.utcnow()
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_session_events(
        self,
        session_id: UUID,
        event_type: Optional[str] = None
    ) -> List[GameEvent]:
        """세션의 게임 이벤트 조회"""
        query = select(GameEvent).where(GameEvent.session_id == session_id)

        if event_type:
            query = query.where(GameEvent.event_type == event_type)

        query = query.order_by(GameEvent.turn_number)

        result = await self.db.execute(query)
        return result.scalars().all()

    # ==================== MissionRecord ====================

    async def create_mission_record(
        self,
        session_id: UUID,
        mission_type: str,
        target_character: Optional[str] = None,
        attempt_count: int = 0,
        success: Optional[bool] = None
    ) -> MissionRecord:
        """미션 완료 기록"""
        record = MissionRecord(
            session_id=session_id,
            mission_type=mission_type,
            target_character=target_character,
            attempt_count=attempt_count,
            success=success,
            completed_at=datetime.utcnow()
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get_session_missions(self, session_id: UUID) -> List[MissionRecord]:
        """세션의 미션 기록 조회"""
        result = await self.db.execute(
            select(MissionRecord)
            .where(MissionRecord.session_id == session_id)
            .order_by(MissionRecord.completed_at)
        )
        return result.scalars().all()

    async def get_user_mission_stats(
        self,
        user_id: UUID,
        mission_type: Optional[str] = None
    ) -> Dict[str, int]:
        """사용자의 미션 통계 (세션을 통해 간접 조회)"""
        # Note: MissionRecord는 session_id만 가지고 있어 user_id로 직접 조회 불가
        # 실제 구현에서는 sessions 테이블과 JOIN 필요
        # 여기서는 기본 구조만 제공
        return {
            "total_missions": 0,
            "successful_missions": 0,
            "failed_missions": 0
        }
