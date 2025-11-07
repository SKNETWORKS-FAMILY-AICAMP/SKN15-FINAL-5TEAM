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
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM progression.v_user_progression_summary
                        WHERE user_id = %s
                    """, (user_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error getting user progression for {user_id}: {e}")
            return None

    def get_user_equipment(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 장비 상태 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT sword_status, uniform_status, crow_status,
                               sword_type, uniform_color, crow_name
                        FROM progression.user_equipment
                        WHERE user_id = %s
                    """, (user_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error getting user equipment for {user_id}: {e}")
            return None

    def update_user_equipment(
        self,
        user_id: str,
        equipment_updates: Dict[str, str]
    ) -> bool:
        """사용자 장비 상태 업데이트"""
        try:
            valid_fields = ['sword_status', 'uniform_status', 'crow_status',
                          'sword_type', 'uniform_color', 'crow_name']

            # 유효한 필드만 필터링
            updates = {k: v for k, v in equipment_updates.items() if k in valid_fields}

            if not updates:
                return False

            # SET 절 동적 생성
            set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
            values = list(updates.values()) + [user_id]

            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        UPDATE progression.user_equipment
                        SET {set_clause}, updated_at = NOW()
                        WHERE user_id = %s
                    """, values)
                    return True
        except Exception as e:
            print(f"Error updating user equipment for {user_id}: {e}")
            return False

    def award_experience(
        self,
        user_id: str,
        xp_amount: int,
        xp_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """사용자에게 경험치 지급"""
        try:
            import json
            metadata_json = json.dumps(metadata) if metadata else None

            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        WITH current_state AS (
                            SELECT user_id, experience_points, level
                            FROM progression.user_progression
                            WHERE user_id = %s
                        ),
                        updated AS (
                            UPDATE progression.user_progression
                            SET experience_points = experience_points + %s,
                                level = FLOOR(SQRT(GREATEST(experience_points + %s, 0)) / 10) + 1,
                                updated_at = NOW()
                            WHERE user_id = %s
                            RETURNING user_id, experience_points, level
                        ),
                        transaction_record AS (
                            INSERT INTO progression.xp_transactions
                                (user_id, xp_amount, xp_type, xp_balance_after, level_before, level_after, did_level_up, description, metadata)
                            SELECT
                                u.user_id,
                                %s,
                                %s,
                                u.experience_points,
                                c.level,
                                u.level,
                                (u.level > c.level),
                                %s,
                                %s::jsonb
                            FROM updated u
                            CROSS JOIN current_state c
                            RETURNING user_id, xp_balance_after AS experience_points, level_before, level_after, did_level_up
                        )
                        SELECT * FROM transaction_record
                    """, (user_id, xp_amount, xp_amount, user_id, xp_amount, xp_type, description, metadata_json))

                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error awarding experience for {user_id}: {e}")
            return None

    def get_xp_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """사용자 경험치 거래 내역 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT transaction_id, user_id, xp_amount, xp_type, xp_balance_after,
                               level_before, level_after, did_level_up, description, metadata, created_at
                        FROM progression.xp_transactions
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (user_id, limit, offset))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error getting xp transactions for {user_id}: {e}")
            return []

    def initialize_user(self, user_id: str) -> bool:
        """사용자 진행도 초기화"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. user_progression 초기화
                    cur.execute("""
                        INSERT INTO progression.user_progression (user_id, rank_code, experience_points, level)
                        VALUES (%s, 'novice', 0, 1)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))

                    # 2. user_equipment 초기화
                    cur.execute("""
                        INSERT INTO progression.user_equipment (user_id, sword_status, uniform_status, crow_status)
                        VALUES (%s, 'good', 'worn', 'waiting')
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))

                    # 3. user_credits 초기화
                    cur.execute("""
                        INSERT INTO auth.user_credits (user_id, bubble_count, total_purchased, total_consumed)
                        VALUES (%s, 0, 0, 0)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))

                    return True
        except Exception as e:
            print(f"Error initializing user progression for {user_id}: {e}")
            return False

    # ============================================================
    # Scenario Progress
    # ============================================================

    def get_scenarios_with_user_progress(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """사용자 진행도가 포함된 시나리오 목록 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT
                            s.scenario_id,
                            s.title,
                            s.description,
                            s.image_url,
                            s.thumbnail_url,
                            s.tags,
                            s.card_size,
                            s.route_path,
                            s.display_order,
                            s.is_active,
                            COALESCE(ss.total_likes, 0) as likes,
                            COALESCE(ss.total_comments, 0) as comments,
                            COALESCE(ss.total_views, 0) as views,
                            COALESCE(ss.total_completions, 0) as total_completions,
                            COALESCE(usp.is_liked, false) as is_liked,
                            COALESCE(usp.has_started, false) as has_started,
                            COALESCE(usp.has_completed, false) as has_completed,
                            COALESCE(usp.completion_percentage, 0) as completion_percentage,
                            usp.last_played_at
                        FROM content.scenarios s
                        LEFT JOIN content.scenario_statistics ss ON s.scenario_id = ss.scenario_id
                        LEFT JOIN progression.user_scenario_progress usp ON s.scenario_id = usp.scenario_id AND usp.user_id = %s
                        WHERE s.is_active = true
                        ORDER BY s.display_order
                    """, (user_id,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error getting scenarios with user progress for {user_id}: {e}")
            return []

    def toggle_scenario_like(
        self,
        user_id: str,
        scenario_id: str
    ) -> Dict[str, Any]:
        """시나리오 좋아요 토글"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Check existing like status
                    cur.execute("""
                        SELECT is_liked FROM progression.user_scenario_progress
                        WHERE user_id = %s AND scenario_id = %s
                    """, (user_id, scenario_id))
                    result = cur.fetchone()

                    if result:
                        new_liked_status = not result['is_liked']
                        cur.execute("""
                            UPDATE progression.user_scenario_progress
                            SET is_liked = %s,
                                liked_at = CASE WHEN %s THEN NOW() ELSE NULL END,
                                updated_at = NOW()
                            WHERE user_id = %s AND scenario_id = %s
                        """, (new_liked_status, new_liked_status, user_id, scenario_id))
                    else:
                        cur.execute("""
                            INSERT INTO progression.user_scenario_progress
                            (user_id, scenario_id, is_liked, liked_at)
                            VALUES (%s, %s, true, NOW())
                        """, (user_id, scenario_id))
                        new_liked_status = True

                    # Get updated total likes
                    cur.execute("""
                        SELECT total_likes FROM content.scenario_statistics
                        WHERE scenario_id = %s
                    """, (scenario_id,))
                    stats = cur.fetchone()
                    total_likes = stats['total_likes'] if stats else 0

                    return {"liked": new_liked_status, "total_likes": total_likes}
        except Exception as e:
            print(f"Error toggling scenario like for {user_id}, {scenario_id}: {e}")
            return {"liked": False, "total_likes": 0}

    def get_user_scenario_progress(
        self,
        user_id: str,
        scenario_id: str
    ) -> Optional[Dict[str, Any]]:
        """사용자의 특정 시나리오 진행도 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM progression.user_scenario_progress
                        WHERE user_id = %s AND scenario_id = %s
                    """, (user_id, scenario_id))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error getting user scenario progress for {user_id}, {scenario_id}: {e}")
            return None

    def update_user_scenario_progress(
        self,
        user_id: str,
        scenario_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """사용자의 시나리오 진행도 업데이트"""
        try:
            update_fields = []
            values = []

            for field in ['has_started', 'has_completed', 'completion_percentage',
                         'last_session_id', 'total_messages', 'total_play_time']:
                if field in progress_data:
                    update_fields.append(f"{field} = %s")
                    values.append(progress_data[field])

            if not update_fields:
                return True

            update_fields.append("last_played_at = NOW()")
            update_fields.append("updated_at = NOW()")

            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        INSERT INTO progression.user_scenario_progress
                        (user_id, scenario_id, has_started, has_completed, completion_percentage,
                         last_session_id, total_messages, total_play_time, last_played_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (user_id, scenario_id)
                        DO UPDATE SET {', '.join(update_fields)}
                    """, [user_id, scenario_id] +
                         [progress_data.get(f, None) for f in ['has_started', 'has_completed', 'completion_percentage',
                                                                'last_session_id', 'total_messages', 'total_play_time']] +
                         values)
                    return True
        except Exception as e:
            print(f"Error updating user scenario progress for {user_id}, {scenario_id}: {e}")
            return False

    def record_scenario_view(
        self,
        scenario_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """시나리오 조회 기록"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO content.scenario_views (scenario_id, user_id, ip_address, user_agent)
                        VALUES (%s, %s, %s, %s)
                    """, (scenario_id, user_id, ip_address, user_agent))
                    return True
        except Exception as e:
            print(f"Error recording scenario view for {scenario_id}: {e}")
            return False

    # ============================================================
    # Mission & Game Events
    # ============================================================

    def save_mission_record(
        self,
        session_id: str,
        mission_type: str,
        target_character: str,
        attempt_count: int,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """미션 기록 저장"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO progression.mission_records
                        (session_id, mission_type, target_character, attempt_count, success, completed_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        RETURNING id
                    """, (session_id, mission_type, target_character, attempt_count, success))
                    result = cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            print(f"Error saving mission record for session {session_id}: {e}")
            return None

    def save_game_event(
        self,
        session_id: str,
        turn_number: int,
        event_type: str,
        event_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """게임 이벤트 저장"""
        try:
            from psycopg2.extras import Json

            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO progression.game_events
                        (session_id, turn_number, event_type, event_data, timestamp)
                        VALUES (%s, %s, %s, %s, NOW())
                        RETURNING id
                    """, (session_id, turn_number, event_type, Json(event_data)))
                    result = cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            print(f"Error saving game event for session {session_id}: {e}")
            return None
