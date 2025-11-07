"""
Core Configuration
Pydantic Settings를 사용한 환경 설정 관리
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """
    애플리케이션 설정
    환경변수 또는 .env 파일에서 로드
    """

    # ============================================================
    # 기본 설정
    # ============================================================
    APP_NAME: str = "KIME Chat API"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True

    # ============================================================
    # 데이터베이스 설정
    # ============================================================
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "kimedb"
    DB_USER: str = "kime"
    DB_PASSWORD: str = "dev123"
    DB_MIN_CONN: int = 2
    DB_MAX_CONN: int = 5

    @property
    def DATABASE_URL(self) -> str:
        """PostgreSQL 연결 URL"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # ============================================================
    # Redis 설정
    # ============================================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_DEFAULT_TTL: int = 3600

    @property
    def REDIS_URL(self) -> str:
        """Redis 연결 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ============================================================
    # JWT 인증 설정
    # ============================================================
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ============================================================
    # OpenAI 설정
    # ============================================================
    OPENAI_PROVIDER: str = "openai"
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7

    # ============================================================
    # CORS 설정
    # ============================================================
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """허용할 CORS Origins"""
        return [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
            "http://localhost:8000",
            self.FRONTEND_URL,
        ]

    # ============================================================
    # 로깅 설정
    # ============================================================
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    설정 싱글톤

    Usage:
        from app.core.config import get_settings
        settings = get_settings()
        print(settings.DATABASE_URL)
    """
    return Settings()
