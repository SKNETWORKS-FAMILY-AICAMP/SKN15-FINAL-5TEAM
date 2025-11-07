"""
KIME 챗 에이전트를 위한 FastAPI 서버
- 라우터 등록과 미들웨어 구성을 담당하는 경량 메인 파일
- 세부 API 로직은 별도 모듈로 분리해 유지보수를 용이하게 함
"""

# ============================================================
# ============================================================
# ------------------------------------------------------------
# ✅ 환경변수 로드 (. 파일에서 에이피아이 키 등 불러옴)
# 반드시 다른 보다 먼저 실행되어야 함!
# ------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv(override=True)
load_dotenv(dotenv_path=".env.local", override=True)  # 로컬 개발용

import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------------
# ------------------------------------------------------------
from src.middleware import setup_rate_limiting

# ------------------------------------------------------------
# ------------------------------------------------------------
from api.routes import system_routes
from api.routes import scenario_routes
from api.routes import session_routes
from api.routes import monitoring_routes
from api.routes import auth_routes
from api.routes import user_routes
from api.routes import chat_routes
# 에만 있던 새로운 라우터들
from api.routes import leaderboard_routes
from api.routes import memories_routes


# ============================================================
# ============================================================
app = FastAPI(
    title="KIME Chat API",
    description="Backend API for KIME Chat Agent using LangGraph",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
)

# ============================================================
# ============================================================
setup_rate_limiting(app)

# ============================================================
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",          # 포트 없이
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:8000",     # 백엔드 자체
        "http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ✅   
# ============================================================
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    API 응답 시간 측정 및 로깅

    모든 요청에 대해 처리 시간을 헤더에 추가하고,
    1초 이상 걸리는 느린 요청은 경고 로그 출력
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # 응답 헤더에 처리 시간 추가
    response.headers["X-Process-Time"] = f"{process_time:.3f}s"

    # 느린 요청 로깅 (1초 이상)
    if process_time > 1.0:
        print(f"⚠️  SLOW REQUEST: {request.method} {request.url.path} took {process_time:.3f}s")

    return response


# ============================================================
# ✅ 에이피아이 라우터 등록
# ============================================================

app.include_router(system_routes.router, tags=["System"])
app.include_router(leaderboard_routes.router, prefix="/api", tags=["Leaderboard"])
app.include_router(scenario_routes.router, prefix="/api/scenarios", tags=["Scenarios"])
app.include_router(session_routes.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(memories_routes.router, prefix="/api/users/me/memories", tags=["Memories"])
app.include_router(monitoring_routes.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Auth"])
app.include_router(user_routes.router, prefix="/api/users", tags=["Users"])
app.include_router(chat_routes.router, prefix="/api/chat", tags=["Chat"])


# ============================================================
# ✅ 서버 시작/종료 이벤트
# ============================================================
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    print("=" * 60)
    print("🚀 KIME Chat API Server Starting...")
    print("=" * 60)
    print("📚 API Documentation: http://localhost:8000/docs")
    print("📘 ReDoc: http://localhost:8000/redoc")
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    print("=" * 60)
    print("🛑 KIME Chat API Server Shutting Down...")
    print("=" * 60)

    # 의존성 정리
    from api.dependencies.api_deps import cleanup_dependencies
    cleanup_dependencies()


# ============================================================
# 🚀 메인 실행부
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.server:app",  # jw 폴더 구조에 맞게 수정
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "true").lower() == "true",
        log_level=os.getenv("API_LOG_LEVEL", "info"),
    )
