"""
Progression Feature - Schemas
Pydantic 모델 (Request/Response DTO)
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class XPTransactionResponse(BaseModel):
    """XP 거래 내역 응답"""
    transaction_id: str = Field(..., description="트랜잭션 ID")
    user_id: str = Field(..., description="사용자 ID")
    xp_amount: int = Field(..., description="XP 변동량 (양수: 획득, 음수: 소비)")
    xp_type: str = Field(..., description="XP 타입 (message/session_complete/scenario_complete/achievement/daily_bonus/event)")
    xp_balance_after: int = Field(..., description="변동 후 XP 잔액")
    level_before: Optional[int] = Field(None, description="변동 전 레벨")
    level_after: Optional[int] = Field(None, description="변동 후 레벨")
    did_level_up: bool = Field(default=False, description="레벨업 여부")
    description: Optional[str] = Field(None, description="설명")
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")
    created_at: Optional[str] = Field(None, description="생성일시")

    class Config:
        from_attributes = True


class XPTransactionListResponse(BaseModel):
    """XP 거래 내역 목록 응답"""
    transactions: List[XPTransactionResponse]
    total: int
