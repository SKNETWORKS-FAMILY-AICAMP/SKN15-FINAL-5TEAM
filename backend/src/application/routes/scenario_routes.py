"""
시나리오 관리 API - Repository Pattern 기반
- 시나리오 조회
- 조회수 기록
- 사용자별 시나리오 진행도
"""

# ============================================================
# 🗺️ 시나리오 라우터 — 시나리오 조회와 통계 제공
# ============================================================
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, List, Optional

from ..schemas.api_models import ScenarioResponse, MessageResponse
from ..dependencies.api_deps import get_character_repository, get_progression_repository, get_cache_manager
from ..dependencies.auth_deps import optional_auth, require_auth
from src.core.interfaces.repositories.character_repository import ICharacterRepository
from src.core.interfaces.repositories.progression_repository import IProgressionRepository

router = APIRouter()

@router.get("", response_model=List[Dict])
async def get_scenarios(
    character_repo: ICharacterRepository = Depends(get_character_repository),
    cache=Depends(get_cache_manager)
):
    """
    모든 시나리오 조회 - Repository Pattern

    Redis 캐싱 적용 (5분 TTL)

    Returns:
        시나리오 목록 (카드 정보, 통계 포함)
    """
    # 레디스 캐시 확인
    cached_scenarios = cache.get_scenarios_cached()
    if cached_scenarios is not None:
        return cached_scenarios

    # 캐시 미스: 데이터베이스에서 조회
    scenarios = character_repo.get_all_scenarios(include_inactive=False)

    # 레디스에 캐싱 (5분)
    cache.set_scenarios_cached(scenarios, ttl=300)

    return scenarios

@router.get("/{scenario_id}", response_model=Dict)
async def get_scenario(
    scenario_id: str,
    character_repo: ICharacterRepository = Depends(get_character_repository)
):
    """
    특정 시나리오 조회 - Repository Pattern

    Args:
        scenario_id: 시나리오 ID

    Returns:
        시나리오 상세 정보 + 통계
    """
    scenario = character_repo.get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return scenario

@router.post("/{scenario_id}/view", response_model=MessageResponse)
async def record_scenario_view(
    scenario_id: str,
    request: Request,
    user: Optional[Dict] = Depends(optional_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """
    시나리오 조회 기록 - Repository Pattern

    인증은 선택 사항 (비로그인 사용자도 조회수 증가)

    Args:
        scenario_id: 시나리오 ID
        user: 사용자 정보 (로그인한 경우)

    Returns:
        성공 메시지
    """
    user_id = user.get("user_id") if user else None

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    success = progression_repo.record_scenario_view(
        scenario_id=scenario_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to record view")

    return {"message": "View recorded successfully", "status": "success"}

@router.post("/{scenario_id}/like", response_model=Dict)
async def toggle_scenario_like(
    scenario_id: str,
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """
    시나리오 좋아요 토글 - Repository Pattern

    인증 필요

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

@router.get("/{scenario_id}/progress", response_model=Dict)
async def get_scenario_progress(
    scenario_id: str,
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """
    사용자의 특정 시나리오 진행도 조회 - Repository Pattern

    인증 필요

    Args:
        scenario_id: 시나리오 ID

    Returns:
        진행도 정보 (시작 여부, 완료 여부, 완료율, 마지막 플레이 시간 등)
    """
    progress = progression_repo.get_user_scenario_progress(user["user_id"], scenario_id)
    if not progress:
        # 기본 진행도 정보가 없을 때 초기 상태 반환
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

@router.put("/{scenario_id}/progress", response_model=MessageResponse)
async def update_scenario_progress(
    scenario_id: str,
    progress_data: Dict,
    user: Dict = Depends(require_auth),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """
    사용자의 시나리오 진행도 업데이트 - Repository Pattern

    인증 필요

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
        성공 메시지
    """
    success = progression_repo.update_user_scenario_progress(
        user["user_id"],
        scenario_id,
        progress_data
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update progress")

    return {"message": "Progress updated successfully", "status": "success"}
