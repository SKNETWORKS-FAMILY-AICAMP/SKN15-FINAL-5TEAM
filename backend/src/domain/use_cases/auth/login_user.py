"""
Login User Use Case

사용자 로그인 비즈니스 로직
"""
from dataclasses import dataclass
from typing import Optional

from src.core.interfaces.repositories.user_repository import IUserRepository
from src.core.exceptions.domain_exceptions import AuthenticationError


@dataclass
class LoginUserRequest:
    """로그인 요청 DTO"""
    username: str
    password: str


@dataclass
class LoginUserResponse:
    """로그인 응답 DTO"""
    user_id: str
    username: str
    display_name: str
    email: Optional[str]


class LoginUserUseCase:
    """
    사용자 로그인 Use Case

    책임:
    1. 사용자 조회
    2. 비밀번호 검증
    3. 사용자 정보 반환
    """

    def __init__(self, user_repository: IUserRepository):
        """
        Args:
            user_repository: 사용자 리포지토리 (DI)
        """
        self._user_repo = user_repository

    def execute(self, request: LoginUserRequest) -> LoginUserResponse:
        """
        로그인 실행

        Args:
            request: 로그인 요청 DTO

        Returns:
            LoginUserResponse

        Raises:
            AuthenticationError: 인증 실패
        """
        # 1. 사용자 조회 및 비밀번호 검증 (Repository에서 처리)
        user = self._user_repo.verify_user_password(
            username=request.username,
            password=request.password
        )

        if not user:
            raise AuthenticationError("Invalid username or password")

        # 2. 사용자 정보 반환
        return LoginUserResponse(
            user_id=user['user_id'],
            username=user['username'],
            display_name=user.get('display_name', user['username']),
            email=user.get('email')
        )
