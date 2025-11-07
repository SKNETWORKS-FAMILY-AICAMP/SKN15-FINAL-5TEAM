"""
PostgreSQL Memory Repository Implementation

IMemoryRepository 인터페이스 구현
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from psycopg2.extras import RealDictCursor

from src.core.interfaces.repositories.memory_repository import IMemoryRepository
from src.infrastructure.database.connection import DatabaseConnection


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

    # ============================================================
    # User Long-term Memories (장기 기억)
    # ============================================================

    def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """사용자의 장기 기억 목록 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    conditions = ["user_id = %s", "importance >= %s"]
                    params = [user_id, 0.0]

                    if memory_type:
                        conditions.append("memory_type = %s")
                        params.append(memory_type)

                    conditions.append("is_active = true")
                    conditions.append("(expires_at IS NULL OR expires_at > NOW())")

                    query = f"""
                        SELECT * FROM knowledge.user_memories
                        WHERE {' AND '.join(conditions)}
                        ORDER BY importance DESC, last_accessed_at DESC NULLS LAST
                        LIMIT %s
                    """
                    params.append(limit)

                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error getting user memories for {user_id}: {e}")
            return []

    def get_memory_by_key(
        self,
        user_id: str,
        memory_key: str
    ) -> Optional[Dict[str, Any]]:
        """특정 키로 기억 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM knowledge.user_memories
                        WHERE user_id = %s AND memory_key = %s AND is_active = true
                    """, (user_id, memory_key))
                    result = cur.fetchone()

                    if result:
                        # Update access count
                        cur.execute("""
                            UPDATE knowledge.user_memories
                            SET access_count = access_count + 1,
                                last_accessed_at = NOW()
                            WHERE user_id = %s AND memory_key = %s
                        """, (user_id, memory_key))

                    return dict(result) if result else None
        except Exception as e:
            print(f"Error getting memory by key for {user_id}, {memory_key}: {e}")
            return None

    def create_or_update_memory(
        self,
        user_id: str,
        memory_key: str,
        memory_value: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[int]:
        """새로운 기억 생성 또는 업데이트 (upsert)"""
        try:
            from psycopg2.extras import Json

            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO knowledge.user_memories
                        (user_id, memory_key, memory_value, memory_type, importance,
                         tags, context, confidence, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, memory_key)
                        DO UPDATE SET
                            memory_value = EXCLUDED.memory_value,
                            memory_type = EXCLUDED.memory_type,
                            importance = EXCLUDED.importance,
                            tags = EXCLUDED.tags,
                            context = EXCLUDED.context,
                            confidence = EXCLUDED.confidence,
                            embedding = EXCLUDED.embedding,
                            updated_at = NOW()
                        RETURNING id
                    """, (user_id, memory_key, memory_value, memory_type, importance,
                          tags, Json(context) if context else None, confidence, embedding))
                    result = cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            print(f"Error creating/updating memory for {user_id}, {memory_key}: {e}")
            return None

    def delete_memory(
        self,
        user_id: str,
        memory_key: str
    ) -> bool:
        """기억 삭제 (소프트 삭제)"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE knowledge.user_memories
                        SET is_active = false, updated_at = NOW()
                        WHERE user_id = %s AND memory_key = %s
                    """, (user_id, memory_key))
                    return True
        except Exception as e:
            print(f"Error deleting memory for {user_id}, {memory_key}: {e}")
            return False

    def search_memories_by_similarity(
        self,
        user_id: str,
        query_embedding: List[float],
        limit: int = 5,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """의미 기반 기억 검색 (Vector Similarity Search)"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT
                            *,
                            embedding <=> %s::vector AS distance
                        FROM knowledge.user_memories
                        WHERE user_id = %s
                          AND embedding IS NOT NULL
                          AND is_active = true
                          AND importance >= %s
                          AND (expires_at IS NULL OR expires_at > NOW())
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (query_embedding, user_id, min_importance, query_embedding, limit))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error searching memories by similarity for {user_id}: {e}")
            return []

    def get_user_memory_context(self, user_id: str) -> Dict[str, Any]:
        """새 세션 시작 시 사용할 사용자 기억 컨텍스트 생성"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            jsonb_build_object(
                                'relationships', (
                                    SELECT jsonb_agg(jsonb_build_object(
                                        'key', memory_key,
                                        'value', memory_value,
                                        'importance', importance,
                                        'context', context
                                    ))
                                    FROM (
                                        SELECT memory_key, memory_value, importance, context
                                        FROM knowledge.user_memories
                                        WHERE user_id = %s
                                          AND memory_type = 'relationship'
                                          AND is_active = TRUE
                                        ORDER BY importance DESC
                                        LIMIT 5
                                    ) r
                                ),
                                'preferences', (
                                    SELECT jsonb_agg(jsonb_build_object(
                                        'key', memory_key,
                                        'value', memory_value
                                    ))
                                    FROM (
                                        SELECT memory_key, memory_value
                                        FROM knowledge.user_memories
                                        WHERE user_id = %s
                                          AND memory_type = 'preference'
                                          AND is_active = TRUE
                                        ORDER BY importance DESC
                                        LIMIT 5
                                    ) p
                                ),
                                'story_progress', (
                                    SELECT jsonb_agg(jsonb_build_object(
                                        'event', memory_value,
                                        'context', context
                                    ))
                                    FROM (
                                        SELECT memory_value, context
                                        FROM knowledge.user_memories
                                        WHERE user_id = %s
                                          AND memory_type = 'event'
                                          AND is_active = TRUE
                                        ORDER BY created_at DESC
                                        LIMIT 10
                                    ) e
                                ),
                                'facts', (
                                    SELECT jsonb_agg(memory_value)
                                    FROM (
                                        SELECT memory_value
                                        FROM knowledge.user_memories
                                        WHERE user_id = %s
                                          AND memory_type = 'fact'
                                          AND is_active = TRUE
                                        ORDER BY importance DESC
                                        LIMIT 10
                                    ) f
                                )
                            ) as memory_context;
                    """, (user_id, user_id, user_id, user_id))

                    result = cur.fetchone()
                    if result and result[0]:
                        return result[0]
                    return {}
        except Exception as e:
            print(f"Error getting user memory context for {user_id}: {e}")
            return {}
