"""
============================================================
📦 Session Router — 세션 관리 엔드포인트
============================================================
세션 조회, 삭제, 마지막 세션 가져오기 등의 기능을 제공합니다.
"""
from __future__ import annotations

from typing import Optional, Dict

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.auth.dependencies import require_auth

# ============================================================
# Router 및 전역 변수
# ============================================================
router = APIRouter(prefix="/api", tags=["session"])

# 의존성 주입용 전역 변수
_session_manager = None
_db_manager = None


def set_dependencies(session_manager, db_manager):
    """
    의존성 주입 함수

    Args:
        session_manager: HybridSessionManager 인스턴스
        db_manager: DatabaseManager 인스턴스
    """
    global _session_manager, _db_manager
    _session_manager = session_manager
    _db_manager = db_manager


# ============================================================
# Pydantic Models
# ============================================================
class SessionInfoResponse(BaseModel):
    session_id: str
    scenario_id: str
    current_stage: Optional[str] = None
    turn_count: int = 0
    affinity_scores: Dict[str, int] = {}


# ============================================================
# Session 엔드포인트
# ============================================================
# ⚠️ 중요: /session/last를 /session/{session_id} 보다 먼저 정의
# FastAPI는 경로를 순서대로 매칭하므로, 구체적인 경로를 먼저 배치해야 함

@router.get("/session/last")
async def get_user_last_session(
    scenario_id: Optional[str] = None,
    current_user: Dict = Depends(require_auth)
):
    """
    현재 로그인한 사용자의 마지막 세션 조회 (세션 복원용)

    Query Parameters:
        scenario_id (Optional[str]): 특정 시나리오의 마지막 세션만 조회 (미지정 시 모든 시나리오 중 최신)

    Returns:
        {
            "session_id": "...",
            "scenario_id": "...",
            "current_stage": "...",
            "turn_count": 5,
            "created_at": "...",
            "updated_at": "...",
            "conversation_summary": "...",
            "has_session": true
        }
    """
    user_id = current_user.get('user_id')

    # 데이터베이스에서 마지막 세션 조회
    last_session = _db_manager.get_user_last_session(user_id=user_id, scenario_id=scenario_id)

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
        "created_at": last_session.get("created_at").isoformat() if last_session.get("created_at") else None,
        "updated_at": last_session.get("updated_at").isoformat() if last_session.get("updated_at") else None,
        "conversation_summary": last_session.get("conversation_summary")
    }


@router.get("/sessions/recent")
async def get_recent_sessions(
    limit: int = 4,
    current_user: Dict = Depends(require_auth)
):
    """
    현재 로그인한 사용자의 최근 세션 목록 조회 (마지막 대화 포함)

    Query Parameters:
        limit (int): 조회할 세션 개수 (기본값: 4, 최대: 20)

    Returns:
        [
            {
                "session_id": "...",
                "scenario_id": "...",
                "scenario_title": "...",
                "scenario_thumbnail": "...",
                "current_stage": "...",
                "turn_count": 5,
                "created_at": "...",
                "updated_at": "...",
                "conversation_summary": "...",
                "last_message_speaker": "...",
                "last_message_content": "..."
            },
            ...
        ]
    """
    user_id = current_user.get('user_id')

    # limit 최대값 제한
    limit = min(limit, 20)

    # 데이터베이스에서 최근 세션 목록 조회
    recent_sessions = _db_manager.get_user_recent_sessions(user_id=user_id, limit=limit)

    # ISO 형식으로 날짜 변환
    for session in recent_sessions:
        if session.get("created_at"):
            session["created_at"] = session["created_at"].isoformat()
        if session.get("updated_at"):
            session["updated_at"] = session["updated_at"].isoformat()
        # session_id를 문자열로 변환
        session["session_id"] = str(session["session_id"])

    return recent_sessions


@router.get("/session/{session_id}", response_model=SessionInfoResponse)
async def get_session(session_id: str):
    """특정 세션의 현재 상태(스테이지, 친밀도 등) 반환"""
    state = _session_manager.get(session_id)
    if not state or "messages" not in state:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionInfoResponse(
        session_id=session_id,
        scenario_id=state.get("scenario_id", "unknown"),
        current_stage=state.get("current_stage"),
        turn_count=state.get("turn_count", 0),
        affinity_scores=state.get("affinity_scores", {}),
    )

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """세션 강제 삭제"""
    if _session_manager.exists(session_id):
        _session_manager.delete(session_id)
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


__all__ = ["router", "set_dependencies"]
