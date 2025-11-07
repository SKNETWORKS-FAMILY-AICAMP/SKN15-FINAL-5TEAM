"""
PostgreSQL Memory Repository Implementation

IMemoryRepository 인터페이스 구현
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from psycopg2.extras import RealDictCursor

from core.interfaces.repositories.memory_repository import IMemoryRepository
from infrastructure.database.connection import DatabaseConnection


class PostgresMemoryRepository(IMemoryRepository):
    """PostgreSQL 기반 메모리 리포지토리"""

    def __init__(self, db_connection: DatabaseConnection):
        """
        Args:
            db_connection: 데이터베이스 연결 관리자
        """
        self._db = db_connection

    def get_conversation_summary(
        self,
        session_id: str,
        character_name: Optional[str] = None
    ) -> Optional[str]:
        """
        세션의 대화 요약 조회

        Args:
            session_id: 세션 ID
            character_name: 캐릭터 이름 (선택)

        Returns:
            대화 요약 텍스트 또는 None
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if character_name:
                        cur.execute("""
                            SELECT summary_text
                            FROM conversation.dialogue_summaries
                            WHERE session_id = %s AND character_name = %s
                            ORDER BY created_at DESC
                            LIMIT 1
                        """, (session_id, character_name))
                    else:
                        cur.execute("""
                            SELECT summary_text
                            FROM conversation.dialogue_summaries
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
        character_name: Optional[str] = None
    ) -> bool:
        """
        대화 요약 저장

        Args:
            session_id: 세션 ID
            summary: 요약 텍스트
            character_name: 캐릭터 이름 (선택)

        Returns:
            성공 여부
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO conversation.dialogue_summaries
                        (session_id, character_name, summary_text, created_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (session_id, character_name)
                        DO UPDATE SET
                            summary_text = EXCLUDED.summary_text,
                            updated_at = NOW()
                    """, (session_id, character_name, summary))
                    return True

        except Exception as e:
            print(f"Error saving conversation summary for session {session_id}: {e}")
            return False

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최근 대화 메시지 조회

        Args:
            session_id: 세션 ID
            limit: 조회할 메시지 개수

        Returns:
            메시지 리스트
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT message_id, session_id, role, content,
                               metadata, created_at
                        FROM conversation.messages
                        WHERE session_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (session_id, limit))

                    return [dict(row) for row in cur.fetchall()]

        except Exception as e:
            print(f"Error getting recent messages for session {session_id}: {e}")
            return []

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        대화 메시지 저장

        Args:
            session_id: 세션 ID
            role: 메시지 역할 (user/assistant/system)
            content: 메시지 내용
            metadata: 메타데이터 (선택)

        Returns:
            메시지 ID
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO conversation.messages
                        (session_id, role, content, metadata, created_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        RETURNING message_id
                    """, (session_id, role, content, metadata or {}))

                    row = cur.fetchone()
                    return str(row[0]) if row else ""

        except Exception as e:
            print(f"Error saving message for session {session_id}: {e}")
            return ""

    def extract_key_memories(
        self,
        session_id: str,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        중요한 기억 추출

        Args:
            session_id: 세션 ID
            threshold: 중요도 임계값

        Returns:
            핵심 기억 리스트
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get user_id from session
                    cur.execute("""
                        SELECT user_id
                        FROM conversation.sessions
                        WHERE session_id = %s
                    """, (session_id,))

                    session_row = cur.fetchone()
                    if not session_row:
                        return []

                    user_id = session_row['user_id']

                    # Get high-importance memories
                    cur.execute("""
                        SELECT memory_id, memory_key, memory_type,
                               memory_value, importance, confidence,
                               tags, created_at
                        FROM knowledge.user_memories
                        WHERE user_id = %s
                          AND importance >= %s
                          AND (deleted_at IS NULL OR NOT soft_deleted)
                        ORDER BY importance DESC, last_accessed DESC
                        LIMIT 10
                    """, (user_id, threshold))

                    return [dict(row) for row in cur.fetchall()]

        except Exception as e:
            print(f"Error extracting key memories for session {session_id}: {e}")
            return []
