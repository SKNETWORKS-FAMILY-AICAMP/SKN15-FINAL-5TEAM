"""
DatabaseManager - PostgreSQL 연동
StateDB와 LogDB에 대한 CRUD 작업 제공
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor, Json
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQL StateDB/LogDB 관리자"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        dbname: str = "kimedb",
        user: str = "kime",
        password: str = "dev123",
        min_conn: int = 2,
        max_conn: int = 10
    ):
        """
        Args:
            host: PostgreSQL 호스트
            port: PostgreSQL 포트
            dbname: 데이터베이스 이름
            user: 사용자 이름
            password: 비밀번호
            min_conn: 최소 연결 수
            max_conn: 최대 연결 수
        """
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(
            min_conn,
            max_conn,
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        logger.info(f"DatabaseManager initialized: {host}:{port}/{dbname}")

    @contextmanager
    def get_connection(self):
        """연결 풀에서 연결 가져오기 (컨텍스트 매니저)"""
        conn = self.connection_pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            self.connection_pool.putconn(conn)

    def close_all(self):
        """모든 연결 종료"""
        self.connection_pool.closeall()
        logger.info("All database connections closed")

    # ========================================
    # StateDB: Sessions
    # ========================================

    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """
        세션 저장 (INSERT or UPDATE)

        Args:
            session_data: {
                "session_id": str (UUID),
                "scenario_id": str,
                "user_name": str,
                "current_stage": str,
                "turn_count": int,
                "stage_turn": int,
                "final_ending": str (optional),
                "is_active": bool
            }
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.sessions (
                            session_id, scenario_id, user_name, current_stage,
                            turn_count, stage_turn, final_ending, is_active, updated_at
                        ) VALUES (
                            %(session_id)s, %(scenario_id)s, %(user_name)s, %(current_stage)s,
                            %(turn_count)s, %(stage_turn)s, %(final_ending)s, %(is_active)s, NOW()
                        )
                        ON CONFLICT (session_id) DO UPDATE SET
                            scenario_id = EXCLUDED.scenario_id,
                            current_stage = EXCLUDED.current_stage,
                            turn_count = EXCLUDED.turn_count,
                            stage_turn = EXCLUDED.stage_turn,
                            final_ending = EXCLUDED.final_ending,
                            is_active = EXCLUDED.is_active,
                            updated_at = NOW()
                    """, session_data)
            logger.debug(f"Session saved: {session_data.get('session_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 로드"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM statedb.sessions WHERE session_id = %s
                    """, (session_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """세션 부분 업데이트"""
        try:
            # 업데이트 가능한 필드만 필터링
            allowed_fields = {
                'current_stage', 'turn_count', 'stage_turn',
                'final_ending', 'is_active'
            }
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

            if not filtered_updates:
                return True

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    set_clause = ", ".join([f"{k} = %s" for k in filtered_updates.keys()])
                    query = f"""
                        UPDATE statedb.sessions
                        SET {set_clause}, updated_at = NOW()
                        WHERE session_id = %s
                    """
                    values = list(filtered_updates.values()) + [session_id]
                    cur.execute(query, values)

            logger.debug(f"Session updated: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False

    # ========================================
    # StateDB: User Inputs
    # ========================================

    def save_user_input(
        self,
        session_id: str,
        turn_number: int,
        user_input: str
    ) -> bool:
        """사용자 입력 저장"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.user_inputs
                        (session_id, turn_number, user_input, timestamp)
                        VALUES (%s, %s, %s, NOW())
                    """, (session_id, turn_number, user_input))
            return True
        except Exception as e:
            logger.error(f"Failed to save user input: {e}")
            return False

    def load_user_inputs(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """최근 사용자 입력 로드"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM statedb.user_inputs
                        WHERE session_id = %s
                        ORDER BY turn_number DESC
                        LIMIT %s
                    """, (session_id, limit))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to load user inputs: {e}")
            return []

    # ========================================
    # StateDB: Dialogues
    # ========================================

    def save_dialogues(
        self,
        session_id: str,
        turn_number: int,
        dialogues: List[Dict[str, Any]]
    ) -> bool:
        """
        대화 목록 저장

        Args:
            session_id: 세션 ID
            turn_number: 턴 번호
            dialogues: [{
                "speaker": str,
                "content": str,
                "emotion": str (optional),
                "emotion_intensity": str (optional)
            }, ...]
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for idx, dialogue in enumerate(dialogues):
                        cur.execute("""
                            INSERT INTO statedb.dialogues
                            (session_id, turn_number, speaker, content,
                             emotion, emotion_intensity, order_index, timestamp)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            session_id,
                            turn_number,
                            dialogue.get("speaker"),
                            dialogue.get("content"),
                            dialogue.get("emotion"),
                            dialogue.get("emotion_intensity"),
                            idx
                        ))
            logger.debug(f"Saved {len(dialogues)} dialogues for turn {turn_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to save dialogues: {e}")
            return False

    def load_dialogues(
        self,
        session_id: str,
        turn_number: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """대화 로드"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if turn_number is not None:
                        cur.execute("""
                            SELECT * FROM statedb.dialogues
                            WHERE session_id = %s AND turn_number = %s
                            ORDER BY order_index ASC
                        """, (session_id, turn_number))
                    else:
                        cur.execute("""
                            SELECT * FROM statedb.dialogues
                            WHERE session_id = %s
                            ORDER BY turn_number DESC, order_index ASC
                            LIMIT %s
                        """, (session_id, limit))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to load dialogues: {e}")
            return []

    # ========================================
    # StateDB: Affinity Records
    # ========================================

    def save_affinity(
        self,
        session_id: str,
        turn_number: int,
        character_name: str,
        affinity_score: int,
        change_amount: Optional[int] = None
    ) -> bool:
        """친밀도 기록 저장"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.affinity_records
                        (session_id, turn_number, character_name,
                         affinity_score, change_amount, timestamp)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (session_id, turn_number, character_name,
                          affinity_score, change_amount))
            return True
        except Exception as e:
            logger.error(f"Failed to save affinity: {e}")
            return False

    def load_latest_affinity(
        self,
        session_id: str
    ) -> Dict[str, int]:
        """최신 친밀도 맵 로드"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT ON (character_name)
                            character_name, affinity_score
                        FROM statedb.affinity_records
                        WHERE session_id = %s
                        ORDER BY character_name, turn_number DESC
                    """, (session_id,))
                    return {row[0]: row[1] for row in cur.fetchall()}
        except Exception as e:
            logger.error(f"Failed to load affinity: {e}")
            return {}

    # ========================================
    # StateDB: Session Snapshots
    # ========================================

    def save_snapshot(
        self,
        session_id: str,
        turn_number: int,
        state_json: Dict[str, Any]
    ) -> bool:
        """세션 스냅샷 저장 (GraphState 전체)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.session_snapshots
                        (session_id, turn_number, state_json, created_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (session_id, turn_number) DO UPDATE
                        SET state_json = EXCLUDED.state_json,
                            created_at = NOW()
                    """, (session_id, turn_number, Json(state_json)))
            logger.debug(f"Snapshot saved: turn {turn_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return False

    def load_latest_snapshot(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """최신 스냅샷 로드"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM statedb.session_snapshots
                        WHERE session_id = %s
                        ORDER BY turn_number DESC
                        LIMIT 1
                    """, (session_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to load snapshot: {e}")
            return None

    # ========================================
    # StateDB: Stage Progression
    # ========================================

    def save_stage_entry(
        self,
        session_id: str,
        stage_id: str,
        stage_order: int
    ) -> bool:
        """스테이지 진입 기록"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.stage_progression
                        (session_id, stage_id, stage_order, entered_at)
                        VALUES (%s, %s, %s, NOW())
                    """, (session_id, stage_id, stage_order))
            return True
        except Exception as e:
            logger.error(f"Failed to save stage entry: {e}")
            return False

    def update_stage_exit(self, session_id: str, stage_id: str) -> bool:
        """스테이지 종료 기록"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE statedb.stage_progression
                        SET exited_at = NOW()
                        WHERE session_id = %s AND stage_id = %s
                          AND exited_at IS NULL
                    """, (session_id, stage_id))
            return True
        except Exception as e:
            logger.error(f"Failed to update stage exit: {e}")
            return False

    # ========================================
    # StateDB: Game Events
    # ========================================

    def save_game_event(
        self,
        session_id: str,
        turn_number: int,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """게임 이벤트 저장"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.game_events
                        (session_id, turn_number, event_type, event_data, timestamp)
                        VALUES (%s, %s, %s, %s, NOW())
                    """, (session_id, turn_number, event_type, Json(event_data)))
            return True
        except Exception as e:
            logger.error(f"Failed to save game event: {e}")
            return False

    # ========================================
    # LogDB: Logs
    # ========================================

    def save_log(
        self,
        log_level: str,
        message: str,
        session_id: Optional[str] = None,
        stage_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> bool:
        """구조화된 로그 저장"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO logdb.logs
                        (session_id, log_level, stage_name, agent_name,
                         message, context_data, duration_ms, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        session_id, log_level, stage_name, agent_name,
                        message, Json(context_data) if context_data else None,
                        duration_ms
                    ))
            return True
        except Exception as e:
            logger.error(f"Failed to save log: {e}")
            return False

    def save_error_log(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        session_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """에러 로그 저장"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO logdb.error_logs
                        (session_id, error_type, error_message,
                         stack_trace, context_data, timestamp)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (
                        session_id, error_type, error_message,
                        stack_trace, Json(context_data) if context_data else None
                    ))
            return True
        except Exception as e:
            logger.error(f"Failed to save error log: {e}")
            return False

    def save_performance_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> bool:
        """성능 메트릭 저장"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO logdb.performance_metrics
                        (metric_name, metric_value, metric_unit, tags, timestamp)
                        VALUES (%s, %s, %s, %s, NOW())
                    """, (
                        metric_name, metric_value, metric_unit,
                        Json(tags) if tags else None
                    ))
            return True
        except Exception as e:
            logger.error(f"Failed to save performance metric: {e}")
            return False


# 환경변수 기반 싱글톤 인스턴스 생성 헬퍼
def create_database_manager_from_env() -> DatabaseManager:
    """환경변수에서 설정을 읽어 DatabaseManager 인스턴스 생성"""
    return DatabaseManager(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "kimedb"),
        user=os.getenv("DB_USER", "kime"),
        password=os.getenv("DB_PASSWORD", "dev123"),
        min_conn=int(os.getenv("DB_MIN_CONN", "2")),
        max_conn=int(os.getenv("DB_MAX_CONN", "10"))
    )
