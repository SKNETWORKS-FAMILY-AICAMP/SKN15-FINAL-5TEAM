"""
Users Feature - Schemas
Pydantic 모델 (Request/Response DTO)
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


# ============================================================
# Affinity Schemas
# ============================================================

class AffinityResponse(BaseModel):
    """캐릭터 호감도 응답"""
    character_name: str = Field(..., description="캐릭터 이름")
    total_affinity_score: int = Field(..., description="총 호감도 점수")
    affinity_level: int = Field(..., description="호감도 레벨")
    total_interactions: int = Field(..., description="총 상호작용 수")
    last_interaction_at: Optional[str] = Field(None, description="마지막 상호작용 시간")

    class Config:
        from_attributes = True


# ============================================================
# Profile Schemas
# ============================================================

class UserProfileResponse(BaseModel):
    """사용자 프로필 응답"""
    user_id: str
    username: str
    display_name: str
    email: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    total_sessions: int = 0
    total_bubbles: int = 0
    last_login: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    affinities: List[AffinityResponse] = Field(default_factory=list, description="캐릭터 호감도 목록")

    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """프로필 수정 요청"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=50, description="표시 이름")
    email: Optional[EmailStr] = Field(None, description="이메일")


# ============================================================
# Stats Schemas
# ============================================================

class UserStatsResponse(BaseModel):
    """사용자 통계 응답"""
    total_dialogues: int = Field(..., description="총 대화 수")
    total_sessions: int = Field(..., description="총 세션 수")
    completed_scenarios: int = Field(..., description="완료한 시나리오 수")
    total_credits_used: int = Field(..., description="사용한 크레딧")
    total_affinity_points: int = Field(..., description="총 친밀도 점수")
    achievements: List[str] = Field(default_factory=list, description="달성한 업적")
    rank: str = Field(..., description="사용자 등급")
    created_at: str = Field(..., description="가입일")
    last_active_at: str = Field(..., description="마지막 활동")

    class Config:
        from_attributes = True


# ============================================================
# Credits Schemas
# ============================================================

class UserCreditsResponse(BaseModel):
    """사용자 크레딧 조회 응답"""
    bubble_count: int = Field(..., description="현재 보유 버블")
    total_purchased: int = Field(default=0, description="총 구매 버블")
    total_consumed: int = Field(default=0, description="총 사용 버블")

    class Config:
        from_attributes = True


class ConsumeCreditsRequest(BaseModel):
    """크레딧 소비 요청"""
    amount: int = Field(..., ge=1, description="소비할 크레딧 양")
    description: str = Field(..., min_length=1, max_length=200, description="사용 목적")


class ConsumeCreditsResponse(BaseModel):
    """크레딧 소비 응답"""
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    remaining_credits: int = Field(..., description="남은 크레딧")

    class Config:
        from_attributes = True


class CreditTransactionResponse(BaseModel):
    """크레딧 트랜잭션 응답"""
    transaction_id: str = Field(..., description="트랜잭션 ID")
    user_id: str = Field(..., description="사용자 ID")
    amount: int = Field(..., description="변동량 (양수: 획득, 음수: 소비)")
    transaction_type: str = Field(..., description="트랜잭션 타입")
    balance_after: int = Field(..., description="변동 후 잔액")
    description: Optional[str] = Field(None, description="설명")
    created_at: str = Field(..., description="생성일시")

    class Config:
        from_attributes = True


class CreateCreditTransactionRequest(BaseModel):
    """크레딧 트랜잭션 생성 요청"""
    amount: int = Field(..., description="변동량 (양수: 획득, 음수: 소비)")
    transaction_type: str = Field(..., description="트랜잭션 타입 (purchase, consume, refund, bonus, initial)")
    description: Optional[str] = Field(None, max_length=500, description="설명")

    class Config:
        from_attributes = True


class CreditTransactionStatsResponse(BaseModel):
    """크레딧 트랜잭션 통계 응답"""
    total_transactions: int = Field(..., description="총 트랜잭션 수")
    by_type: dict = Field(..., description="타입별 통계")

    class Config:
        from_attributes = True


# ============================================================
# Progression Schemas
# ============================================================

class UserProgressionResponse(BaseModel):
    """사용자 진행도 응답"""
    user_id: str = Field(..., description="사용자 ID")
    rank_code: str = Field(..., description="계급 코드")
    rank_name_ko: str = Field(..., description="계급 이름 (한글)")
    rank_name_en: Optional[str] = Field(None, description="계급 이름 (영어)")
    rank_name_ja: Optional[str] = Field(None, description="계급 이름 (일본어)")
    icon_emoji: Optional[str] = Field(None, description="계급 아이콘 이모지")
    level: int = Field(..., description="현재 레벨 (1-99)")
    experience_points: int = Field(..., description="총 경험치 (XP)")
    total_messages: int = Field(default=0, description="전체 메시지 수")
    total_sessions: int = Field(default=0, description="전체 세션 수")
    total_play_minutes: int = Field(default=0, description="전체 플레이 시간 (분)")
    scenarios_completed: int = Field(default=0, description="완료한 시나리오 수")
    achievements_count: int = Field(default=0, description="달성한 업적 수")
    min_xp: int = Field(..., description="현재 계급의 최소 XP")
    description_ko: Optional[str] = Field(None, description="계급 설명 (한글)")
    created_at: Optional[str] = Field(None, description="생성일시")
    updated_at: Optional[str] = Field(None, description="수정일시")

    class Config:
        from_attributes = True


# ============================================================
# Settings Schemas
# ============================================================

class UserSettingsBase(BaseModel):
    """사용자 설정 업데이트 요청"""
    sound_enabled: Optional[bool] = Field(None, description="사운드 활성화 여부")
    bgm_volume: Optional[int] = Field(None, ge=0, le=100, description="BGM 볼륨 (0-100)")
    sfx_volume: Optional[int] = Field(None, ge=0, le=100, description="SFX 볼륨 (0-100)")
    language: Optional[str] = Field(None, min_length=2, max_length=10, description="언어 설정 (ko/en/ja)")


class UserSettingsResponse(BaseModel):
    """사용자 설정 조회 응답"""
    user_id: str = Field(..., description="사용자 ID")
    sound_enabled: bool = Field(..., description="사운드 활성화 여부")
    bgm_volume: int = Field(..., description="BGM 볼륨 (0-100)")
    sfx_volume: int = Field(..., description="SFX 볼륨 (0-100)")
    language: str = Field(..., description="언어 설정")
    updated_at: str = Field(..., description="최종 수정 시간")

    class Config:
        from_attributes = True
