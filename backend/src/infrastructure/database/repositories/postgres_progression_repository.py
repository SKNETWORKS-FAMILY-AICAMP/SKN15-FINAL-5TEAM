"""
PostgreSQL Progression Repository Implementation

IProgressionRepository 인터페이스 구현
"""
from typing import Optional, Dict, Any, List
from psycopg2.extras import RealDictCursor, Json

from src.core.interfaces.repositories.progression_repository import IProgressionRepository
from src.infrastructure.database.connection import DatabaseConnection


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

    # ============================================================
    # User Progression - Credits, XP, Equipment
    # ============================================================

    def get_user_credits(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 크레딧 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT bubble_count, total_purchased, total_consumed, last_updated
                        FROM auth.user_credits
                        WHERE user_id = %s
                    """, (user_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error getting user credits for {user_id}: {e}")
            return None

    def consume_credits(
        self,
        user_id: str,
        amount: int,
        description: str
    ) -> bool:
        """크레딧 소비"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH updated AS (
                          UPDATE auth.user_credits
                          SET bubble_count = bubble_count - %s,
                              total_consumed = total_consumed + %s,
                              last_updated = NOW()
                          WHERE user_id = %s AND bubble_count >= %s
                          RETURNING user_id, bubble_count
                        )
                        INSERT INTO auth.credit_transactions
                          (user_id, amount, transaction_type, description, balance_after, created_at)
                        SELECT user_id, %s, 'consume', %s, bubble_count, NOW()
                        FROM updated
                        RETURNING transaction_id
                    """, (amount, amount, user_id, amount, -amount, description))

                    result = cur.fetchone()
                    return result is not None
        except Exception as e:
            print(f"Error consuming credits for {user_id}: {e}")
            return False

    def get_user_progression(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 진행도 조회 (랭크, XP, 레벨, 장비 등)"""
        # FIXME: Implement proper SQL join for user progression
        # For now, delegate to DatabaseManager
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.get_user_progression(user_id)

    def get_user_equipment(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 장비 상태 조회"""
        # FIXME: Implement proper SQL query
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.get_user_equipment(user_id)

    def update_user_equipment(
        self,
        user_id: str,
        equipment_updates: Dict[str, str]
    ) -> bool:
        """사용자 장비 상태 업데이트"""
        # FIXME: Implement proper SQL update
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.update_user_equipment(user_id, equipment_updates)

    def award_experience(
        self,
        user_id: str,
        xp_amount: int,
        xp_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """사용자에게 경험치 지급"""
        # FIXME: Implement proper SQL for XP award with level up logic
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.award_experience(user_id, xp_amount, xp_type, description, metadata)

    def get_xp_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """사용자 경험치 거래 내역 조회"""
        # FIXME: Implement proper SQL query
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.get_xp_transactions(user_id, limit, offset)

    def initialize_user(self, user_id: str) -> bool:
        """사용자 진행도 초기화"""
        # FIXME: Implement proper SQL insert for user initialization
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.initialize_user_progression(user_id)

    # ============================================================
    # Scenario Progress
    # ============================================================

    def get_scenarios_with_user_progress(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """사용자 진행도가 포함된 시나리오 목록 조회"""
        # FIXME: Implement proper SQL join
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.get_scenarios_with_user_progress(user_id)

    def toggle_scenario_like(
        self,
        user_id: str,
        scenario_id: str
    ) -> Dict[str, Any]:
        """시나리오 좋아요 토글"""
        # FIXME: Implement proper SQL toggle
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.toggle_scenario_like(user_id, scenario_id)

    def get_user_scenario_progress(
        self,
        user_id: str,
        scenario_id: str
    ) -> Optional[Dict[str, Any]]:
        """사용자의 특정 시나리오 진행도 조회"""
        # FIXME: Implement proper SQL query
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.get_user_scenario_progress(user_id, scenario_id)

    def update_user_scenario_progress(
        self,
        user_id: str,
        scenario_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """사용자의 시나리오 진행도 업데이트"""
        # FIXME: Implement proper SQL update
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.update_user_scenario_progress(user_id, scenario_id, progress_data)

    def record_scenario_view(
        self,
        scenario_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """시나리오 조회 기록"""
        # FIXME: Implement proper SQL insert
        from src.infrastructure.database.db_manager import DatabaseManager
        db = DatabaseManager()
        return db.record_scenario_view(scenario_id, user_id, ip_address, user_agent)
