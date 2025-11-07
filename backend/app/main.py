"""
KIME Chat Backend - Main Application
4-Layer Architecture: Controller → UseCase → Parent/Agent → Repository
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

# Core
from app.core.config import get_settings
from app.core.logging import setup_logging, print_layer_debug
from app.core.errors import register_exception_handlers

# Features
from app.features.chat.controller import router as chat_router
from app.features.auth.controller import router as auth_router

settings = get_settings()

# ============================================================
# 로깅 초기화
# ============================================================
setup_logging(settings.LOG_LEVEL)

# ============================================================
# FastAPI 앱 생성
# ============================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================
# 예외 핸들러 등록
# ============================================================
register_exception_handlers(app)

# ============================================================
# CORS 설정
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 성능 모니터링 미들웨어
# ============================================================
@app.middleware("http")
async def add_process_time_header(request, call_next):
    """API 응답 시간 측정"""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000

    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

    # 느린 요청 경고
    if process_time > 1000:
        print(f"⚠️  SLOW REQUEST: {request.method} {request.url.path} took {process_time:.2f}ms")

    return response

# ============================================================
# 라우터 등록
# ============================================================
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

# ============================================================
# 헬스 체크
# ============================================================
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }

# ============================================================
# 임시 더미 API (Frontend 동작용)
# ============================================================
@app.get("/api/scenarios")
async def get_scenarios():
    """시나리오 목록 조회 (실제 데이터)"""
    return [
        {
            "scenario_id": "cutscene5_llm_driven",
            "title": "🔥 무한열차",
            "description": "갈림길→전략 개입→동료 규합→보스 퇴장 시네마틱→판정→히든/기본 엔딩",
            "image_url": "/images/scenarios/mugen_train.jpg",
            "thumbnail_url": "/images/scenarios/mugen_train_thumb.jpg",
            "tags": ["전투", "스토리", "다이쇼 시대"],
            "card_size": "large",
            "route_path": "/character/cutscene5_llm_driven",
            "display_order": 1,
            "is_active": True,
            "likes": 256,
            "comments": 89,
            "views": 3420,
            "total_completions": 147,
            "is_liked": False,
            "has_started": False,
            "has_completed": False
        }
    ]

@app.get("/api/session/last")
async def get_last_session(scenario_id: str = None):
    """마지막 세션 조회 (더미)"""
    return {"has_session": False}

@app.get("/api/users/me/scenarios")
async def get_user_scenarios():
    """사용자 시나리오 목록 (더미)"""
    # 로그인한 사용자도 전체 시나리오 목록 반환
    return await get_scenarios()

@app.get("/api/auth/me")
async def get_current_user():
    """현재 사용자 정보 (더미)"""
    return {
        "user_id": "1",
        "username": "admin",
        "email": "admin@kimechat.com",
        "display_name": "관리자"
    }

@app.get("/api/users/me/credits")
async def get_user_credits():
    """사용자 크레딧 조회 (더미)"""
    return {
        "credits": 1000,
        "total_credits": 1000,
        "used_credits": 0,
        "bubble_count": 1000  # 프론트엔드가 기대하는 필드
    }

# ============================================================
# 시작/종료 이벤트
# ============================================================
@app.on_event("startup")
async def startup_event():
    """서버 시작 이벤트"""
    print("=" * 60)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 60)
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"🌍 Environment: {settings.ENVIRONMENT}")
    print(f"🗄️  Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print("=" * 60)
    print_layer_debug("MAIN", "App", "startup", "✅ Server started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 이벤트"""
    print("=" * 60)
    print(f"🛑 {settings.APP_NAME} Shutting Down...")
    print("=" * 60)
    print_layer_debug("MAIN", "App", "shutdown", "Server stopped")

# ============================================================
# 개발 서버 실행 (직접 실행 시)
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 모드
        log_level="info"
    )
