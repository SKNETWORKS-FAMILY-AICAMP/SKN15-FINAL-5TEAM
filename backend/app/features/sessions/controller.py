"""
Sessions Controller
세션 목록 및 관리 엔드포인트
Layer 1: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.logging import get_controller_logger
from app.shared.exceptions import BusinessException
from app.core.auth import get_current_user_id

from .usecase import SessionUseCase
from .schemas import (
    SessionListResponse,
    SessionListItemResponse,
    SessionDetailResponse,
    SessionCreateRequest,
    SessionCreateResponse,
)

logger = get_controller_logger("Session")

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ============================================================
# 의존성 주입
# ============================================================

def get_session_usecase(db: AsyncSession = Depends(get_db)) -> SessionUseCase:
    """SessionUseCase 의존성"""
    return SessionUseCase(db)


# ============================================================
# 세션 엔드포인트
# ============================================================

@router.get("", response_model=SessionListResponse)
async def list_user_sessions(
    limit: int = Query(20, ge=1, le=100, description="페이징 크기"),
    offset: int = Query(0, ge=0, description="페이징 오프셋"),
    scenario_id: Optional[str] = Query(None, description="시나리오 ID 필터"),
    user_id: str = Depends(get_current_user_id),
    usecase: SessionUseCase = Depends(get_session_usecase)
):
    """
    사용자 세션 목록 조회

    Controller → UseCase → Repository
    """
    logger.info("list_user_sessions", "Listing user sessions",
               user_id=user_id, limit=limit)

    try:
        sessions = await usecase.list_user_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset,
            scenario_id=scenario_id
        )

        return SessionListResponse(
            sessions=[SessionListItemResponse(**s) for s in sessions],
            total=len(sessions)
        )

    except BusinessException as e:
        logger.error("list_user_sessions", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("list_user_sessions", f"Unexpected error: {e}", exc=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/last")
async def get_last_session_endpoint(
    scenario_id: Optional[str] = Query(None, description="시나리오 ID 필터"),
    user_id: str = Depends(get_current_user_id),
    usecase: SessionUseCase = Depends(get_session_usecase)
):
    """
    사용자의 마지막 세션 조회

    Controller → UseCase → Repository
    """
    logger.info("get_last_session", "Getting last session",
               user_id=user_id, scenario_id=scenario_id)

    try:
        session = await usecase.get_last_session(user_id, scenario_id)

        if not session:
            return {"has_session": False}

        return {
            "has_session": True,
            "session_id": session["session_id"],
            "scenario_id": session["scenario_id"],
            "current_stage": session.get("current_stage"),
            "turn_count": session.get("turn_count", 0),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "conversation_summary": session.get("conversation_summary")
        }

    except BusinessException as e:
        logger.error("get_last_session", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("get_last_session", f"Unexpected error: {e}", exc=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    usecase: SessionUseCase = Depends(get_session_usecase)
):
    """
    세션 상세 조회

    Controller → UseCase → Repository
    """
    logger.info("get_session_detail", "Getting session detail",
               session_id=session_id, user_id=user_id)

    try:
        session = await usecase.get_session_detail(
            session_id=session_id,
            user_id=user_id
        )

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionDetailResponse(**session)

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("get_session_detail", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("get_session_detail", f"Unexpected error: {e}", exc=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    usecase: SessionUseCase = Depends(get_session_usecase)
):
    """
    세션 삭제

    Controller → UseCase → Repository
    """
    logger.info("delete_session", "Deleting session",
               session_id=session_id, user_id=user_id)

    try:
        success = await usecase.delete_session(
            session_id=session_id,
            user_id=user_id
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail="Session not found or permission denied"
            )

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except BusinessException as e:
        logger.error("delete_session", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("delete_session", f"Unexpected error: {e}", exc=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=SessionCreateResponse)
async def create_session(
    request: SessionCreateRequest,
    user_id: str = Depends(get_current_user_id),
    usecase: SessionUseCase = Depends(get_session_usecase)
):
    """
    새 세션 생성

    Controller → UseCase → Repository
    """
    logger.info("create_session", "Creating session",
               user_id=user_id, scenario_id=request.scenario_id)

    try:
        session = await usecase.create_session(
            user_id=user_id,
            scenario_id=request.scenario_id
        )

        return SessionCreateResponse(**session)

    except BusinessException as e:
        logger.error("create_session", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("create_session", f"Unexpected error: {e}", exc=e)
        raise HTTPException(status_code=500, detail="Internal server error")
