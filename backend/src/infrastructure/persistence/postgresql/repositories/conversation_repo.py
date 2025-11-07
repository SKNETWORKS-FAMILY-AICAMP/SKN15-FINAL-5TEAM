"""
PostgreSQL Conversation Repository Implementation

IConversationRepository 인터페이스 구현
"""
from typing import Optional, Dict, Any, List
from psycopg2.extras import RealDictCursor, Json

from core.interfaces.repositories.conversation_repository import IConversationRepository
from infrastructure.database.connection import DatabaseConnection


class PostgresConversationRepository(IConversationRepository):
    """PostgreSQL 기반 대화 리포지토리"""

    def __init__(self, db_connection: DatabaseConnection):
        """
        Args:
            db_connection: 데이터베이스 연결 관리자
        """
        self._db = db_connection

    def get_dialogue_by_id(
        self,
        dialogue_id: int
    ) -> Optional[Dict[str, Any]]:
        """대화 ID로 대화 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT dialogue_id, session_id, turn_number,
                               user_input, agent_response, metadata,
                               created_at
                        FROM conversation.dialogues
                        WHERE dialogue_id = %s
                    """, (dialogue_id,))

                    row = cur.fetchone()
                    return dict(row) if row else None

        except Exception as e:
            print(f"Error getting dialogue {dialogue_id}: {e}")
            return None

    def save_dialogue(
        self,
        session_id: str,
        turn_number: int,
        user_input: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """대화 저장"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO conversation.dialogues
                        (session_id, turn_number, user_input, agent_response, metadata, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        RETURNING dialogue_id
                    """, (session_id, turn_number, user_input, agent_response, Json(metadata or {})))

                    row = cur.fetchone()
                    return row[0] if row else 0

        except Exception as e:
            print(f"Error saving dialogue for session {session_id}: {e}")
            return 0

    def get_session_dialogues(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """세션의 대화 목록 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if limit:
                        cur.execute("""
                            SELECT dialogue_id, session_id, turn_number,
                                   user_input, agent_response, metadata,
                                   created_at
                            FROM conversation.dialogues
                            WHERE session_id = %s
                            ORDER BY turn_number DESC
                            LIMIT %s
                        """, (session_id, limit))
                    else:
                        cur.execute("""
                            SELECT dialogue_id, session_id, turn_number,
                                   user_input, agent_response, metadata,
                                   created_at
                            FROM conversation.dialogues
                            WHERE session_id = %s
                            ORDER BY turn_number DESC
                        """, (session_id,))

                    return [dict(row) for row in cur.fetchall()]

        except Exception as e:
            print(f"Error getting dialogues for session {session_id}: {e}")
            return []

    def update_dialogue_metadata(
        self,
        dialogue_id: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """대화 메타데이터 업데이트"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE conversation.dialogues
                        SET metadata = %s,
                            updated_at = NOW()
                        WHERE dialogue_id = %s
                    """, (Json(metadata), dialogue_id))

                    return cur.rowcount > 0

        except Exception as e:
            print(f"Error updating dialogue metadata {dialogue_id}: {e}")
            return False

    def get_conversation_summary(
        self,
        session_id: str
    ) -> Optional[str]:
        """대화 요약 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT summary_text
                        FROM conversation.summaries
                        WHERE session_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (session_id,))

                    row = cur.fetchone()
                    return row['summary_text'] if row else None

        except Exception as e:
            print(f"Error getting conversation summary for session {session_id}: {e}")
            return None

    def save_conversation_summary(
        self,
        session_id: str,
        summary: str,
        turn_count: int
    ) -> bool:
        """대화 요약 저장"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO conversation.summaries
                        (session_id, summary_text, turn_count, created_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (session_id)
                        DO UPDATE SET
                            summary_text = EXCLUDED.summary_text,
                            turn_count = EXCLUDED.turn_count,
                            updated_at = NOW()
                    """, (session_id, summary, turn_count))

                    return True

        except Exception as e:
            print(f"Error saving conversation summary for session {session_id}: {e}")
            return False
