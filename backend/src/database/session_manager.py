"""
HybridSessionManager - 통합 세션 관리자
Redis (hot cache) + PostgreSQL (cold storage) 하이브리드 아키텍처
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from .db_manager import DatabaseManager
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class HybridSessionManager:
    """
    하이브리드 세션 관리자

    전략:
    - 읽기: Cache-first (Redis -> PostgreSQL fallback)
    - 쓰기: Write-through (Redis + PostgreSQL 동시)
    - TTL: Redis에만 적용 (자동 세션 만료)
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: CacheManager
    ):
        """
        Args:
            db_manager: DatabaseManager 인스턴스
            cache_manager: CacheManager 인스턴스
        """
        self.db = db_manager
        self.cache = cache_manager
        logger.info("HybridSessionManager initialized")

    # ========================================
    # 핵심 세션 관리
    # ========================================

    def load_or_create(
        self,
        session_id: str,
        scenario_id: str,
        user_name: Optional[str] = None,
        create_if_missing: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        세션 로드 (없으면 생성)

        Args:
            session_id: 세션 ID (UUID 문자열)
            scenario_id: 시나리오 ID
            user_name: 사용자 이름
            create_if_missing: 없으면 새로 생성할지 여부

        Returns:
            세션 데이터 또는 None
        """
        # 1. 캐시에서 조회 (Cache-first)
        session = self.cache.get_session(session_id)
        if session:
            logger.debug(f"Session loaded from cache: {session_id}")
            return session

        # 2. DB에서 조회
        session = self.db.load_session(session_id)
        if session:
            logger.debug(f"Session loaded from DB: {session_id}")
            # 캐시에 저장 (warming)
            self.cache.set_session(session_id, session)
            return session

        # 3. 없으면 새로 생성
        if create_if_missing:
            logger.info(f"Creating new session: {session_id}")
            new_session = {
                "session_id": session_id,
                "scenario_id": scenario_id,
                "user_name": user_name,
                "current_stage": None,
                "turn_count": 0,
                "stage_turn": 0,
                "final_ending": None,
                "is_active": True
            }

            # DB와 캐시 모두에 저장
            if self.save(session_id, new_session):
                return new_session

        logger.warning(f"Session not found and creation disabled: {session_id}")
        return None

    def save(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        세션 저장 (Write-through)

        Args:
            session_id: 세션 ID
            session_data: 세션 데이터
            ttl: 캐시 TTL (None이면 기본값 사용)

        Returns:
            성공 여부
        """
        # 1. DB 저장 (영구 저장)
        db_success = self.db.save_session(session_data)

        # 2. 캐시 저장 (빠른 접근)
        cache_success = self.cache.set_session(session_id, session_data, ttl)

        success = db_success and cache_success
        if success:
            logger.debug(f"Session saved to DB and cache: {session_id}")
        else:
            logger.error(
                f"Session save failed - DB: {db_success}, Cache: {cache_success}"
            )

        return success

    def update(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        세션 부분 업데이트

        Args:
            session_id: 세션 ID
            updates: 업데이트할 필드 맵

        Returns:
            성공 여부
        """
        # 1. DB 업데이트
        db_success = self.db.update_session(session_id, updates)

        # 2. 캐시 무효화 (다음 조회 시 DB에서 새로 로드)
        self.cache.delete_session(session_id)

        if db_success:
            logger.debug(f"Session updated and cache invalidated: {session_id}")
        else:
            logger.error(f"Session update failed: {session_id}")

        return db_success

    def delete(self, session_id: str) -> bool:
        """
        세션 삭제 (soft delete - is_active = false)

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        # DB: is_active = false
        db_success = self.db.update_session(
            session_id,
            {"is_active": False}
        )

        # 캐시에서 제거
        cache_success = self.cache.delete_session(session_id)

        success = db_success and cache_success
        if success:
            logger.info(f"Session deleted: {session_id}")
        else:
            logger.error(
                f"Session delete failed - DB: {db_success}, Cache: {cache_success}"
            )

        return success

    # ========================================
    # 사용자 입력
    # ========================================

    def save_user_input(
        self,
        session_id: str,
        turn_number: int,
        user_input: str
    ) -> bool:
        """사용자 입력 저장"""
        return self.db.save_user_input(session_id, turn_number, user_input)

    def load_user_inputs(
        self,
        session_id: str,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """최근 사용자 입력 로드"""
        return self.db.load_user_inputs(session_id, limit)

    # ========================================
    # 대화 기록
    # ========================================

    def save_dialogues(
        self,
        session_id: str,
        turn_number: int,
        dialogues: list[Dict[str, Any]]
    ) -> bool:
        """대화 목록 저장"""
        return self.db.save_dialogues(session_id, turn_number, dialogues)

    def load_dialogues(
        self,
        session_id: str,
        turn_number: Optional[int] = None,
        limit: int = 50
    ) -> list[Dict[str, Any]]:
        """대화 로드"""
        return self.db.load_dialogues(session_id, turn_number, limit)

    # ========================================
    # 친밀도 기록
    # ========================================

    def save_affinity(
        self,
        session_id: str,
        turn_number: int,
        character_name: str,
        affinity_score: int,
        change_amount: Optional[int] = None
    ) -> bool:
        """친밀도 기록 저장"""
        return self.db.save_affinity(
            session_id,
            turn_number,
            character_name,
            affinity_score,
            change_amount
        )

    def load_latest_affinity(self, session_id: str) -> Dict[str, int]:
        """최신 친밀도 맵 로드"""
        return self.db.load_latest_affinity(session_id)

    # ========================================
    # 스냅샷 (GraphState 복구)
    # ========================================

    def save_snapshot(
        self,
        session_id: str,
        turn_number: int,
        state_json: Dict[str, Any]
    ) -> bool:
        """GraphState 스냅샷 저장"""
        return self.db.save_snapshot(session_id, turn_number, state_json)

    def load_latest_snapshot(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """최신 스냅샷 로드 (복구용)"""
        return self.db.load_latest_snapshot(session_id)

    # ========================================
    # 스테이지 진행
    # ========================================

    def save_stage_entry(
        self,
        session_id: str,
        stage_id: str,
        stage_order: int
    ) -> bool:
        """스테이지 진입 기록"""
        return self.db.save_stage_entry(session_id, stage_id, stage_order)

    def update_stage_exit(self, session_id: str, stage_id: str) -> bool:
        """스테이지 종료 기록"""
        return self.db.update_stage_exit(session_id, stage_id)

    # ========================================
    # 게임 이벤트
    # ========================================

    def save_game_event(
        self,
        session_id: str,
        turn_number: int,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """게임 이벤트 저장"""
        return self.db.save_game_event(
            session_id,
            turn_number,
            event_type,
            event_data
        )

    # ========================================
    # 로그 (LogDB)
    # ========================================

    def save_log(
        self,
        log_level: str,
        message: str,
        session_id: Optional[str] = None,
        stage_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> bool:
        """구조화된 로그 저장"""
        return self.db.save_log(
            log_level,
            message,
            session_id,
            stage_name,
            agent_name,
            context_data,
            duration_ms
        )

    def save_error_log(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        session_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """에러 로그 저장"""
        return self.db.save_error_log(
            error_type,
            error_message,
            stack_trace,
            session_id,
            context_data
        )

    def save_performance_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> bool:
        """성능 메트릭 저장"""
        return self.db.save_performance_metric(
            metric_name,
            metric_value,
            metric_unit,
            tags
        )

    # ========================================
    # 통계 및 유틸리티
    # ========================================

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        return self.cache.get_stats()

    def reset_cache_stats(self):
        """캐시 통계 초기화"""
        self.cache.reset_stats()

    def extend_session_ttl(self, session_id: str, additional_seconds: int) -> bool:
        """세션 TTL 연장 (활성 사용자 유지)"""
        return self.cache.extend_ttl(session_id, additional_seconds)

    def health_check(self) -> Dict[str, bool]:
        """
        시스템 헬스 체크

        Returns:
            {"db": bool, "cache": bool}
        """
        return {
            "db": self._check_db_health(),
            "cache": self.cache.ping()
        }

    def _check_db_health(self) -> bool:
        """DB 연결 확인"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"DB health check failed: {e}")
            return False

    def close(self):
        """모든 연결 종료"""
        self.db.close_all()
        self.cache.close()
        logger.info("HybridSessionManager closed")


# 환경변수 기반 싱글톤 인스턴스 생성 헬퍼
def create_hybrid_session_manager_from_env() -> HybridSessionManager:
    """환경변수에서 설정을 읽어 HybridSessionManager 인스턴스 생성"""
    from .db_manager import create_database_manager_from_env
    from .cache_manager import create_cache_manager_from_env

    db_manager = create_database_manager_from_env()
    cache_manager = create_cache_manager_from_env()

    return HybridSessionManager(db_manager, cache_manager)
