"""
Session Manager Adapter

기존 HybridSessionManager를 ISessionManager 인터페이스로 감싸는 어댑터
"""
from typing import Optional, Dict, Any

from src.core.interfaces.managers.session_manager import ISessionManager
from src.infrastructure.database.session_manager import HybridSessionManager


class SessionManagerAdapter(ISessionManager):
    """
    HybridSessionManager를 ISessionManager 인터페이스로 감싸는 어댑터

    기존 코드와의 호환성을 유지하면서 새 인터페이스를 제공
    """

    def __init__(self, hybrid_session_manager: HybridSessionManager):
        """
        Args:
            hybrid_session_manager: 기존 HybridSessionManager 인스턴스
        """
        self._manager = hybrid_session_manager

    def create_session(
        self,
        user_id: str,
        scenario_id: str,
        **kwargs
    ) -> str:
        """
        새 세션 생성

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            **kwargs: 추가 세션 속성

        Returns:
            생성된 세션 ID
        """
        # HybridSessionManager.load_or_create를 사용
        session_data = self._manager.load_or_create(
            session_id=kwargs.get("session_id"),  # UUID 생성은 내부에서
            scenario_id=scenario_id,
            user_name=kwargs.get("user_name"),
            create_if_missing=True
        )
        return session_data.get("session_id") if session_data else ""

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 정보 조회 (DB + Cache 하이브리드)

        Args:
            session_id: 세션 ID

        Returns:
            세션 정보 딕셔너리 또는 None
        """
        return self._manager.load_or_create(
            session_id=session_id,
            scenario_id="",  # load_or_create에서 기존 세션이면 scenario_id 무시
            create_if_missing=False
        )

    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        세션 정보 업데이트

        Args:
            session_id: 세션 ID
            updates: 업데이트할 필드

        Returns:
            성공 여부
        """
        try:
            # 기존 세션 조회
            session_data = self.get_session(session_id)
            if not session_data:
                return False

            # updates 적용
            session_data.update(updates)

            # 저장 (DB + Cache)
            self._manager.db.update_session_state(session_id, session_data)
            self._manager.cache.set_session(session_id, session_data)

            return True
        except Exception as e:
            print(f"Error updating session {session_id}: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        try:
            # Cache에서 삭제
            self._manager.cache.delete_session(session_id)

            # DB에서는 soft delete
            self._manager.db.update_session_state(
                session_id,
                {"is_active": False, "ended_at": "NOW()"}
            )

            return True
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 상태 조회 (GraphState)

        Args:
            session_id: 세션 ID

        Returns:
            GraphState 딕셔너리 또는 None
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return None

        # GraphState 추출 (session_data 내부에 포함)
        return session_data.get("state") or session_data

    def save_session_state(
        self,
        session_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        세션 상태 저장

        Args:
            session_id: 세션 ID
            state: GraphState 딕셔너리

        Returns:
            성공 여부
        """
        return self.update_session(session_id, {"state": state})

    def increment_turn_count(self, session_id: str) -> int:
        """
        세션 턴 카운트 증가

        Args:
            session_id: 세션 ID

        Returns:
            새로운 턴 카운트
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return 0

        new_turn_count = session_data.get("turn_count", 0) + 1

        self.update_session(session_id, {"turn_count": new_turn_count})

        return new_turn_count
