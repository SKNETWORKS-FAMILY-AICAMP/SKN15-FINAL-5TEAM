"""
Database Connection - PostgreSQL Connection Pool 관리

단일 책임: Connection Pool만 관리 (쿼리 실행은 Repository에서)
"""

import logging
from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection

from core.config.settings import get_settings
from core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    PostgreSQL Connection Pool 관리자

    책임:
    - Connection Pool 생성 및 관리
    - Connection 제공 (context manager)
    - Health Check
    - Connection Pool 종료
    """

    def __init__(self):
        """
        환경변수에서 설정을 읽어 Connection Pool 생성
        """
        settings = get_settings()
        db_config = settings.database

        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=db_config.min_conn,
                maxconn=db_config.max_conn,
                host=db_config.host,
                port=db_config.port,
                database=db_config.name,
                user=db_config.user,
                password=db_config.password,
                # Connection 기본 설정
                connect_timeout=10,
                options="-c statement_timeout=30000"  # 30초 쿼리 타임아웃
            )

            # Autocommit 모드로 모든 Connection 설정
            for _ in range(db_config.min_conn):
                conn = self._pool.getconn()
                conn.autocommit = True
                self._pool.putconn(conn)

            logger.info(
                f"✅ Database Connection Pool initialized: "
                f"{db_config.host}:{db_config.port}/{db_config.name} "
                f"(pool: {db_config.min_conn}-{db_config.max_conn})"
            )

        except psycopg2.OperationalError as e:
            logger.error(f"❌ Failed to create database connection pool: {e}")
            raise DatabaseConnectionError(
                message=f"Failed to connect to database: {str(e)}",
                details={"host": db_config.host, "port": db_config.port}
            )

    @contextmanager
    def get_connection(self) -> Generator[connection, None, None]:
        """
        Connection Pool에서 Connection 가져오기 (Context Manager)

        Usage:
            with db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")

        Yields:
            psycopg2 connection
        """
        conn = None
        try:
            conn = self._pool.getconn()

            # Autocommit 활성화 (Connection Pool에서 가져온 연결)
            if not conn.autocommit:
                conn.autocommit = True

            # Search path 설정 (도메인 기반 스키마)
            with conn.cursor() as cur:
                cur.execute("""
                    SET search_path TO auth, conversation, knowledge,
                                      content, progression, observability, ml, public
                """)

            yield conn

        except psycopg2.Error as e:
            logger.error(f"❌ Database error: {e}")
            raise DatabaseConnectionError(
                message=f"Database operation failed: {str(e)}",
                details={"error_code": e.pgcode if hasattr(e, 'pgcode') else None}
            )

        finally:
            if conn and not conn.closed:
                self._pool.putconn(conn)

    def health_check(self) -> bool:
        """
        Database 연결 상태 확인

        Returns:
            연결 정상 여부
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    return result is not None and result[0] == 1
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            return False

    def close_all(self):
        """모든 Connection Pool 종료"""
        try:
            if self._pool:
                self._pool.closeall()
                logger.info("✅ All database connections closed")
        except Exception as e:
            logger.error(f"❌ Failed to close database connections: {e}")

    def __del__(self):
        """소멸자: Connection Pool 자동 종료"""
        self.close_all()
