"""
Auth UseCase
사용자 인증 비즈니스 로직
"""
import bcrypt
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional
import secrets
from app.core.config import get_settings
from app.core.logging import get_parent_logger
from app.shared.exceptions import BusinessException
from .repository import AuthRepository
from app.features.users.repository import UserRepository

logger = get_parent_logger("AuthUseCase")
settings = get_settings()

# 회원가입 시 지급할 초기 크레딧
INITIAL_CREDITS = 200


class AuthResult:
    """인증 결과 DTO"""
    def __init__(self, access_token: str, refresh_token: str, user_id: str, username: str, role: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_id = user_id
        self.username = username
        self.role = role


class RegisterResult:
    """회원가입 결과 DTO"""
    def __init__(self, user_id: str, username: str, display_name: str,
                 access_token: str = None, refresh_token: str = None, role: str = "user"):
        self.user_id = user_id
        self.username = username
        self.display_name = display_name
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.role = role


class AuthUseCase:
    """
    사용자 인증 UseCase
    Layer 2: UseCase
    """

    def __init__(self, repository: AuthRepository, user_repository: Optional[UserRepository] = None):
        self.repository = repository
        self.user_repository = user_repository

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

        # 3. JWT Access 토큰 생성 (60분 유효)
        access_payload = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        }

        access_token = jwt.encode(
            access_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        # 4. JWT Refresh 토큰 생성 (7일 유효)
        refresh_payload = {
            "user_id": user.user_id,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=7)
        }

        refresh_token = jwt.encode(
            refresh_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        # 5. 마지막 로그인 시간 업데이트
        await self.repository.update_last_login(user.user_id)

        logger.info("authenticate_user", "Authentication successful", username=username, user_id=user.user_id)

        return AuthResult(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.user_id,
            username=user.username,
            role=user.role
        )

    async def register_user(
        self,
        username: str,
        password: str,
        display_name: str,
        email: Optional[str] = None
    ) -> RegisterResult:
        """
        새 사용자 등록

        Args:
            username: 사용자명
            password: 비밀번호
            display_name: 표시 이름
            email: 이메일 (선택)

        Returns:
            RegisterResult

        Raises:
            BusinessException: 회원가입 실패
        """
        logger.info("register_user", "Registration attempt", username=username)

        # 1. 중복 체크
        if await self.repository.username_exists(username):
            logger.warning("register_user", "Username already exists", username=username)
            raise BusinessException("Username already exists", error_code="USERNAME_EXISTS")

        if email and await self.repository.email_exists(email):
            logger.warning("register_user", "Email already exists")
            raise BusinessException("Email already exists", error_code="EMAIL_EXISTS")

        # 2. 비밀번호 해싱
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

        # 3. 사용자 생성
        user_id = await self.repository.create_user(
            username=username,
            password_hash=password_hash,
            display_name=display_name,
            email=email,
            role="user"
        )

        logger.info("register_user", "User registered successfully", user_id=user_id, username=username)

        # 4. 초기 크레딧 지급 (200 버블)
        if self.user_repository:
            try:
                await self.user_repository.add_credits(
                    user_id=user_id,
                    amount=INITIAL_CREDITS,
                    transaction_type="initial",
                    description="회원가입 축하 크레딧"
                )
                logger.info("register_user", f"Initial credits granted", user_id=user_id, amount=INITIAL_CREDITS)
            except Exception as e:
                logger.error("register_user", f"Failed to grant initial credits: {e}", user_id=user_id)
                # 크레딧 지급 실패해도 회원가입은 완료되도록 함

        # 5. JWT 토큰 생성 (자동 로그인)
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = jwt.encode(
            {
                "user_id": user_id,
                "username": username,
                "role": "user",
                "exp": datetime.utcnow() + access_token_expires
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = jwt.encode(
            {
                "user_id": user_id,
                "type": "refresh",
                "exp": datetime.utcnow() + refresh_token_expires
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        logger.info("register_user", "Auto-login tokens generated", user_id=user_id)

        return RegisterResult(
            user_id=user_id,
            username=username,
            display_name=display_name,
            access_token=access_token,
            refresh_token=refresh_token,
            role="user"
        )

    async def request_password_reset(self, email: str) -> str:
        """
        비밀번호 재설정 요청

        Args:
            email: 이메일

        Returns:
            재설정 토큰 (실제로는 이메일로 전송해야 함)

        Raises:
            BusinessException: 사용자 없음
        """
        logger.info("request_password_reset", "Password reset requested")

        # 1. 이메일로 사용자 조회
        user = await self.repository.get_user_by_email(email)
        if not user:
            # 보안을 위해 사용자가 없어도 성공 메시지 반환 (타이밍 공격 방지)
            logger.warning("request_password_reset", "User not found for email")
            raise BusinessException("If this email exists, a reset link has been sent", error_code="EMAIL_SENT")

        # 2. 재설정 토큰 생성 (32바이트 랜덤)
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)  # 1시간 유효

        # 3. 토큰 저장
        await self.repository.create_password_reset_token(
            user_id=user.user_id,
            token=reset_token,
            expires_at=expires_at
        )

        logger.info("request_password_reset", "Reset token created", user_id=user.user_id)

        # TODO: 실제로는 이메일로 토큰 전송
        # 개발 환경에서는 토큰 반환
        return reset_token

    async def reset_password(self, token: str, new_password: str):
        """
        비밀번호 재설정

        Args:
            token: 재설정 토큰
            new_password: 새 비밀번호

        Raises:
            BusinessException: 토큰 무효 또는 만료
        """
        logger.info("reset_password", "Password reset attempt")

        # 1. 토큰 조회
        token_data = await self.repository.get_password_reset_token(token)
        if not token_data:
            logger.warning("reset_password", "Invalid token")
            raise BusinessException("Invalid or expired reset token", error_code="INVALID_TOKEN")

        # 2. 토큰 검증
        if token_data.is_used:
            logger.warning("reset_password", "Token already used")
            raise BusinessException("Reset token has already been used", error_code="TOKEN_USED")

        if datetime.utcnow() > token_data.expires_at:
            logger.warning("reset_password", "Token expired")
            raise BusinessException("Reset token has expired", error_code="TOKEN_EXPIRED")

        # 3. 새 비밀번호 해싱
        password_bytes = new_password.encode('utf-8')
        salt = bcrypt.gensalt()
        new_password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

        # 4. 비밀번호 업데이트
        await self.repository.update_user_password(token_data.user_id, new_password_hash)

        # 5. 토큰을 사용됨으로 표시
        await self.repository.mark_token_as_used(token)

        logger.info("reset_password", "Password reset successful", user_id=token_data.user_id)

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Refresh 토큰으로 새로운 Access 토큰 발급

        Args:
            refresh_token: 리프레시 토큰

        Returns:
            새로운 access_token

        Raises:
            BusinessException: 토큰 검증 실패
        """
        logger.info("refresh_access_token", "Token refresh attempt")

        try:
            # 1. Refresh 토큰 검증
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )

            # 2. 토큰 타입 확인
            if payload.get("type") != "refresh":
                logger.warning("refresh_access_token", "Invalid token type")
                raise BusinessException("Invalid refresh token", error_code="INVALID_TOKEN_TYPE")

            user_id = payload.get("user_id")
            if not user_id:
                logger.warning("refresh_access_token", "Missing user_id in token")
                raise BusinessException("Invalid refresh token", error_code="INVALID_TOKEN")

            # 3. 사용자 조회 (탈퇴/비활성화 체크)
            user = await self.repository.get_user_by_id(user_id)
            if not user or not user.is_active:
                logger.warning("refresh_access_token", "User not found or inactive", user_id=user_id)
                raise BusinessException("User not found or inactive", error_code="USER_INACTIVE")

            # 4. 새로운 Access 토큰 생성
            access_payload = {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role,
                "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            }

            new_access_token = jwt.encode(
                access_payload,
                settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM
            )

            logger.info("refresh_access_token", "Token refreshed successfully", user_id=user_id)
            return new_access_token

        except jwt.ExpiredSignatureError:
            logger.warning("refresh_access_token", "Refresh token expired")
            raise BusinessException("Refresh token expired", error_code="TOKEN_EXPIRED")
        except jwt.JWTError as e:
            logger.warning("refresh_access_token", f"JWT decode error: {e}")
            raise BusinessException("Invalid refresh token", error_code="INVALID_TOKEN")
