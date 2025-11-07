"""
Progression Repository Interface (Port)

게임 진행도 데이터 접근을 위한 포트 정의
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class IProgressionRepository(ABC):
    """진행도 리포지토리 인터페이스"""

    @abstractmethod
    def get_user_rank(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 랭크 조회

        Args:
            user_id: 사용자 ID

        Returns:
            랭크 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def update_user_rank(
        self,
        user_id: str,
        rank_data: Dict[str, Any]
    ) -> bool:
        """
        사용자 랭크 업데이트

        Args:
            user_id: 사용자 ID
            rank_data: 랭크 데이터

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            통계 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def update_user_stats(
        self,
        user_id: str,
        stats: Dict[str, Any]
    ) -> bool:
        """
        사용자 통계 업데이트

        Args:
            user_id: 사용자 ID
            stats: 통계 데이터

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def get_affinity_scores(
        self,
        session_id: str
    ) -> Dict[str, int]:
        """
        호감도 점수 조회

        Args:
            session_id: 세션 ID

        Returns:
            {캐릭터명: 호감도} 딕셔너리
        """
        pass

    @abstractmethod
    def update_affinity_score(
        self,
        session_id: str,
        character_name: str,
        score: int
    ) -> bool:
        """
        호감도 점수 업데이트

        Args:
            session_id: 세션 ID
            character_name: 캐릭터 이름
            score: 호감도 점수

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def get_mission_progress(
        self,
        session_id: str,
        mission_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        미션 진행도 조회

        Args:
            session_id: 세션 ID
            mission_id: 미션 ID

        Returns:
            미션 진행도 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def update_mission_progress(
        self,
        session_id: str,
        mission_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """
        미션 진행도 업데이트

        Args:
            session_id: 세션 ID
            mission_id: 미션 ID
            progress_data: 진행도 데이터

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def get_leaderboard(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        리더보드 조회

        Args:
            limit: 조회 개수
            offset: 오프셋

        Returns:
            리더보드 엔트리 리스트
        """
        pass

    # ============================================================
    # User Progression - Credits, XP, Equipment
    # ============================================================

    @abstractmethod
    def get_user_credits(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 크레딧(버블) 조회

        Args:
            user_id: 사용자 ID

        Returns:
            크레딧 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def consume_credits(
        self,
        user_id: str,
        amount: int,
        description: str
    ) -> bool:
        """
        사용자 크레딧(버블) 소비

        Args:
            user_id: 사용자 ID
            amount: 소비할 크레딧 양
            description: 소비 사유

        Returns:
            성공 여부 (잔액 부족 시 False)
        """
        pass

    @abstractmethod
    def get_user_progression(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 진행도 조회 (랭크, XP, 레벨, 장비 등 통합)

        Args:
            user_id: 사용자 ID

        Returns:
            진행도 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def get_user_equipment(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 장비 상태 조회

        Args:
            user_id: 사용자 ID

        Returns:
            장비 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def update_user_equipment(
        self,
        user_id: str,
        equipment_updates: Dict[str, str]
    ) -> bool:
        """
        사용자 장비 상태 업데이트

        Args:
            user_id: 사용자 ID
            equipment_updates: 업데이트할 장비 정보

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def award_experience(
        self,
        user_id: str,
        xp_amount: int,
        xp_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        사용자에게 경험치 지급

        Args:
            user_id: 사용자 ID
            xp_amount: 지급할 경험치
            xp_type: 경험치 유형
            description: 설명
            metadata: 메타데이터

        Returns:
            경험치 지급 결과 (레벨업 여부 등) 또는 None
        """
        pass

    @abstractmethod
    def get_xp_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        사용자 경험치 거래 내역 조회

        Args:
            user_id: 사용자 ID
            limit: 조회 개수
            offset: 오프셋

        Returns:
            경험치 거래 내역 리스트
        """
        pass

    @abstractmethod
    def initialize_user(self, user_id: str) -> bool:
        """
        사용자 진행도 초기화 (회원가입 시)

        Args:
            user_id: 사용자 ID

        Returns:
            성공 여부
        """
        pass

    # ============================================================
    # Scenario Progress
    # ============================================================

    @abstractmethod
    def get_scenarios_with_user_progress(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        사용자 진행도가 포함된 시나리오 목록 조회

        Args:
            user_id: 사용자 ID

        Returns:
            시나리오 목록 (진행도 포함)
        """
        pass

    @abstractmethod
    def toggle_scenario_like(
        self,
        user_id: str,
        scenario_id: str
    ) -> Dict[str, Any]:
        """
        시나리오 좋아요 토글

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            {"liked": bool, "total_likes": int}
        """
        pass

    @abstractmethod
    def get_user_scenario_progress(
        self,
        user_id: str,
        scenario_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        사용자의 특정 시나리오 진행도 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            진행도 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def update_user_scenario_progress(
        self,
        user_id: str,
        scenario_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """
        사용자의 시나리오 진행도 업데이트

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            progress_data: 업데이트할 진행도 데이터

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def record_scenario_view(
        self,
        scenario_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        시나리오 조회 기록 (조회수 증가)

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID (선택)
            ip_address: IP 주소 (선택)
            user_agent: User Agent (선택)

        Returns:
            성공 여부
        """
        pass

    # ============================================================
    # Mission & Game Events
    # ============================================================

    @abstractmethod
    def save_mission_record(
        self,
        session_id: str,
        mission_type: str,
        target_character: str,
        attempt_count: int,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        미션 기록 저장

        Args:
            session_id: 세션 ID
            mission_type: 미션 타입 (예: 'recruit')
            target_character: 대상 캐릭터
            attempt_count: 시도 횟수
            success: 성공 여부
            metadata: 메타데이터 (선택)

        Returns:
            생성된 레코드 ID 또는 None
        """
        pass

    @abstractmethod
    def save_game_event(
        self,
        session_id: str,
        turn_number: int,
        event_type: str,
        event_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        게임 이벤트 저장

        Args:
            session_id: 세션 ID
            turn_number: 턴 번호
            event_type: 이벤트 타입 (예: 'character_recruited')
            event_data: 이벤트 데이터
            metadata: 메타데이터 (선택)

        Returns:
            생성된 이벤트 ID 또는 None
        """
        pass
