"""
리더보드 API
- 경험치 기준 사용자 순위 조회
"""

from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import datetime

from src.api.models import LeaderboardResponse, LeaderboardEntry
from src.api.dependencies import get_db_manager
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
    # DB에서 리더보드 조회
    leaderboard = db.get_rank_leaderboard(limit)

    return leaderboard
