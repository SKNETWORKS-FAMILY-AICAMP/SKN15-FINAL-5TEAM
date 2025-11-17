"""
Scenario Buffer Repository - 시나리오 진행 정보 임시 저장소
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete
from datetime import datetime

from ..models.scenario_buffer import ScenarioBuffer
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScenarioBufferRepository:
    """Scenario Buffer Repository

    목적: 시나리오 진행 정보 임시 저장 (시나리오 완료 시 삭제)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_buffer(self, user_id: str, scenario_id: str) -> Optional[ScenarioBuffer]:
        """Scenario Buffer 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            ScenarioBuffer 또는 None
        """
        try:
            query = select(ScenarioBuffer).where(
                ScenarioBuffer.user_id == user_id,
                ScenarioBuffer.scenario_id == scenario_id
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("get_buffer", f"Failed to get buffer for scenario {scenario_id}: {e}")
            return None

    async def update_buffer(
        self,
        user_id: str,
        scenario_id: str,
        buffer_summary: Optional[str] = None,
        progress_data: Optional[dict] = None
    ) -> ScenarioBuffer:
        """Scenario Buffer 업데이트 (없으면 생성)

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            buffer_summary: 시나리오 연속성 요약
            progress_data: 진행 상황 데이터

        Returns:
            ScenarioBuffer
        """
        buffer = await self.get_buffer(user_id, scenario_id)

        if buffer:
            # 업데이트
            if buffer_summary is not None:
                buffer.buffer_summary = buffer_summary
            if progress_data is not None:
                buffer.progress_data = progress_data
            buffer.updated_at = datetime.utcnow()
            logger.info("update_buffer", f"Updated buffer for scenario {scenario_id}")
        else:
            # 생성
            buffer = ScenarioBuffer(
                user_id=user_id,
                scenario_id=scenario_id,
                buffer_summary=buffer_summary,
                progress_data=progress_data or {}
            )
            self.db.add(buffer)
            logger.info("update_buffer", f"Created buffer for scenario {scenario_id}")

        await self.db.flush()
        return buffer

    async def delete_buffer(self, user_id: str, scenario_id: str) -> None:
        """Scenario Buffer 삭제 (시나리오 완료 시)

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
        """
        try:
            stmt = sql_delete(ScenarioBuffer).where(
                ScenarioBuffer.user_id == user_id,
                ScenarioBuffer.scenario_id == scenario_id
            )
            await self.db.execute(stmt)
            await self.db.flush()
            logger.info("delete_buffer", f"Deleted buffer for scenario {scenario_id}")
        except Exception as e:
            logger.error("delete_buffer", f"Failed to delete buffer for scenario {scenario_id}: {e}")
            raise

    async def get_all_buffers_by_user(self, user_id: str) -> list[ScenarioBuffer]:
        """사용자의 모든 Scenario Buffer 조회

        Args:
            user_id: 사용자 ID

        Returns:
            ScenarioBuffer 리스트
        """
        try:
            query = select(ScenarioBuffer).where(
                ScenarioBuffer.user_id == user_id
            ).order_by(ScenarioBuffer.updated_at.desc())

            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("get_all_buffers_by_user", f"Failed to get buffers for user {user_id}: {e}")
            return []

    async def clear_all_buffers_by_user(self, user_id: str) -> None:
        """사용자의 모든 Scenario Buffer 삭제

        Args:
            user_id: 사용자 ID
        """
        try:
            stmt = sql_delete(ScenarioBuffer).where(ScenarioBuffer.user_id == user_id)
            await self.db.execute(stmt)
            await self.db.flush()
            logger.info("clear_all_buffers_by_user", f"Cleared all buffers for user {user_id}")
        except Exception as e:
            logger.error("clear_all_buffers_by_user", f"Failed to clear buffers for user {user_id}: {e}")
            raise
