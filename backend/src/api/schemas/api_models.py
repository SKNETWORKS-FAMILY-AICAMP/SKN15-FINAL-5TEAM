""""
API Request/Response Pydantic Models
- 모든 API 엔드포인트에서 사용하는 데이터 모델 정의
"""

# ============================================================
# 📦 에이피아이 데이터 모델 — 요청·응답 스키마 정의
# ============================================================
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
#  
# ============================================================

class RegisterRequest(BaseModel):
    """회원가입 요청"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = None  # EmailStr 대신 str 사용 (email_validator 불필요)
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    """로그인 요청"""
    username: str
    password: str


class AuthResponse(BaseModel):
    """인증 응답 (회원가입/로그인)"""
    success: bool
    message: str
    user_id: Optional[str] = None
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


class PasswordResetRequest(BaseModel):
    """비밀번호 재설정 요청"""
    email: str


class PasswordResetConfirm(BaseModel):
    """비밀번호 재설정 확인"""
    token: str
    new_password: str = Field(..., min_length=6)


# ============================================================
#   
# ============================================================

class ConsumeCreditsRequest(BaseModel):
    """크레딧 소비 요청"""
    amount: int = Field(..., gt=0)
    description: str


class AwardXPRequest(BaseModel):
    """경험치 지급 요청"""
    xp_amount: int = Field(..., gt=0)
    xp_type: str = Field(..., description="'message', 'session_complete', 'scenario_complete', etc.")
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateEquipmentRequest(BaseModel):
    """장비 업데이트 요청"""
    equipment_updates: Dict[str, str]


# ============================================================
#  
# ============================================================

class ChatRequest(BaseModel):
    """프론트엔드 → 백엔드 대화 요청"""
    session_id: Optional[str] = None
    scenario_id: str = Field(..., description="예: 'train', 'ending', etc.")
    user_input: str = Field(..., min_length=1, max_length=1000)


class DialogueResponse(BaseModel):
    """단일 대화 응답"""
    speaker: str
    content: str
    emotion: Optional[str] = "neutral"
    image_url: Optional[str] = None
    choices: Optional[List[str]] = None


class ChatResponse(BaseModel):
    """백엔드 → 프론트엔드 대화 응답"""
    session_id: str
    turn_count: int
    dialogues: List[DialogueResponse]
    current_stage: Optional[str] = None
    stage_turn: Optional[int] = None
    is_ended: bool = False
    final_ending: Optional[str] = None


# ============================================================
#  
# ============================================================

class SessionInfoResponse(BaseModel):
    """세션 상태 조회 응답"""
    session_id: str
    scenario_id: str
    current_stage: Optional[str] = None
    turn_count: int = 0
    stage_turn: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================
#  
# ============================================================

class ScenarioResponse(BaseModel):
    """시나리오 정보 응답"""
    scenario_id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: bool = True
    difficulty: Optional[str] = None
    estimated_duration: Optional[int] = None  # minutes
    tags: Optional[List[str]] = None


class ScenarioStatsResponse(BaseModel):
    """시나리오 통계 응답"""
    scenario_id: str
    view_count: int = 0
    like_count: int = 0
    play_count: int = 0
    completion_count: int = 0
    average_rating: Optional[float] = None


# ============================================================
#  
# ============================================================

class MemoryCreateRequest(BaseModel):
    """메모리 생성 요청"""
    memory_key: str = Field(..., max_length=255)
    memory_value: str = Field(..., max_length=5000)
    memory_type: str = Field(default="dialogue_summary")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryUpdateRequest(BaseModel):
    """메모리 업데이트 요청"""
    memory_value: Optional[str] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)


class MemoryResponse(BaseModel):
    """메모리 응답"""
    memory_id: int
    user_id: str
    memory_key: str
    memory_value: str
    memory_type: str
    importance: float
    created_at: datetime


class MemorySearchRequest(BaseModel):
    """메모리 유사도 검색 요청"""
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)


# ============================================================
#  
# ============================================================

class LeaderboardEntry(BaseModel):
    """리더보드 엔트리"""
    rank: int
    user_id: str
    display_name: str
    level: int
    total_xp: int
    achievements_count: int = 0


class LeaderboardResponse(BaseModel):
    """리더보드 응답"""
    leaderboard: List[LeaderboardEntry]
    total_users: int
    updated_at: datetime


# ============================================================
# ============================================================

class MessageResponse(BaseModel):
    """일반 메시지 응답"""
    message: str
    status: str = "success"


class ErrorResponse(BaseModel):
    """에러 응답"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
