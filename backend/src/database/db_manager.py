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
from psycopg2 import pool, sql, extensions
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
        # Autocommit 활성화한 connection pool 생성
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(
            min_conn,
            max_conn,
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )

        # 모든 풀의 연결에 autocommit 설정
        for i in range(min_conn):
            conn = self.connection_pool.getconn()
            conn.autocommit = True
            self.connection_pool.putconn(conn)

        logger.info(f"DatabaseManager initialized with autocommit: {host}:{port}/{dbname}")

    @contextmanager
    def get_connection(self):
        """연결 풀에서 연결 가져오기 (컨텍스트 매니저)"""
        conn = self.connection_pool.getconn()
        try:
            # Autocommit 활성화 (연결 풀에서 가져온 모든 연결에 대해)
            if not conn.autocommit:
                conn.autocommit = True

            # search_path 설정 (statedb, public 순으로 검색)
            with conn.cursor() as cur:
                cur.execute("SET search_path TO statedb, public, logdb")

            yield conn

            # Autocommit 모드에서는 명시적 commit 불필요
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn and not conn.closed:
                self.connection_pool.putconn(conn)

    def close_all(self):
        """모든 연결 종료"""
        self.connection_pool.closeall()
        logger.info("All database connections closed")

    # ========================================
    # StateDB: Users
    # ========================================

    def create_user(
        self,
        username: str,
        password_hash: str,
        email: Optional[str] = None,
        provider: str = "email",
        display_name: Optional[str] = None
    ) -> Optional[str]:
        """
        사용자 생성

        Args:
            username: 사용자명 (고유)
            password_hash: bcrypt 해시된 비밀번호
            email: 이메일 (선택)
            provider: 인증 제공자 (email, google, kakao 등)
            display_name: 표시 이름

        Returns:
            생성된 user_id (UUID) 또는 None
        """
        print(f"🔵 create_user() 호출됨: username={username}")
        try:
            with self.get_connection() as conn:
                print(f"🟢 Connection 획득: autocommit={conn.autocommit}")
                with conn.cursor() as cur:
                    print(f"🟡 INSERT 쿼리 실행 중...")
                    cur.execute("""
                        INSERT INTO statedb.users
                        (username, password_hash, email, provider, display_name)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING user_id
                    """, (username, password_hash, email, provider, display_name))
                    result = cur.fetchone()
                    user_id = str(result[0]) if result else None
                    print(f"🟢 User created: {username} (ID: {user_id})")
                    logger.info(f"User created: {username} (ID: {user_id})")
                    return user_id
        except Exception as e:
            print(f"🔴 Error in create_user: {e}")
            logger.error(f"Failed to create user {username}: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """사용자명으로 사용자 조회"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM statedb.users WHERE username = %s
                    """, (username,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get user {username}: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """이메일로 사용자 조회"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM statedb.users WHERE email = %s
                    """, (email,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None

    def update_user_last_login(self, user_id: str) -> bool:
        """마지막 로그인 시간 업데이트"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE statedb.users
                        SET last_login = NOW(), updated_at = NOW()
                        WHERE user_id = %s
                    """, (user_id,))
            logger.debug(f"Last login updated for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            return False

    def verify_user_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        사용자 인증 (비밀번호 확인)

        Args:
            username: 사용자명
            password: 평문 비밀번호

        Returns:
            인증 성공 시 사용자 정보, 실패 시 None
        """
        import bcrypt

        user = self.get_user_by_username(username)
        if not user:
            return None

        # 비밀번호 확인
        password_hash = user.get("password_hash")
        if not password_hash:
            return None

        try:
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                # 마지막 로그인 시간 업데이트
                self.update_user_last_login(str(user["user_id"]))
                return user
            else:
                return None
        except Exception as e:
            logger.error(f"Password verification failed for {username}: {e}")
            return None

    # ========================================
    # StateDB: Password Reset Tokens
    # ========================================

    def create_password_reset_token(self, user_id: str, token: str, expires_at: str) -> Optional[str]:
        """
        비밀번호 재설정 토큰 생성

        Args:
            user_id: 사용자 ID
            token: 재설정 토큰
            expires_at: 만료 시간

        Returns:
            Optional[str]: 토큰 ID (성공 시) or None
        """
        try:
            query = """
                INSERT INTO statedb.password_reset_tokens (user_id, token, expires_at)
                VALUES (%s, %s, %s)
                RETURNING token_id;
            """
            result = self.execute_query(query, (user_id, token, expires_at), fetch=True)
            if result and len(result) > 0:
                return str(result[0][0])
            return None
        except Exception as e:
            logger.error(f"Failed to create password reset token: {e}")
            return None

    def get_password_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        비밀번호 재설정 토큰 조회

        Args:
            token: 재설정 토큰

        Returns:
            Optional[Dict]: 토큰 정보 or None
        """
        try:
            query = """
                SELECT token_id, user_id, token, expires_at, used, created_at
                FROM statedb.password_reset_tokens
                WHERE token = %s AND used = false AND expires_at > NOW();
            """
            result = self.execute_query(query, (token,), fetch=True)
            if result and len(result) > 0:
                return {
                    "token_id": str(result[0][0]),
                    "user_id": str(result[0][1]),
                    "token": result[0][2],
                    "expires_at": result[0][3],
                    "used": result[0][4],
                    "created_at": result[0][5],
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get password reset token: {e}")
            return None

    def mark_password_reset_token_as_used(self, token: str) -> bool:
        """
        비밀번호 재설정 토큰을 사용됨으로 표시

        Args:
            token: 재설정 토큰

        Returns:
            bool: 성공 여부
        """
        try:
            query = """
                UPDATE statedb.password_reset_tokens
                SET used = true
                WHERE token = %s;
            """
            self.execute_query(query, (token,))
            return True
        except Exception as e:
            logger.error(f"Failed to mark token as used: {e}")
            return False

    def update_user_password(self, user_id: str, new_password_hash: str) -> bool:
        """
        사용자 비밀번호 업데이트

        Args:
            user_id: 사용자 ID
            new_password_hash: 새 비밀번호 해시

        Returns:
            bool: 성공 여부
        """
        try:
            query = """
                UPDATE statedb.users
                SET password_hash = %s, updated_at = NOW()
                WHERE user_id = %s;
            """
            self.execute_query(query, (new_password_hash, user_id))
            return True
        except Exception as e:
            logger.error(f"Failed to update user password: {e}")
            return False

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
                "user_id": str (UUID, optional) - 인증된 사용자 ID,
                "user_name": str,
                "current_stage": str,
                "turn_count": int,
                "stage_turn": int,
                "final_ending": str (optional),
                "is_active": bool,
                "conversation_summary": str (optional),
                "summary_turn_count": int (optional)
            }
        """
        try:
            # 🧠 장기기억 필드에 기본값 설정
            session_data.setdefault("conversation_summary", "")
            session_data.setdefault("summary_turn_count", 0)
            # user_id가 없으면 None으로 설정 (익명 사용자)
            session_data.setdefault("user_id", None)

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.sessions (
                            session_id, scenario_id, user_id, user_name, current_stage,
                            turn_count, stage_turn, final_ending, is_active,
                            conversation_summary, summary_turn_count, updated_at
                        ) VALUES (
                            %(session_id)s, %(scenario_id)s, %(user_id)s, %(user_name)s, %(current_stage)s,
                            %(turn_count)s, %(stage_turn)s, %(final_ending)s, %(is_active)s,
                            %(conversation_summary)s, %(summary_turn_count)s, NOW()
                        )
                        ON CONFLICT (session_id) DO UPDATE SET
                            scenario_id = EXCLUDED.scenario_id,
                            user_id = EXCLUDED.user_id,
                            current_stage = EXCLUDED.current_stage,
                            turn_count = EXCLUDED.turn_count,
                            stage_turn = EXCLUDED.stage_turn,
                            final_ending = EXCLUDED.final_ending,
                            is_active = EXCLUDED.is_active,
                            conversation_summary = EXCLUDED.conversation_summary,
                            summary_turn_count = EXCLUDED.summary_turn_count,
                            updated_at = NOW()
                    """, session_data)
            logger.debug(f"Session saved: {session_data.get('session_id')} (user_id: {session_data.get('user_id')})")
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
                'final_ending', 'is_active',
                'conversation_summary', 'summary_turn_count'  # 장기기억 필드 추가
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

    def get_user_last_session(
        self,
        user_id: str,
        scenario_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        사용자의 마지막 세션 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID (Optional, 지정하면 해당 시나리오의 마지막 세션만 반환)

        Returns:
            Optional[Dict]: 세션 정보 or None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if scenario_id:
                        # 특정 시나리오의 마지막 세션
                        cur.execute("""
                            SELECT * FROM statedb.sessions
                            WHERE user_id = %s AND scenario_id = %s
                            ORDER BY updated_at DESC
                            LIMIT 1
                        """, (user_id, scenario_id))
                    else:
                        # 모든 시나리오 중 마지막 세션
                        cur.execute("""
                            SELECT * FROM statedb.sessions
                            WHERE user_id = %s
                            ORDER BY updated_at DESC
                            LIMIT 1
                        """, (user_id,))

                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get last session for user {user_id}: {e}")
            return None

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

    def get_session_dialogues(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """세션의 모든 대화 조회 (시간순 정렬)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if limit:
                        cur.execute("""
                            SELECT
                                turn_number, speaker, content,
                                emotion, emotion_intensity, order_index,
                                timestamp
                            FROM statedb.dialogues
                            WHERE session_id = %s
                            ORDER BY turn_number ASC, order_index ASC
                            LIMIT %s
                        """, (session_id, limit))
                    else:
                        cur.execute("""
                            SELECT
                                turn_number, speaker, content,
                                emotion, emotion_intensity, order_index,
                                timestamp
                            FROM statedb.dialogues
                            WHERE session_id = %s
                            ORDER BY turn_number ASC, order_index ASC
                        """, (session_id,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get session dialogues: {e}")
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
    # StateDB: Mission Records
    # ========================================

    def save_mission_record(
        self,
        session_id: str,
        mission_type: str,
        target_character: Optional[str] = None,
        attempt_count: int = 1,
        success: Optional[bool] = None
    ) -> bool:
        """미션 기록 저장"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.mission_records
                        (session_id, mission_type, target_character, attempt_count, success, completed_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (session_id, mission_type, target_character, attempt_count, success))
            return True
        except Exception as e:
            logger.error(f"Failed to save mission record: {e}")
            return False

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

    # ========================================
    # StateDB: User Memories (Long-term Memory)
    # ========================================

    def save_user_memory(
        self,
        user_id: str,
        memory_key: str,
        memory_value: str,
        memory_type: str = "fact",
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        source_session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        confidence: Optional[float] = None
    ) -> Optional[int]:
        """
        사용자 장기 기억 저장 (upsert)

        Args:
            user_id: 사용자 ID (UUID)
            memory_key: 기억 키 (예: "character_relationship:tanjiro")
            memory_value: 기억 내용
            memory_type: 기억 타입 ('fact', 'preference', 'relationship', 'event', 'goal')
            context: 추가 메타데이터 (JSONB)
            importance: 중요도 (0.0 ~ 1.0)
            source_session_id: 출처 세션 ID
            tags: 태그 목록
            confidence: 신뢰도 (0.0 ~ 1.0, auto-extracted memories용)

        Returns:
            int: 생성/업데이트된 memory의 ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.user_memories (
                            user_id, memory_key, memory_value, memory_type,
                            context, importance, source_session_id, tags, confidence
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (user_id, memory_key) DO UPDATE SET
                            memory_value = EXCLUDED.memory_value,
                            memory_type = EXCLUDED.memory_type,
                            context = EXCLUDED.context,
                            importance = GREATEST(statedb.user_memories.importance, EXCLUDED.importance),
                            source_session_id = COALESCE(EXCLUDED.source_session_id, statedb.user_memories.source_session_id),
                            tags = EXCLUDED.tags,
                            confidence = EXCLUDED.confidence,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id;
                    """, (
                        user_id, memory_key, memory_value, memory_type,
                        Json(context) if context else None,
                        importance, source_session_id, tags, confidence
                    ))
                    memory_id = cur.fetchone()[0]
                    logger.debug(f"Saved user memory: {memory_key} (ID: {memory_id})")
                    return memory_id
        except Exception as e:
            logger.error(f"Failed to save user memory: {e}")
            return None

    def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 20,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        사용자 장기 기억 조회

        Args:
            user_id: 사용자 ID
            memory_type: 기억 타입 필터 (None이면 전체)
            min_importance: 최소 중요도
            limit: 최대 조회 개수
            active_only: 활성화된 기억만 조회

        Returns:
            List[Dict]: 기억 목록
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT
                            id, memory_key, memory_value, memory_type,
                            context, importance, access_count, last_accessed_at,
                            source_session_id, tags, created_at, updated_at
                        FROM statedb.user_memories
                        WHERE user_id = %s
                          AND importance >= %s
                    """
                    params = [user_id, min_importance]

                    if memory_type:
                        query += " AND memory_type = %s"
                        params.append(memory_type)

                    if active_only:
                        query += " AND is_active = TRUE"

                    query += " ORDER BY importance DESC, last_accessed_at DESC NULLS LAST LIMIT %s"
                    params.append(limit)

                    cur.execute(query, params)
                    memories = cur.fetchall()
                    return [dict(row) for row in memories]
        except Exception as e:
            logger.error(f"Failed to get user memories: {e}")
            return []

    def update_memory_access(self, memory_id: int, importance_boost: float = 0.05) -> bool:
        """
        기억 액세스 기록 및 중요도 증가

        Args:
            memory_id: 기억 ID
            importance_boost: 중요도 증가량 (기본 0.05)

        Returns:
            bool: 성공 여부
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE statedb.user_memories
                        SET
                            importance = LEAST(1.0, importance + %s),
                            access_count = access_count + 1,
                            last_accessed_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (importance_boost, memory_id))
            return True
        except Exception as e:
            logger.error(f"Failed to update memory access: {e}")
            return False

    def get_user_memory_context(self, user_id: str) -> Dict[str, Any]:
        """
        새 세션 시작 시 사용할 사용자 기억 컨텍스트 생성

        Args:
            user_id: 사용자 ID

        Returns:
            Dict: 타입별로 정리된 기억 컨텍스트
        """
        try:
            with self.get_connection() as conn:
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
                                        FROM statedb.user_memories
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
                                        FROM statedb.user_memories
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
                                        FROM statedb.user_memories
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
                                        FROM statedb.user_memories
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
            logger.error(f"Failed to get user memory context: {e}")
            return {}

    def archive_old_memories(self, user_id: str, days_inactive: int = 90, min_importance: float = 0.3) -> int:
        """
        오래되고 중요하지 않은 기억을 비활성화

        Args:
            user_id: 사용자 ID
            days_inactive: 비활성 기간 (일)
            min_importance: 최소 중요도

        Returns:
            int: 비활성화된 기억 개수
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE statedb.user_memories
                        SET is_active = FALSE
                        WHERE user_id = %s
                          AND is_active = TRUE
                          AND importance < %s
                          AND (
                              last_accessed_at < NOW() - INTERVAL '%s days'
                              OR (last_accessed_at IS NULL AND created_at < NOW() - INTERVAL '%s days')
                          )
                    """, (user_id, min_importance, days_inactive, days_inactive))
                    return cur.rowcount
        except Exception as e:
            logger.error(f"Failed to archive old memories: {e}")
            return 0

    def update_user_memory_embedding(
        self,
        memory_id: int,
        embedding: List[float],
        related_entity_ids: Optional[List[int]] = None
    ) -> bool:
        """
        사용자 기억에 임베딩 및 엔티티 링크 추가

        Args:
            memory_id: 기억 ID
            embedding: 임베딩 벡터 (1536-dim)
            related_entity_ids: 관련 엔티티 ID 목록

        Returns:
            bool: 성공 여부
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE statedb.user_memories
                        SET
                            embedding = %s,
                            related_entity_ids = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (embedding, related_entity_ids or [], memory_id))
                    return True
        except Exception as e:
            logger.error(f"Failed to update memory embedding: {e}")
            return False

    def get_user_memories_without_embeddings(
        self,
        limit: int = 50,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        임베딩이 없는 기억 목록 조회 (백필용)

        Args:
            limit: 최대 조회 개수
            active_only: 활성화된 기억만 조회

        Returns:
            List[Dict]: 기억 목록
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT
                            id, user_id, memory_key, memory_value, memory_type,
                            context, importance, source_session_id, tags, created_at
                        FROM statedb.user_memories
                        WHERE embedding IS NULL
                    """

                    if active_only:
                        query += " AND is_active = TRUE"

                    query += " ORDER BY created_at ASC LIMIT %s"

                    cur.execute(query, (limit,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get memories without embeddings: {e}")
            return []

    def find_similar_memories(
        self,
        user_id: str,
        embedding: List[float],
        memory_type: Optional[str] = None,
        limit: int = 5,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        임베딩 기반 유사 기억 검색

        Args:
            user_id: 사용자 ID
            embedding: 쿼리 임베딩
            memory_type: 기억 타입 필터
            limit: 최대 결과 개수
            min_importance: 최소 중요도

        Returns:
            List[Dict]: 유사한 기억 목록
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT
                            id, memory_key, memory_value, memory_type,
                            context, importance, tags,
                            embedding <=> %s::vector AS distance
                        FROM statedb.user_memories
                        WHERE user_id = %s
                          AND embedding IS NOT NULL
                          AND is_active = TRUE
                          AND importance >= %s
                    """

                    params = [embedding, user_id, min_importance]

                    if memory_type:
                        query += " AND memory_type = %s"
                        params.append(memory_type)

                    query += " ORDER BY embedding <=> %s::vector LIMIT %s"
                    params.extend([embedding, limit])

                    cur.execute(query, params)

                    results = []
                    for row in cur.fetchall():
                        results.append({
                            "id": row[0],
                            "memory_key": row[1],
                            "memory_value": row[2],
                            "memory_type": row[3],
                            "context": row[4],
                            "importance": row[5],
                            "tags": row[6],
                            "distance": row[7]
                        })

                    return results

        except Exception as e:
            logger.error(f"Failed to find similar memories: {e}")
            return []
    # ========================================================================
    # Graph RAG: Entity Management
    # ========================================================================

    def save_entity(
        self,
        entity_type: str,
        entity_name: str,
        canonical_name: Optional[str] = None,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
        importance_score: float = 0.5
    ) -> Optional[int]:
        """
        Save or update an entity

        Returns:
            entity_id if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Upsert entity (insert or update if exists)
                    cur.execute("""
                        INSERT INTO statedb.entities (
                            entity_type, entity_name, canonical_name, description,
                            properties, embedding, importance_score, mention_count
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                        ON CONFLICT (entity_type, canonical_name)
                        DO UPDATE SET
                            entity_name = EXCLUDED.entity_name,
                            description = COALESCE(EXCLUDED.description, entities.description),
                            properties = entities.properties || COALESCE(EXCLUDED.properties, '{}'::jsonb),
                            embedding = COALESCE(EXCLUDED.embedding, entities.embedding),
                            importance_score = GREATEST(entities.importance_score, EXCLUDED.importance_score),
                            mention_count = entities.mention_count + 1,
                            last_updated_at = NOW()
                        RETURNING entity_id
                    """, (
                        entity_type,
                        entity_name,
                        canonical_name or entity_name,
                        description,
                        json.dumps(properties) if properties else None,
                        embedding,
                        importance_score
                    ))

                    result = cur.fetchone()
                    return result[0] if result else None

        except Exception as e:
            logger.error(f"Failed to save entity {entity_name}: {e}")
            return None

    def get_entity_by_name(
        self,
        entity_type: str,
        canonical_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get entity by type and canonical name"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            entity_id, entity_type, entity_name, canonical_name,
                            description, properties, importance_score, mention_count,
                            community_id, created_at, last_updated_at
                        FROM statedb.entities
                        WHERE entity_type = %s AND canonical_name = %s
                    """, (entity_type, canonical_name))

                    row = cur.fetchone()
                    if row:
                        return {
                            "entity_id": row[0],
                            "entity_type": row[1],
                            "entity_name": row[2],
                            "canonical_name": row[3],
                            "description": row[4],
                            "properties": row[5],
                            "importance_score": row[6],
                            "mention_count": row[7],
                            "community_id": row[8],
                            "created_at": row[9],
                            "last_updated_at": row[10]
                        }
                    return None

        except Exception as e:
            logger.error(f"Failed to get entity {canonical_name}: {e}")
            return None

    def save_entity_mention(
        self,
        entity_id: int,
        source_type: str,
        source_id: int,
        session_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        mention_context: Optional[str] = None,
        extraction_method: str = "rule",
        confidence: float = 0.8
    ) -> bool:
        """Save entity mention (link entity to log/dialogue/memory)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.entity_mentions (
                            entity_id, source_type, source_id, session_id,
                            turn_number, mention_context, extraction_method, confidence
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        entity_id, source_type, source_id, session_id,
                        turn_number, mention_context, extraction_method, confidence
                    ))
                    return True

        except Exception as e:
            logger.error(f"Failed to save entity mention: {e}")
            return False

    def save_entity_relationship(
        self,
        source_entity_id: int,
        target_entity_id: int,
        relationship_type: str,
        strength: float = 0.5,
        confidence: float = 0.5,
        properties: Optional[Dict[str, Any]] = None,
        provenance: Optional[str] = None
    ) -> Optional[int]:
        """
        Save or update entity relationship

        Returns:
            relationship_id if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statedb.entity_relationships (
                            source_entity_id, target_entity_id, relationship_type,
                            strength, confidence, properties, evidence_count, provenance
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
                        ON CONFLICT (source_entity_id, target_entity_id, relationship_type)
                        DO UPDATE SET
                            strength = (entity_relationships.strength + EXCLUDED.strength) / 2.0,
                            confidence = GREATEST(entity_relationships.confidence, EXCLUDED.confidence),
                            properties = entity_relationships.properties || COALESCE(EXCLUDED.properties, '{}'::jsonb),
                            evidence_count = entity_relationships.evidence_count + 1,
                            last_observed_at = NOW()
                        RETURNING relationship_id
                    """, (
                        source_entity_id,
                        target_entity_id,
                        relationship_type,
                        strength,
                        confidence,
                        json.dumps(properties) if properties else None,
                        provenance
                    ))

                    result = cur.fetchone()
                    return result[0] if result else None

        except Exception as e:
            logger.error(f"Failed to save relationship: {e}")
            return None

    def get_related_entities(
        self,
        entity_id: int,
        relationship_type: Optional[str] = None,
        min_strength: float = 0.0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get entities related to the given entity"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT
                            e.entity_id, e.entity_type, e.entity_name, e.canonical_name,
                            e.description, e.importance_score,
                            r.relationship_type, r.strength, r.confidence
                        FROM statedb.entity_relationships r
                        JOIN statedb.entities e ON (
                            CASE
                                WHEN r.source_entity_id = %s THEN e.entity_id = r.target_entity_id
                                ELSE e.entity_id = r.source_entity_id
                            END
                        )
                        WHERE (r.source_entity_id = %s OR r.target_entity_id = %s)
                          AND r.strength >= %s
                    """

                    params = [entity_id, entity_id, entity_id, min_strength]

                    if relationship_type:
                        query += " AND r.relationship_type = %s"
                        params.append(relationship_type)

                    query += " ORDER BY r.strength DESC, r.confidence DESC LIMIT %s"
                    params.append(limit)

                    cur.execute(query, params)

                    results = []
                    for row in cur.fetchall():
                        results.append({
                            "entity_id": row[0],
                            "entity_type": row[1],
                            "entity_name": row[2],
                            "canonical_name": row[3],
                            "description": row[4],
                            "importance_score": row[5],
                            "relationship_type": row[6],
                            "strength": row[7],
                            "confidence": row[8]
                        })

                    return results

        except Exception as e:
            logger.error(f"Failed to get related entities: {e}")
            return []

    def find_similar_entities(
        self,
        embedding: List[float],
        entity_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find entities similar to the given embedding using vector search"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT
                            entity_id, entity_type, entity_name, canonical_name,
                            description, importance_score,
                            embedding <=> %s::vector AS distance
                        FROM statedb.entities
                        WHERE embedding IS NOT NULL
                    """

                    params = [embedding]

                    if entity_type:
                        query += " AND entity_type = %s"
                        params.append(entity_type)

                    query += " ORDER BY embedding <=> %s::vector LIMIT %s"
                    params.extend([embedding, limit])

                    cur.execute(query, params)

                    results = []
                    for row in cur.fetchall():
                        results.append({
                            "entity_id": row[0],
                            "entity_type": row[1],
                            "entity_name": row[2],
                            "canonical_name": row[3],
                            "description": row[4],
                            "importance_score": row[5],
                            "distance": row[6]
                        })

                    return results

        except Exception as e:
            logger.error(f"Failed to find similar entities: {e}")
            return []

    # ============================================================
    # User Credits (Bubble System)
    # ============================================================

    def get_user_credits(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 크레딧 조회"""
        query = """
        SELECT bubble_count, total_purchased, total_consumed, last_updated
        FROM statedb.user_credits
        WHERE user_id = %s
        """
        results = self.execute_query(query, (user_id,))
        return results[0] if results else None

    def consume_credits(self, user_id: str, amount: int, description: str) -> bool:
        """크레딧 소비 (트랜잭션)"""
        query = """
        WITH updated AS (
          UPDATE statedb.user_credits
          SET bubble_count = bubble_count - %s,
              total_consumed = total_consumed + %s,
              last_updated = NOW()
          WHERE user_id = %s AND bubble_count >= %s
          RETURNING user_id, bubble_count
        )
        INSERT INTO statedb.credit_transactions
          (user_id, amount, transaction_type, balance_after, description)
        SELECT user_id, -%s, 'consume', bubble_count, %s
        FROM updated
        RETURNING transaction_id;
        """
        results = self.execute_query(query, (amount, amount, user_id, amount, amount, description))
        return len(results) > 0

    def add_credits(self, user_id: str, amount: int, transaction_type: str, description: str) -> bool:
        """크레딧 추가 (purchase, bonus, refund)"""
        query = """
        WITH updated AS (
          UPDATE statedb.user_credits
          SET bubble_count = bubble_count + %s,
              total_purchased = total_purchased + %s,
              last_updated = NOW()
          WHERE user_id = %s
          RETURNING user_id, bubble_count
        )
        INSERT INTO statedb.credit_transactions
          (user_id, amount, transaction_type, balance_after, description)
        SELECT user_id, %s, %s, bubble_count, %s
        FROM updated
        RETURNING transaction_id;
        """
        results = self.execute_query(query, (amount, amount, user_id, amount, transaction_type, description))
        return len(results) > 0


# 환경변수 기반 싱글톤 인스턴스 생성 헬퍼
def create_database_manager_from_env() -> DatabaseManager:
    """환경변수에서 설정을 읽어 DatabaseManager 인스턴스 생성"""
    return DatabaseManager(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5433")),
        dbname=os.getenv("DB_NAME", "kimedb"),
        user=os.getenv("DB_USER", "kime"),
        password=os.getenv("DB_PASSWORD", "dev123"),
        min_conn=int(os.getenv("DB_MIN_CONN", "2")),
        max_conn=int(os.getenv("DB_MAX_CONN", "10"))
    )
