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
from src.infrastructure.cache.cache_manager import create_cache_manager_from_env
from src.infrastructure.database.session_manager import HybridSessionManager

from src.domain.workflow import create_workflow
from src.domain.services.orchestration.scenario_loader import scenario_loader
# from src.domain.services.image_manager import ImageManager  # TODO: 이미지 매니저 위치 확인 후 수정


# ============================================================
# 싱글톤 인스턴스
# ============================================================
_cache_manager = None
_hybrid_session_manager: Optional[HybridSessionManager] = None
_workflow = None
_image_manager = None  # TODO: ImageManager 타입 힌트 재활성화


# ============================================================
# Cache Manager
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
# 하이브리드 Session Manager
# ============================================================
def get_session_manager() -> HybridSessionManager:
    """
    HybridSessionManager 싱글톤 인스턴스 반환
    (PostgreSQL + Redis 하이브리드)

    Note: DI Container에서 이미 생성된 SessionManager를 사용합니다
    """
    global _hybrid_session_manager
    if _hybrid_session_manager is None:
        from src.infrastructure.shared.dependency_container import get_container
        container = get_container()
        # SessionManagerAdapter가 감싸고 있는 HybridSessionManager 추출
        session_mgr_adapter = container.session_manager
        _hybrid_session_manager = session_mgr_adapter._manager
    return _hybrid_session_manager


# ============================================================
# Workflow (TODO: 재구성 필요)
# ============================================================
def get_workflow():
    """
    LangGraph Workflow 싱글톤 인스턴스 반환

    Domain layer의 Workflow를 반환 (ParentAgent 래핑)
    """
    global _workflow
    if _workflow is None:
        _workflow = create_workflow(locale="ko")
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
    global _cache_manager, _hybrid_session_manager, _workflow, _image_manager

    if _hybrid_session_manager:
        # 필요 시 세션 정리 로직
        pass

    if _cache_manager:
        # 레디스 연결 종료
        try:
            _cache_manager.close()
        except Exception:
            pass

    # 인스턴스 초기화
    _cache_manager = None
    _hybrid_session_manager = None
    _workflow = None
    _image_manager = None
