"""
사용자 라우터 - Repository Pattern 기반
- 크레딧, 진행도, 장비, 시나리오 진행도를 관리한다.
"""

# ============================================================
# 👤 사용자 라우터 — Repository Pattern 기반
# ============================================================
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException

from ..dependencies.auth_deps import require_auth
from ..dependencies.api_deps import get_progression_repository
from ..schemas.api_models import (
    ConsumeCreditsRequest,
    AwardXPRequest,
    UpdateEquipmentRequest,
)
from src.core.interfaces.repositories.progression_repository import IProgressionRepository

# ============================================================
# 라우터 생성
# ============================================================
router = APIRouter()

# ============================================================
# 💰 크레딧 및 리소스 관련 엔드포인트
# ============================================================

@router.get("/me/credits")
async def get_user_credits(
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """사용자 크레딧(버블) 조회 - Repository Pattern"""
    credits = progression_repo.get_user_credits(user["user_id"])
    if not credits:
        raise HTTPException(status_code=404, detail="크레딧 정보를 찾을 수 없습니다")
    return credits

@router.post("/me/credits/consume")
async def consume_user_credits(
    req: ConsumeCreditsRequest,
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """사용자 크레딧(버블) 소비 - Repository Pattern"""
    success = progression_repo.consume_credits(user["user_id"], req.amount, req.description)
    if not success:
        raise HTTPException(status_code=400, detail="크레딧 잔액이 부족합니다")
    return {"success": True, "message": f"{req.amount} 버블이 차감되었습니다"}

# ============================================================
# ============================================================

@router.get("/me/progression")
async def get_user_progression(
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """현재 사용자의 진행도 조회 - Repository Pattern

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
    progression = progression_repo.get_user_progression(user["user_id"])
    if not progression:
        raise HTTPException(status_code=404, detail="Progression data not found")
    return progression

@router.get("/me/equipment")
async def get_user_equipment(
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """현재 사용자의 장비 상태 조회 - Repository Pattern

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
    equipment = progression_repo.get_user_equipment(user["user_id"])
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

@router.post("/me/progression/award-xp")
async def award_user_experience(
    req: AwardXPRequest,
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """사용자에게 경험치 지급 - Repository Pattern

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

    result = progression_repo.award_experience(
        user["user_id"],
        req.xp_amount,
        req.xp_type,
        req.description,
        req.metadata
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to award XP")

    return result

@router.put("/me/equipment")
async def update_user_equipment(
    req: UpdateEquipmentRequest,
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """사용자 장비 상태 업데이트 - Repository Pattern

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
    success = progression_repo.update_user_equipment(user["user_id"], req.equipment_updates)
    if not success:
        raise HTTPException(status_code=400, detail="No valid equipment fields to update")
    return {"success": True}

@router.get("/me/xp-transactions")
async def get_user_xp_transactions(
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository),
    limit: int = 50,
    offset: int = 0
):
    """사용자 경험치 거래 내역 조회 - Repository Pattern

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

    transactions = progression_repo.get_xp_transactions(user["user_id"], limit, offset)
    return transactions

# ============================================================
# 🗺️ 시나리오 진행 관련 엔드포인트
# ============================================================

@router.get("/me/scenarios")
async def get_user_scenarios(
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """사용자별 시나리오 조회 - Repository Pattern

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
    scenarios = progression_repo.get_scenarios_with_user_progress(user["user_id"])
    return scenarios

@router.post("/me/scenarios/{scenario_id}/like")
async def toggle_scenario_like(
    scenario_id: str,
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """시나리오 좋아요 토글 - Repository Pattern

    Args:
        scenario_id: 시나리오 ID

    Returns:
        {
            "liked": bool,
            "total_likes": int
        }
    """
    try:
        result = progression_repo.toggle_scenario_like(user["user_id"], scenario_id)
        return result
    except Exception as e:
        print(f"❌ Error toggling like: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle like")

@router.get("/me/scenarios/{scenario_id}/progress")
async def get_scenario_progress(
    scenario_id: str,
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """사용자의 특정 시나리오 진행도 조회 - Repository Pattern

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
    progress = progression_repo.get_user_scenario_progress(user["user_id"], scenario_id)
    if not progress:
        # 기본 진행도 데이터가 없는 경우를 위한 초기 구조 반환
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

@router.put("/me/scenarios/{scenario_id}/progress")
async def update_scenario_progress(
    scenario_id: str,
    progress_data: Dict,
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """사용자의 시나리오 진행도 업데이트 - Repository Pattern

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
    success = progression_repo.update_user_scenario_progress(
        user["user_id"],
        scenario_id,
        progress_data
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update progress")

    return {"success": True}
