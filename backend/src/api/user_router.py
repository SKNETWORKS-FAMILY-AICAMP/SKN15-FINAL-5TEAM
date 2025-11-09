"""
User API Router

사용자 관련 모든 엔드포인트를 관리합니다:
- 크레딧 (버블) 관리
- 프로그레션 (레벨, 경험치)
- 장비 관리
- 시나리오 진행도
- 기억 시스템 (Memories)
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.auth.dependencies import require_auth

# Router 생성
router = APIRouter(prefix="/api/users/me", tags=["users"])


# ============================================================
# Database Manager Dependency
# ============================================================
db_manager = None


def set_db_manager(manager):
    """DB Manager를 설정합니다"""
    global db_manager
    db_manager = manager


# ============================================================
# Pydantic Models
# ============================================================


class ConsumeCreditsRequest(BaseModel):
    amount: int
    description: str


class AwardXPRequest(BaseModel):
    xp_amount: int
    xp_type: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateEquipmentRequest(BaseModel):
    equipment_updates: Dict[str, str]


class UpdateScenarioProgressRequest(BaseModel):
    has_started: Optional[bool] = None
    has_completed: Optional[bool] = None
    completion_percentage: Optional[int] = None
    last_session_id: Optional[str] = None


class CreateMemoryRequest(BaseModel):
    memory_key: str
    memory_type: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class UpdateMemoryRequest(BaseModel):
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchMemoriesRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    limit: int = 10


class UpdateSettingsRequest(BaseModel):
    sound_enabled: Optional[bool] = None
    bgm_volume: Optional[int] = None
    sfx_volume: Optional[int] = None
    auto_save: Optional[bool] = None
    language: Optional[str] = None
    font_size: Optional[str] = None
    animation_speed: Optional[str] = None


# ============================================================
# Credits Endpoints
# ============================================================


@router.get("/credits")
async def get_user_credits(user: Dict = Depends(require_auth)):
    """사용자 크레딧(버블) 조회"""
    credits = db_manager.get_user_credits(user["user_id"])
    if not credits:
        raise HTTPException(status_code=404, detail="크레딧 정보를 찾을 수 없습니다")
    return credits


@router.post("/credits/consume")
async def consume_user_credits(req: ConsumeCreditsRequest, user: Dict = Depends(require_auth)):
    """사용자 크레딧(버블) 소비"""
    success = db_manager.consume_credits(user["user_id"], req.amount, req.description)
    if not success:
        raise HTTPException(status_code=400, detail="크레딧 잔액이 부족합니다")
    return {"success": True, "message": f"{req.amount} 버블이 차감되었습니다"}


# ============================================================
# Settings Endpoints
# ============================================================


@router.get("/settings")
async def get_user_settings(user: Dict = Depends(require_auth)):
    """
    사용자 설정 조회

    Returns:
        {
            "sound_enabled": bool,
            "bgm_volume": int,
            "sfx_volume": int,
            "auto_save": bool,
            "language": str,
            "font_size": str,
            "animation_speed": str,
            "created_at": str,
            "updated_at": str
        }
    """
    settings = db_manager.get_user_settings(user["user_id"])
    if not settings:
        raise HTTPException(status_code=404, detail="설정 정보를 찾을 수 없습니다")
    return settings


@router.put("/settings")
async def update_user_settings(req: UpdateSettingsRequest, user: Dict = Depends(require_auth)):
    """
    사용자 설정 업데이트

    Args:
        req: UpdateSettingsRequest (업데이트할 필드만 포함)

    Returns:
        {"success": bool, "message": str}
    """
    # None이 아닌 값들만 딕셔너리로 변환
    settings_dict = {k: v for k, v in req.dict().items() if v is not None}

    if not settings_dict:
        raise HTTPException(status_code=400, detail="업데이트할 설정이 없습니다")

    success = db_manager.update_user_settings(user["user_id"], settings_dict)
    if not success:
        raise HTTPException(status_code=500, detail="설정 업데이트에 실패했습니다")
    return {"success": True, "message": "설정이 업데이트되었습니다"}


# ============================================================
# User Statistics Endpoints
# ============================================================


@router.get("/statistics")
async def get_user_statistics(user: Dict = Depends(require_auth)):
    """
    사용자 통계 조회

    Returns:
        {
            "total_play_time_minutes": int,
            "total_sessions": int,
            "total_messages": int,
            "top_affinity_characters": [
                {"character_name": str, "affinity_score": int}
            ],
            "frequent_scenarios": [
                {"scenario_id": str, "title": str, "play_count": int, "total_messages": int}
            ]
        }
    """
    statistics = db_manager.get_user_statistics(user["user_id"])
    if not statistics:
        raise HTTPException(status_code=404, detail="통계 정보를 찾을 수 없습니다")
    return statistics


# ============================================================
# Progression Endpoints
# ============================================================


@router.get("/progression")
async def get_user_progression(user: Dict = Depends(require_auth)):
    """
    현재 사용자의 진행도 조회 (rank, level, XP, stats, equipment)

    Returns:
        {
            "user_id": str,
            "rank_code": str,
            "rank_name_ko": str,
            "experience_points": int,
            "level": int,
            ...
        }
    """
    progression = db_manager.get_user_progression(user["user_id"])
    if not progression:
        raise HTTPException(status_code=404, detail="진행도 정보를 찾을 수 없습니다")
    return progression


@router.get("/equipment")
async def get_user_equipment(user: Dict = Depends(require_auth)):
    """
    사용자 장비 상태 조회

    Returns:
        {
            "sword_status": str,
            "uniform_status": str,
            "crow_status": str,
            ...
        }
    """
    equipment = db_manager.get_user_equipment(user["user_id"])
    if not equipment:
        raise HTTPException(status_code=404, detail="장비 정보를 찾을 수 없습니다")
    return equipment


@router.post("/progression/award-xp")
async def award_xp(req: AwardXPRequest, user: Dict = Depends(require_auth)):
    """
    경험치 지급 (내부 API - 백엔드에서 호출)

    Args:
        req: AwardXPRequest

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
    result = db_manager.award_experience_points(
        user_id=user["user_id"],
        xp_amount=req.xp_amount,
        xp_type=req.xp_type,
        description=req.description,
        metadata=req.metadata
    )
    if not result:
        raise HTTPException(status_code=500, detail="경험치 지급에 실패했습니다")
    return result


@router.put("/equipment")
async def update_equipment(req: UpdateEquipmentRequest, user: Dict = Depends(require_auth)):
    """
    장비 업데이트

    Args:
        req: UpdateEquipmentRequest

    Returns:
        {"success": bool}
    """
    success = db_manager.update_user_equipment(
        user_id=user["user_id"],
        equipment_updates=req.equipment_updates
    )
    if not success:
        raise HTTPException(status_code=500, detail="장비 업데이트에 실패했습니다")
    return {"success": True}


@router.get("/xp-transactions")
async def get_xp_transactions(
    limit: int = 50,
    offset: int = 0,
    user: Dict = Depends(require_auth)
):
    """
    경험치 거래 내역 조회 (페이지네이션)

    Args:
        limit: 조회할 개수
        offset: 오프셋

    Returns:
        List[XPTransaction]
    """
    transactions = db_manager.get_xp_transactions(
        user_id=user["user_id"],
        limit=limit,
        offset=offset
    )
    return transactions


# ============================================================
# Scenario Progress Endpoints
# ============================================================


@router.get("/scenarios")
async def get_user_scenarios(user: Dict = Depends(require_auth)):
    """
    사용자의 시나리오 목록 조회 (진행도 포함)

    Returns:
        List[ScenarioWithProgress]
        [
            {
                "scenario_id": str,
                "title": str,
                ...,
                "is_liked": bool,
                "has_started": bool,
                "completion_percentage": int
            }
        ]
    """
    scenarios = db_manager.get_scenarios_with_user_progress(user["user_id"])
    return scenarios


@router.post("/scenarios/{scenario_id}/like")
async def toggle_scenario_like(scenario_id: str, user: Dict = Depends(require_auth)):
    """
    시나리오 좋아요 토글

    Args:
        scenario_id: 시나리오 ID

    Returns:
        {"liked": bool, "total_likes": int}
    """
    try:
        result = db_manager.toggle_scenario_like(user["user_id"], scenario_id)
        return result
    except Exception as e:
        print(f"❌ Error toggling like: {e}")
        raise HTTPException(status_code=500, detail="좋아요 처리에 실패했습니다")


@router.get("/scenarios/{scenario_id}/progress")
async def get_scenario_progress(scenario_id: str, user: Dict = Depends(require_auth)):
    """
    시나리오 진행도 조회

    Args:
        scenario_id: 시나리오 ID

    Returns:
        {
            "scenario_id": str,
            "has_started": bool,
            "has_completed": bool,
            "completion_percentage": int,
            ...
        }
    """
    progress = db_manager.get_user_scenario_progress(user["user_id"], scenario_id)
    if not progress:
        # 진행도가 없으면 초기값 반환
        return {
            "scenario_id": scenario_id,
            "has_started": False,
            "has_completed": False,
            "completion_percentage": 0,
            "total_messages": 0,
            "total_play_time": 0,
            "is_liked": False
        }
    return progress


@router.put("/scenarios/{scenario_id}/progress")
async def update_scenario_progress(
    scenario_id: str,
    req: UpdateScenarioProgressRequest,
    user: Dict = Depends(require_auth)
):
    """
    시나리오 진행도 업데이트

    Args:
        scenario_id: 시나리오 ID
        req: UpdateScenarioProgressRequest

    Returns:
        {"success": bool}
    """
    success = db_manager.update_user_scenario_progress(
        user_id=user["user_id"],
        scenario_id=scenario_id,
        has_started=req.has_started,
        has_completed=req.has_completed,
        completion_percentage=req.completion_percentage,
        last_session_id=req.last_session_id
    )
    if not success:
        raise HTTPException(status_code=500, detail="진행도 업데이트에 실패했습니다")
    return {"success": True}


# ============================================================
# Memory Endpoints
# ============================================================


@router.get("/memories")
async def get_user_memories(
    memory_type: Optional[str] = None,
    limit: int = 100,
    user: Dict = Depends(require_auth)
):
    """
    사용자 장기 기억 조회

    Args:
        memory_type: 기억 타입 필터 (optional)
        limit: 조회 개수

    Returns:
        List[Memory]
    """
    memories = db_manager.get_user_memories(
        user_id=user["user_id"],
        memory_type=memory_type,
        limit=limit
    )
    return memories


@router.get("/memories/{memory_key}")
async def get_memory_by_key(memory_key: str, user: Dict = Depends(require_auth)):
    """
    특정 키로 기억 조회

    Args:
        memory_key: 기억 키

    Returns:
        Memory
    """
    memory = db_manager.get_user_memory_by_key(user["user_id"], memory_key)
    if not memory:
        raise HTTPException(status_code=404, detail="기억을 찾을 수 없습니다")
    return memory


@router.post("/memories")
async def create_memory(req: CreateMemoryRequest, user: Dict = Depends(require_auth)):
    """
    새로운 기억 생성

    Args:
        req: CreateMemoryRequest

    Returns:
        {"memory_id": str}
    """
    memory_id = db_manager.create_user_memory(
        user_id=user["user_id"],
        memory_key=req.memory_key,
        memory_type=req.memory_type,
        content=req.content,
        metadata=req.metadata
    )
    if not memory_id:
        raise HTTPException(status_code=500, detail="기억 생성에 실패했습니다")
    return {"memory_id": memory_id}


@router.put("/memories/{memory_key}")
async def update_memory(
    memory_key: str,
    req: UpdateMemoryRequest,
    user: Dict = Depends(require_auth)
):
    """
    기억 업데이트

    Args:
        memory_key: 기억 키
        req: UpdateMemoryRequest

    Returns:
        {"success": bool}
    """
    success = db_manager.update_user_memory(
        user_id=user["user_id"],
        memory_key=memory_key,
        content=req.content,
        metadata=req.metadata
    )
    if not success:
        raise HTTPException(status_code=500, detail="기억 업데이트에 실패했습니다")
    return {"success": True}


@router.delete("/memories/{memory_key}")
async def delete_memory(memory_key: str, user: Dict = Depends(require_auth)):
    """
    기억 삭제

    Args:
        memory_key: 기억 키

    Returns:
        {"success": bool}
    """
    success = db_manager.delete_user_memory(user["user_id"], memory_key)
    if not success:
        raise HTTPException(status_code=404, detail="기억을 찾을 수 없습니다")
    return {"success": True}


@router.post("/memories/search")
async def search_memories(req: SearchMemoriesRequest, user: Dict = Depends(require_auth)):
    """
    의미 기반 기억 검색 (Vector Search)

    Args:
        req: SearchMemoriesRequest

    Returns:
        List[Memory]
    """
    memories = db_manager.search_user_memories(
        user_id=user["user_id"],
        query=req.query,
        memory_type=req.memory_type,
        limit=req.limit
    )
    return memories


@router.get("/memories/session/{session_id}")
async def get_session_memories(session_id: str, user: Dict = Depends(require_auth)):
    """
    특정 세션의 기억 조회

    Args:
        session_id: 세션 ID

    Returns:
        List[Memory]
    """
    memories = db_manager.get_session_memories(user["user_id"], session_id)
    return memories
