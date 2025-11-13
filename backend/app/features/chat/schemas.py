"""
Chat Feature - Pydantic Schemas
Request/Response DTO
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# ============================================================
# Request Schemas
# ============================================================

class ChatRequest(BaseModel):
    """
    채팅 요청

    Frontend API 계약:
    - session_id: 선택 (없으면 신규 생성)
    - scenario_id: 필수
    - user_input: 필수
    - user_name: 선택
    """
    session_id: Optional[str] = None
    scenario_id: str = Field(..., description="Scenario ID (e.g., 'train', 'ending')")
    user_input: str = Field(..., min_length=1, max_length=1000, description="User message")
    user_name: Optional[str] = Field(None, description="User display name")


# ============================================================
# Response Schemas
# ============================================================

class ChatMessage(BaseModel):
    """
    단일 대화 메시지

    ✅ Frontend 기대 필드: text (content 아님!)
    """
    speaker: str = Field(..., description="Character name (e.g., 'tanjiro', 'nezuko')")
    text: str = Field(..., description="Dialogue text")  # ✅ text로 통일
    emotion: Optional[str] = Field("neutral", description="Emotion (e.g., 'happy', 'sad')")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    fx: Optional[str] = Field(None, description="Sound effect")
    image_index: Optional[str] = Field(None, description="Image index")
    affinity_level: Optional[str] = Field(None, description="Affinity level")
    emotion_intensity: Optional[str] = Field(None, description="Emotion intensity")


class MemoryEvent(BaseModel):
    """
    메모리 이벤트 (UI 표시용)
    """
    event_type: str = Field(..., description="Event type: 'saved' or 'recalled'")
    character_name: str = Field(..., description="Character who saved/recalled the memory")
    memory_type: str = Field(..., description="Memory type: fact, event, relationship, preference")
    memory_content: str = Field(..., description="Memory content (max 100 chars)")
    importance: float = Field(..., description="Importance score (0.0-1.0)")
    count: Optional[int] = Field(None, description="Number of memories (for batch events)")


class ChatResponse(BaseModel):
    """
    채팅 응답

    Frontend API 계약 준수
    """
    session_id: str
    turn_count: int
    dialogues: List[ChatMessage]
    current_stage: Optional[str] = None
    affinity_scores: Optional[Dict[str, float]] = None
    is_ended: bool = False
    has_more: bool = False  # 배치 모드
    system_message: Optional[str] = None
    current_image: Optional[str] = None
    output: Optional[Dict] = None
    memory_events: Optional[List[MemoryEvent]] = Field(None, description="Memory save/recall events for UI display")


# ============================================================
# Internal DTOs (레이어 간 데이터 전송)
# ============================================================

class DialogueResult(BaseModel):
    """
    Parent Agent 실행 결과
    """
    dialogues: List[ChatMessage]
    next_stage: Optional[str] = None
    stage_complete: bool = False
    updated_state: Dict = Field(default_factory=dict)
    affinity_delta: Optional[Dict[str, float]] = None
    affinity_scores: Optional[Dict[str, float]] = None  # 현재 친밀도 (DB 로드 + 델타 적용)
    current_image: Optional[str] = Field(None, description="선택된 배경 이미지 식별자")
    memory_events: List[MemoryEvent] = Field(default_factory=list, description="Memory events during this turn")


class StageResult(BaseModel):
    """
    Stage Handler 실행 결과
    """
    context: Dict = Field(default_factory=dict)
    speaker_pool: List[str] = Field(default_factory=list)
    beats: List[Dict] = Field(default_factory=list)
    next_stage: Optional[str] = None
    stage_complete: bool = False


# ========================================
# Memory Schemas (from memories feature)
# ========================================

class MemoryResponse(BaseModel):
    """사용자 장기기억 응답"""
    memory_id: int = Field(..., description="기억 ID")
    memory_key: str = Field(..., description="기억 키")
    memory_value: str = Field(..., description="기억 내용")
    memory_type: str = Field(..., description="기억 유형 (fact/event/relationship/preference)")
    importance: Optional[float] = Field(None, description="중요도 점수 (0.0-1.0)")
    access_count: int = Field(default=0, description="액세스 횟수")
    last_accessed_at: Optional[str] = Field(None, description="마지막 액세스 시간")
    created_at: Optional[str] = Field(None, description="생성일시")

    class Config:
        from_attributes = True
