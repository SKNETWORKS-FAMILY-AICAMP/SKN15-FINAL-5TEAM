"""
Scenarios Controller
시나리오 목록, 상세, 댓글, 좋아요 엔드포인트
Layer 1: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.logging import get_controller_logger
from app.shared.exceptions import BusinessException

from .usecase import ScenarioUseCase
from .schemas import (
    ScenarioListResponse,
    ScenarioDetailResponse,
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentResponse,
    CommentListResponse,
    LikeResponse,
)

logger = get_controller_logger("Scenario")

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


# ============================================================
# 의존성 주입
# ============================================================

def get_scenario_usecase(db: AsyncSession = Depends(get_db)) -> ScenarioUseCase:
    """ScenarioUseCase 의존성"""
    return ScenarioUseCase(db)


# TODO: 인증 의존성 (임시로 None)
async def get_current_user_id() -> Optional[str]:
    """현재 사용자 ID (임시)"""
    return None


# ============================================================
# 시나리오 엔드포인트
# ============================================================

@router.get("", response_model=ScenarioListResponse)
async def list_scenarios(
    limit: int = Query(20, ge=1, le=100, description="페이징 크기"),
    offset: int = Query(0, ge=0, description="페이징 오프셋"),
    user_id: Optional[str] = Depends(get_current_user_id),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    시나리오 목록 조회

    Controller → UseCase → Service + Repository
    """
    logger.info("list_scenarios", "Listing scenarios", limit=limit, offset=offset)

    try:
        scenarios = await usecase.list_scenarios(
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        return ScenarioListResponse(
            scenarios=scenarios,
            total=len(scenarios)
        )

    except BusinessException as e:
        logger.error("list_scenarios", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("list_scenarios", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{scenario_id}", response_model=ScenarioDetailResponse)
async def get_scenario_detail(
    scenario_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    시나리오 상세 조회

    Controller → UseCase → Service + Repository
    """
    logger.info("get_scenario_detail", "Getting scenario detail", scenario_id=scenario_id)

    try:
        scenario = await usecase.get_scenario_detail(
            scenario_id=scenario_id,
            user_id=user_id
        )

        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        return ScenarioDetailResponse(
            scenario_id=scenario.get("scenario_id", scenario_id),
            title=scenario.get("title", ""),
            description=scenario.get("description"),
            world_id=scenario.get("world_id"),
            like_count=scenario.get("like_count", 0),
            user_liked=scenario.get("user_liked", False),
            comment_count=scenario.get("comment_count", 0),
            metadata=scenario.get("metadata")
        )

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("get_scenario_detail", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_scenario_detail", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{scenario_id}/view")
async def record_scenario_view(
    scenario_id: str,
    request: Request,
    user_id: Optional[str] = Depends(get_current_user_id),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    시나리오 조회 기록 (Public API - 인증 선택적)

    Controller → UseCase → Repository
    """
    # IP 주소 및 User Agent 추출
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    logger.info("record_scenario_view", "Recording scenario view",
               scenario_id=scenario_id, user_id=user_id, ip_address=ip_address)

    try:
        success = await usecase.record_scenario_view(
            scenario_id=scenario_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"success": success}

    except BusinessException as e:
        logger.error("record_scenario_view", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("record_scenario_view", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Failed to record view")


@router.post("/{scenario_id}/like", response_model=LikeResponse)
async def toggle_scenario_like(
    scenario_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    시나리오 좋아요 토글

    Controller → UseCase → Repository
    """
    # 인증 체크 (임시)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    logger.info("toggle_scenario_like", "Toggling like", scenario_id=scenario_id, user_id=user_id)

    try:
        result = await usecase.toggle_like(
            scenario_id=scenario_id,
            user_id=user_id
        )

        return LikeResponse(
            is_liked=result["is_liked"],
            like_count=result["like_count"]
        )

    except BusinessException as e:
        logger.error("toggle_scenario_like", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("toggle_scenario_like", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{scenario_id}/like")
async def check_scenario_like(
    scenario_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    시나리오 좋아요 상태 확인 (로그인 필수)

    Controller → UseCase → Repository
    """
    # 인증 체크 (임시)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    logger.info("check_scenario_like", "Checking like status", scenario_id=scenario_id, user_id=user_id)

    try:
        liked = await usecase.check_scenario_like(
            scenario_id=scenario_id,
            user_id=user_id
        )

        return {"liked": liked}

    except BusinessException as e:
        logger.error("check_scenario_like", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("check_scenario_like", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 댓글 엔드포인트
# ============================================================

@router.get("/{scenario_id}/comments", response_model=CommentListResponse)
async def get_comments(
    scenario_id: str,
    sort_by: str = Query("created_at", regex="^(created_at|like_count)$", description="정렬 기준"),
    limit: int = Query(50, ge=1, le=100, description="페이징 크기"),
    offset: int = Query(0, ge=0, description="페이징 오프셋"),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    시나리오 댓글 목록 조회

    Controller → UseCase → Repository
    """
    logger.info("get_comments", "Getting comments", scenario_id=scenario_id, sort_by=sort_by)

    try:
        comments = await usecase.get_comments(
            scenario_id=scenario_id,
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )

        return CommentListResponse(
            comments=[CommentResponse(**c) for c in comments],
            total=len(comments)
        )

    except BusinessException as e:
        logger.error("get_comments", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_comments", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{scenario_id}/comments/{comment_id}/replies", response_model=CommentListResponse)
async def get_comment_replies(
    scenario_id: str,
    comment_id: int,
    limit: int = Query(20, ge=1, le=100, description="페이징 크기"),
    offset: int = Query(0, ge=0, description="페이징 오프셋"),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    대댓글 목록 조회 (Public API - 인증 선택적)

    Controller → UseCase → Repository

    Args:
        scenario_id: 시나리오 ID (URL 일관성을 위해 포함)
        comment_id: 부모 댓글 ID
    """
    logger.info("get_comment_replies", "Getting comment replies",
               scenario_id=scenario_id, comment_id=comment_id)

    try:
        replies = await usecase.get_comment_replies(
            parent_comment_id=comment_id,
            limit=limit,
            offset=offset
        )

        return CommentListResponse(
            comments=[CommentResponse(**r) for r in replies],
            total=len(replies)
        )

    except BusinessException as e:
        logger.error("get_comment_replies", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_comment_replies", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{scenario_id}/comments", response_model=CommentResponse)
async def create_comment(
    scenario_id: str,
    request: CommentCreateRequest,
    user_id: Optional[str] = Depends(get_current_user_id),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    댓글 작성

    Controller → UseCase → Repository
    """
    # 인증 체크 (임시)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    logger.info("create_comment", "Creating comment", scenario_id=scenario_id, user_id=user_id)

    try:
        comment = await usecase.create_comment(
            scenario_id=scenario_id,
            user_id=user_id,
            content=request.content,
            parent_comment_id=request.parent_comment_id
        )

        return CommentResponse(**comment)

    except ValueError as e:
        # 검증 에러 (예: 빈 댓글, 너무 긴 댓글)
        logger.warning("create_comment", f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        logger.error("create_comment", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("create_comment", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{scenario_id}/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    scenario_id: str,
    comment_id: int,
    request: CommentUpdateRequest,
    user_id: Optional[str] = Depends(get_current_user_id),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    댓글 수정

    Controller → UseCase → Repository
    """
    # 인증 체크 (임시)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    logger.info("update_comment", "Updating comment", comment_id=comment_id, user_id=user_id)

    try:
        comment = await usecase.update_comment(
            comment_id=comment_id,
            user_id=user_id,
            content=request.content
        )

        if not comment:
            raise HTTPException(
                status_code=404,
                detail="Comment not found or permission denied"
            )

        return CommentResponse(**comment)

    except HTTPException:
        raise
    except ValueError as e:
        # 검증 에러
        logger.warning("update_comment", f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        logger.error("update_comment", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("update_comment", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{scenario_id}/comments/{comment_id}")
async def delete_comment(
    scenario_id: str,
    comment_id: int,
    user_id: Optional[str] = Depends(get_current_user_id),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    댓글 삭제 (소프트 삭제)

    Controller → UseCase → Repository
    """
    # 인증 체크 (임시)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    logger.info("delete_comment", "Deleting comment", comment_id=comment_id, user_id=user_id)

    try:
        success = await usecase.delete_comment(
            comment_id=comment_id,
            user_id=user_id
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail="Comment not found or permission denied"
            )

        return {"message": "Comment deleted successfully"}

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("delete_comment", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("delete_comment", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{scenario_id}/comments/{comment_id}/like", response_model=LikeResponse)
async def toggle_comment_like(
    scenario_id: str,
    comment_id: int,
    user_id: Optional[str] = Depends(get_current_user_id),
    usecase: ScenarioUseCase = Depends(get_scenario_usecase)
):
    """
    댓글 추천 토글

    Controller → UseCase → Repository
    """
    # 인증 체크 (임시)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    logger.info("toggle_comment_like", "Toggling comment like", comment_id=comment_id, user_id=user_id)

    try:
        result = await usecase.toggle_comment_like(
            comment_id=comment_id,
            user_id=user_id
        )

        return LikeResponse(
            is_liked=result["is_liked"],
            like_count=result["like_count"]
        )

    except BusinessException as e:
        logger.error("toggle_comment_like", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("toggle_comment_like", "Unexpected error", e)
        raise HTTPException(status_code=500, detail="Internal server error")
