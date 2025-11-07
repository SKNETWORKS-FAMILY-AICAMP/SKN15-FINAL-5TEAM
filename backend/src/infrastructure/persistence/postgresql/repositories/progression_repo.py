"""
PostgreSQL Progression Repository Implementation

IProgressionRepository 인터페이스 구현
"""
from typing import Optional, Dict, Any, List
from psycopg2.extras import RealDictCursor, Json

from core.interfaces.repositories.progression_repository import IProgressionRepository
from infrastructure.database.connection import DatabaseConnection


class PostgresProgressionRepository(IProgressionRepository):
    """PostgreSQL 기반 진행도 리포지토리"""

    def __init__(self, db_connection: DatabaseConnection):
        """
        Args:
            db_connection: 데이터베이스 연결 관리자
        """
        self._db = db_connection

    def get_user_rank(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 랭크 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT user_id, rank_level, rank_name, rank_points,
                               total_sessions, total_turns, created_at, updated_at
                        FROM progression.user_ranks
                        WHERE user_id = %s
                    """, (user_id,))

                    row = cur.fetchone()
                    return dict(row) if row else None

        except Exception as e:
            print(f"Error getting user rank for {user_id}: {e}")
            return None

    def update_user_rank(
        self,
        user_id: str,
        rank_data: Dict[str, Any]
    ) -> bool:
        """사용자 랭크 업데이트"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO progression.user_ranks
                        (user_id, rank_level, rank_name, rank_points,
                         total_sessions, total_turns, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (user_id)
                        DO UPDATE SET
                            rank_level = EXCLUDED.rank_level,
                            rank_name = EXCLUDED.rank_name,
                            rank_points = EXCLUDED.rank_points,
                            total_sessions = EXCLUDED.total_sessions,
                            total_turns = EXCLUDED.total_turns,
                            updated_at = NOW()
                    """, (
                        user_id,
                        rank_data.get('rank_level', 1),
                        rank_data.get('rank_name', 'Beginner'),
                        rank_data.get('rank_points', 0),
                        rank_data.get('total_sessions', 0),
                        rank_data.get('total_turns', 0)
                    ))

                    return True

        except Exception as e:
            print(f"Error updating user rank for {user_id}: {e}")
            return False

    def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 통계 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT user_id, total_sessions, total_turns,
                               total_playtime_minutes, favorite_character,
                               achievements, stats_data, updated_at
                        FROM progression.user_stats
                        WHERE user_id = %s
                    """, (user_id,))

                    row = cur.fetchone()
                    return dict(row) if row else None

        except Exception as e:
            print(f"Error getting user stats for {user_id}: {e}")
            return None

    def update_user_stats(
        self,
        user_id: str,
        stats: Dict[str, Any]
    ) -> bool:
        """사용자 통계 업데이트"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO progression.user_stats
                        (user_id, total_sessions, total_turns,
                         total_playtime_minutes, favorite_character,
                         achievements, stats_data, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (user_id)
                        DO UPDATE SET
                            total_sessions = EXCLUDED.total_sessions,
                            total_turns = EXCLUDED.total_turns,
                            total_playtime_minutes = EXCLUDED.total_playtime_minutes,
                            favorite_character = EXCLUDED.favorite_character,
                            achievements = EXCLUDED.achievements,
                            stats_data = EXCLUDED.stats_data,
                            updated_at = NOW()
                    """, (
                        user_id,
                        stats.get('total_sessions', 0),
                        stats.get('total_turns', 0),
                        stats.get('total_playtime_minutes', 0),
                        stats.get('favorite_character'),
                        Json(stats.get('achievements', [])),
                        Json(stats.get('stats_data', {}))
                    ))

                    return True

        except Exception as e:
            print(f"Error updating user stats for {user_id}: {e}")
            return False

    def get_affinity_scores(
        self,
        session_id: str
    ) -> Dict[str, int]:
        """호감도 점수 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT character_name, affinity_score
                        FROM progression.affinity_scores
                        WHERE session_id = %s
                    """, (session_id,))

                    return {row['character_name']: row['affinity_score'] for row in cur.fetchall()}

        except Exception as e:
            print(f"Error getting affinity scores for session {session_id}: {e}")
            return {}

    def update_affinity_score(
        self,
        session_id: str,
        character_name: str,
        score: int
    ) -> bool:
        """호감도 점수 업데이트"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO progression.affinity_scores
                        (session_id, character_name, affinity_score, updated_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (session_id, character_name)
                        DO UPDATE SET
                            affinity_score = EXCLUDED.affinity_score,
                            updated_at = NOW()
                    """, (session_id, character_name, score))

                    return True

        except Exception as e:
            print(f"Error updating affinity score for {session_id}, {character_name}: {e}")
            return False

    def get_mission_progress(
        self,
        session_id: str,
        mission_id: str
    ) -> Optional[Dict[str, Any]]:
        """미션 진행도 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT session_id, mission_id, status,
                               progress_data, completed_at, updated_at
                        FROM progression.mission_progress
                        WHERE session_id = %s AND mission_id = %s
                    """, (session_id, mission_id))

                    row = cur.fetchone()
                    return dict(row) if row else None

        except Exception as e:
            print(f"Error getting mission progress for {session_id}, {mission_id}: {e}")
            return None

    def update_mission_progress(
        self,
        session_id: str,
        mission_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """미션 진행도 업데이트"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO progression.mission_progress
                        (session_id, mission_id, status, progress_data,
                         completed_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (session_id, mission_id)
                        DO UPDATE SET
                            status = EXCLUDED.status,
                            progress_data = EXCLUDED.progress_data,
                            completed_at = EXCLUDED.completed_at,
                            updated_at = NOW()
                    """, (
                        session_id,
                        mission_id,
                        progress_data.get('status', 'in_progress'),
                        Json(progress_data.get('data', {})),
                        progress_data.get('completed_at')
                    ))

                    return True

        except Exception as e:
            print(f"Error updating mission progress for {session_id}, {mission_id}: {e}")
            return False

    def get_leaderboard(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """리더보드 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT ur.user_id, u.display_name, ur.rank_level,
                               ur.rank_name, ur.rank_points, ur.total_sessions,
                               ur.total_turns, ur.updated_at
                        FROM progression.user_ranks ur
                        JOIN auth.users u ON ur.user_id = u.user_id
                        ORDER BY ur.rank_points DESC, ur.updated_at ASC
                        LIMIT %s OFFSET %s
                    """, (limit, offset))

                    return [dict(row) for row in cur.fetchall()]

        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []
