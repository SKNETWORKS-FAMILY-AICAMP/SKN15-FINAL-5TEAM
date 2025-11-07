"""
Auth UseCase
사용자 인증 비즈니스 로직
"""
import bcrypt
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional
from app.core.config import get_settings
from app.core.logging import get_parent_logger
from app.shared.exceptions import BusinessException
from .repository import AuthRepository

logger = get_parent_logger("AuthUseCase")
settings = get_settings()


class AuthResult:
    """인증 결과 DTO"""
    def __init__(self, access_token: str, user_id: int, username: str, role: str):
        self.access_token = access_token
        self.user_id = user_id
        self.username = username
        self.role = role


class AuthUseCase:
    """
    사용자 인증 UseCase
    Layer 2: UseCase
    """

    def __init__(self, repository: AuthRepository):
        self.repository = repository

    async def authenticate_user(self, username: str, password: str) -> AuthResult:
        """
        사용자 인증 및 토큰 발급

        Args:
            username: 사용자명
            password: 비밀번호

        Returns:
            AuthResult (토큰 및 사용자 정보)

        Raises:
            BusinessException: 인증 실패
        """
        logger.info("authenticate_user", f"Authentication attempt", username=username)

        # 1. 사용자 조회
        user = await self.repository.get_user_by_username(username)
        if not user:
            logger.warning("authenticate_user", "User not found", username=username)
            raise BusinessException("Invalid username or password", error_code="AUTH_FAILED")

        # 2. 비밀번호 검증
        password_bytes = password.encode('utf-8')
        hash_bytes = user.password_hash.encode('utf-8') if isinstance(user.password_hash, str) else user.password_hash

        if not bcrypt.checkpw(password_bytes, hash_bytes):
            logger.warning("authenticate_user", "Password mismatch", username=username)
            raise BusinessException("Invalid username or password", error_code="AUTH_FAILED")

        # 3. JWT 토큰 생성
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        }

        access_token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        logger.info("authenticate_user", "Authentication successful", username=username, user_id=user.id)

        return AuthResult(
            access_token=access_token,
            user_id=user.id,
            username=user.username,
            role=user.role
        )
