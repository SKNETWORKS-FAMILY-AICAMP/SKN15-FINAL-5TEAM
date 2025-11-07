"""
Dependency Container - 의존성 주입(DI) 컨테이너

모든 인프라 의존성을 싱글톤으로 관리.
"""

import logging
from typing import Optional

# Core Interfaces
from core.interfaces.repositories.user_repository import IUserRepository
from core.interfaces.repositories.session_repository import ISessionRepository
from core.interfaces.repositories.character_repository import ICharacterRepository
from core.interfaces.repositories.memory_repository import IMemoryRepository
from core.interfaces.managers.session_manager import ISessionManager
from core.interfaces.providers.llm_provider import ILLMProvider
from core.interfaces.providers.cache_provider import ICacheProvider

# Infrastructure Implementations
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.repositories.postgres_user_repository import PostgresUserRepository
from infrastructure.database.repositories.postgres_session_repository import PostgresSessionRepository
from infrastructure.persistence.postgresql.repositories.character_repo import PostgresCharacterRepository
from infrastructure.persistence.postgresql.repositories.memory_repo import PostgresMemoryRepository
from infrastructure.database.session_manager import HybridSessionManager
from infrastructure.database.session_manager_adapter import SessionManagerAdapter
from infrastructure.database.db_manager import DatabaseManager
from infrastructure.cache.cache_manager import CacheManager
from infrastructure.cache.redis_connection import RedisConnection
from infrastructure.cache.redis_cache_provider import RedisCacheProvider
from infrastructure.cache.strategies.session_cache_strategy import SessionCacheStrategy
from infrastructure.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    의존성 컨테이너 (Singleton Pattern)

    모든 인프라 의존성을 중앙에서 관리:
    - Connections (DB, Redis)
    - Repositories (User, Session)
    - Providers (LLM, Cache)
    - Strategies (SessionCache)
    """

    def __init__(self):
        # Connections (Lazy initialization)
        self._db_connection: Optional[DatabaseConnection] = None
        self._redis_connection: Optional[RedisConnection] = None

        # Repositories (Lazy initialization)
        self._user_repository: Optional[IUserRepository] = None
        self._session_repository: Optional[ISessionRepository] = None
        self._character_repository: Optional[ICharacterRepository] = None
        self._memory_repository: Optional[IMemoryRepository] = None

        # Managers (Lazy initialization)
        self._session_manager: Optional[ISessionManager] = None

        # Providers (Lazy initialization)
        self._llm_provider: Optional[ILLMProvider] = None
        self._cache_provider: Optional[ICacheProvider] = None

        # Strategies (Lazy initialization)
        self._session_cache_strategy: Optional[SessionCacheStrategy] = None

        logger.info("🔧 DependencyContainer initialized (lazy loading)")

    # ============================================================
    # Connections
    # ============================================================

    @property
    def db_connection(self) -> DatabaseConnection:
        """Database Connection (Singleton)"""
        if self._db_connection is None:
            logger.info("🔌 Creating DatabaseConnection...")
            self._db_connection = DatabaseConnection()
        return self._db_connection

    @property
    def redis_connection(self) -> RedisConnection:
        """Redis Connection (Singleton)"""
        if self._redis_connection is None:
            logger.info("🔌 Creating RedisConnection...")
            self._redis_connection = RedisConnection()
        return self._redis_connection

    # ============================================================
    # Repositories
    # ============================================================

    @property
    def user_repository(self) -> IUserRepository:
        """User Repository (Singleton)"""
        if self._user_repository is None:
            logger.info("📦 Creating UserRepository...")
            self._user_repository = PostgresUserRepository(self.db_connection)
        return self._user_repository

    @property
    def session_repository(self) -> ISessionRepository:
        """Session Repository (Singleton)"""
        if self._session_repository is None:
            logger.info("📦 Creating SessionRepository...")
            self._session_repository = PostgresSessionRepository(self.db_connection)
        return self._session_repository

    @property
    def character_repository(self) -> ICharacterRepository:
        """Character Repository (Singleton)"""
        if self._character_repository is None:
            logger.info("📦 Creating CharacterRepository...")
            self._character_repository = PostgresCharacterRepository(self.db_connection)
        return self._character_repository

    @property
    def memory_repository(self) -> IMemoryRepository:
        """Memory Repository (Singleton)"""
        if self._memory_repository is None:
            logger.info("📦 Creating MemoryRepository...")
            self._memory_repository = PostgresMemoryRepository(self.db_connection)
        return self._memory_repository

    # ============================================================
    # Managers
    # ============================================================

    @property
    def session_manager(self) -> ISessionManager:
        """Session Manager (Singleton)"""
        if self._session_manager is None:
            logger.info("🔧 Creating SessionManager...")
            # Legacy 지원: DatabaseManager + CacheManager로 HybridSessionManager 생성
            db_manager = DatabaseManager()
            cache_manager = CacheManager()
            hybrid_manager = HybridSessionManager(db_manager, cache_manager)
            self._session_manager = SessionManagerAdapter(hybrid_manager)
        return self._session_manager

    # ============================================================
    # Providers
    # ============================================================

    @property
    def llm_provider(self) -> ILLMProvider:
        """LLM Provider (Singleton)"""
        if self._llm_provider is None:
            logger.info("🤖 Creating LLM Provider...")
            self._llm_provider = LLMFactory.create_from_env()
        return self._llm_provider

    @property
    def cache_provider(self) -> ICacheProvider:
        """Cache Provider (Singleton)"""
        if self._cache_provider is None:
            logger.info("🗄️  Creating Cache Provider...")
            self._cache_provider = RedisCacheProvider(self.redis_connection)
        return self._cache_provider

    # ============================================================
    # Strategies
    # ============================================================

    @property
    def session_cache_strategy(self) -> SessionCacheStrategy:
        """Session Cache Strategy (Singleton)"""
        if self._session_cache_strategy is None:
            logger.info("📋 Creating SessionCacheStrategy...")
            self._session_cache_strategy = SessionCacheStrategy(self.cache_provider)
        return self._session_cache_strategy

    # ============================================================
    # Lifecycle Management
    # ============================================================

    def close_all(self):
        """모든 연결 종료"""
        logger.info("🔌 Closing all connections...")

        if self._db_connection:
            self._db_connection.close_all()

        if self._redis_connection:
            self._redis_connection.close()

        logger.info("✅ All connections closed")

    def health_check(self) -> dict:
        """
        모든 인프라 컴포넌트 헬스 체크

        Returns:
            각 컴포넌트의 상태
        """
        return {
            "database": self.db_connection.health_check() if self._db_connection else None,
            "redis": self.redis_connection.health_check() if self._redis_connection else None,
            "cache": self.cache_provider.health_check() if self._cache_provider else None,
        }


# ============================================================
# Singleton Instance
# ============================================================
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """
    DependencyContainer 싱글톤 인스턴스 반환

    Returns:
        DependencyContainer 인스턴스
    """
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


# ============================================================
# FastAPI Dependency Functions
# ============================================================

def get_user_repository() -> IUserRepository:
    """FastAPI Dependency: User Repository"""
    return get_container().user_repository


def get_session_repository() -> ISessionRepository:
    """FastAPI Dependency: Session Repository"""
    return get_container().session_repository


def get_llm_provider() -> ILLMProvider:
    """FastAPI Dependency: LLM Provider"""
    return get_container().llm_provider


def get_cache_provider() -> ICacheProvider:
    """FastAPI Dependency: Cache Provider"""
    return get_container().cache_provider


def get_character_repository() -> ICharacterRepository:
    """FastAPI Dependency: Character Repository"""
    return get_container().character_repository


def get_memory_repository() -> IMemoryRepository:
    """FastAPI Dependency: Memory Repository"""
    return get_container().memory_repository


def get_session_manager() -> ISessionManager:
    """FastAPI Dependency: Session Manager"""
    return get_container().session_manager
