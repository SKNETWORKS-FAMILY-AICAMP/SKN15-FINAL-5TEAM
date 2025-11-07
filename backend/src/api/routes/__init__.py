"""
라우터 패키지 초기화.

서버 초기화 단계에서 import 경로를 단순화하기 위해
각 서브 모듈을 재노출한다.
"""

# ============================================================
# 📚 라우터 패키지 초기화 — 서브 모듈 재노출
# ============================================================
from . import (
    auth_routes,
    chat_routes,
    leaderboard_routes,
    memories_routes,
    monitoring_routes,
    scenario_routes,
    session_routes,
    system_routes,
    user_routes,
)  # noqa: F401

__all__ = [
    "auth_routes",
    "chat_routes",
    "leaderboard_routes",
    "memories_routes",
    "monitoring_routes",
    "scenario_routes",
    "session_routes",
    "system_routes",
    "user_routes",
]
