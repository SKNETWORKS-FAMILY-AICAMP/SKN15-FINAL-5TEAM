"""
Core Interfaces - Port Definitions

의존성 역전 원칙(Dependency Inversion Principle)을 위한 인터페이스 정의.
Infrastructure 계층은 이 인터페이스를 구현하는 Adapter를 제공함.
"""

from .repositories.user_repository import IUserRepository
from .repositories.session_repository import ISessionRepository
from .providers.llm_provider import ILLMProvider
from .providers.cache_provider import ICacheProvider

__all__ = [
    # Repositories
    "IUserRepository",
    "ISessionRepository",
    # Providers
    "ILLMProvider",
    "ICacheProvider",
]
