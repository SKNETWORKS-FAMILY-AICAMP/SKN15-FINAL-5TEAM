#!/usr/bin/env python3
"""
FastAPI Server for KIME Chat Agent
- LangGraph 기반 멀티에이전트 워크플로우를 REST API 형태로 래핑
- 프론트엔드(React 등)에서 /api/chat 으로 요청을 보내면 여기서 처리함
"""

# ------------------------------------------------------------
# ✅ 환경변수 로드 (.env 파일에서 API 키 등 불러옴)
# 반드시 다른 import보다 먼저 실행되어야 함!
# ------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv(override=True)

import os
import uuid
import json
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Dict
from fastapi import Depends
import asyncio

# ------------------------------------------------------------
# ✅ LangGraph 관련 내부 모듈 로드
# ------------------------------------------------------------
from src.core.workflow import create_workflow  # 그래프 구성 생성기
from src.core.graph_state import (
    create_initial_graph_state,
    GraphState,
)  # 초기 상태 생성
from src.utils.scenario_loader import scenario_loader  # 시나리오(JSON) 로더
from src.tools.image_manager import ImageManager  # 이미지 매니저
from src.core.scenes_repo import ScenesRepo

# ------------------------------------------------------------
# ✅ Database 모듈 로드 (PostgreSQL + Redis)
# ------------------------------------------------------------
from src.database.session_manager import HybridSessionManager
from src.database.db_manager import DatabaseManager
from src.database.cache_manager import create_cache_manager_from_env

# ------------------------------------------------------------
# ✅ Conversation Summarizer 로드 (대화 요약 자동화)
# ------------------------------------------------------------
from src.utils.conversation_summarizer import update_conversation_summary, generate_embedding

# ------------------------------------------------------------
# ✅ Authentication 모듈 로드
# ------------------------------------------------------------
from src.auth.dependencies import require_auth, optional_auth

# ------------------------------------------------------------
# ✅ Rate Limiting 모듈 로드
# ------------------------------------------------------------
from src.middleware import setup_rate_limiting, limiter, AUTH_RATE_LIMIT

# ------------------------------------------------------------
# ✅ API Routers 로드
# ------------------------------------------------------------
from src.api.monitoring_api import router as monitoring_router
from src.api import auth_router, scenario_router, user_router, chat_router, session_router, gallery_router

# ------------------------------------------------------------
# ✅ FastAPI 인스턴스 생성
# ------------------------------------------------------------
app = FastAPI(
    title="KIME Chat API",
    description="Backend API for KIME Chat Agent using LangGraph",
    version="1.0.0",
)

# Rate Limiting 설정
setup_rate_limiting(app)

# ------------------------------------------------------------
# ✅ CORS 설정 (프론트엔드에서 API 호출 가능하게 허용)
# ------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        # AWS ALB 엔드포인트 추가 (프로덕션)
        "http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com",
    ],  # 허용할 프론트엔드 도메인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# ✅ Performance Monitoring Middleware
# ------------------------------------------------------------
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """API 응답 시간 측정 및 로깅"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # 응답 헤더에 처리 시간 추가
    response.headers["X-Process-Time"] = f"{process_time:.3f}s"

    # 느린 요청 로깅 (1초 이상)
    if process_time > 1.0:
        print(f"⚠️  SLOW REQUEST: {request.method} {request.url.path} took {process_time:.3f}s")

    return response

# ------------------------------------------------------------
# ✅ API 라우터 등록
# ------------------------------------------------------------
app.include_router(monitoring_router)

# TODO: 라우터들에 DB Manager 주입 (db_manager 초기화 후 진행)
# 이 부분은 db_manager 초기화 후에 실행됩니다 (아래 참조)


# ------------------------------------------------------------
# ✅ 세션 저장소 (PostgreSQL + Redis 하이브리드)
#    - GraphState 전체를 Redis(캐시) + PostgreSQL(영구)에 저장
#    - 자동으로 대화, 친밀도 등을 정규화된 테이블에도 저장
# ------------------------------------------------------------
class SessionManagerAdapter:
    """
    HybridSessionManager를 래핑하여 api_server.py가 기대하는 인터페이스 제공
    - 전체 GraphState를 캐시(Redis) + 스냅샷(PostgreSQL)에 저장
    """
    def __init__(self, hybrid_manager):
        self._hybrid = hybrid_manager
        self._cache_key_prefix = "graphstate"

    def _make_cache_key(self, session_id: str) -> str:
        return f"{self._cache_key_prefix}:{session_id}"

    def load_or_create(self, session_id: str) -> Dict[str, Any]:
        """
        GraphState 로드 또는 빈 dict 생성
        """
        # 1. Redis 캐시에서 조회
        cache_key = self._make_cache_key(session_id)
        cached_state = self._hybrid.cache.get_session(cache_key)
        if cached_state:
            return cached_state

        # 2. PostgreSQL 스냅샷에서 조회
        snapshot = self._hybrid.load_latest_snapshot(session_id)
        if snapshot and snapshot.get("state_json"):
            state = snapshot["state_json"]
            # 캐시에 저장
            self._hybrid.cache.set_session(cache_key, state)
            return state

        # 3. 없으면 빈 dict 반환
        return {}

    def save(self, session_id: str, state: Dict[str, Any]) -> None:
        """
        GraphState 저장 (캐시 + 스냅샷 + 정규화 데이터)
        """
        turn_count = state.get("turn_count", 0)
        scenario_id = state.get("scenario_id", "unknown")
        user_id = state.get("user_id")  # 인증된 사용자 ID (없으면 None)
        user_name = state.get("user_name")
        current_stage = state.get("current_stage")
        final_ending = state.get("final_ending")
        is_active = state.get("is_active", True)

        # 1. 세션 메타데이터 먼저 저장 (foreign key를 위해)
        session_meta = {
            "session_id": session_id,
            "scenario_id": scenario_id,
            "user_id": user_id,  # ✅ 추가: 사용자 ID
            "user_name": user_name,
            "current_stage": current_stage,
            "turn_count": turn_count,
            "stage_turn": state.get("stage_turn", 0),
            "final_ending": final_ending,
            "is_active": is_active,
            "conversation_summary": state.get("conversation_summary", ""),  # 🧠 장기기억
            "summary_turn_count": state.get("summary_turn_count", 0)  # 🧠 장기기억
        }
        self._hybrid.db.save_session(session_meta)

        # 2. PostgreSQL 스냅샷에 저장 (복구용) - session이 먼저 생성되어야 함
        self._hybrid.save_snapshot(session_id, turn_count, state)

        # 3. 캐시에 저장 (빠른 접근)
        cache_key = self._make_cache_key(session_id)
        self._hybrid.cache.set_session(cache_key, state)

        # 4. 대화 및 사용자 입력 저장 (정규화 데이터)
        # 4-1. 사용자 입력 저장
        user_input = state.get("user_input")
        if user_input and not user_input.startswith("__AUTO_CONTINUE__"):
            try:
                self._hybrid.db.save_user_input(session_id, turn_count, user_input)
                print(f"💬 User input saved: turn={turn_count}")
            except Exception as e:
                print(f"⚠️ Failed to save user input: {e}")

        # 4-2. 대화 저장
        # state에서 messages 또는 output의 dialogues 추출
        dialogues_to_save = []

        # messages 필드에서 대화 추출 (일반적인 경우)
        messages = state.get("messages", [])
        if messages and isinstance(messages, list):
            # 마지막 메시지가 현재 턴의 대화
            last_message = messages[-1] if messages else None
            if last_message and isinstance(last_message, dict):
                dialogues_data = last_message.get("dialogues", [])
                if dialogues_data:
                    dialogues_to_save = dialogues_data

        # output 필드에서 대화 추출 (fallback)
        if not dialogues_to_save:
            output = state.get("output", {})
            if isinstance(output, dict) and "dialogues" in output:
                dialogues_to_save = output.get("dialogues", [])

        # 대화가 있으면 저장
        if dialogues_to_save:
            try:
                # Dialogue 객체를 dict로 변환
                dialogues_dict = []
                for dialogue in dialogues_to_save:
                    if hasattr(dialogue, '__dict__'):
                        # Pydantic 모델이나 클래스 객체
                        d = dialogue.__dict__
                    elif isinstance(dialogue, dict):
                        d = dialogue
                    else:
                        continue

                    dialogues_dict.append({
                        "speaker": d.get("speaker", "unknown"),
                        "content": d.get("content") or d.get("text", ""),
                        "emotion": d.get("emotion"),
                        "emotion_intensity": d.get("emotion_intensity")
                    })

                if dialogues_dict:
                    self._hybrid.db.save_dialogues(session_id, turn_count, dialogues_dict)
                    print(f"💬 Dialogues saved: {len(dialogues_dict)} dialogues, turn={turn_count}")
            except Exception as e:
                print(f"⚠️ Failed to save dialogues: {e}")
                import traceback
                traceback.print_exc()

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        GraphState 조회 (없으면 None 반환)
        """
        cache_key = self._make_cache_key(session_id)
        cached_state = self._hybrid.cache.get_session(cache_key)
        if cached_state:
            return cached_state

        snapshot = self._hybrid.load_latest_snapshot(session_id)
        if snapshot and snapshot.get("state_json"):
            state = snapshot["state_json"]
            self._hybrid.cache.set_session(cache_key, state)
            return state

        return None

    def delete(self, session_id: str) -> None:
        """
        세션 삭제 (캐시에서만 제거, DB는 is_active=false)
        """
        cache_key = self._make_cache_key(session_id)
        self._hybrid.cache.delete_session(cache_key)
        self._hybrid.db.update_session(session_id, {"is_active": False})

    def exists(self, session_id: str) -> bool:
        """
        세션 존재 여부 확인
        """
        cache_key = self._make_cache_key(session_id)
        if self._hybrid.cache.exists(cache_key):
            return True

        snapshot = self._hybrid.load_latest_snapshot(session_id)
        return snapshot is not None

    def save_log(self, log_level: str, log_message: str, session_id: str = None, metadata: Dict[str, Any] = None) -> None:
        """
        일반 로그 저장 (logdb.logs 테이블)
        """
        # HybridSessionManager 시그니처에 맞게 파라미터 매핑
        success = self._hybrid.save_log(
            log_level=log_level,
            message=log_message,  # log_message -> message
            session_id=session_id,
            stage_name=None,
            agent_name=None,
            context_data=metadata,  # metadata -> context_data
            duration_ms=None
        )
        if not success:
            raise Exception(f"Failed to save log to database")

    def save_error_log(self, error_type: str, error_message: str, session_id: str = None, metadata: Dict[str, Any] = None) -> None:
        """
        에러 로그 저장 (logdb.error_logs 테이블)
        """
        # HybridSessionManager 시그니처에 맞게 파라미터 매핑
        success = self._hybrid.save_error_log(
            error_type=error_type,
            error_message=error_message,
            stack_trace=None,
            session_id=session_id,
            context_data=metadata  # metadata -> context_data
        )
        if not success:
            raise Exception(f"Failed to save error log to database")

    def save_performance_metric(self, metric_name: str, metric_value: float, session_id: str = None, metadata: Dict[str, Any] = None) -> None:
        """
        성능 메트릭 저장 (logdb.performance_metrics 테이블)
        """
        # HybridSessionManager 시그니처에 맞게 파라미터 매핑
        success = self._hybrid.save_performance_metric(
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit="ms",
            tags=metadata  # metadata -> tags
        )
        if not success:
            raise Exception(f"Failed to save performance metric to database")


# HybridSessionManager 초기화
_hybrid_manager = None  # Global variable initialization
db_manager = None  # Global DatabaseManager
cache_manager = None  # Global CacheManager

try:
    # DatabaseManager를 환경 변수에서 생성
    db_manager = DatabaseManager(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        dbname=os.getenv('DB_NAME', 'kimedb'),
        user=os.getenv('DB_USER', 'kime'),
        password=os.getenv('DB_PASSWORD', 'dev123'),
        min_conn=2,
        max_conn=10
    )
    print(f"✅ DatabaseManager 생성: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")

    # CacheManager 생성 (Redis 실패 시에도 db_manager는 유지됨)
    try:
        cache_manager = create_cache_manager_from_env()
        # HybridSessionManager 생성
        _hybrid_manager = HybridSessionManager(db_manager, cache_manager)
        SESSION_MANAGER = SessionManagerAdapter(_hybrid_manager)
        print("✅ Database-backed SessionManager initialized")
    except Exception as cache_error:
        print(f"⚠️ Failed to initialize cache manager: {cache_error}")
        print("⚠️ Database connected but Redis failed - using in-memory sessions")
        raise  # Re-raise to hit outer except block
except Exception as e:
    print(f"⚠️ Failed to initialize session manager: {e}")
    print("⚠️ Falling back to in-memory session storage")

    # Fallback: 메모리 기반 SessionManager
    class InMemorySessionManager:
        def __init__(self):
            self._sessions: Dict[str, Dict[str, Any]] = {}

        def load_or_create(self, session_id: str) -> Dict[str, Any]:
            return self._sessions.setdefault(session_id, {})

        def save(self, session_id: str, state: Dict[str, Any]) -> None:
            self._sessions[session_id] = state

        def get(self, session_id: str) -> Optional[Dict[str, Any]]:
            return self._sessions.get(session_id)

        def delete(self, session_id: str) -> None:
            self._sessions.pop(session_id, None)

        def exists(self, session_id: str) -> bool:
            return session_id in self._sessions

    SESSION_MANAGER = InMemorySessionManager()

    # Fallback용 mock managers 생성
    class MockCacheManager:
        """In-memory fallback에서 사용할 mock cache manager"""
        def get_scenarios_cached(self):
            return None
        def set_scenarios_cached(self, data, ttl=None):
            pass

    class MockDbManager:
        """In-memory fallback에서 사용할 mock db manager"""
        def get_all_scenarios(self, include_inactive=False):
            return []
        def get_user_by_username(self, username):
            return None
        def create_user(self, *args, **kwargs):
            raise Exception("Database not available in fallback mode")

    if db_manager is None:
        db_manager = MockDbManager()
    if cache_manager is None:
        cache_manager = MockCacheManager()

# ------------------------------------------------------------
# ✅ API 라우터 의존성 주입 및 등록
# ------------------------------------------------------------
print("🔧 Injecting dependencies into API routers...")

# Auth Router에 DB Manager 주입
auth_router.set_db_manager(db_manager)
app.include_router(auth_router.router)
print("  ✅ Auth router registered")

# Scenario Router에 Managers 주입
scenario_router.set_managers(db_manager, cache_manager)
app.include_router(scenario_router.router)
print("  ✅ Scenario router registered")

# User Router에 DB Manager 주입
user_router.set_db_manager(db_manager)
app.include_router(user_router.router)
print("  ✅ User router registered")

# Chat Router에 Managers 및 load_scenario 주입 (라우터 등록 뒤에서 수행)
# Session Router에 Managers 주입 (라우터 등록 뒤에서 수행)

print("✅ All API routers registered successfully")

# ------------------------------------------------------------
# ✅ Workflow 싱글톤 (LangGraph 파이프라인)
# ------------------------------------------------------------
workflow = None


# ------------------------------------------------------------
# ✅ LangGraph 워크플로우 가져오기 (싱글톤)
# ------------------------------------------------------------
def get_workflow():
    global workflow
    if workflow is None:
        workflow = create_workflow()
    return workflow


# ------------------------------------------------------------
# ✅ 시나리오 로더 (파일 or 캐시)
# ------------------------------------------------------------
def load_scenario(scenario_id: str) -> Optional[Dict]:
    """Frontend ID로 요청받은 시나리오를 JSON으로 로드"""
    import time  # 🚀 Performance measurement
    start_time = time.perf_counter()

    try:
        if not scenario_id:
            return None

        # 🔄 Scenario ID mapping (frontend → backend)
        SCENARIO_ID_MAP = {
            'train': 'mugen_train_full',
            'ending': 'cutscene5_llm_driven',
        }

        # Apply mapping if exists
        mapped_id = SCENARIO_ID_MAP.get(scenario_id, scenario_id)
        if mapped_id != scenario_id:
            print(f"🔄 Mapping scenario: '{scenario_id}' → '{mapped_id}'")
            scenario_id = mapped_id

        candidates = []
        if scenario_id.endswith(".json"):
            candidates.append(scenario_id)
        else:
            candidates.extend([scenario_id, f"{scenario_id}.json"])

        # 🚀 Try scenario_loader first (with timing)
        loader_start = time.perf_counter()
        for candidate in candidates:
            data = scenario_loader.load_scenario(candidate)
            if data:
                loader_time = (time.perf_counter() - loader_start) * 1000
                total_time = (time.perf_counter() - start_time) * 1000
                print(f"⏱️  [scenario_loader] Loaded '{scenario_id}' in {loader_time:.2f}ms (total: {total_time:.2f}ms)")
                return data
        loader_time = (time.perf_counter() - loader_start) * 1000
        print(f"⏱️  [scenario_loader] Not found '{scenario_id}' after {loader_time:.2f}ms")

        # 🚀 Try ScenesRepo as fallback (with timing)
        repo_start = time.perf_counter()
        repo = ScenesRepo()
        for candidate in candidates:
            result = repo.load(candidate.replace(".json", ""))
            if result:
                repo_time = (time.perf_counter() - repo_start) * 1000
                total_time = (time.perf_counter() - start_time) * 1000
                print(f"⏱️  [ScenesRepo] Loaded '{scenario_id}' in {repo_time:.2f}ms (total: {total_time:.2f}ms)")
                return result
        repo_time = (time.perf_counter() - repo_start) * 1000

        total_time = (time.perf_counter() - start_time) * 1000
        print(f"⚠️  Scenario '{scenario_id}' not found (total search: {total_time:.2f}ms)")
        return None
    except Exception as e:
        total_time = (time.perf_counter() - start_time) * 1000
        print(f"❌ Error loading scenario '{scenario_id}' after {total_time:.2f}ms: {e}")
        return None


# ------------------------------------------------------------
# ✅ Chat & Session Router 등록 (의존성 주입)
# ------------------------------------------------------------
chat_router.set_dependencies(SESSION_MANAGER, db_manager, load_scenario)
app.include_router(chat_router.router)
print("  ✅ Chat router registered")

session_router.set_dependencies(SESSION_MANAGER, db_manager)
app.include_router(session_router.router)
print("  ✅ Session router registered")

gallery_router.set_db_manager(db_manager)
app.include_router(gallery_router.router)
print("  ✅ Gallery router registered")

# ============================================================
# 🧩 Request / Response 데이터 모델 정의
# ============================================================


class ChatRequest(BaseModel):
    """프론트엔드 → 백엔드 요청 구조"""

    session_id: Optional[str] = None
    scenario_id: str  # 예: "train", "ending", ...
    user_input: str  # 사용자의 입력 문장
    user_name: Optional[str] = "츠구코"  # 유저 이름 (없으면 기본값)


class DialogueResponse(BaseModel):
    """단일 대화 응답"""

    speaker: str
    content: str
    emotion: Optional[str] = "neutral"


class ChatResponse(BaseModel):
    """백엔드 → 프론트엔드 응답 구조"""

    session_id: str
    turn_count: int
    dialogues: List[DialogueResponse]
    current_stage: Optional[str] = None
    affinity_scores: Optional[Dict[str, int]] = None
    is_ended: bool = False  # 시나리오 종료 여부
    has_more: bool = False  # 더 생성할 대화가 남아있는지 여부
    system_message: Optional[str] = None  # 시스템 메시지 (fallback, 경고 등)
    current_image: Optional[str] = None  # 현재 표시할 이미지 파일명


class SessionInfoResponse(BaseModel):
    """세션 상태 조회 응답"""

    session_id: str
    scenario_id: str
    current_stage: Optional[str]
    turn_count: int
    affinity_scores: Dict[str, int]


# ============================================================
# 🔐 인증 관련 데이터 모델
# ============================================================


class LoginRequest(BaseModel):
    """로그인 요청"""

    username: str
    password: str


class RegisterRequest(BaseModel):
    """회원가입 요청"""

    username: str
    password: str
    email: Optional[str] = None
    display_name: Optional[str] = None


class AuthResponse(BaseModel):
    """인증 응답"""

    success: bool
    message: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """토큰 갱신 요청"""

    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """토큰 갱신 응답"""

    access_token: str
    token_type: str = "bearer"


# ============================================================
# 🧠 API 엔드포인트 구현부
# ============================================================


@app.get("/")
async def root():
    """서버 상태 확인용"""
    return {"status": "running", "service": "KIME Chat API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """ALB 헬스 체크용"""
    return {"status": "healthy"}


# ============================================================
# 🔐 인증 API 엔드포인트
# ============================================================


@app.post("/api/auth/register", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(req: RegisterRequest, request: Request):
    """
    회원가입 엔드포인트

    Args:
        req: RegisterRequest (username, password, email, display_name)

    Returns:
        AuthResponse (success, message, user_id, username, display_name)
    """
    import bcrypt

    try:
        # 사용자명 중복 체크
        existing_user = db_manager.get_user_by_username(req.username)
        if existing_user:
            return AuthResponse(
                success=False,
                message="이미 존재하는 사용자명입니다."
            )

        # 이메일 중복 체크 (이메일이 제공된 경우)
        if req.email:
            existing_email = db_manager.get_user_by_email(req.email)
            if existing_email:
                return AuthResponse(
                    success=False,
                    message="이미 존재하는 이메일입니다."
                )

        # 비밀번호 해시 생성
        password_hash = bcrypt.hashpw(
            req.password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # 사용자 생성
        user_id = db_manager.create_user(
            username=req.username,
            password_hash=password_hash,
            email=req.email,
            display_name=req.display_name or req.username
        )

        if user_id:
            # 진행도 초기화 (ranks, stats, equipment)
            try:
                db_manager.initialize_user_progression(user_id)
            except Exception as e:
                print(f"⚠️  Warning: Failed to initialize progression for user {user_id}: {e}")
                # 진행도 초기화 실패해도 계정은 생성됨 (나중에 수동 초기화 가능)
            # JWT 토큰 생성
            from src.auth.jwt_utils import create_access_token, create_refresh_token

            token_data = {
                "user_id": user_id,
                "username": req.username,
                "display_name": req.display_name or req.username
            }
            access_token = create_access_token(data=token_data)
            refresh_token = create_refresh_token(data={"user_id": user_id})

            return AuthResponse(
                success=True,
                message="회원가입이 완료되었습니다.",
                user_id=user_id,
                username=req.username,
                display_name=req.display_name or req.username,
                access_token=access_token,
                refresh_token=refresh_token
            )
        else:
            return AuthResponse(
                success=False,
                message="회원가입 중 오류가 발생했습니다."
            )

    except Exception as e:
        print(f"❌ Error in register endpoint: {e}")
        import traceback
        traceback.print_exc()
        return AuthResponse(
            success=False,
            message=f"서버 오류: {str(e)}"
        )


@app.post("/api/auth/login", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(req: LoginRequest, request: Request):
    """
    로그인 엔드포인트

    Args:
        req: LoginRequest (username, password)

    Returns:
        AuthResponse (success, message, user_id, username, display_name)
    """
    try:
        # 사용자 인증
        user = db_manager.verify_user_password(
            username=req.username,
            password=req.password
        )

        if user:
            # JWT 토큰 생성
            from src.auth.jwt_utils import create_access_token, create_refresh_token

            user_id = str(user["user_id"])
            token_data = {
                "user_id": user_id,
                "username": user["username"],
                "display_name": user.get("display_name") or user["username"]
            }
            access_token = create_access_token(data=token_data)
            refresh_token = create_refresh_token(data={"user_id": user_id})

            return AuthResponse(
                success=True,
                message="로그인 성공",
                user_id=user_id,
                username=user["username"],
                display_name=user.get("display_name") or user["username"],
                access_token=access_token,
                refresh_token=refresh_token
            )
        else:
            return AuthResponse(
                success=False,
                message="사용자명 또는 비밀번호가 올바르지 않습니다."
            )

    except Exception as e:
        print(f"❌ Error in login endpoint: {e}")
        import traceback
        traceback.print_exc()
        return AuthResponse(
            success=False,
            message=f"서버 오류: {str(e)}"
        )


@app.post("/api/auth/refresh", response_model=TokenRefreshResponse)
async def refresh_token(request: TokenRefreshRequest):
    """
    토큰 갱신 엔드포인트

    Args:
        request: TokenRefreshRequest (refresh_token)

    Returns:
        TokenRefreshResponse (new access_token)
    """
    from src.auth.jwt_utils import refresh_access_token

    try:
        new_access_token = refresh_access_token(request.refresh_token)
        return TokenRefreshResponse(access_token=new_access_token)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Error in refresh endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 갱신에 실패했습니다",
        )


@app.get("/api/auth/me")
async def get_me(user: Dict = Depends(require_auth)):
    """
    현재 사용자 정보 조회 (보호된 라우트 예제)

    Args:
        user: 인증된 사용자 정보 (JWT 토큰에서 추출)

    Returns:
        사용자 정보
    """
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user.get("display_name")
    }


@app.get("/api/users/me/credits")
async def get_user_credits(user: Dict = Depends(require_auth)):
    """사용자 크레딧(버블) 조회"""
    credits = db_manager.get_user_credits(user["user_id"])
    if not credits:
        raise HTTPException(status_code=404, detail="크레딧 정보를 찾을 수 없습니다")
    return credits


class ConsumeCreditsRequest(BaseModel):
    amount: int
    description: str


@app.post("/api/users/me/credits/consume")
async def consume_user_credits(req: ConsumeCreditsRequest, user: Dict = Depends(require_auth)):
    """사용자 크레딧(버블) 소비"""
    success = db_manager.consume_credits(user["user_id"], req.amount, req.description)
    if not success:
        raise HTTPException(status_code=400, detail="크레딧 잔액이 부족합니다")
    return {"success": True, "message": f"{req.amount} 버블이 차감되었습니다"}


# ============================================================
# 사용자 Progression 엔드포인트 (레벨, 경험치, 장비)
# ============================================================

@app.get("/api/users/me/progression")
async def get_user_progression(user: Dict = Depends(require_auth)):
    """현재 사용자의 진행도 조회 (rank, level, XP, stats, equipment)

    Returns:
        {
            "user_id": str,
            "rank_code": str,
            "rank_name_ko": str,
            "rank_icon": str,
            "experience_points": int,
            "level": int,
            "next_rank_xp": int,
            "total_messages": int,
            "total_sessions": int,
            "total_play_minutes": int,
            "scenarios_completed": int,
            "achievements_count": int,
            "sword_status": str,
            "uniform_status": str,
            "crow_status": str
        }
    """
    progression = db_manager.get_user_progression(user["user_id"])
    if not progression:
        raise HTTPException(status_code=404, detail="Progression data not found")
    return progression


@app.get("/api/users/me/equipment")
async def get_user_equipment(user: Dict = Depends(require_auth)):
    """현재 사용자의 장비 상태 조회

    Returns:
        {
            "sword_status": str,
            "uniform_status": str,
            "crow_status": str,
            "sword_type": str,
            "uniform_color": str,
            "crow_name": str
        }
    """
    equipment = db_manager.get_user_equipment(user["user_id"])
    if not equipment:
        # 기본값 반환
        return {
            "sword_status": "good",
            "uniform_status": "worn",
            "crow_status": "waiting",
            "sword_type": None,
            "uniform_color": None,
            "crow_name": None
        }
    return equipment


class AwardXPRequest(BaseModel):
    xp_amount: int
    xp_type: str  # 'message', 'session_complete', 'scenario_complete', 'achievement', 'daily_bonus', 'event'
    description: str = None
    metadata: Dict = None


@app.post("/api/users/me/progression/award-xp")
async def award_user_experience(req: AwardXPRequest, user: Dict = Depends(require_auth)):
    """사용자에게 경험치 지급 (내부 API - 메시지 전송 시 자동 호출)

    Request Body:
        {
            "xp_amount": 10,
            "xp_type": "message",
            "description": "메시지 전송",
            "metadata": {"message_id": "..."}
        }

    Returns:
        {
            "user_id": str,
            "experience_points": int,
            "level": int,
            "level_before": int,
            "level_after": int,
            "did_level_up": bool
        }
    """
    valid_xp_types = ['message', 'session_complete', 'scenario_complete', 'achievement', 'daily_bonus', 'event']
    if req.xp_type not in valid_xp_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid xp_type. Must be one of {valid_xp_types}"
        )

    result = db_manager.award_experience(
        user["user_id"],
        req.xp_amount,
        req.xp_type,
        req.description,
        req.metadata
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to award XP")

    return result


class UpdateEquipmentRequest(BaseModel):
    equipment_updates: Dict[str, str]


@app.put("/api/users/me/equipment")
async def update_user_equipment(req: UpdateEquipmentRequest, user: Dict = Depends(require_auth)):
    """사용자 장비 상태 업데이트

    Request Body:
        {
            "equipment_updates": {
                "sword_status": "excellent",
                "uniform_status": "equipped"
            }
        }

    Returns:
        {"success": true}
    """
    success = db_manager.update_user_equipment(user["user_id"], req.equipment_updates)
    if not success:
        raise HTTPException(status_code=400, detail="No valid equipment fields to update")
    return {"success": True}


@app.get("/api/users/me/xp-transactions")
async def get_user_xp_transactions(
    user: Dict = Depends(require_auth),
    limit: int = 50,
    offset: int = 0
):
    """사용자 경험치 거래 내역 조회 (페이지네이션)

    Query Parameters:
        limit: 조회 개수 (기본 50, 최대 100)
        offset: 오프셋 (페이지네이션)

    Returns:
        [
            {
                "transaction_id": str,
                "xp_amount": int,
                "xp_type": str,
                "xp_balance_after": int,
                "level_before": int,
                "level_after": int,
                "did_level_up": bool,
                "description": str,
                "created_at": str
            },
            ...
        ]
    """
    if limit > 100:
        limit = 100

    transactions = db_manager.get_xp_transactions(user["user_id"], limit, offset)
    return transactions


@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 100):
    """경험치 기준 리더보드 조회 (공개 API)

    Query Parameters:
        limit: 조회 개수 (기본 100, 최대 500)

    Returns:
        [
            {
                "rank": int,
                "user_id": str,
                "username": str,
                "display_name": str,
                "rank_code": str,
                "rank_name_ko": str,
                "rank_icon": str,
                "experience_points": int,
                "level": int,
                "total_messages": int,
                "scenarios_completed": int
            },
            ...
        ]
    """
    if limit > 500:
        limit = 500

    leaderboard = db_manager.get_rank_leaderboard(limit)
    return leaderboard


# ============================================================
# Scenario Management 엔드포인트 (시나리오 관리)
# ============================================================

@app.get("/api/scenarios")
async def get_scenarios():
    """모든 시나리오 조회 (공개 API) - Redis 캐싱 적용 (P2 최적화)

    Returns:
        List of scenario cards with statistics
        [
            {
                "scenario_id": str,
                "title": str,
                "description": str,
                "image_url": str,
                "tags": List[str],
                "card_size": str,
                "route_path": str,
                "likes": int,
                "comments": int,
                "views": int
            },
            ...
        ]
    """
    # Redis 캐시 확인
    cached_scenarios = cache_manager.get_scenarios_cached()
    if cached_scenarios is not None:
        return cached_scenarios

    # 캐시 미스: DB에서 조회
    scenarios = db_manager.get_all_scenarios(include_inactive=False)

    # Redis에 캐싱 (5분 TTL)
    cache_manager.set_scenarios_cached(scenarios, ttl=300)

    return scenarios


@app.get("/api/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    """특정 시나리오 조회 (공개 API)

    Args:
        scenario_id: 시나리오 ID

    Returns:
        Scenario details with statistics
    """
    scenario = db_manager.get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@app.post("/api/scenarios/{scenario_id}/view")
async def record_scenario_view(
    scenario_id: str,
    request: Request,
    user: Dict = Depends(optional_auth)
):
    """시나리오 조회 기록 (조회수 증가)

    Args:
        scenario_id: 시나리오 ID
        user: 사용자 정보 (선택, 인증된 경우)

    Returns:
        {"success": bool}
    """
    # Get user_id if authenticated, otherwise None
    user_id = user.get("user_id") if user else None

    # Get client IP and user agent
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    success = db_manager.record_scenario_view(
        scenario_id=scenario_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to record view")

    return {"success": True}


@app.get("/api/users/me/scenarios")
async def get_user_scenarios(user: Dict = Depends(require_auth)):
    """사용자별 시나리오 조회 (진행도 포함)

    인증 필요. 사용자의 진행도 정보가 포함된 시나리오 리스트 반환.

    Returns:
        [
            {
                "scenario_id": str,
                "title": str,
                "description": str,
                "image_url": str,
                "tags": List[str],
                "card_size": str,
                "route_path": str,
                "likes": int,
                "comments": int,
                "views": int,
                "is_liked": bool,
                "has_started": bool,
                "has_completed": bool,
                "completion_percentage": int,
                "last_played_at": str
            },
            ...
        ]
    """
    scenarios = db_manager.get_scenarios_with_user_progress(user["user_id"])
    return scenarios


@app.post("/api/users/me/scenarios/{scenario_id}/like")
async def toggle_scenario_like(scenario_id: str, user: Dict = Depends(require_auth)):
    """시나리오 좋아요 토글 (좋아요/취소)

    Args:
        scenario_id: 시나리오 ID

    Returns:
        {
            "liked": bool,
            "total_likes": int
        }
    """
    try:
        result = db_manager.toggle_scenario_like(user["user_id"], scenario_id)
        return result
    except Exception as e:
        print(f"❌ Error toggling like: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle like")


@app.get("/api/users/me/scenarios/{scenario_id}/progress")
async def get_scenario_progress(scenario_id: str, user: Dict = Depends(require_auth)):
    """사용자의 특정 시나리오 진행도 조회

    Args:
        scenario_id: 시나리오 ID

    Returns:
        {
            "user_id": str,
            "scenario_id": str,
            "has_started": bool,
            "has_completed": bool,
            "completion_percentage": int,
            "last_session_id": str,
            "last_played_at": str,
            "total_messages": int,
            "total_play_time": int,
            "is_liked": bool
        }
    """
    progress = db_manager.get_user_scenario_progress(user["user_id"], scenario_id)
    if not progress:
        # Return default progress if not found
        return {
            "user_id": user["user_id"],
            "scenario_id": scenario_id,
            "has_started": False,
            "has_completed": False,
            "completion_percentage": 0,
            "total_messages": 0,
            "total_play_time": 0,
            "is_liked": False
        }
    return progress


@app.put("/api/users/me/scenarios/{scenario_id}/progress")
async def update_scenario_progress(
    scenario_id: str,
    progress_data: Dict,
    user: Dict = Depends(require_auth)
):
    """사용자의 시나리오 진행도 업데이트

    Args:
        scenario_id: 시나리오 ID
        progress_data: 업데이트할 진행도 데이터
            {
                "has_started": bool (optional),
                "has_completed": bool (optional),
                "completion_percentage": int (optional),
                "last_session_id": str (optional),
                "total_messages": int (optional),
                "total_play_time": int (optional)
            }

    Returns:
        {"success": bool}
    """
    success = db_manager.update_user_scenario_progress(
        user["user_id"],
        scenario_id,
        progress_data
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update progress")

    return {"success": True}


# ============================================================
# 사용자 장기 기억 관리 엔드포인트 (Long-term Memory)
# ============================================================

@app.get("/api/users/me/memories")
async def get_user_memories(
    memory_type: Optional[str] = None,
    limit: int = 50,
    user: Dict = Depends(require_auth)
):
    """사용자의 장기 기억 목록 조회

    Args:
        memory_type: 기억 타입 필터 (character_preference, user_fact, game_progress, relationship, important_event)
        limit: 반환할 최대 개수 (기본값: 50)
        user: 인증된 사용자 정보

    Returns:
        List of memories with metadata
    """
    try:
        memories = db_manager.get_user_memories(
            user_id=user["user_id"],
            memory_type=memory_type,
            limit=limit
        )
        return memories if memories else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memories: {str(e)}")


@app.get("/api/users/me/memories/{memory_key}")
async def get_memory_by_key(
    memory_key: str,
    user: Dict = Depends(require_auth)
):
    """특정 키로 기억 조회

    Args:
        memory_key: 기억 키 (예: "favorite_character")
        user: 인증된 사용자 정보

    Returns:
        Memory object or 404
    """
    try:
        memory = db_manager.get_memory_by_key(
            user_id=user["user_id"],
            memory_key=memory_key
        )

        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        return memory
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memory: {str(e)}")


@app.post("/api/users/me/memories")
async def create_memory(
    memory_data: Dict,
    user: Dict = Depends(require_auth)
):
    """새로운 기억 생성

    Args:
        memory_data: {
            "memory_key": str (required),
            "memory_value": str (required),
            "memory_type": str (optional, default: "fact"),
            "importance": float (optional, 0.0-1.0),
            "tags": List[str] (optional),
            "context": Dict (optional),
            "confidence": float (optional, 0.0-1.0)
        }
        user: 인증된 사용자 정보

    Returns:
        {"success": bool, "memory_id": int}
    """
    try:
        # Required fields
        if "memory_key" not in memory_data or "memory_value" not in memory_data:
            raise HTTPException(status_code=400, detail="memory_key and memory_value are required")

        # Generate embedding for the memory value
        embedding = None
        if memory_data.get("memory_value"):
            embedding = generate_embedding(memory_data["memory_value"])

        # Create or update memory
        memory_id = db_manager.create_or_update_memory(
            user_id=user["user_id"],
            memory_key=memory_data["memory_key"],
            memory_value=memory_data["memory_value"],
            memory_type=memory_data.get("memory_type", "fact"),
            importance=memory_data.get("importance", 0.5),
            tags=memory_data.get("tags"),
            context=memory_data.get("context"),
            confidence=memory_data.get("confidence"),
            embedding=embedding
        )

        if not memory_id:
            raise HTTPException(status_code=500, detail="Failed to create memory")

        return {"success": True, "memory_id": memory_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create memory: {str(e)}")


@app.put("/api/users/me/memories/{memory_key}")
async def update_memory(
    memory_key: str,
    memory_data: Dict,
    user: Dict = Depends(require_auth)
):
    """기존 기억 업데이트

    Args:
        memory_key: 업데이트할 기억 키
        memory_data: {
            "memory_value": str (required),
            "memory_type": str (optional),
            "importance": float (optional),
            "tags": List[str] (optional),
            "context": Dict (optional),
            "confidence": float (optional)
        }
        user: 인증된 사용자 정보

    Returns:
        {"success": bool, "memory_id": int}
    """
    try:
        # Check if memory exists
        existing_memory = db_manager.get_memory_by_key(
            user_id=user["user_id"],
            memory_key=memory_key
        )

        if not existing_memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # Required field
        if "memory_value" not in memory_data:
            raise HTTPException(status_code=400, detail="memory_value is required")

        # Generate new embedding if memory_value changed
        embedding = None
        if memory_data.get("memory_value"):
            embedding = generate_embedding(memory_data["memory_value"])

        # Update memory (same as create - upsert pattern)
        memory_id = db_manager.create_or_update_memory(
            user_id=user["user_id"],
            memory_key=memory_key,
            memory_value=memory_data["memory_value"],
            memory_type=memory_data.get("memory_type", existing_memory.get("memory_type", "fact")),
            importance=memory_data.get("importance", existing_memory.get("importance", 0.5)),
            tags=memory_data.get("tags", existing_memory.get("tags")),
            context=memory_data.get("context", existing_memory.get("context")),
            confidence=memory_data.get("confidence", existing_memory.get("confidence")),
            embedding=embedding
        )

        if not memory_id:
            raise HTTPException(status_code=500, detail="Failed to update memory")

        return {"success": True, "memory_id": memory_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update memory: {str(e)}")


@app.delete("/api/users/me/memories/{memory_key}")
async def delete_memory(
    memory_key: str,
    user: Dict = Depends(require_auth)
):
    """기억 삭제 (소프트 삭제)

    Args:
        memory_key: 삭제할 기억 키
        user: 인증된 사용자 정보

    Returns:
        {"success": bool}
    """
    try:
        success = db_manager.delete_memory(
            user_id=user["user_id"],
            memory_key=memory_key
        )

        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")


@app.post("/api/users/me/memories/search")
async def search_memories_by_similarity(
    search_data: Dict,
    user: Dict = Depends(require_auth)
):
    """의미 기반 기억 검색 (Vector Similarity Search)

    Args:
        search_data: {
            "query": str (required) - 검색 쿼리,
            "limit": int (optional, default: 5) - 반환할 최대 개수,
            "min_importance": float (optional, default: 0.0) - 최소 중요도
        }
        user: 인증된 사용자 정보

    Returns:
        List of memories sorted by similarity (with distance field)
    """
    try:
        if "query" not in search_data:
            raise HTTPException(status_code=400, detail="query is required")

        # Generate embedding for query
        query_embedding = generate_embedding(search_data["query"])

        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")

        # Search by similarity
        memories = db_manager.search_memories_by_similarity(
            user_id=user["user_id"],
            query_embedding=query_embedding,
            limit=search_data.get("limit", 5),
            min_importance=search_data.get("min_importance", 0.0)
        )

        return memories if memories else []

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


@app.get("/api/users/me/memories/session/{session_id}")
async def get_memories_by_session(
    session_id: str,
    user: Dict = Depends(require_auth)
):
    """특정 세션에서 생성된 기억 조회

    Args:
        session_id: 세션 ID
        user: 인증된 사용자 정보

    Returns:
        List of memories from this session
    """
    try:
        memories = db_manager.get_user_memories(
            user_id=user["user_id"],
            limit=100  # Higher limit for session-specific queries
        )

        # Filter by source_session_id
        session_memories = [
            m for m in memories
            if m.get("source_session_id") == session_id
        ]

        return session_memories

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session memories: {str(e)}")


# ============================================================
# OAuth 2.0 소셜 로그인 엔드포인트 (Google, Kakao)
# ============================================================

@app.get("/api/auth/google")
async def google_login():
    """
    Google OAuth 로그인 URL 생성

    Returns:
        {"auth_url": str} - Google OAuth 로그인 페이지 URL
    """
    from src.auth.oauth_google import get_google_oauth_url

    try:
        auth_url, state = get_google_oauth_url()
        if not auth_url:
            raise HTTPException(
                status_code=500,
                detail="Google OAuth URL 생성 실패"
            )
        return {"auth_url": auth_url, "state": state}
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/api/auth/google/callback")
async def google_callback(code: str, state: Optional[str] = None):
    """
    Google OAuth 콜백 처리

    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection

    Returns:
        AuthResponse with JWT tokens
    """
    from src.auth.oauth_google import verify_google_token, create_or_get_google_user
    from src.auth.jwt_utils import create_access_token, create_refresh_token

    try:
        # Google 토큰 검증 및 사용자 정보 가져오기
        google_user_info = verify_google_token(code)
        if not google_user_info:
            raise HTTPException(
                status_code=401,
                detail="Google 인증 실패"
            )

        # DB에 사용자 생성 또는 가져오기
        user = create_or_get_google_user(db_manager, google_user_info)
        if not user:
            raise HTTPException(
                status_code=500,
                detail="사용자 생성/조회 실패"
            )

        # JWT 토큰 생성
        user_id = str(user['user_id'])
        token_data = {
            "user_id": user_id,
            "username": user["username"],
            "display_name": user.get("display_name", user["username"]),
        }
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data={"user_id": user_id})

        return AuthResponse(
            success=True,
            message="Google 로그인 성공",
            user_id=user_id,
            username=user["username"],
            display_name=user.get("display_name"),
            email=user.get("email"),
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Google callback error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Google 로그인 처리 중 오류가 발생했습니다"
        )


@app.get("/api/auth/kakao")
async def kakao_login():
    """
    Kakao OAuth 로그인 URL 생성

    Returns:
        {"auth_url": str} - Kakao OAuth 로그인 페이지 URL
    """
    from src.auth.oauth_kakao import get_kakao_oauth_url

    try:
        auth_url = get_kakao_oauth_url()
        if not auth_url:
            raise HTTPException(
                status_code=500,
                detail="Kakao OAuth URL 생성 실패"
            )
        return {"auth_url": auth_url}
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/api/auth/kakao/callback")
async def kakao_callback(code: str):
    """
    Kakao OAuth 콜백 처리

    Args:
        code: Authorization code from Kakao

    Returns:
        AuthResponse with JWT tokens
    """
    from src.auth.oauth_kakao import verify_kakao_token, create_or_get_kakao_user
    from src.auth.jwt_utils import create_access_token, create_refresh_token

    try:
        # Kakao 토큰 검증 및 사용자 정보 가져오기
        kakao_user_info = verify_kakao_token(code)
        if not kakao_user_info:
            raise HTTPException(
                status_code=401,
                detail="Kakao 인증 실패"
            )

        # DB에 사용자 생성 또는 가져오기
        user = create_or_get_kakao_user(db_manager, kakao_user_info)
        if not user:
            raise HTTPException(
                status_code=500,
                detail="사용자 생성/조회 실패"
            )

        # JWT 토큰 생성
        user_id = str(user['user_id'])
        token_data = {
            "user_id": user_id,
            "username": user["username"],
            "display_name": user.get("display_name", user["username"]),
        }
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data={"user_id": user_id})

        return AuthResponse(
            success=True,
            message="Kakao 로그인 성공",
            user_id=user_id,
            username=user["username"],
            display_name=user.get("display_name"),
            email=user.get("email"),
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Kakao callback error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kakao 로그인 처리 중 오류가 발생했습니다"
        )


# ============================================================
# 비밀번호 재설정 엔드포인트
# ============================================================

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


@app.post("/api/auth/password-reset/request")
async def request_password_reset(req: PasswordResetRequest):
    """
    비밀번호 재설정 요청 - 이메일로 재설정 링크 전송

    Args:
        req: PasswordResetRequest (email)

    Returns:
        성공 메시지
    """
    import secrets
    from datetime import datetime, timedelta
    from src.utils.email_sender import send_email, generate_password_reset_email

    try:
        # 이메일로 사용자 찾기
        user = db_manager.get_user_by_username(req.email)
        if not user:
            # 보안상 사용자가 없어도 성공 응답 (이메일 존재 여부 노출 방지)
            return {"success": True, "message": "비밀번호 재설정 이메일이 전송되었습니다."}

        user_id = str(user['user_id'])

        # 재설정 토큰 생성 (보안 랜덤 문자열)
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)  # 1시간 유효

        # DB에 토큰 저장
        token_id = db_manager.create_password_reset_token(
            user_id, reset_token, expires_at.isoformat()
        )

        if not token_id:
            raise HTTPException(status_code=500, detail="토큰 생성 실패")

        # 재설정 링크 생성
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"

        # 이메일 전송
        html_content, text_content = generate_password_reset_email(
            reset_link,
            user.get("display_name", user["username"])
        )

        email_sent = await send_email(
            to_email=user.get("email", req.email),
            subject="[KIME Chat] 비밀번호 재설정 요청",
            html_content=html_content,
            text_content=text_content
        )

        if not email_sent:
            # 이메일 전송 실패해도 클라이언트에는 성공 응답 (보안)
            logger.warning(f"Failed to send password reset email to {req.email}")

        return {
            "success": True,
            "message": "비밀번호 재설정 이메일이 전송되었습니다. 이메일을 확인해주세요."
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Password reset request error: {e}")
        raise HTTPException(
            status_code=500,
            detail="비밀번호 재설정 요청 처리 중 오류가 발생했습니다"
        )


@app.post("/api/auth/password-reset/confirm")
async def confirm_password_reset(req: PasswordResetConfirm):
    """
    비밀번호 재설정 확인 - 새 비밀번호 설정

    Args:
        req: PasswordResetConfirm (token, new_password)

    Returns:
        성공 메시지
    """
    import bcrypt

    try:
        # 토큰 검증
        token_data = db_manager.get_password_reset_token(req.token)
        if not token_data:
            raise HTTPException(
                status_code=400,
                detail="유효하지 않거나 만료된 토큰입니다"
            )

        user_id = token_data["user_id"]

        # 새 비밀번호 해싱
        new_password_hash = bcrypt.hashpw(
            req.new_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # 비밀번호 업데이트
        if not db_manager.update_user_password(user_id, new_password_hash):
            raise HTTPException(status_code=500, detail="비밀번호 업데이트 실패")

        # 토큰 사용 처리
        db_manager.mark_password_reset_token_as_used(req.token)

        return {
            "success": True,
            "message": "비밀번호가 성공적으로 변경되었습니다"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Password reset confirm error: {e}")
        raise HTTPException(
            status_code=500,
            detail="비밀번호 재설정 처리 중 오류가 발생했습니다"
        )




# ------------------------------------------------------------
# ✅ 세션 상태 조회 (디버깅용)
# ------------------------------------------------------------


# ------------------------------------------------------------
# ✅ 사용 가능한 시나리오 목록 조회 (프론트 시나리오 선택용)
# ------------------------------------------------------------
@app.get("/api/scenarios")
async def list_scenarios():
    """data/scenarios 폴더의 JSON 파일 목록 반환"""
    try:
        scenarios_dir = os.path.join("data", "scenarios")
        if not os.path.exists(scenarios_dir):
            return {"scenarios": []}

        scenarios = []
        for filename in os.listdir(scenarios_dir):
            if filename.endswith(".json"):
                scenario_id = filename.replace(".json", "")
                scenarios.append({"id": scenario_id})
        return {"scenarios": scenarios}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🚀 메인 실행부
# ============================================================
if __name__ == "__main__":
    import uvicorn

    # OpenAI 키 체크
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Warning: OPENAI_API_KEY not found in environment")

    print("🚀 Starting KIME Chat API Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📖 API docs: http://localhost:8000/docs")

    # FastAPI 실행
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Auto-reload disabled for stability
        log_level="info",
    )
