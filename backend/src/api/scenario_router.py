"""
Scenario API Router

시나리오 관련 Public 엔드포인트를 관리합니다:
- 시나리오 목록 조회
- 시나리오 상세 정보 조회
- 시나리오 조회 기록
- 시나리오 댓글 CRUD
"""

from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from src.auth.dependencies import optional_auth, require_auth

# Router 생성
router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


# ============================================================
# Pydantic Models for Comments
# ============================================================

class CommentCreate(BaseModel):
    content: str
    parent_comment_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str


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


@router.post("/{scenario_id}/like")
async def toggle_scenario_like(
    scenario_id: str,
    current_user: Dict = Depends(require_auth)
):
    """
    시나리오 좋아요 토글 (로그인 필수)

    Args:
        scenario_id: 시나리오 ID
        current_user: 인증된 사용자 (필수)

    Returns:
        {"liked": bool, "like_count": int}
    """
    user_id = current_user.get("user_id")

    try:
        result = db_manager.toggle_scenario_like(
            scenario_id=scenario_id,
            user_id=user_id
        )
        return result
    except Exception as e:
        print(f"❌ Error toggling scenario like: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{scenario_id}/like")
async def check_scenario_like(
    scenario_id: str,
    current_user: Dict = Depends(require_auth)
):
    """
    시나리오 좋아요 상태 확인 (로그인 필수)

    Args:
        scenario_id: 시나리오 ID
        current_user: 인증된 사용자 (필수)

    Returns:
        {"liked": bool}
    """
    user_id = current_user.get("user_id")

    try:
        liked = db_manager.check_scenario_like(
            scenario_id=scenario_id,
            user_id=user_id
        )
        return {"liked": liked}
    except Exception as e:
        print(f"❌ Error checking scenario like: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Comment Endpoints
# ============================================================

@router.get("/{scenario_id}/comments")
async def get_comments(
    scenario_id: str,
    sort_by: str = "recent",  # 'recent' or 'popular'
    limit: int = 50,
    offset: int = 0,
    current_user: Optional[Dict] = Depends(optional_auth)
):
    """
    시나리오 댓글 목록 조회 (Public API - 인증 선택적)

    Args:
        scenario_id: 시나리오 ID
        sort_by: 정렬 기준 ('recent' 또는 'popular')
        limit: 조회 개수
        offset: 오프셋
        current_user: 인증된 사용자 (선택적)

    Returns:
        댓글 목록
    """
    user_id = current_user.get("user_id") if current_user else None

    try:
        comments = db_manager.get_scenario_comments(
            scenario_id=scenario_id,
            sort_by=sort_by,
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        return comments
    except Exception as e:
        print(f"❌ Error getting comments: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comments")


@router.get("/{scenario_id}/comments/{comment_id}/replies")
async def get_comment_replies(
    scenario_id: str,
    comment_id: int,
    current_user: Optional[Dict] = Depends(optional_auth)
):
    """
    대댓글 목록 조회 (Public API - 인증 선택적)

    Args:
        scenario_id: 시나리오 ID (URL 일관성을 위해 포함)
        comment_id: 부모 댓글 ID
        current_user: 인증된 사용자 (선택적)

    Returns:
        대댓글 목록
    """
    user_id = current_user.get("user_id") if current_user else None

    try:
        replies = db_manager.get_comment_replies(
            parent_comment_id=comment_id,
            user_id=user_id
        )
        return replies
    except Exception as e:
        print(f"❌ Error getting replies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get replies")


@router.post("/{scenario_id}/comments")
async def create_comment(
    scenario_id: str,
    comment_data: CommentCreate,
    current_user: Dict = Depends(require_auth)
):
    """
    댓글 작성 (로그인 필수)

    Args:
        scenario_id: 시나리오 ID
        comment_data: 댓글 내용
        current_user: 인증된 사용자 (필수)

    Returns:
        생성된 댓글 정보
    """
    user_id = current_user.get("user_id")

    try:
        comment = db_manager.create_comment(
            scenario_id=scenario_id,
            user_id=user_id,
            content=comment_data.content,
            parent_comment_id=comment_data.parent_comment_id
        )

        if not comment:
            raise HTTPException(status_code=500, detail="Failed to create comment")

        return comment
    except Exception as e:
        print(f"❌ Error creating comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{scenario_id}/comments/{comment_id}")
async def update_comment(
    scenario_id: str,
    comment_id: int,
    comment_data: CommentUpdate,
    current_user: Dict = Depends(require_auth)
):
    """
    댓글 수정 (로그인 필수, 본인만 가능)

    Args:
        scenario_id: 시나리오 ID (URL 일관성을 위해 포함)
        comment_id: 댓글 ID
        comment_data: 수정할 내용
        current_user: 인증된 사용자 (필수)

    Returns:
        성공 여부
    """
    user_id = current_user.get("user_id")

    try:
        success = db_manager.update_comment(
            comment_id=comment_id,
            user_id=user_id,
            content=comment_data.content
        )

        if not success:
            raise HTTPException(
                status_code=403,
                detail="Comment not found or you are not the owner"
            )

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{scenario_id}/comments/{comment_id}")
async def delete_comment(
    scenario_id: str,
    comment_id: int,
    current_user: Dict = Depends(require_auth)
):
    """
    댓글 삭제 (로그인 필수, 본인만 가능)

    Args:
        scenario_id: 시나리오 ID (URL 일관성을 위해 포함)
        comment_id: 댓글 ID
        current_user: 인증된 사용자 (필수)

    Returns:
        성공 여부
    """
    user_id = current_user.get("user_id")

    try:
        success = db_manager.delete_comment(
            comment_id=comment_id,
            user_id=user_id
        )

        if not success:
            raise HTTPException(
                status_code=403,
                detail="Comment not found or you are not the owner"
            )

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{scenario_id}/comments/{comment_id}/like")
async def toggle_comment_like(
    scenario_id: str,
    comment_id: int,
    current_user: Dict = Depends(require_auth)
):
    """
    댓글 추천 토글 (로그인 필수)

    Args:
        scenario_id: 시나리오 ID (URL 일관성을 위해 포함)
        comment_id: 댓글 ID
        current_user: 인증된 사용자 (필수)

    Returns:
        {"liked": bool, "like_count": int}
    """
    user_id = current_user.get("user_id")

    try:
        result = db_manager.toggle_comment_like(
            comment_id=comment_id,
            user_id=user_id
        )
        return result
    except Exception as e:
        print(f"❌ Error toggling comment like: {e}")
        raise HTTPException(status_code=500, detail=str(e))
