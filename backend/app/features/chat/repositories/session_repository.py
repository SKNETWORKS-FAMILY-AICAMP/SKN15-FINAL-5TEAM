"""
Session Repository
세션 상태 관리 DB 접근 레이어
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any

from app.core.logging import get_repository_logger

logger = get_repository_logger("Session")


class SessionRepository:
    """
    세션 상태 CRUD 전담 Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

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
            SELECT session_id, user_id, scenario_id, user_name, current_stage, turn_count,
                   stage_turn, is_active, conversation_summary, total_dialogue_count,
                   summary_dialogue_count, created_at, updated_at
            FROM conversation.sessions
            WHERE session_id = :session_id AND is_active = TRUE
        """)

        result = await self.db.execute(stmt, {"session_id": session_id})
        row = result.fetchone()

        if not row:
            logger.debug("get_session", "Session not found", session_id=session_id)
            return None

        # Build state dict from individual columns
        state = {
            "current_stage": row.current_stage,
            "turn_count": row.turn_count or 0,
            "stage_turn": row.stage_turn or 0,
            "conversation_summary": row.conversation_summary,
            "total_dialogue_count": row.total_dialogue_count or 0,
            "summary_dialogue_count": row.summary_dialogue_count or 0,
        }

        session_data = {
            "session_id": str(row.session_id),
            "user_id": str(row.user_id) if row.user_id else None,
            "scenario_id": row.scenario_id,
            "user_name": row.user_name,
            "state": state,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "last_interaction_at": row.updated_at,  # Use updated_at as last_interaction_at
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

        # Extract state fields
        current_stage = state.get("current_stage")
        turn_count = state.get("turn_count", 0)
        stage_turn = state.get("stage_turn", 0)
        conversation_summary = state.get("conversation_summary")
        summary_dialogue_count = state.get("summary_dialogue_count", 0)  # 변경: summary_turn_count → summary_dialogue_count
        total_dialogue_count = state.get("total_dialogue_count", 0)  # 추가: 총 대화 개수
        user_name = state.get("user_name")

        stmt = text("""
            INSERT INTO conversation.sessions (session_id, user_id, scenario_id, user_name, current_stage, turn_count,
                                 stage_turn, is_active, conversation_summary, summary_dialogue_count,
                                 total_dialogue_count, summary_updated_at, created_at, updated_at)
            VALUES (:session_id, :user_id, :scenario_id, :user_name, :current_stage, :turn_count,
                    :stage_turn, TRUE, :conversation_summary, :summary_dialogue_count,
                    :total_dialogue_count, NOW(), NOW(), NOW())
            ON CONFLICT (session_id)
            DO UPDATE SET
                current_stage = :current_stage,
                turn_count = :turn_count,
                stage_turn = :stage_turn,
                conversation_summary = :conversation_summary,
                summary_dialogue_count = :summary_dialogue_count,
                total_dialogue_count = :total_dialogue_count,
                summary_updated_at = CASE
                    WHEN :conversation_summary IS NOT NULL AND :conversation_summary != ''
                    THEN NOW()
                    ELSE sessions.summary_updated_at
                END,
                updated_at = NOW()
        """)

        await self.db.execute(stmt, {
            "session_id": session_id,
            "user_id": user_id,
            "scenario_id": scenario_id,
            "user_name": user_name,
            "current_stage": current_stage,
            "turn_count": turn_count,
            "stage_turn": stage_turn,
            "conversation_summary": conversation_summary,
            "summary_dialogue_count": summary_dialogue_count,
            "total_dialogue_count": total_dialogue_count
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
            UPDATE conversation.sessions
            SET is_active = FALSE, updated_at = NOW()
            WHERE session_id = :session_id
        """)

        result = await self.db.execute(stmt, {"session_id": session_id})
        await self.db.flush()

        deleted = result.rowcount > 0
        logger.warning("delete_session", f"Session deleted: {deleted}", session_id=session_id)
        return deleted
