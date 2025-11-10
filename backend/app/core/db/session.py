"""
[Core/DB] 데이터베이스 세션 관리 모듈

이 모듈은 SQLAlchemy를 사용하여 데이터베이스 연결 및 세션 관리를 담당합니다.
비동기(asyncio) 환경에 맞춰 `AsyncEngine`과 `AsyncSession`을 생성하고,
FastAPI의 의존성 주입(Dependency Injection) 시스템을 통해 API 핸들러에
DB 세션을 안전하게 제공하는 역할을 합니다.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
from app.core.config import get_settings

# 전역 설정 객체 로드
settings = get_settings()

# ============================================================
# 비동기 SQLAlchemy 엔진 (Async Engine) 생성
# ============================================================
# create_async_engine: 데이터베이스와 상호작용하는 핵심 인터페이스입니다.
# 애플리케이션 전체에서 단 하나만 존재하며, 커넥션 풀을 관리합니다.
engine = create_async_engine(
    settings.DATABASE_URL,  # config.py에서 정의된 DB 연결 정보
    echo=settings.DEBUG,  # True일 경우, 실행되는 모든 SQL 쿼리를 콘솔에 출력 (개발용)

    # --- 커넥션 풀 설정 ---
    pool_size=settings.DB_POOL_SIZE,          # 풀에서 유지할 최소 연결 수
    max_overflow=settings.DB_MAX_OVERFLOW,    # 풀 크기를 초과하여 생성 가능한 임시 연결 수
    pool_timeout=settings.DB_POOL_TIMEOUT,    # 새 연결을 기다리는 최대 시간
    pool_recycle=settings.DB_POOL_RECYCLE,    # 설정된 시간(초)이 지나면 연결을 재활용
    pool_pre_ping=settings.DB_POOL_PRE_PING,  # 연결 사용 전, DB 연결이 유효한지 테스트

    # --- 추가 최적화 설정 ---
    pool_use_lifo=True,  # LIFO(Last-In, First-Out) 방식으로 풀에서 연결을 가져옴.
                         # 최근에 사용된 연결이 캐시에 남아있을 확률이 높아 성능에 유리할 수 있음.
)

# ============================================================
# 비동기 세션 팩토리 (Async Session Factory)
# ============================================================
# async_sessionmaker: 데이터베이스 트랜잭션을 처리하는 세션 객체를 생성하는 팩토리입니다.
# 이 팩토리를 통해 필요할 때마다 새로운 DB 세션을 일관된 설정으로 생성할 수 있습니다.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,                # 이 팩토리가 사용할 DB 엔진
    class_=AsyncSession,        # 생성할 세션의 클래스 (비동기용)
    expire_on_commit=False,     # commit 후에도 객체 속성에 접근할 수 있도록 설정
    autocommit=False,           # 자동 커밋 비활성화
    autoflush=False,            # 자동 flush 비활성화 (직접 db.flush() 호출 필요)
)


# ============================================================
# FastAPI 의존성 주입용 세션 생성기
# ============================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI의 `Depends`를 통해 API 핸들러에 DB 세션을 주입하는 의존성 함수입니다.

    요청이 시작될 때 세션을 생성하고, 요청 처리가 끝나면 세션을 자동으로 닫습니다.
    요청 처리 중 예외가 발생하면 트랜잭션을 롤백하고, 성공하면 커밋합니다.
    이 패턴은 API 핸들러에서 세션 관리에 대한 boilerplate 코드를 제거해줍니다.

    Yields:
        AsyncSession: 생성된 비동기 DB 세션 객체

    Usage:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # db 세션을 사용하여 비즈니스 로직 수행
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session  # API 핸들러에 세션 객체를 전달
            await session.commit()  # 핸들러가 성공적으로 실행되면 트랜잭션 커밋
        except Exception:
            await session.rollback()  # 핸들러에서 예외 발생 시 트랜잭션 롤백
            raise  # 예외를 다시 발생시켜 전역 에러 핸들러가 처리하도록 함
        finally:
            await session.close()  # 모든 작업 후 세션 닫기


# ============================================================
# 수동 세션 컨텍스트 관리자 (주로 테스트 또는 백그라운드 작업용)
# ============================================================
async def get_db_context():
    """
    FastAPI의 요청-응답 사이클 외부에서 DB 세션을 사용해야 할 때 쓰는 컨텍스트 관리자입니다.
    (예: 테스트 코드, 백그라운드 스크립트)

    `async with` 구문과 함께 사용하여 세션을 안전하게 관리할 수 있습니다.

    Usage:
        async def some_background_task():
            async with get_db_context() as db:
                # db 세션을 사용하여 작업 수행
                ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
