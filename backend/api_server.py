#!/usr/bin/env python3
"""
FastAPI Server for KIME Chat Agent (Refactored)
- 경량화된 메인 파일: 라우터 등록 및 미들웨어만 관리
- 모든 API 로직은 src/api/ 모듈로 분리
"""

# ------------------------------------------------------------
# ✅ 환경변수 로드 (.env 파일에서 API 키 등 불러옴)
# 반드시 다른 import보다 먼저 실행되어야 함!
# ------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv(override=True)
load_dotenv(dotenv_path=".env.local", override=True)  # 로컬 개발용

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------------
# ✅ Rate Limiting 모듈 로드
# ------------------------------------------------------------
from src.middleware import setup_rate_limiting

# ------------------------------------------------------------
# ✅ 라우터 import (리팩토링된 모듈들)
# ------------------------------------------------------------
from src.api import (
    system_router,
    leaderboard_router,
    scenarios_router,
    sessions_router,
    memories_router,
    monitoring_router,
    auth_router,
    users_router,
    chat_router,
)


# ============================================================
# ✅ FastAPI 앱 생성
# ============================================================
app = FastAPI(
    title="KIME Chat API",
    description="Backend API for KIME Chat Agent using LangGraph",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
)

# ============================================================
# ✅ Rate Limiting 설정
# ============================================================
setup_rate_limiting(app)

# ============================================================
# ✅ CORS 설정 (프론트엔드에서 API 호출 가능하게 허용)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",          # 포트 없이
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:8000",     # 백엔드 자체
        # AWS ALB 엔드포인트 (프로덕션)
        "http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ✅ Performance Monitoring Middleware
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
# ✅ API 라우터 등록
# ============================================================

# 시스템 엔드포인트 (/, /health, /ping)
app.include_router(system_router, tags=["System"])

# 리더보드
app.include_router(leaderboard_router, prefix="/api", tags=["Leaderboard"])

# 시나리오 관리
app.include_router(scenarios_router, prefix="/api/scenarios", tags=["Scenarios"])

# 세션 관리
app.include_router(sessions_router, prefix="/api/sessions", tags=["Sessions"])

# 장기 기억 (Memories)
app.include_router(memories_router, prefix="/api/users/me/memories", tags=["Memories"])

# 모니터링
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["Monitoring"])

# 인증 (회원가입, 로그인, 토큰 갱신)
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

# 사용자 관리 (크레딧, 진행도, 장비, 시나리오 진행도)
app.include_router(users_router, prefix="/api/users", tags=["Users"])

# 대화 시스템 (LangGraph 워크플로우)
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])


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
    from src.api.dependencies import cleanup_dependencies
    cleanup_dependencies()


# ============================================================
# 🚀 메인 실행부
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",  # 모듈:앱 객체
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 모드: 코드 변경 시 자동 재시작
        log_level="info"
    )
