"""
Admin Controller
관리자 전용 엔드포인트
Layer 1: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_controller_logger
from app.shared.exceptions import BusinessException

from .usecase import AdminUseCase
from .schemas import (
    DialogueSessionListResponse,
    DialogueSessionInfoResponse,
    DialogueTurnListResponse,
    DialogueTurnResponse,
)

logger = get_controller_logger("Admin")

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================
# 의존성 주입
# ============================================================

def get_admin_usecase(db: AsyncSession = Depends(get_db)) -> AdminUseCase:
    """AdminUseCase 의존성"""
    return AdminUseCase(db)


# ============================================================
# 관리자 엔드포인트
# ============================================================

@router.get("/dialogues", response_model=DialogueSessionListResponse)
async def list_dialogue_sessions(
    limit: int = Query(100, ge=1, le=500, description="페이징 크기"),
    offset: int = Query(0, ge=0, description="페이징 오프셋"),
    usecase: AdminUseCase = Depends(get_admin_usecase)
):
    """
    모든 대화 세션 목록 조회 (관리자 전용)

    Controller → UseCase → Repository
    """
    logger.info("list_dialogue_sessions", "Listing all dialogue sessions",
               limit=limit, offset=offset)

    try:
        result = await usecase.list_dialogue_sessions(
            limit=limit,
            offset=offset
        )

        return DialogueSessionListResponse(
            sessions=[DialogueSessionInfoResponse(**session) for session in result["sessions"]],
            total=result["total"]
        )

    except BusinessException as e:
        logger.error("list_dialogue_sessions", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("list_dialogue_sessions", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dialogues/{session_id}", response_model=DialogueTurnListResponse)
async def get_dialogue_session_detail(
    session_id: str,
    usecase: AdminUseCase = Depends(get_admin_usecase)
):
    """
    특정 세션의 대화 내역 상세 조회 (관리자 전용)

    Controller → UseCase → Repository
    """
    logger.info("get_dialogue_session_detail", f"Getting session detail: {session_id}")

    try:
        result = await usecase.get_dialogue_session_detail(session_id)

        return DialogueTurnListResponse(
            session_id=result["session_id"],
            turns=[DialogueTurnResponse(**turn) for turn in result["turns"]],
            total=result["total"]
        )

    except BusinessException as e:
        logger.error("get_dialogue_session_detail", f"Business error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("get_dialogue_session_detail", f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
