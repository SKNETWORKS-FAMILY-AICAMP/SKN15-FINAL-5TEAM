"""
Memory Repository Interface (Port)

대화 메모리 및 요약 데이터 접근을 위한 포트 정의
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class IMemoryRepository(ABC):
    """메모리 리포지토리 인터페이스"""

    @abstractmethod
    def get_conversation_summary(
        self,
        session_id: str,
        character_name: Optional[str] = None
    ) -> Optional[str]:
        """
        세션의 대화 요약 조회

        Args:
            session_id: 세션 ID
            character_name: 캐릭터 이름 (선택)

        Returns:
            대화 요약 텍스트 또는 None
        """
        pass

    @abstractmethod
    def save_conversation_summary(
        self,
        session_id: str,
        summary: str,
        character_name: Optional[str] = None
    ) -> bool:
        """
        대화 요약 저장

        Args:
            session_id: 세션 ID
            summary: 요약 텍스트
            character_name: 캐릭터 이름 (선택)

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최근 대화 메시지 조회

        Args:
            session_id: 세션 ID
            limit: 조회할 메시지 개수

        Returns:
            메시지 리스트
        """
        pass

    @abstractmethod
    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        대화 메시지 저장

        Args:
            session_id: 세션 ID
            role: 메시지 역할 (user/assistant/system)
            content: 메시지 내용
            metadata: 메타데이터 (선택)

        Returns:
            메시지 ID
        """
        pass

    @abstractmethod
    def extract_key_memories(
        self,
        session_id: str,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        중요한 기억 추출

        Args:
            session_id: 세션 ID
            threshold: 중요도 임계값

        Returns:
            핵심 기억 리스트
        """
        pass

    # ============================================================
    # User Long-term Memories (장기 기억)
    # ============================================================

    @abstractmethod
    def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        사용자의 장기 기억 목록 조회

        Args:
            user_id: 사용자 ID
            memory_type: 기억 타입 필터 (선택)
            limit: 반환할 최대 개수

        Returns:
            메모리 목록
        """
        pass

    @abstractmethod
    def get_memory_by_key(
        self,
        user_id: str,
        memory_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        특정 키로 기억 조회

        Args:
            user_id: 사용자 ID
            memory_key: 기억 키

        Returns:
            메모리 객체 또는 None
        """
        pass

    @abstractmethod
    def create_or_update_memory(
        self,
        user_id: str,
        memory_key: str,
        memory_value: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[int]:
        """
        새로운 기억 생성 또는 업데이트 (upsert)

        Args:
            user_id: 사용자 ID
            memory_key: 기억 키
            memory_value: 기억 값
            memory_type: 기억 타입
            importance: 중요도 (0.0-1.0)
            tags: 태그 리스트
            context: 컨텍스트 정보
            confidence: 신뢰도 (0.0-1.0)
            embedding: 벡터 임베딩

        Returns:
            메모리 ID 또는 None
        """
        pass

    @abstractmethod
    def delete_memory(
        self,
        user_id: str,
        memory_key: str
    ) -> bool:
        """
        기억 삭제 (소프트 삭제)

        Args:
            user_id: 사용자 ID
            memory_key: 삭제할 기억 키

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def search_memories_by_similarity(
        self,
        user_id: str,
        query_embedding: List[float],
        limit: int = 5,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        의미 기반 기억 검색 (Vector Similarity Search)

        Args:
            user_id: 사용자 ID
            query_embedding: 검색 쿼리의 벡터 임베딩
            limit: 반환할 최대 개수
            min_importance: 최소 중요도

        Returns:
            유사도순으로 정렬된 메모리 목록
        """
        pass

    @abstractmethod
    def get_user_memory_context(self, user_id: str) -> Dict[str, Any]:
        """
        새 세션 시작 시 사용할 사용자 기억 컨텍스트 생성

        Args:
            user_id: 사용자 ID

        Returns:
            Dict: 타입별로 정리된 기억 컨텍스트
            {
                "relationships": [...],
                "preferences": [...],
                "story_progress": [...],
                "facts": [...]
            }
        """
        pass
