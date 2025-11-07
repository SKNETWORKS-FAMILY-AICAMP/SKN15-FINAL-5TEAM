"""
공유 FastAPI Depends 모음.

비즈니스 라우터는 여기서 제공하는 팩토리만 사용해 의존성을 주입하도록 통일한다.
"""

# ============================================================
# 4-layer 아키텍처 imports
# ============================================================
from .auth_deps import optional_auth, require_auth  # noqa: F401
from .api_deps import (  # noqa: F401
    get_cache_manager,
    get_db_manager,
    get_image_manager,
    get_session_manager,
    get_workflow,
)

__all__ = [
    "optional_auth",
    "require_auth",
    "get_cache_manager",
    "get_db_manager",
    "get_image_manager",
    "get_session_manager",
    "get_workflow",
]
