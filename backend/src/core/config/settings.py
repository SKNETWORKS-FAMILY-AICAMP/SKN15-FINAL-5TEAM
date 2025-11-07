"""
Application Settings - Pydantic Settings로 환경변수 관리

모든 환경변수를 타입 안전하게 관리.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class DatabaseSettings(BaseSettings):
    """Database 설정"""
    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    name: str = Field(default="kimedb", description="Database name")
    user: str = Field(default="kime", description="Database user")
    password: str = Field(default="dev123", description="Database password")
    min_conn: int = Field(default=2, description="Minimum connections")
    max_conn: int = Field(default=5, description="Maximum connections")

    class Config:
        env_prefix = "DB_"
        extra = "ignore"  # Pydantic v2: 추가 필드 무시


class RedisSettings(BaseSettings):
    """Redis 설정"""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis DB number")
    default_ttl: int = Field(default=3600, description="Default TTL in seconds")

    class Config:
        env_prefix = "REDIS_"
        extra = "ignore"  # Pydantic v2: 추가 필드 무시


class LLMSettings(BaseSettings):
    """LLM 설정"""
    provider: str = Field(default="openai", description="LLM provider (openai/anthropic)")
    api_key: str = Field(..., description="LLM API key")
    model: str = Field(default="gpt-4o-mini", description="Model name")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")
    max_tokens: int = Field(default=2000, description="Max tokens per request")
    temperature: float = Field(default=0.7, description="Temperature (0.0~1.0)")

    class Config:
        env_prefix = "OPENAI_"
        extra = "ignore"  # Pydantic v2: 추가 필드 무시

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v


class JWTSettings(BaseSettings):
    """JWT 설정"""
    secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=60, description="Access token expiry (minutes)")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiry (days)")

    class Config:
        env_prefix = "JWT_"
        extra = "ignore"  # Pydantic v2: 추가 필드 무시


class AppSettings(BaseSettings):
    """Application 설정"""
    environment: str = Field(default="development", description="Environment (development/production)")
    debug: bool = Field(default=True, description="Debug mode")
    frontend_url: str = Field(default="http://localhost:5173", description="Frontend URL")
    backend_host: str = Field(default="0.0.0.0", description="Backend host")
    backend_port: int = Field(default=8000, description="Backend port")

    class Config:
        env_prefix = ""
        extra = "ignore"  # Pydantic v2: 추가 필드 무시

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


class Settings(BaseSettings):
    """
    통합 설정 클래스

    모든 하위 설정을 포함.
    """
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    app: AppSettings = Field(default_factory=AppSettings)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Pydantic v2: 추가 필드 무시


# ============================================================
# Singleton 인스턴스
# ============================================================
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Settings 싱글톤 인스턴스 반환

    Returns:
        Settings 인스턴스
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# 편의를 위한 직접 접근 (backward compatibility)
settings = get_settings()
