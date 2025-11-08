"""
Scenario API Router

시나리오 관련 Public 엔드포인트를 관리합니다:
- 시나리오 목록 조회
- 시나리오 상세 정보 조회
- 시나리오 조회 기록
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from src.auth.dependencies import optional_auth

# Router 생성
router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


# ============================================================
# Database Manager Dependency
# ============================================================
db_manager = None
cache_manager = None


def set_managers(db_mgr, cache_mgr):
    """DB Manager와 Cache Manager를 설정합니다"""
    global db_manager, cache_manager
    db_manager = db_mgr
    cache_manager = cache_mgr


# ============================================================
# Scenario Endpoints
# ============================================================


@router.get("")
async def get_scenarios():
    """
    시나리오 목록 조회 (Public API)

    Returns:
        List of scenario cards with statistics
        [
            {
                "scenario_id": str,
                "title": str,
                "description": str,
                "image_url": str,
                "tags": List[str],
                "card_size": "large" | "normal",
                "route_path": str,
                "likes": int,
                "comments": int,
                "views": int
            }
        ]
    """
    # 캐시 확인
    cached_scenarios = cache_manager.get_scenarios_cached()
    if cached_scenarios is not None:
        return cached_scenarios

    # DB에서 조회
    scenarios = db_manager.get_all_scenarios(include_inactive=False)

    # 캐시 저장 (5분)
    cache_manager.set_scenarios_cached(scenarios, ttl=300)

    return scenarios


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """
    시나리오 상세 정보 조회 (Public API)

    Args:
        scenario_id: 시나리오 ID

    Returns:
        시나리오 상세 정보
    """
    scenario = db_manager.get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.post("/{scenario_id}/view")
async def record_scenario_view(
    scenario_id: str,
    request: Request,
    current_user: Optional[dict] = None  # Depends(optional_auth) - 선택적 인증
):
    """
    시나리오 조회 기록 (Public API - 인증 선택적)

    Args:
        scenario_id: 시나리오 ID
        current_user: 인증된 사용자 (선택적)

    Returns:
        성공 여부
    """
    user_id = current_user.get("user_id") if current_user else None
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        success = db_manager.record_scenario_view(
            scenario_id=scenario_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return {"success": success}
    except Exception as e:
        print(f"❌ Error recording scenario view: {e}")
        raise HTTPException(status_code=500, detail="Failed to record view")
