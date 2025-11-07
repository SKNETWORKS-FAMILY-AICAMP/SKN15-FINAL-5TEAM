"""
Chat Feature - Repository
DB 접근 레이어 (CRUD)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import json

from .models import DialogueTurn
from app.core.logging import get_repository_logger

logger = get_repository_logger("Chat")


class ChatRepository:
    """
    [Layer 4] Repository
    책임: DB CRUD, 쿼리 최적화
    금지: 비즈니스 로직, 트랜잭션 관리 (UseCase가 담당)
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

    # ============================================================
    # Session State Management (JSONB)
    # ============================================================

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 상태 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 상태 dict (없으면 None)
        """
        logger.debug("get_session", "Fetching session", session_id=session_id)

        stmt = text("""
            SELECT id, user_id, scenario_id, state, created_at, updated_at, last_interaction_at
            FROM chat_sessions
            WHERE id = :session_id AND is_active = TRUE
        """)

        result = await self.db.execute(stmt, {"session_id": session_id})
        row = result.fetchone()

        if not row:
            logger.debug("get_session", "Session not found", session_id=session_id)
            return None

        session_data = {
            "session_id": row.id,
            "user_id": row.user_id,
            "scenario_id": row.scenario_id,
            "state": row.state if isinstance(row.state, dict) else json.loads(row.state),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "last_interaction_at": row.last_interaction_at,
        }

        logger.debug("get_session", "Session found", session_id=session_id)
        return session_data

    async def save_session(
        self,
        session_id: str,
        user_id: str,
        scenario_id: str,
        state: Dict[str, Any]
    ) -> None:
        """
        세션 상태 저장 (upsert)

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            state: 세션 상태 dict
        """
        logger.info("save_session", "Saving session", session_id=session_id)

        stmt = text("""
            INSERT INTO chat_sessions (id, user_id, scenario_id, state, created_at, updated_at, last_interaction_at)
            VALUES (:session_id, :user_id, :scenario_id, CAST(:state AS jsonb), NOW(), NOW(), NOW())
            ON CONFLICT (id)
            DO UPDATE SET
                state = CAST(:state AS jsonb),
                updated_at = NOW(),
                last_interaction_at = NOW()
        """)

        await self.db.execute(stmt, {
            "session_id": session_id,
            "user_id": user_id,
            "scenario_id": scenario_id,
            "state": json.dumps(state)
        })

        await self.db.flush()
        logger.info("save_session", "Session saved", session_id=session_id)

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (soft delete)

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부
        """
        logger.warning("delete_session", "Deleting session", session_id=session_id)

        stmt = text("""
            UPDATE chat_sessions
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = :session_id
        """)

        result = await self.db.execute(stmt, {"session_id": session_id})
        await self.db.flush()

        deleted = result.rowcount > 0
        logger.warning("delete_session", f"Session deleted: {deleted}", session_id=session_id)
        return deleted
