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
        stmt = text("""
            SELECT session_id, user_id, scenario_id, user_name, current_stage, turn_count,
                   stage_turn, is_active, conversation_summary, total_dialogue_count,
                   summary_dialogue_count, state_json, created_at, updated_at
            FROM conversation.sessions
            WHERE session_id = :session_id AND is_active = TRUE
        """)

        result = await self.db.execute(stmt, {"session_id": session_id})
        row = result.fetchone()

        if not row:
            return None

        # ✅ state_json이 있으면 사용, 없으면 개별 컬럼에서 구성
        if hasattr(row, 'state_json') and row.state_json:
            import json
            state = json.loads(row.state_json) if isinstance(row.state_json, str) else row.state_json
            mission_data = state.get("mission", {})
            logger.info("get_session", "✅ Loaded state from state_json",
                       session_id=session_id,
                       has_mission=bool(mission_data),
                       mission_active=mission_data.get("active"),
                       mission_target=mission_data.get("target"),
                       mission_turn=mission_data.get("turn"),
                       mission_scene_playing=mission_data.get("scene_playing"),
                       recruit_attempts=state.get("recruit_attempts"))
        else:
            # Fallback: Build state dict from individual columns
            logger.warning("get_session", "⚠️ state_json not found, using fallback", session_id=session_id)
            state = {
                "current_stage": row.current_stage,
                "turn_count": row.turn_count or 0,
                "stage_turn": row.stage_turn or 0,
                "conversation_summary": row.conversation_summary,
                "last_summary_message_count": row.summary_dialogue_count or 0,  # 컬럼명 재활용
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
        # Extract state fields
        current_stage = state.get("current_stage")
        turn_count = state.get("turn_count", 0)
        stage_turn = state.get("stage_turn", 0)
        conversation_summary = state.get("conversation_summary")
        last_summary_message_count = state.get("last_summary_message_count", 0)  # 요약한 메시지 개수
        user_name = state.get("user_name")

        # ✅ 전체 state를 JSON으로 저장 (mission, temp_data 등 포함)
        import json
        state_json = json.dumps(state, default=str)

        # ✅ 로깅: mission 상태 확인
        logger.info("save_session", "💾 Saving mission state to state_json",
                   session_id=session_id,
                   has_mission=bool(state.get("mission")),
                   mission_active=state.get("mission", {}).get("active"),
                   mission_target=state.get("mission", {}).get("target"),
                   mission_turn=state.get("mission", {}).get("turn"),
                   recruit_attempts=state.get("recruit_attempts"))

        stmt = text("""
            INSERT INTO conversation.sessions (session_id, user_id, scenario_id, user_name, current_stage, turn_count,
                                 stage_turn, is_active, conversation_summary, summary_dialogue_count,
                                 summary_updated_at, state_json, created_at, updated_at)
            VALUES (:session_id, :user_id, :scenario_id, :user_name, :current_stage, :turn_count,
                    :stage_turn, TRUE, :conversation_summary, :last_summary_message_count,
                    NOW(), CAST(:state_json AS jsonb), NOW(), NOW())
            ON CONFLICT (session_id)
            DO UPDATE SET
                current_stage = :current_stage,
                turn_count = :turn_count,
                stage_turn = :stage_turn,
                conversation_summary = :conversation_summary,
                summary_dialogue_count = :last_summary_message_count,
                state_json = CAST(:state_json AS jsonb),
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
            "last_summary_message_count": last_summary_message_count,
            "state_json": state_json
        })

        await self.db.flush()

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (soft delete)

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부
        """
        stmt = text("""
            UPDATE conversation.sessions
            SET is_active = FALSE, updated_at = NOW()
            WHERE session_id = :session_id
        """)

        result = await self.db.execute(stmt, {"session_id": session_id})
        await self.db.flush()

        deleted = result.rowcount > 0
        return deleted
