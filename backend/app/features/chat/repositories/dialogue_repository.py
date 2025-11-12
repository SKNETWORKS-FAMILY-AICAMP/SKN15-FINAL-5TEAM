"""
Dialogue Repository
대화 관련 DB 접근 레이어
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import date, datetime, timedelta

from ..models import DialogueTurn
from app.core.logging import get_repository_logger

logger = get_repository_logger("Dialogue")


class DialogueRepository:
    """
    대화 CRUD 전담 Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_dialogue(self, dialogue: DialogueTurn) -> DialogueTurn:
        """
        대사 저장

        Args:
            dialogue: DialogueTurn 인스턴스

        Returns:
            저장된 DialogueTurn (id 포함)
        """
        logger.info("save_dialogue", "Saving dialogue", speaker=dialogue.speaker, session_id=dialogue.session_id)

        self.db.add(dialogue)
        await self.db.flush()  # ID 생성

        logger.info("save_dialogue", "Dialogue saved", dialogue_id=dialogue.id)
        return dialogue

    async def save_dialogues_batch(self, dialogues: List[DialogueTurn]) -> List[DialogueTurn]:
        """
        대사 배치 저장

        Args:
            dialogues: DialogueTurn 리스트

        Returns:
            저장된 DialogueTurn 리스트
        """
        logger.info("save_dialogues_batch", f"Saving {len(dialogues)} dialogues")

        self.db.add_all(dialogues)
        await self.db.flush()

        logger.info("save_dialogues_batch", f"Batch saved: {len(dialogues)} dialogues")
        return dialogues

    async def count_today(self, user_id: str) -> int:
        """
        오늘 사용자의 대화 횟수

        Args:
            user_id: 사용자 ID

        Returns:
            오늘 대화 횟수
        """
        logger.debug("count_today", "Counting today's dialogues", user_id=user_id)

        today_start = datetime.combine(date.today(), datetime.min.time())

        stmt = select(func.count(DialogueTurn.id)).where(
            and_(
                DialogueTurn.user_id == user_id,
                DialogueTurn.created_at >= today_start
            )
        )

        result = await self.db.execute(stmt)
        count = result.scalar_one()

        logger.debug("count_today", f"Today's count: {count}", user_id=user_id, count=count)
        return count

    async def get_recent_dialogues(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[DialogueTurn]:
        """
        세션의 최근 대화 조회

        Args:
            session_id: 세션 ID
            limit: 조회 개수

        Returns:
            최근 대화 리스트 (시간 역순)
        """
        logger.debug("get_recent_dialogues", "Fetching recent dialogues", session_id=session_id, limit=limit)

        stmt = (
            select(DialogueTurn)
            .where(DialogueTurn.session_id == session_id)
            .order_by(DialogueTurn.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        dialogues = result.scalars().all()

        logger.debug("get_recent_dialogues", f"Fetched {len(dialogues)} dialogues", session_id=session_id)
        return list(dialogues)

    async def get_user_dialogue_history(
        self,
        user_id: str,
        scenario_id: Optional[str] = None,
        days: int = 7,
        limit: int = 100
    ) -> List[DialogueTurn]:
        """
        사용자의 대화 히스토리 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID (선택)
            days: 최근 N일
            limit: 최대 개수

        Returns:
            대화 히스토리
        """
        logger.debug("get_user_dialogue_history", "Fetching user history", user_id=user_id, scenario_id=scenario_id)

        since = datetime.utcnow() - timedelta(days=days)

        conditions = [
            DialogueTurn.user_id == user_id,
            DialogueTurn.created_at >= since
        ]

        if scenario_id:
            conditions.append(DialogueTurn.scenario_id == scenario_id)

        stmt = (
            select(DialogueTurn)
            .where(and_(*conditions))
            .order_by(DialogueTurn.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        dialogues = result.scalars().all()

        logger.debug("get_user_dialogue_history", f"Fetched {len(dialogues)} dialogues", user_id=user_id)
        return list(dialogues)

    async def delete_session_dialogues(self, session_id: str) -> int:
        """
        세션의 모든 대화 삭제

        Args:
            session_id: 세션 ID

        Returns:
            삭제된 대화 수
        """
        logger.warning("delete_session_dialogues", "Deleting session dialogues", session_id=session_id)

        stmt = select(DialogueTurn).where(DialogueTurn.session_id == session_id)
        result = await self.db.execute(stmt)
        dialogues = result.scalars().all()

        count = len(dialogues)
        for dialogue in dialogues:
            await self.db.delete(dialogue)

        await self.db.flush()

        logger.warning("delete_session_dialogues", f"Deleted {count} dialogues", session_id=session_id)
        return count
