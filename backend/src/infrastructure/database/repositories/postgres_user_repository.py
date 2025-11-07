"""
PostgreSQL User Repository - IUserRepository 구현체

User 도메인 데이터 접근을 위한 Adapter.
"""

import uuid
import bcrypt
import logging
from typing import Optional, Dict, Any
from psycopg2.extras import RealDictCursor

from src.core.interfaces.repositories.user_repository import IUserRepository
from src.core.exceptions import DatabaseQueryError
from src.infrastructure.database.connection import DatabaseConnection
from src.infrastructure.database.queries.auth_queries import AuthQueries

logger = logging.getLogger(__name__)


class PostgresUserRepository(IUserRepository):
    """
    PostgreSQL User Repository 구현체

    의존성: DatabaseConnection (Connection Pool)
    """

    def __init__(self, db_connection: DatabaseConnection):
        self._db = db_connection

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 ID로 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(AuthQueries.SELECT_USER_BY_ID, (user_id,))
                    row = cursor.fetchone()
                    return dict(row) if row else None

        except Exception as e:
            logger.error(f"❌ Failed to get user by ID: {e}")
            raise DatabaseQueryError(
                query="SELECT_USER_BY_ID",
                message=f"Failed to get user: {str(e)}",
                details={"user_id": user_id}
            )

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """사용자명으로 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(AuthQueries.SELECT_USER_BY_USERNAME, (username,))
                    row = cursor.fetchone()
                    return dict(row) if row else None

        except Exception as e:
            logger.error(f"❌ Failed to get user by username: {e}")
            raise DatabaseQueryError(
                query="SELECT_USER_BY_USERNAME",
                message=f"Failed to get user: {str(e)}",
                details={"username": username}
            )

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """이메일로 조회"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(AuthQueries.SELECT_USER_BY_EMAIL, (email,))
                    row = cursor.fetchone()
                    return dict(row) if row else None

        except Exception as e:
            logger.error(f"❌ Failed to get user by email: {e}")
            raise DatabaseQueryError(
                query="SELECT_USER_BY_EMAIL",
                message=f"Failed to get user: {str(e)}",
                details={"email": email}
            )

    def create_user(
        self,
        username: str,
        password_hash: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> Optional[str]:
        """사용자 생성"""
        user_id = str(uuid.uuid4())
        display_name = display_name or username

        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        AuthQueries.INSERT_USER,
                        (user_id, username, password_hash, email, display_name)
                    )
                    result = cursor.fetchone()
                    created_user_id = result[0] if result else user_id

                    logger.info(f"✅ User created: {username} (ID: {created_user_id})")
                    return created_user_id

        except Exception as e:
            logger.error(f"❌ Failed to create user: {e}")
            raise DatabaseQueryError(
                query="INSERT_USER",
                message=f"Failed to create user: {str(e)}",
                details={"username": username}
            )

    def update_password(self, user_id: str, password_hash: str) -> bool:
        """비밀번호 업데이트"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(AuthQueries.UPDATE_PASSWORD, (password_hash, user_id))
                    logger.info(f"✅ Password updated for user: {user_id}")
                    return True

        except Exception as e:
            logger.error(f"❌ Failed to update password: {e}")
            raise DatabaseQueryError(
                query="UPDATE_PASSWORD",
                message=f"Failed to update password: {str(e)}",
                details={"user_id": user_id}
            )

    def verify_user_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """사용자 인증 (사용자명 + 비밀번호)"""
        try:
            user = self.get_by_username(username)
            if not user:
                return None

            password_hash = user.get("password_hash")
            if not password_hash:
                return None

            # bcrypt로 비밀번호 검증
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                logger.info(f"✅ User authenticated: {username}")
                return user
            else:
                logger.warning(f"⚠️  Authentication failed: {username}")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to verify user password: {e}")
            return None

    def initialize_user_progression(self, user_id: str) -> bool:
        """사용자 진행도 초기화 (ranks, stats, equipment)"""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Ranks 초기화
                    cursor.execute("""
                        INSERT INTO progression.ranks (user_id, rank_name, rank_level)
                        VALUES (%s, '초심자', 1)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))

                    # Stats 초기화
                    cursor.execute("""
                        INSERT INTO progression.stats (user_id, credits, total_sessions, total_dialogues)
                        VALUES (%s, 100, 0, 0)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))

                    # Equipment 초기화 (기본 장비)
                    cursor.execute("""
                        INSERT INTO progression.equipment (user_id, item_type, item_name)
                        VALUES (%s, 'weapon', '기본 검')
                        ON CONFLICT (user_id, item_type) DO NOTHING
                    """, (user_id,))

                    logger.info(f"✅ User progression initialized: {user_id}")
                    return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize user progression: {e}")
            raise DatabaseQueryError(
                query="INITIALIZE_USER_PROGRESSION",
                message=f"Failed to initialize progression: {str(e)}",
                details={"user_id": user_id}
            )
