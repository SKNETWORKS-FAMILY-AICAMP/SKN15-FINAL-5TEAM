"""
리더보드 API - Repository Pattern 기반
- 경험치 기준 사용자 순위 조회
"""

# ============================================================
# 🏆 리더보드 라우터 — 경험치 순위 조회
# ============================================================
from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import datetime

from ..schemas.api_models import LeaderboardResponse, LeaderboardEntry
from ..dependencies.api_deps import get_progression_repository
from src.core.interfaces.repositories.progression_repository import IProgressionRepository

router = APIRouter()

@router.get("/leaderboard", response_model=List[dict])
async def get_leaderboard(
    limit: int = Query(default=100, ge=1, le=500, description="조회할 사용자 수"),
    progression_repo: IProgressionRepository = Depends(get_progression_repository)
):
    """
    경험치 기준 리더보드 조회 - Repository Pattern

    Args:
        limit: 조회할 사용자 수 (기본 100, 최대 500)

    Returns:
        리더보드 목록 (순위, 사용자 정보, 경험치, 레벨 등)
    """
    # Repository에서 리더보드 조회
    leaderboard = progression_repo.get_leaderboard(limit)

    return leaderboard
