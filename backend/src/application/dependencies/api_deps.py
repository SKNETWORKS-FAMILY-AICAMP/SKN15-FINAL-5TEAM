"""
공통 의존성 설정
- FastAPI Depends에서 사용하는 공통 객체를 생성한다.
"""

# ============================================================
# 🧩 공용 의존성 팩토리 — 데이터베이스·캐시·워크플로우 싱글톤 관리
# ============================================================
import os
from typing import Optional, Dict
from functools import lru_cache

from src.infrastructure.database.db_manager import DatabaseManager
from src.infrastructure.cache.cache_manager import create_cache_manager_from_env
from src.infrastructure.database.session_manager import HybridSessionManager
from src.core.workflow import create_workflow
from src.utils.scenario_loader import scenario_loader
from src.tools.image_manager import ImageManager


# ============================================================
# 싱글톤 인스턴스 (전역 변수)
# ============================================================
_db_manager: Optional[DatabaseManager] = None
_cache_manager = None
_hybrid_session_manager: Optional[HybridSessionManager] = None
_workflow = None
_image_manager: Optional[ImageManager] = None


# ============================================================
#  
# ============================================================
def get_db_manager() -> DatabaseManager:
    """
    DatabaseManager 싱글톤 인스턴스 반환
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


# ============================================================
# ============================================================
def get_cache_manager():
    """
    CacheManager 싱글톤 인스턴스 반환
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = create_cache_manager_from_env()
    return _cache_manager


# ============================================================
# 하이브리드  
# ============================================================
def get_session_manager() -> HybridSessionManager:
    """
    HybridSessionManager 싱글톤 인스턴스 반환
    (PostgreSQL + Redis 하이브리드)
    """
    global _hybrid_session_manager
    if _hybrid_session_manager is None:
        db = get_db_manager()
        cache = get_cache_manager()
        _hybrid_session_manager = HybridSessionManager(db_manager=db, cache_manager=cache)
    return _hybrid_session_manager


# ============================================================
#  
# ============================================================
def get_workflow():
    """
    LangGraph Workflow 싱글톤 인스턴스 반환
    """
    global _workflow
    if _workflow is None:
        _workflow = create_workflow()
    return _workflow


# ============================================================
#  
# ============================================================
@lru_cache(maxsize=1)
def get_scenario_loader():
    """
    ScenarioLoader 싱글톤 인스턴스 반환
    """
    return scenario_loader


# ============================================================
#  
# ============================================================
def get_image_manager() -> ImageManager:
    """
    ImageManager 싱글톤 인스턴스 반환
    """
    global _image_manager
    if _image_manager is None:
        _image_manager = ImageManager()
    return _image_manager


# ============================================================
# 시나리오 로드 헬퍼
# ============================================================
def load_scenario(scenario_id: str) -> Optional[Dict]:
    """
    시나리오 JSON 로드

    Args:
        scenario_id: 시나리오 ID (예: "train", "ending")

    Returns:
        시나리오 딕셔너리 또는 None
    """
    loader = get_scenario_loader()
    return loader.load_scenario(scenario_id)


# ============================================================
# 의존성 클린업 (앱 종료 시)
# ============================================================
def cleanup_dependencies():
    """
    모든 싱글톤 인스턴스 정리
    앱 종료 시 호출
    """
    global _db_manager, _cache_manager, _hybrid_session_manager, _workflow, _image_manager

    if _hybrid_session_manager:
        # 필요 시 세션 정리 로직
        pass

    if _cache_manager:
        # 레디스 연결 종료
        try:
            _cache_manager.close()
        except Exception:
            pass

    if _db_manager:
        # 데이터베이스 연결 종료
        try:
            _db_manager.close()
        except Exception:
            pass

    # 인스턴스 초기화
    _db_manager = None
    _cache_manager = None
    _hybrid_session_manager = None
    _workflow = None
    _image_manager = None
