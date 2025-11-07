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
