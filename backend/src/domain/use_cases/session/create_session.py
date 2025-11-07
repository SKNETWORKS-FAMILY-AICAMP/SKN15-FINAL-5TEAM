"""
Create Session Use Case

세션 생성 비즈니스 로직
"""
from dataclasses import dataclass
from typing import Optional

from src.core.interfaces.managers.session_manager import ISessionManager
from src.core.interfaces.repositories.user_repository import IUserRepository
from src.core.exceptions.domain_exceptions import EntityNotFoundError


@dataclass
class CreateSessionRequest:
    """세션 생성 요청 DTO"""
    user_id: str
    scenario_id: str
    user_name: Optional[str] = None


@dataclass
class CreateSessionResponse:
    """세션 생성 응답 DTO"""
    session_id: str
    user_id: str
    scenario_id: str
    turn_count: int


class CreateSessionUseCase:
    """
    세션 생성 Use Case

    책임:
    1. 사용자 존재 확인
    2. 세션 생성
    3. 초기 상태 설정
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        session_manager: ISessionManager
    ):
        """
        Args:
            user_repository: 사용자 리포지토리 (DI)
            session_manager: 세션 관리자 (DI)
        """
        self._user_repo = user_repository
        self._session_manager = session_manager

    def execute(self, request: CreateSessionRequest) -> CreateSessionResponse:
        """
        세션 생성 실행

        Args:
            request: 세션 생성 요청 DTO

        Returns:
            CreateSessionResponse

        Raises:
            EntityNotFoundError: 사용자 없음
        """
        # 1. 사용자 존재 확인
        user = self._user_repo.get_by_id(request.user_id)
        if not user:
            raise EntityNotFoundError(f"User {request.user_id} not found")

        # 2. 세션 생성
        session_id = self._session_manager.create_session(
            user_id=request.user_id,
            scenario_id=request.scenario_id,
            user_name=request.user_name or user.get('display_name', user['username'])
        )

        return CreateSessionResponse(
            session_id=session_id,
            user_id=request.user_id,
            scenario_id=request.scenario_id,
            turn_count=0
        )
