"""
[Core] 애플리케이션 설정 관리 모듈

이 모듈은 Pydantic의 BaseSettings를 사용하여 애플리케이션의 모든 설정을 중앙에서 관리합니다.
환경 변수나 .env 파일을 통해 설정을 주입받으며, 타입 검증을 통해 안정성을 보장합니다.
설정 값들은 애플리케이션 전역에서 싱글톤으로 사용됩니다.

Attributes:
    get_settings: 설정 객체를 반환하는 싱글톤 함수
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """
    애플리케이션의 모든 설정을 담는 Pydantic 모델 클래스입니다.
    환경 변수 또는 .env 파일에서 값을 자동으로 로드하고 타입을 검증합니다.
    설정 항목은 그룹별로 구분되어 관리됩니다.
    """

    # --- 기본 애플리케이션 정보 ---
    APP_NAME: str = "KIME Chat API"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"  # 배포 환경 (development, staging, production)
    DEBUG: bool = True  # 디버그 모드 활성화 여부

    # --- 데이터베이스 연결 정보 (PostgreSQL) ---
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "kimedb"
    DB_USER: str = "kime"
    DB_PASSWORD: str = "dev123"
    DB_MIN_CONN: int = 2  # 사용되지 않는 설정 (SQLAlchemy 2.0에서는 pool_size로 통합)
    DB_MAX_CONN: int = 5  # 사용되지 않는 설정 (SQLAlchemy 2.0에서는 pool_size+max_overflow로 통합)

    # --- 데이터베이스 커넥션 풀 (Connection Pool) 설정 ---
    DB_POOL_SIZE: int = 10  # 유지할 최소한의 유휴 커넥션 수
    DB_MAX_OVERFLOW: int = 20  # 풀 크기를 초과하여 생성할 수 있는 최대 임시 커넥션 수
    DB_POOL_TIMEOUT: int = 30  # 커넥션을 얻기 위해 대기할 최대 시간 (초)
    DB_POOL_RECYCLE: int = 3600  # 커넥션을 재사용하기 전 최대 유지 시간 (초), -1이면 비활성화
    DB_POOL_PRE_PING: bool = True  # 커넥션을 사용하기 전, 유효한지 확인하는 PING 테스트 실행 여부

    @property
    def DATABASE_URL(self) -> str:
        """SQLAlchemy에서 사용할 비동기 PostgreSQL 연결 DSN(Data Source Name)을 생성합니다."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # --- Redis 연결 정보 ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None  # Redis 비밀번호 (없으면 None)
    REDIS_DB: int = 0  # 사용할 Redis 데이터베이스 번호
    REDIS_DEFAULT_TTL: int = 3600  # 캐시의 기본 만료 시간 (초)

    @property
    def REDIS_URL(self) -> str:
        """Redis 클라이언트에서 사용할 연결 URL을 생성합니다."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- JWT (JSON Web Token) 인증 정보 ---
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"  # 토큰 서명에 사용할 비밀 키. **프로덕션 환경에서는 반드시 변경해야 합니다.**
    JWT_ALGORITHM: str = "HS256"  # 서명 알고리즘
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Access Token 만료 시간 (분)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh Token 만료 시간 (일)

    # --- SMTP 이메일 발송 정보 ---
    SMTP_SERVER: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "KIME-CHAT"
    SMTP_USE_TLS: bool = True

    # --- OpenAI API 정보 ---
    OPENAI_PROVIDER: str = "openai"  # LLM 제공자 (향후 다른 모델 추가 대비)
    OPENAI_API_KEY: str  # OpenAI API 키. 환경 변수를 통해 반드시 설정해야 합니다.
    OPENAI_MODEL: str = "gpt-4o-mini"  # 기본으로 사용할 채팅 모델
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"  # 기본으로 사용할 임베딩 모델
    OPENAI_MAX_TOKENS: int = 2000  # API 호출 시 최대 생성 토큰 수
    OPENAI_TEMPERATURE: float = 0.7  # 모델의 창의성 조절 (0.0 ~ 1.0)

    # --- CORS (Cross-Origin Resource Sharing) 설정 ---
    FRONTEND_URL: str = "http://localhost:5173"  # 프론트엔드 개발 서버 주소
    BACKEND_HOST: str = "0.0.0.0"  # 백엔드 서버가 바인딩할 호스트
    BACKEND_PORT: int = 8000  # 백엔드 서버가 바인딩할 포트

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """CORS를 허용할 출처(Origin) 목록을 반환합니다."""
        # 개발 편의성을 위해 여러 로컬 주소를 포함.
        # 프로덕션 환경에서는 실제 서비스 도메인만 포함하도록 제한해야 합니다.
        return [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
            "http://localhost:8000",
            self.FRONTEND_URL,
        ]

    # --- 로깅 설정 ---
    LOG_LEVEL: str = "INFO"  # 애플리케이션의 전역 로그 레벨 (DEBUG, INFO, WARNING, ERROR)

    class Config:
        """Pydantic의 동작을 제어하는 내부 클래스"""
        env_file = ".env"  # 읽어올 .env 파일 이름
        env_file_encoding = "utf-8"  # 파일 인코딩
        case_sensitive = True  # 환경 변수 이름의 대소문자 구분


@lru_cache()
def get_settings() -> Settings:
    """
    애플리케이션 전역에서 사용될 설정(Settings) 객체를 반환합니다.

    `@lru_cache` 데코레이터를 사용하여 최초 호출 시에만 Settings 객체를 생성하고,
    이후에는 캐시된 객체를 반환하여 싱글톤(Singleton) 패턴을 구현합니다.
    이를 통해 불필요한 설정 파일 재탐색 및 객체 생성을 방지합니다.

    Returns:
        Settings: 애플리케이션 설정 정보를 담은 싱글톤 객체

    Usage:
        from app.core.config import get_settings
        settings = get_settings()
        print(settings.DATABASE_URL)
    """
    return Settings()
