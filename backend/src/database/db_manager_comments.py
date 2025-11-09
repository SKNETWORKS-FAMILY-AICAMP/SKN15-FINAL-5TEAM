"""
댓글 관련 DatabaseManager 확장 메서드
db_manager.py가 너무 커서 별도 파일로 분리
"""

from typing import List, Dict, Any, Optional
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)


class CommentsMixin:
    """댓글 관련 메서드 Mixin"""

    # ========================================
    # Scenario Comments (시나리오 댓글)
    # ========================================

    def get_scenario_comments(
        self,
        scenario_id: str,
        sort_by: str = 'recent',  # 'recent' or 'popular'
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        시나리오 댓글 목록 조회 (최신순/인기순)

        Args:
            scenario_id: 시나리오 ID
            sort_by: 정렬 기준 ('recent' 또는 'popular')
            limit: 조회 개수
            offset: 오프셋
            user_id: 현재 사용자 ID (좋아요 여부 확인용)

        Returns:
            댓글 목록
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM statedb.get_scenario_comments(%s, %s, %s, %s, %s)
                    """, (scenario_id, sort_by, limit, offset, user_id))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get scenario comments: {e}")
            return []

    def get_comment_replies(
        self,
        parent_comment_id: int,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        대댓글 목록 조회

        Args:
            parent_comment_id: 부모 댓글 ID
            user_id: 현재 사용자 ID (좋아요 여부 확인용)

        Returns:
            대댓글 목록
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM statedb.get_comment_replies(%s, %s)
                    """, (parent_comment_id, user_id))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get comment replies: {e}")
            return []

    def create_comment(
        self,
        scenario_id: str,
        user_id: str,
        content: str,
        parent_comment_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        댓글 작성

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID
            content: 댓글 내용
            parent_comment_id: 부모 댓글 ID (대댓글인 경우)

        Returns:
            생성된 댓글 정보 (username, display_name 포함)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 댓글 생성 후 사용자 정보와 함께 반환
                    cur.execute("""
                        WITH inserted_comment AS (
                            INSERT INTO statedb.scenario_comments
                            (scenario_id, user_id, content, parent_comment_id)
                            VALUES (%s, %s, %s, %s)
                            RETURNING id, scenario_id, user_id, content, parent_comment_id,
                                      like_count, is_edited, created_at, updated_at
                        )
                        SELECT
                            ic.id,
                            ic.scenario_id,
                            ic.user_id,
                            u.username,
                            u.display_name,
                            ic.content,
                            ic.parent_comment_id,
                            ic.like_count,
                            0 as reply_count,
                            false as is_liked,
                            ic.is_edited,
                            ic.created_at,
                            ic.updated_at
                        FROM inserted_comment ic
                        LEFT JOIN statedb.users u ON ic.user_id = u.user_id
                    """, (scenario_id, user_id, content, parent_comment_id))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to create comment: {e}")
            raise

    def update_comment(
        self,
        comment_id: int,
        user_id: str,
        content: str
    ) -> bool:
        """
        댓글 수정 (본인만 가능)

        Args:
            comment_id: 댓글 ID
            user_id: 사용자 ID
            content: 수정할 내용

        Returns:
            성공 여부
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE statedb.scenario_comments
                        SET content = %s,
                            is_edited = true,
                            updated_at = NOW()
                        WHERE id = %s AND user_id = %s AND is_deleted = false
                    """, (content, comment_id, user_id))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update comment: {e}")
            return False

    def delete_comment(
        self,
        comment_id: int,
        user_id: str
    ) -> bool:
        """
        댓글 삭제 (소프트 삭제, 본인만 가능)

        Args:
            comment_id: 댓글 ID
            user_id: 사용자 ID

        Returns:
            성공 여부
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE statedb.scenario_comments
                        SET is_deleted = true,
                            updated_at = NOW()
                        WHERE id = %s AND user_id = %s
                    """, (comment_id, user_id))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete comment: {e}")
            return False

    def toggle_comment_like(
        self,
        comment_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        댓글 추천 토글

        Args:
            comment_id: 댓글 ID
            user_id: 사용자 ID

        Returns:
            {"liked": bool, "like_count": int}
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 현재 좋아요 상태 확인
                    cur.execute("""
                        SELECT 1 FROM statedb.comment_likes
                        WHERE comment_id = %s AND user_id = %s
                    """, (comment_id, user_id))
                    is_liked = cur.fetchone() is not None

                    if is_liked:
                        # 좋아요 취소
                        cur.execute("""
                            DELETE FROM statedb.comment_likes
                            WHERE comment_id = %s AND user_id = %s
                        """, (comment_id, user_id))
                        new_liked = False
                    else:
                        # 좋아요 추가
                        cur.execute("""
                            INSERT INTO statedb.comment_likes (comment_id, user_id)
                            VALUES (%s, %s)
                        """, (comment_id, user_id))
                        new_liked = True

                    # 업데이트된 좋아요 수 조회
                    cur.execute("""
                        SELECT like_count FROM statedb.scenario_comments
                        WHERE id = %s
                    """, (comment_id,))
                    result = cur.fetchone()
                    like_count = result['like_count'] if result else 0

                    return {
                        "liked": new_liked,
                        "like_count": like_count
                    }
        except Exception as e:
            logger.error(f"Failed to toggle comment like: {e}")
            raise
