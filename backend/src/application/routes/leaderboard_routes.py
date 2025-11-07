"""
리더보드 API
- 경험치 기준 사용자 순위 조회
"""

# ============================================================
# 🏆 리더보드 라우터 — 경험치 순위 조회
# ============================================================
from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import datetime

from ..schemas.api_models import LeaderboardResponse, LeaderboardEntry

from ..dependencies.api_deps import get_db_manager

from src.infrastructure.database.db_manager import DatabaseManager

router = APIRouter()

@router.get("/leaderboard", response_model=List[dict])
async def get_leaderboard(
    limit: int = Query(default=100, ge=1, le=500, description="조회할 사용자 수"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    경험치 기준 리더보드 조회 (공개 API)

    Args:
        limit: 조회할 사용자 수 (기본 100, 최대 500)

    Returns:
        리더보드 목록 (순위, 사용자 정보, 경험치, 레벨 등)
    """
    # 데이터베이스에서 리더보드 조회
    leaderboard = db.get_rank_leaderboard(limit)

    return leaderboard
