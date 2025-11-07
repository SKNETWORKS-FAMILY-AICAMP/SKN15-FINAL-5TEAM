"""
세션 관리 API
- 세션 상태 조회
- 세션 삭제
- 마지막 세션 조회 (세션 복원용)
"""

# ============================================================
# 🗃️ 세션 라우터 — 세션 복원·조회·삭제
# ============================================================
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional

from ..schemas.api_models import SessionInfoResponse, MessageResponse

from ..dependencies.api_deps import get_session_manager, get_session_repository

from ..dependencies.auth_deps import require_auth

from src.core.interfaces.repositories.session_repository import ISessionRepository

from src.infrastructure.database.session_manager import HybridSessionManager

router = APIRouter()

# ============================================================
# ============================================================
class SessionManagerAdapter:
    """
    HybridSessionManager를 래핑하여 기대하는 인터페이스 제공
    """
    def __init__(self, hybrid_manager: HybridSessionManager):
        self._hybrid = hybrid_manager

    def get(self, session_id: str) -> Optional[Dict]:
        """세션 상태 조회"""
        return self._hybrid.load_or_create(session_id, scenario_id="", create_if_missing=False)

    def exists(self, session_id: str) -> bool:
        """세션 존재 여부 확인"""
        state = self.get(session_id)
        return state is not None

    def delete(self, session_id: str) -> None:
        """세션 삭제"""
        self._hybrid.delete_session(session_id)

# ============================================================
# 에이피아이 엔드포인트
# ============================================================

# 🔄 최근 세션 복원 엔드포인트

@router.get("/last", response_model=Dict)
async def get_user_last_session(
    scenario_id: Optional[str] = None,
    user: Dict = Depends(require_auth),
    session_repo: ISessionRepository = Depends(get_session_repository)
):
    """
    현재 로그인한 사용자의 마지막 세션 조회 (세션 복원용) - Repository Pattern

    Args:
        scenario_id: 특정 시나리오의 마지막 세션만 조회 (선택)

    Returns:
        마지막 세션 정보 (세션 ID, 턴 수, 대화 요약 등)
        또는 세션이 없으면 has_session: false
    """
    user_id = user.get("user_id")

    # Repository를 통해 마지막 세션 조회
    last_session = session_repo.get_user_last_session(user_id=user_id, scenario_id=scenario_id)

    if not last_session:
        return {
            "has_session": False,
            "message": "저장된 세션이 없습니다"
        }

    return {
        "has_session": True,
        "session_id": str(last_session.get("session_id")),
        "scenario_id": last_session.get("scenario_id"),
        "current_stage": last_session.get("current_stage"),
        "turn_count": last_session.get("turn_count", 0),
        "created_at": (
            last_session.get("created_at").isoformat()
            if last_session.get("created_at")
            else None
        ),
        "updated_at": (
            last_session.get("updated_at").isoformat()
            if last_session.get("updated_at")
            else None
        ),
        "conversation_summary": last_session.get("conversation_summary")  # 장기기억 요약
    }

@router.get("/{session_id}", response_model=SessionInfoResponse)
async def get_session(
    session_id: str,
    session_manager: HybridSessionManager = Depends(get_session_manager)
):
    """
    특정 세션의 현재 상태 조회

    Args:
        session_id: 세션 ID

    Returns:
        세션 정보 (시나리오 ID, 현재 스테이지, 턴 수 등)
    """
    adapter = SessionManagerAdapter(session_manager)
    state = adapter.get(session_id)

    if not state or "messages" not in state:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionInfoResponse(
        session_id=session_id,
        scenario_id=state.get("scenario_id", "unknown"),
        current_stage=state.get("current_stage"),
        turn_count=state.get("turn_count", 0),
        stage_turn=state.get("stage_turn", 0),
        is_active=True
    )

@router.delete("/{session_id}", response_model=MessageResponse)
async def delete_session(
    session_id: str,
    session_manager: HybridSessionManager = Depends(get_session_manager)
):
    """
    세션 강제 삭제 (테스트용)

    Args:
        session_id: 세션 ID

    Returns:
        삭제 성공 메시지
    """
    adapter = SessionManagerAdapter(session_manager)

    if adapter.exists(session_id):
        adapter.delete(session_id)
        return {
            "message": f"Session {session_id} deleted successfully",
            "status": "deleted"
        }

    raise HTTPException(status_code=404, detail="Session not found")
