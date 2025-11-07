"""
Register User Use Case

사용자 등록 비즈니스 로직
"""
from dataclasses import dataclass
from typing import Optional
import bcrypt

from core.interfaces.repositories.user_repository import IUserRepository
from core.exceptions.domain_exceptions import ValidationError, DuplicateEntityError


@dataclass
class RegisterUserRequest:
    """사용자 등록 요청 DTO"""
    username: str
    password: str
    email: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class RegisterUserResponse:
    """사용자 등록 응답 DTO"""
    user_id: str
    username: str
    display_name: str


class RegisterUserUseCase:
    """
    사용자 등록 Use Case

    책임:
    1. 입력 검증 (username, password 형식)
    2. 중복 확인
    3. 비밀번호 해싱
    4. 사용자 생성
    """

    def __init__(self, user_repository: IUserRepository):
        """
        Args:
            user_repository: 사용자 리포지토리 (DI)
        """
        self._user_repo = user_repository

    def execute(self, request: RegisterUserRequest) -> RegisterUserResponse:
        """
        사용자 등록 실행

        Args:
            request: 등록 요청 DTO

        Returns:
            RegisterUserResponse

        Raises:
            ValidationError: 입력 검증 실패
            DuplicateEntityError: 이미 존재하는 사용자
        """
        # 1. 입력 검증
        self._validate_input(request)

        # 2. 중복 확인
        existing_user = self._user_repo.get_by_username(request.username)
        if existing_user:
            raise DuplicateEntityError(f"Username '{request.username}' already exists")

        # 3. 비밀번호 해싱
        password_hash = self._hash_password(request.password)

        # 4. 사용자 생성
        user_id = self._user_repo.create_user(
            username=request.username,
            password_hash=password_hash,
            email=request.email,
            display_name=request.display_name or request.username
        )

        if not user_id:
            raise Exception("Failed to create user")

        return RegisterUserResponse(
            user_id=user_id,
            username=request.username,
            display_name=request.display_name or request.username
        )

    def _validate_input(self, request: RegisterUserRequest) -> None:
        """입력 검증"""
        if not request.username or len(request.username) < 3:
            raise ValidationError("Username must be at least 3 characters")

        if not request.password or len(request.password) < 4:
            raise ValidationError("Password must be at least 4 characters")

        # Username 형식 검증 (영문, 숫자, 언더스코어만)
        if not request.username.replace('_', '').isalnum():
            raise ValidationError("Username can only contain letters, numbers, and underscores")

    def _hash_password(self, password: str) -> str:
        """비밀번호 해싱 (bcrypt)"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
