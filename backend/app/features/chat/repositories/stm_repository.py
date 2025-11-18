"""
STM Repository - Short-term Memory 저장소
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete
from datetime import datetime

from ..models.short_term_memory import ShortTermMemory
from app.core.logging import get_logger

logger = get_logger(__name__)


class STMRepository:
    """Short-term Memory Repository

    목적: 세션 전용 맥락 저장 (5턴 단위 chunk 요약)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stm(
        self,
        user_id: str,
        scenario_id: str,
        session_id: str
    ) -> Optional[ShortTermMemory]:
        """STM 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            session_id: 세션 ID

        Returns:
            ShortTermMemory 또는 None
        """
        try:
            query = select(ShortTermMemory).where(
                ShortTermMemory.user_id == user_id,
                ShortTermMemory.scenario_id == scenario_id,
                ShortTermMemory.session_id == session_id
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("get_stm", f"Failed to get STM for session {session_id}: {e}")
            return None

    async def create_or_update_stm(
        self,
        user_id: str,
        scenario_id: str,
        session_id: str,
        stm_summary: Optional[str] = None,
        chunk_summaries: Optional[list] = None,
        turn_count: Optional[int] = None
    ) -> ShortTermMemory:
        """STM 생성 또는 업데이트

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            session_id: 세션 ID
            stm_summary: 세션 전체 요약
            chunk_summaries: 5턴 단위 chunk 배열
            turn_count: 현재 턴 수

        Returns:
            ShortTermMemory
        """
        stm = await self.get_stm(user_id, scenario_id, session_id)

        if stm:
            # 업데이트
            if stm_summary is not None:
                stm.stm_summary = stm_summary
            if chunk_summaries is not None:
                stm.chunk_summaries = chunk_summaries
            if turn_count is not None:
                stm.turn_count = turn_count

            stm.last_turn_timestamp = datetime.utcnow()
            stm.updated_at = datetime.utcnow()
            logger.info("create_or_update_stm", f"Updated STM for session {session_id}")
        else:
            # 생성
            stm = ShortTermMemory(
                user_id=user_id,
                scenario_id=scenario_id,
                session_id=session_id,
                stm_summary=stm_summary,
                chunk_summaries=chunk_summaries or [],
                turn_count=turn_count or 0,
                last_turn_timestamp=datetime.utcnow()
            )
            self.db.add(stm)
            logger.info("create_or_update_stm", f"Created STM for session {session_id}")

        await self.db.flush()
        return stm

    async def append_chunk(self, stm_id: int, chunk_summary: dict) -> None:
        """새 chunk 추가

        Args:
            stm_id: STM ID
            chunk_summary: chunk 요약 딕셔너리
        """
        try:
            query = select(ShortTermMemory).where(ShortTermMemory.id == stm_id)
            result = await self.db.execute(query)
            stm = result.scalar_one()

            chunks = stm.chunk_summaries or []
            chunks.append(chunk_summary)
            stm.chunk_summaries = chunks
            stm.updated_at = datetime.utcnow()

            await self.db.flush()
            logger.info("append_chunk", f"Appended chunk to STM {stm_id}, total chunks: {len(chunks)}")
        except Exception as e:
            logger.error("append_chunk", f"Failed to append chunk to STM {stm_id}: {e}")
            raise

    async def delete_session_stm(self, session_id: str) -> None:
        """세션 STM 삭제

        Args:
            session_id: 세션 ID
        """
        try:
            stmt = sql_delete(ShortTermMemory).where(ShortTermMemory.session_id == session_id)
            await self.db.execute(stmt)
            await self.db.flush()
            logger.info("delete_session_stm", f"Deleted STM for session {session_id}")
        except Exception as e:
            logger.error("delete_session_stm", f"Failed to delete STM for session {session_id}: {e}")
            raise

    async def get_stm_by_user_scenario(
        self,
        user_id: str,
        scenario_id: str,
        limit: int = 10
    ) -> list[ShortTermMemory]:
        """사용자의 특정 시나리오 STM 목록 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            limit: 최대 개수

        Returns:
            STM 리스트 (최근 순)
        """
        try:
            query = select(ShortTermMemory).where(
                ShortTermMemory.user_id == user_id,
                ShortTermMemory.scenario_id == scenario_id
            ).order_by(ShortTermMemory.updated_at.desc()).limit(limit)

            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("get_stm_by_user_scenario", f"Failed to get STMs: {e}")
            return []
