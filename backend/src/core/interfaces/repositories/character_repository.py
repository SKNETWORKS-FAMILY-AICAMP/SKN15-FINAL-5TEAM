"""
Character Repository Interface (Port)

캐릭터 데이터 접근을 위한 포트 정의
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class ICharacterRepository(ABC):
    """캐릭터 리포지토리 인터페이스"""

    @abstractmethod
    def get_by_id(self, character_id: str) -> Optional[Dict[str, Any]]:
        """
        캐릭터 ID로 캐릭터 정보 조회

        Args:
            character_id: 캐릭터 ID

        Returns:
            캐릭터 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def get_by_name(self, character_name: str) -> Optional[Dict[str, Any]]:
        """
        캐릭터 이름으로 캐릭터 정보 조회

        Args:
            character_name: 캐릭터 이름

        Returns:
            캐릭터 정보 딕셔너리 또는 None
        """
        pass

    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        """
        모든 캐릭터 정보 조회

        Returns:
            캐릭터 정보 리스트
        """
        pass

    @abstractmethod
    def get_by_scenario(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        시나리오별 캐릭터 목록 조회

        Args:
            scenario_id: 시나리오 ID

        Returns:
            캐릭터 정보 리스트
        """
        pass
