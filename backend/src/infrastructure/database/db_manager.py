"""
DatabaseManager - PostgreSQL 연동
StateDB와 LogDB에 대한 CRUD 작업 제공
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager
from urllib.parse import urlparse
import psycopg2
from psycopg2 import pool, sql, extensions
from psycopg2.extras import RealDictCursor, Json
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQL StateDB/LogDB 관리자"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        dbname: str = None,
        user: str = None,
        password: str = None,
        database_url: Optional[str] = None,
        min_conn: int = 2,
        max_conn: int = 5  # Optimized for single server instance
    ):
        """
        Args:
            host: PostgreSQL 호스트 (기본값: DB_HOST 환경변수 또는 localhost)
            port: PostgreSQL 포트 (기본값: DB_PORT 환경변수 또는 5432)
            dbname: 데이터베이스 이름 (기본값: DB_NAME 환경변수 또는 kimedb)
            user: 사용자 이름 (기본값: DB_USER 환경변수 또는 kime)
            password: 비밀번호 (기본값: DB_PASSWORD 환경변수 또는 dev123)
            min_conn: 최소 연결 수
            max_conn: 최대 연결 수
        """
        # 우선순위: 명시적 인자 > DATABASE_URL > 전통적인 DB_* 환경변수 > 기본값
        database_url = (
            database_url
            or os.getenv('DATABASE_URL')
            or os.getenv('LOGDB_URL')
        )

        if database_url:
            parsed = urlparse(database_url)
            path_db = parsed.path.lstrip('/') if parsed.path else None
            host = host or parsed.hostname
            port = port or parsed.port
            dbname = dbname or path_db
            user = user or parsed.username
            password = password or parsed.password

        # 환경변수에서 기본값 읽기 (DATABASE_URL 파싱 이후에도 비어있을 수 있음)
        host = host or os.getenv('DB_HOST', 'localhost')
        port = port or int(os.getenv('DB_PORT', '5432'))
        dbname = dbname or os.getenv('DB_NAME', 'kimedb')
        user = user or os.getenv('DB_USER', 'kime')
        password = password or os.getenv('DB_PASSWORD', 'dev123')

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

        logger.info(
            "DatabaseManager initialized with autocommit: %s:%s/%s (user=%s, pool=%s-%s)",
            host,
            port,
            dbname,
            user,
            min_conn,
            max_conn,
        )

    @contextmanager
    def get_connection(self):
        """연결 풀에서 연결 가져오기 (컨텍스트 매니저)"""
        conn = self.connection_pool.getconn()
        try:
            # Autocommit 활성화 (연결 풀에서 가져온 모든 연결에 대해)
            if not conn.autocommit:
                conn.autocommit = True

            # search_path 설정 (새로운 도메인 기반 스키마 사용)
            with conn.cursor() as cur:
                cur.execute("""
                    SET search_path TO auth, conversation, knowledge,
                                      content, progression, observability, ml, public
                """)

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
                        INSERT INTO auth.users
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
                        SELECT * FROM auth.users WHERE username = %s
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
                        SELECT * FROM auth.users WHERE email = %s
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
                        UPDATE auth.users
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
                INSERT INTO auth.password_reset_tokens (user_id, token, expires_at)
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
                FROM auth.password_reset_tokens
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
                UPDATE auth.password_reset_tokens
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
                UPDATE auth.users
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
                        INSERT INTO conversation.sessions (
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
                        SELECT * FROM conversation.sessions WHERE session_id = %s
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
                        UPDATE conversation.sessions
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
                            SELECT * FROM conversation.sessions
                            WHERE user_id = %s AND scenario_id = %s
                            ORDER BY updated_at DESC
                            LIMIT 1
                        """, (user_id, scenario_id))
                    else:
                        # 모든 시나리오 중 마지막 세션
                        cur.execute("""
                            SELECT * FROM conversation.sessions
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
                        INSERT INTO conversation.user_inputs
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
                        SELECT * FROM conversation.user_inputs
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
                            INSERT INTO conversation.dialogues
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
                            SELECT * FROM conversation.dialogues
                            WHERE session_id = %s AND turn_number = %s
                            ORDER BY order_index ASC
                        """, (session_id, turn_number))
                    else:
                        cur.execute("""
                            SELECT * FROM conversation.dialogues
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
                            FROM conversation.dialogues
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
                            FROM conversation.dialogues
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
                        INSERT INTO progression.affinity_records
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
                        FROM progression.affinity_records
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
                        INSERT INTO conversation.session_snapshots
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
                        SELECT * FROM conversation.session_snapshots
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
                        INSERT INTO progression.mission_records
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
                        INSERT INTO progression.stage_progression
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
                        UPDATE progression.stage_progression
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
                        INSERT INTO progression.game_events
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
                        INSERT INTO observability.logs
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
                        INSERT INTO observability.error_logs
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
                        INSERT INTO observability.performance_metrics
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
                        INSERT INTO knowledge.user_memories (
                            user_id, memory_key, memory_value, memory_type,
                            context, importance, source_session_id, tags, confidence
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (user_id, memory_key) DO UPDATE SET
                            memory_value = EXCLUDED.memory_value,
                            memory_type = EXCLUDED.memory_type,
                            context = EXCLUDED.context,
                            importance = GREATEST(knowledge.user_memories.importance, EXCLUDED.importance),
                            source_session_id = COALESCE(EXCLUDED.source_session_id, knowledge.user_memories.source_session_id),
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
                        FROM knowledge.user_memories
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
                        UPDATE knowledge.user_memories
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
                        UPDATE knowledge.user_memories
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
                        UPDATE knowledge.user_memories
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
                        FROM knowledge.user_memories
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
                        FROM knowledge.user_memories
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
                        INSERT INTO knowledge.entities (
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
                        FROM knowledge.entities
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
                        INSERT INTO knowledge.entity_mentions (
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
                        INSERT INTO knowledge.entity_relationships (
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
                        FROM knowledge.entity_relationships r
                        JOIN knowledge.entities e ON (
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
                        FROM knowledge.entities
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
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT bubble_count, total_purchased, total_consumed, last_updated
                        FROM auth.user_credits
                        WHERE user_id = %s
                    """, (user_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get user credits: {e}")
            return None

    def consume_credits(self, user_id: str, amount: int, description: str) -> bool:
        """크레딧 소비 (트랜잭션)"""
        try:
            with self.get_connection() as conn:
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
                          (user_id, amount, transaction_type, balance_after, description)
                        SELECT user_id, -%s, 'consume', bubble_count, %s
                        FROM updated
                        RETURNING transaction_id;
                    """, (amount, amount, user_id, amount, amount, description))
                    result = cur.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Failed to consume credits: {e}")
            return False

    def add_credits(self, user_id: str, amount: int, transaction_type: str, description: str) -> bool:
        """크레딧 추가 (purchase, bonus, refund)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH updated AS (
                          UPDATE auth.user_credits
                          SET bubble_count = bubble_count + %s,
                              total_purchased = total_purchased + %s,
                              last_updated = NOW()
                          WHERE user_id = %s
                          RETURNING user_id, bubble_count
                        )
                        INSERT INTO auth.credit_transactions
                          (user_id, amount, transaction_type, balance_after, description)
                        SELECT user_id, %s, %s, bubble_count, %s
                        FROM updated
                        RETURNING transaction_id;
                    """, (amount, amount, user_id, amount, transaction_type, description))
                    result = cur.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Failed to add credits: {e}")
            return False

    # ============================================================
    # User Progression Methods (사용자 진행도)
    # ============================================================

    def initialize_user_progression(self, user_id: str) -> bool:
        """신규 사용자 진행도 초기화

        새로운 사용자가 등록될 때 호출되어 progression 관련 3개 테이블에
        초기 레코드를 생성합니다.

        Args:
            user_id: 사용자 UUID

        Returns:
            bool: 초기화 성공 여부

        Raises:
            Exception: DB 오류 시 예외 발생
        """
        # NOTE: 이 함수는 더 이상 필요하지 않을 수 있음
        # 012_user_progression.sql의 Trigger (create_user_progression)가
        # 자동으로 신규 사용자의 progression을 초기화합니다.
        # 하지만 Trigger가 없는 환경을 위해 이 함수는 유지합니다.

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. user_progression 초기화 (novice, level 1, 0 XP)
                    cur.execute("""
                        INSERT INTO progression.user_progression (user_id, rank_code, experience_points, level)
                        VALUES (%s, 'novice', 0, 1)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))

                    # 2. user_equipment 초기화 (good, worn, waiting 상태)
                    cur.execute("""
                        INSERT INTO progression.user_equipment (user_id, sword_status, uniform_status, crow_status)
                        VALUES (%s, 'good', 'worn', 'waiting')
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))

            print(f"✅ User progression initialized for user_id: {user_id}")
            return True

        except Exception as e:
            print(f"⚠️ Warning: Failed to initialize progression for user {user_id}: {e}")
            print("   (Trigger may have already initialized progression)")
            import traceback
            traceback.print_exc()
            # 예외를 발생시키지 않고 False 반환 (Trigger가 처리할 수 있으므로)
            return False

    def get_user_progression(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 진행도 조회 (rank, level, XP, stats, equipment 포함)

        Args:
            user_id: 사용자 UUID

        Returns:
            사용자 진행도 전체 정보 딕셔너리 또는 None
            {
                'user_id': str,
                'rank_code': str,
                'rank_name_ko': str,
                'rank_icon': str,
                'experience_points': int,
                'level': int,
                'next_rank_xp': int,
                'total_messages': int,
                'total_sessions': int,
                'total_play_minutes': int,
                'scenarios_completed': int,
                'achievements_count': int,
                'sword_status': str,
                'uniform_status': str,
                'crow_status': str
            }
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM progression.v_user_progression_summary
                        WHERE user_id = %s
                    """, (user_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get user progression for {user_id}: {e}")
            return None

    def get_user_equipment(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 장비 상태 조회

        Args:
            user_id: 사용자 UUID

        Returns:
            장비 상태 딕셔너리 또는 None
            {
                'sword_status': str,
                'uniform_status': str,
                'crow_status': str,
                'sword_type': str,
                'uniform_color': str,
                'crow_name': str
            }
        """
        query = """
        SELECT sword_status, uniform_status, crow_status,
               sword_type, uniform_color, crow_name
        FROM progression.user_equipment
        WHERE user_id = %s
        """
        results = self.execute_query(query, (user_id,))
        return results[0] if results else None

    def award_experience(self, user_id: str, xp_amount: int, xp_type: str, description: str = None, metadata: Dict = None) -> Optional[Dict[str, Any]]:
        """경험치 지급 및 레벨업 처리

        Args:
            user_id: 사용자 UUID
            xp_amount: 지급할 경험치
            xp_type: 경험치 타입 ('message', 'session_complete', 'scenario_complete', 'achievement', 'daily_bonus', 'event')
            description: 설명 (선택)
            metadata: 추가 메타데이터 (선택, JSONB)

        Returns:
            업데이트된 progression 정보 또는 None
            {
                'user_id': str,
                'experience_points': int,
                'level': int,
                'level_before': int,
                'level_after': int,
                'did_level_up': bool
            }
        """
        import json
        metadata_json = json.dumps(metadata) if metadata else None

        query = """
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
            RETURNING user_id, experience_points AS xp_balance_after, level_before, level_after, did_level_up
        )
        SELECT * FROM transaction_record
        """
        results = self.execute_query(
            query,
            (user_id, xp_amount, xp_amount, user_id, xp_amount, xp_type, description, metadata_json)
        )
        return results[0] if results else None

    def increment_user_stat(self, user_id: str, stat_name: str, increment_by: int = 1) -> bool:
        """사용자 통계 증가

        Args:
            user_id: 사용자 UUID
            stat_name: 통계 컬럼명 ('total_messages', 'total_sessions', 'total_play_minutes', 'scenarios_completed', 'achievements_count')
            increment_by: 증가량 (기본 1)

        Returns:
            성공 여부
        """
        valid_stats = ['total_messages', 'total_sessions', 'total_play_minutes', 'scenarios_completed', 'achievements_count']
        if stat_name not in valid_stats:
            raise ValueError(f"Invalid stat name: {stat_name}. Must be one of {valid_stats}")

        query = f"""
        UPDATE progression.user_progression
        SET {stat_name} = {stat_name} + %s,
            updated_at = NOW()
        WHERE user_id = %s
        """
        self.execute_query(query, (increment_by, user_id))
        return True

    def update_user_equipment(self, user_id: str, equipment_updates: Dict[str, str]) -> bool:
        """사용자 장비 상태 업데이트

        Args:
            user_id: 사용자 UUID
            equipment_updates: 업데이트할 장비 딕셔너리
                예: {'sword_status': 'excellent', 'uniform_status': 'equipped'}

        Returns:
            성공 여부
        """
        valid_fields = ['sword_status', 'uniform_status', 'crow_status', 'sword_type', 'uniform_color', 'crow_name']

        # 유효한 필드만 필터링
        updates = {k: v for k, v in equipment_updates.items() if k in valid_fields}

        if not updates:
            return False

        # SET 절 동적 생성
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [user_id]

        query = f"""
        UPDATE progression.user_equipment
        SET {set_clause}, updated_at = NOW()
        WHERE user_id = %s
        """
        self.execute_query(query, values)
        return True

    def get_xp_transactions(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """사용자 경험치 거래 내역 조회

        Args:
            user_id: 사용자 UUID
            limit: 조회 개수 (기본 50)
            offset: 오프셋 (페이지네이션)

        Returns:
            거래 내역 리스트
        """
        query = """
        SELECT transaction_id, user_id, xp_amount, xp_type, xp_balance_after,
               level_before, level_after, did_level_up, description, metadata, created_at
        FROM progression.xp_transactions
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
        return self.execute_query(query, (user_id, limit, offset))

    def get_rank_leaderboard(self, limit: int = 100) -> List[Dict[str, Any]]:
        """경험치 기준 리더보드 조회

        Args:
            limit: 조회 개수 (기본 100)

        Returns:
            상위 사용자 리스트 (순위 포함)
        """
        query = """
        SELECT
            ROW_NUMBER() OVER (ORDER BY up.experience_points DESC, up.level DESC) AS rank,
            u.user_id,
            u.username,
            u.display_name,
            up.rank_code,
            rd.rank_name_ko,
            rd.icon_emoji AS rank_icon,
            up.experience_points,
            up.level,
            up.total_messages,
            up.scenarios_completed
        FROM progression.user_progression up
        LEFT JOIN auth.users u ON up.user_id = u.user_id
        LEFT JOIN content.rank_definitions rd ON
            up.experience_points >= rd.min_xp AND
            up.level BETWEEN rd.level_range_start AND rd.level_range_end
        ORDER BY up.experience_points DESC, up.level DESC
        LIMIT %s
        """
        return self.execute_query(query, (limit,))

    # ============================================================
    # Scenario Management Methods (시나리오 관리)
    # ============================================================

    def get_all_scenarios(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """모든 시나리오 조회 (통계 포함)

        Args:
            include_inactive: 비활성 시나리오도 포함 여부

        Returns:
            시나리오 리스트 (통계 포함)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if include_inactive:
                        cur.execute("SELECT * FROM content.v_scenario_cards ORDER BY display_order")
                    else:
                        cur.execute("""
                            SELECT * FROM content.v_scenario_cards
                            WHERE is_active = true
                            ORDER BY display_order
                        """)
                    results = cur.fetchall()
                    return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Failed to get scenarios: {e}")
            return []

    def get_scenario_by_id(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """ID로 시나리오 조회

        Args:
            scenario_id: 시나리오 ID

        Returns:
            시나리오 정보 (통계 포함) 또는 None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM content.v_scenario_cards
                        WHERE scenario_id = %s
                    """, (scenario_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get scenario {scenario_id}: {e}")
            return None

    def get_scenario_statistics(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """시나리오 통계 조회

        Args:
            scenario_id: 시나리오 ID

        Returns:
            통계 정보 또는 None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM content.scenario_statistics
                        WHERE scenario_id = %s
                    """, (scenario_id,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get statistics for scenario {scenario_id}: {e}")
            return None

    def record_scenario_view(self, scenario_id: str, user_id: Optional[str] = None,
                            ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
        """시나리오 조회 기록 (조회수 증가)

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID (선택, 익명 가능)
            ip_address: IP 주소 (선택)
            user_agent: User Agent (선택)

        Returns:
            성공 여부
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO content.scenario_views (scenario_id, user_id, ip_address, user_agent)
                        VALUES (%s, %s, %s, %s)
                    """, (scenario_id, user_id, ip_address, user_agent))
                    # Trigger will auto-increment scenario_statistics.total_views
            return True
        except Exception as e:
            logger.error(f"Failed to record view for scenario {scenario_id}: {e}")
            return False

    def get_user_scenario_progress(self, user_id: str, scenario_id: str) -> Optional[Dict[str, Any]]:
        """사용자의 특정 시나리오 진행도 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            진행도 정보 또는 None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM progression.user_scenario_progress
                        WHERE user_id = %s AND scenario_id = %s
                    """, (user_id, scenario_id))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get progress for user {user_id}, scenario {scenario_id}: {e}")
            return None

    def get_all_user_scenario_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자의 모든 시나리오 진행도 조회

        Args:
            user_id: 사용자 ID

        Returns:
            진행도 리스트
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM progression.user_scenario_progress
                        WHERE user_id = %s
                        ORDER BY last_played_at DESC NULLS LAST
                    """, (user_id,))
                    results = cur.fetchall()
                    return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Failed to get all progress for user {user_id}: {e}")
            return []

    def toggle_scenario_like(self, user_id: str, scenario_id: str) -> Dict[str, Any]:
        """시나리오 좋아요 토글 (좋아요/취소)

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            {"liked": bool, "total_likes": int}
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Check if progress record exists
                    cur.execute("""
                        SELECT is_liked FROM progression.user_scenario_progress
                        WHERE user_id = %s AND scenario_id = %s
                    """, (user_id, scenario_id))
                    result = cur.fetchone()

                    if result:
                        # Toggle existing like status
                        new_liked_status = not result['is_liked']
                        cur.execute("""
                            UPDATE progression.user_scenario_progress
                            SET is_liked = %s,
                                liked_at = CASE WHEN %s THEN NOW() ELSE NULL END,
                                updated_at = NOW()
                            WHERE user_id = %s AND scenario_id = %s
                        """, (new_liked_status, new_liked_status, user_id, scenario_id))
                    else:
                        # Create new progress record with like
                        cur.execute("""
                            INSERT INTO progression.user_scenario_progress
                            (user_id, scenario_id, is_liked, liked_at)
                            VALUES (%s, %s, true, NOW())
                        """, (user_id, scenario_id))
                        new_liked_status = True

                    # Trigger will auto-update scenario_statistics.total_likes

                    # Get updated total likes
                    cur.execute("""
                        SELECT total_likes FROM content.scenario_statistics
                        WHERE scenario_id = %s
                    """, (scenario_id,))
                    stats = cur.fetchone()
                    total_likes = stats['total_likes'] if stats else 0

                    return {
                        "liked": new_liked_status,
                        "total_likes": total_likes
                    }
        except Exception as e:
            logger.error(f"Failed to toggle like for scenario {scenario_id}, user {user_id}: {e}")
            raise

    def update_user_scenario_progress(self, user_id: str, scenario_id: str,
                                     progress_data: Dict[str, Any]) -> bool:
        """사용자 시나리오 진행도 업데이트

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            progress_data: 업데이트할 데이터
                {
                    "has_started": bool,
                    "has_completed": bool,
                    "completion_percentage": int,
                    "last_session_id": str,
                    "total_messages": int,
                    "total_play_time": int
                }

        Returns:
            성공 여부
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Build update query dynamically
                    update_fields = []
                    values = []

                    for field in ['has_started', 'has_completed', 'completion_percentage',
                                 'last_session_id', 'total_messages', 'total_play_time']:
                        if field in progress_data:
                            update_fields.append(f"{field} = %s")
                            values.append(progress_data[field])

                    if not update_fields:
                        return True  # Nothing to update

                    update_fields.append("last_played_at = NOW()")
                    update_fields.append("updated_at = NOW()")

                    values.extend([user_id, scenario_id])

                    query = f"""
                        INSERT INTO progression.user_scenario_progress (user_id, scenario_id, {', '.join([f.split('=')[0].strip() for f in update_fields])})
                        VALUES (%s, %s, {', '.join(['%s'] * len(update_fields))})
                        ON CONFLICT (user_id, scenario_id)
                        DO UPDATE SET {', '.join(update_fields)}
                    """

                    cur.execute(query, [user_id, scenario_id] + [progress_data.get(f.split('=')[0].strip(), None) for f in update_fields if '=' in f][:len(update_fields)-2] + values[-2:])

            return True
        except Exception as e:
            logger.error(f"Failed to update progress for user {user_id}, scenario {scenario_id}: {e}")
            return False

    def get_scenarios_with_user_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자별 진행도가 포함된 시나리오 리스트 조회

        Args:
            user_id: 사용자 ID

        Returns:
            시나리오 리스트 (통계 + 사용자 진행도 포함)
        """
        try:
            with self.get_connection() as conn:
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
                    results = cur.fetchall()
                    return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Failed to get scenarios with user progress for {user_id}: {e}")
            return []

    # ========================================
    # StateDB: User Memories (장기 기억 시스템)
    # ========================================

    def create_or_update_memory(
        self,
        user_id: str,
        memory_key: str,
        memory_value: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        source_session_id: Optional[str] = None,
        confidence: Optional[float] = None,
        embedding: Optional[List[float]] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[int]:
        """사용자 기억 생성 또는 업데이트

        Args:
            user_id: 사용자 ID
            memory_key: 기억의 키 (예: "favorite_character")
            memory_value: 기억 내용 (예: "탄지로를 좋아함")
            memory_type: 기억 타입 (fact, preference, progress 등)
            importance: 중요도 (0.0~1.0)
            tags: 태그 리스트
            context: 추가 컨텍스트 (JSONB)
            source_session_id: 원본 세션 ID
            confidence: 신뢰도 (0.0~1.0)
            embedding: 임베딩 벡터 (1536차원)
            expires_at: 만료 시간

        Returns:
            생성/업데이트된 기억의 ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO knowledge.user_memories
                        (user_id, memory_key, memory_value, memory_type, importance,
                         tags, context, source_session_id, confidence, embedding, expires_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, memory_key)
                        DO UPDATE SET
                            memory_value = EXCLUDED.memory_value,
                            memory_type = EXCLUDED.memory_type,
                            importance = EXCLUDED.importance,
                            tags = EXCLUDED.tags,
                            context = EXCLUDED.context,
                            confidence = EXCLUDED.confidence,
                            embedding = EXCLUDED.embedding,
                            expires_at = EXCLUDED.expires_at,
                            updated_at = NOW()
                        RETURNING id
                    """, (user_id, memory_key, memory_value, memory_type, importance,
                          tags, Json(context) if context else None, source_session_id,
                          confidence, embedding, expires_at))
                    result = cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to create/update memory for user {user_id}, key {memory_key}: {e}")
            return None

    def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """사용자의 기억 조회

        Args:
            user_id: 사용자 ID
            memory_type: 특정 타입만 조회 (선택)
            min_importance: 최소 중요도
            tags: 특정 태그가 포함된 기억만 조회
            limit: 최대 조회 개수
            include_inactive: 비활성 기억 포함 여부

        Returns:
            기억 리스트
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    conditions = ["user_id = %s", "importance >= %s"]
                    params = [user_id, min_importance]

                    if memory_type:
                        conditions.append("memory_type = %s")
                        params.append(memory_type)

                    if tags:
                        conditions.append("tags && %s")
                        params.append(tags)

                    if not include_inactive:
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
                    results = cur.fetchall()
                    return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Failed to get memories for user {user_id}: {e}")
            return []

    def get_memory_by_key(self, user_id: str, memory_key: str) -> Optional[Dict[str, Any]]:
        """특정 키의 기억 조회

        Args:
            user_id: 사용자 ID
            memory_key: 기억 키

        Returns:
            기억 정보 또는 None
        """
        try:
            with self.get_connection() as conn:
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
            logger.error(f"Failed to get memory {memory_key} for user {user_id}: {e}")
            return None

    def search_memories_by_similarity(
        self,
        user_id: str,
        query_embedding: List[float],
        limit: int = 5,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """임베딩 벡터 유사도로 기억 검색

        Args:
            user_id: 사용자 ID
            query_embedding: 검색할 임베딩 벡터 (1536차원)
            limit: 최대 조회 개수
            min_importance: 최소 중요도

        Returns:
            유사도 순으로 정렬된 기억 리스트 (distance 포함)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # pgvector의 <=> 연산자는 코사인 거리 (작을수록 유사)
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
                    results = cur.fetchall()
                    return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Failed to search memories by similarity for user {user_id}: {e}")
            return []

    def delete_memory(self, user_id: str, memory_key: str, soft_delete: bool = True) -> bool:
        """기억 삭제

        Args:
            user_id: 사용자 ID
            memory_key: 기억 키
            soft_delete: True면 is_active=false, False면 실제 삭제

        Returns:
            성공 여부
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if soft_delete:
                        cur.execute("""
                            UPDATE knowledge.user_memories
                            SET is_active = false, updated_at = NOW()
                            WHERE user_id = %s AND memory_key = %s
                        """, (user_id, memory_key))
                    else:
                        cur.execute("""
                            DELETE FROM knowledge.user_memories
                            WHERE user_id = %s AND memory_key = %s
                        """, (user_id, memory_key))
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_key} for user {user_id}: {e}")
            return False

    def add_related_session_to_memory(self, user_id: str, memory_key: str, session_id: str) -> bool:
        """기억에 관련 세션 추가

        Args:
            user_id: 사용자 ID
            memory_key: 기억 키
            session_id: 추가할 세션 ID

        Returns:
            성공 여부
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE knowledge.user_memories
                        SET related_session_ids = array_append(
                            COALESCE(related_session_ids, ARRAY[]::uuid[]),
                            %s::uuid
                        ),
                        updated_at = NOW()
                        WHERE user_id = %s AND memory_key = %s
                    """, (session_id, user_id, memory_key))
            return True
        except Exception as e:
            logger.error(f"Failed to add related session to memory {memory_key} for user {user_id}: {e}")
            return False
    # ========================================
    # Content: Characters
    # ========================================

    def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete character data from database

        Args:
            character_id: Character ID

        Returns:
            Character dict with all related data (formatted like JSON structure)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Main character data
                    cur.execute("""
                        SELECT character_id, name, description, personality, breathing_style,
                               default_affinity, appearance_hair, appearance_eyes,
                               appearance_distinctive, appearance_impression
                        FROM content.characters
                        WHERE character_id = %s
                    """, (character_id,))

                    char = cur.fetchone()
                    if not char:
                        return None

                    result = dict(char)
                    result['id'] = character_id

                    # Appearance dict
                    result['appearance'] = {
                        'hair': char['appearance_hair'],
                        'eyes': char['appearance_eyes'],
                        'distinctive': char['appearance_distinctive'],
                        'impression': char['appearance_impression']
                    }

                    # Core values
                    cur.execute("""
                        SELECT value_text
                        FROM content.character_core_values
                        WHERE character_id = %s
                        ORDER BY display_order
                    """, (character_id,))
                    result['core_values'] = [row['value_text'] for row in cur.fetchall()]

                    # Emotional triggers
                    cur.execute("""
                        SELECT emotion_type, trigger_text
                        FROM content.character_emotional_triggers
                        WHERE character_id = %s
                        ORDER BY emotion_type, display_order
                    """, (character_id,))

                    triggers = {}
                    for row in cur.fetchall():
                        emotion = row['emotion_type']
                        if emotion not in triggers:
                            triggers[emotion] = []
                        triggers[emotion].append(row['trigger_text'])
                    result['emotional_triggers'] = triggers

                    # Tone settings
                    cur.execute("""
                        SELECT affinity_level, level_range_min, level_range_max,
                               style, calling, suffix, samples
                        FROM content.character_tone
                        WHERE character_id = %s
                        ORDER BY level_range_min
                    """, (character_id,))

                    tone = {}
                    for row in cur.fetchall():
                        tone[row['affinity_level']] = {
                            'level_range': [row['level_range_min'], row['level_range_max']],
                            'style': row['style'],
                            'calling': row['calling'],
                            'suffix': row['suffix'],
                            'samples': row['samples'] if isinstance(row['samples'], list) else []
                        }
                    result['tone'] = tone

                    # Aliases
                    cur.execute("""
                        SELECT alias
                        FROM content.character_aliases
                        WHERE character_id = %s
                    """, (character_id,))
                    result['aliases'] = [row['alias'] for row in cur.fetchall()]

                    # Quotes
                    cur.execute("""
                        SELECT quote_text
                        FROM content.character_quotes
                        WHERE character_id = %s
                        ORDER BY display_order
                    """, (character_id,))
                    result['signature_quotes'] = [row['quote_text'] for row in cur.fetchall()]

                    # Intent rules
                    cur.execute("""
                        SELECT rule_category, rule_type, rule_value
                        FROM content.character_intent_rules
                        WHERE character_id = %s
                    """, (character_id,))

                    intent_rules = {}
                    for row in cur.fetchall():
                        category = row['rule_category']
                        if category not in intent_rules:
                            intent_rules[category] = {}
                        # rule_value is already parsed as dict/list from JSONB
                        intent_rules[category][row['rule_type']] = row['rule_value']
                    result['intent_rules'] = intent_rules

                    return result

        except Exception as e:
            logger.error(f"Failed to get character {character_id}: {e}")
            return None

    def list_characters(self) -> List[str]:
        """
        Get list of all character IDs

        Returns:
            List of character IDs
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT character_id FROM content.characters ORDER BY character_id")
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list characters: {e}")
            return []

    # ========================================
    # Content: Scenario Beats
    # ========================================

    def get_scenario_beats(self, scenario_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all scenario beats and goals for a scenario

        Args:
            scenario_id: Scenario ID

        Returns:
            Dict mapping beat_name to list of goals
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT sb.beat_id, sb.beat_name, bg.goal_text,
                               bg.speaker_hints, bg.fx, bg.display_order
                        FROM content.scenario_beats sb
                        LEFT JOIN content.beat_goals bg ON sb.beat_id = bg.beat_id
                        WHERE sb.scenario_id = %s
                        ORDER BY sb.beat_name, bg.display_order
                    """, (scenario_id,))

                    beats = {}
                    for row in cur.fetchall():
                        beat_name = row['beat_name']
                        if beat_name not in beats:
                            beats[beat_name] = []

                        if row['goal_text']:  # Only add if goal exists
                            goal = {
                                'goal': row['goal_text'],
                                'speaker_hint': row['speaker_hints'] if isinstance(row['speaker_hints'], list) else [],
                            }
                            if row['fx']:
                                goal['fx'] = row['fx']
                            beats[beat_name].append(goal)

                    return beats

        except Exception as e:
            logger.error(f"Failed to get scenario beats for {scenario_id}: {e}")
            return {}

    def get_image_mappings(self, scenario_id: str) -> Dict[str, str]:
        """
        Get image mappings for a scenario

        Args:
            scenario_id: Scenario ID

        Returns:
            Dict mapping image_key to image_url
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT image_key, image_url, metadata
                        FROM content.image_mappings
                        WHERE scenario_id = %s
                        ORDER BY mapping_category, image_key
                    """, (scenario_id,))

                    return {row['image_key']: row['image_url'] for row in cur.fetchall()}

        except Exception as e:
            logger.error(f"Failed to get image mappings for {scenario_id}: {e}")
            return {}


# 환경변수 기반 싱글톤 인스턴스 생성 헬퍼
def create_database_manager_from_env() -> DatabaseManager:
    """환경변수에서 설정을 읽어 DatabaseManager 인스턴스 생성"""
    return DatabaseManager(
        database_url=os.getenv("DATABASE_URL") or os.getenv("LOGDB_URL"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")) if os.getenv("DB_PORT") else None,
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        min_conn=int(os.getenv("DB_MIN_CONN", "2")),
        max_conn=int(os.getenv("DB_MAX_CONN", "10"))
    )
