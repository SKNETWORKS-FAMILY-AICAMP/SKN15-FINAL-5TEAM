"""
API 라우터 통합 모듈
- 모든 API 라우터를 여기서 import하여 api_server.py에서 사용
"""

from src.api import system
from src.api import auth
from src.api import users
from src.api import scenarios
from src.api import chat
from src.api import sessions
from src.api import memories
from src.api import leaderboard
from src.api import monitoring_api

# 라우터 객체 export
system_router = system.router
leaderboard_router = leaderboard.router
scenarios_router = scenarios.router
sessions_router = sessions.router
memories_router = memories.router
monitoring_router = monitoring_api.router
auth_router = auth.router
users_router = users.router
chat_router = chat.router

__all__ = [
    "system_router",
    "leaderboard_router",
    "scenarios_router",
    "sessions_router",
    "memories_router",
    "monitoring_router",
    "auth_router",
    "users_router",
    "chat_router",
]
