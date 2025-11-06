"""
PostgreSQL Session Repository - ISessionRepository 구현체

Session 도메인 데이터 접근을 위한 Adapter.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from psycopg2.extras import RealDictCursor

from core.interfaces.repositories.session_repository import ISessionRepository
from core.exceptions import DatabaseQueryError
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.queries.conversation_queries import ConversationQueries

logger = logging.getLogger(__name__)


class PostgresSessionRepository(ISessionRepository):
    """
    PostgreSQL Session Repository 구현체

    의존성: DatabaseConnection
    """

    def __init__(self, db_connection: DatabaseConnection):
        self._db = db_connection

    def get_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 ID로 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(ConversationQueries.SELECT_SESSION_BY_ID, (session_id,))
                    row = cursor.fetchone()

                    if row:
                        session = dict(row)
                        # JSON 필드 파싱
                        if session.get("session_state"):
                            session["session_state"] = json.loads(session["session_state"]) \
                                if isinstance(session["session_state"], str) else session["session_state"]
                        return session
                    return None

        except Exception as e:
            logger.error(f"❌ Failed to get session by ID: {e}")
            raise DatabaseQueryError(
                query="SELECT_SESSION_BY_ID",
                message=f"Failed to get session: {str(e)}",
                details={"session_id": session_id}
            )

    def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """활성 세션 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(ConversationQueries.SELECT_ACTIVE_SESSION_BY_USER, (user_id,))
                    row = cursor.fetchone()

                    if row:
                        session = dict(row)
                        if session.get("session_state"):
                            session["session_state"] = json.loads(session["session_state"]) \
                                if isinstance(session["session_state"], str) else session["session_state"]
                        return session
                    return None

        except Exception as e:
            logger.error(f"❌ Failed to get active session: {e}")
            raise DatabaseQueryError(
                query="SELECT_ACTIVE_SESSION_BY_USER",
                message=f"Failed to get active session: {str(e)}",
                details={"user_id": user_id}
            )

    def create_session(
        self,
        session_id: str,
        user_id: str,
        scenario_id: str,
        initial_state: Dict[str, Any]
    ) -> Optional[str]:
        """새 세션 생성"""
        try:
            state_json = json.dumps(initial_state, ensure_ascii=False, default=str)

            with self._db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        ConversationQueries.INSERT_SESSION,
                        (session_id, user_id, scenario_id, state_json)
                    )
                    result = cursor.fetchone()
                    created_session_id = result[0] if result else session_id

                    logger.info(f"✅ Session created: {created_session_id}")
                    return created_session_id

        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            raise DatabaseQueryError(
                query="INSERT_SESSION",
                message=f"Failed to create session: {str(e)}",
                details={"session_id": session_id, "user_id": user_id}
            )

    def update_session_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """세션 상태 업데이트"""
        try:
            state_json = json.dumps(state, ensure_ascii=False, default=str)

            with self._db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        ConversationQueries.UPDATE_SESSION_STATE,
                        (state_json, session_id)
                    )
                    return True

        except Exception as e:
            logger.error(f"❌ Failed to update session state: {e}")
            raise DatabaseQueryError(
                query="UPDATE_SESSION_STATE",
                message=f"Failed to update session: {str(e)}",
                details={"session_id": session_id}
            )

    def end_session(self, session_id: str) -> bool:
        """세션 종료"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(ConversationQueries.END_SESSION, (session_id,))
                    logger.info(f"✅ Session ended: {session_id}")
                    return True

        except Exception as e:
            logger.error(f"❌ Failed to end session: {e}")
            raise DatabaseQueryError(
                query="END_SESSION",
                message=f"Failed to end session: {str(e)}",
                details={"session_id": session_id}
            )

    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """사용자의 세션 목록 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(ConversationQueries.SELECT_USER_SESSIONS, (user_id, limit))
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"❌ Failed to get user sessions: {e}")
            raise DatabaseQueryError(
                query="SELECT_USER_SESSIONS",
                message=f"Failed to get sessions: {str(e)}",
                details={"user_id": user_id}
            )
