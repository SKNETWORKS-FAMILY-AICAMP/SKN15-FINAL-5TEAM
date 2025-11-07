"""
공통 의존성 설정
- FastAPI Depends에서 사용하는 공통 객체를 생성한다.
- DependencyContainer를 통한 Repository Pattern 기반 DI 제공
"""

# ============================================================
# 🧩 공용 의존성 팩토리 — Repository Pattern 기반
# ============================================================
import os
from typing import Optional, Dict
from functools import lru_cache

# New: Repository Pattern 기반 의존성
from src.infrastructure.shared.dependency_container import (
    get_container,
    get_user_repository,
    get_session_repository,
    get_character_repository,
    get_memory_repository,
    get_conversation_repository,
    get_progression_repository,
    get_session_manager,
    get_cache_provider,
)

# Legacy: 하위 호환성을 위해 유지
from src.infrastructure.database.db_manager import DatabaseManager
from src.infrastructure.cache.cache_manager import create_cache_manager_from_env
from src.infrastructure.database.session_manager import HybridSessionManager

# from src.domain.workflow import create_workflow  # TODO: 워크플로우 재구성 후 활성화
from src.domain.services.orchestration.scenario_loader import scenario_loader
# from src.domain.services.image_manager import ImageManager  # TODO: 이미지 매니저 위치 확인 후 수정


# ============================================================
# 싱글톤 인스턴스 (Legacy - 하위 호환성)
# ============================================================
_db_manager: Optional[DatabaseManager] = None
_cache_manager = None
_hybrid_session_manager: Optional[HybridSessionManager] = None
_workflow = None
_image_manager = None  # TODO: ImageManager 타입 힌트 재활성화


# ============================================================
# DEPRECATED: Legacy Database Manager (하위 호환성용)
# 새 코드에서는 get_user_repository(), get_session_repository() 등 사용
# ============================================================
def get_db_manager() -> DatabaseManager:
    """
    ⚠️  DEPRECATED: DatabaseManager 싱글톤 (Legacy 지원용)

    새 코드에서는 Repository Pattern을 사용하세요:
    - get_user_repository()
    - get_session_repository()
    - get_conversation_repository()
    - get_memory_repository()
    - get_progression_repository()
    - get_character_repository()
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
# Workflow (TODO: 재구성 필요)
# ============================================================
def get_workflow():
    """
    LangGraph Workflow 싱글톤 인스턴스 반환

    TODO: workflow가 Domain layer로 이동 후 경로 수정 필요
    """
    global _workflow
    if _workflow is None:
        # _workflow = create_workflow()  # TODO: 재활성화
        raise NotImplementedError("Workflow는 Domain layer 재구성 중입니다")
    return _workflow


# ============================================================
# Scenario Loader
# ============================================================
@lru_cache(maxsize=1)
def get_scenario_loader():
    """
    ScenarioLoader 싱글톤 인스턴스 반환
    """
    return scenario_loader


# ============================================================
# Image Manager (TODO: 재구성 필요)
# ============================================================
def get_image_manager():
    """
    ImageManager 싱글톤 인스턴스 반환

    TODO: ImageManager 위치 확인 및 경로 수정 필요
    """
    global _image_manager
    if _image_manager is None:
        # _image_manager = ImageManager()  # TODO: 재활성화
        raise NotImplementedError("ImageManager는 재구성 중입니다")
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
