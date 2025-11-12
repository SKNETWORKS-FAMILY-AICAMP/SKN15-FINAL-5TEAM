"""
Auth Repository
사용자 데이터 액세스 계층
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_parent_logger
import uuid

logger = get_parent_logger("AuthRepository")


class UserData:
    """사용자 데이터 DTO"""
    def __init__(self, user_id: str, username: str, password_hash: str, role: str, email: Optional[str] = None, is_active: bool = True):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.email = email
        self.is_active = is_active


class PasswordResetTokenData:
    """비밀번호 재설정 토큰 DTO"""
    def __init__(self, token_id: str, user_id: str, token: str, expires_at: datetime, is_used: bool):
        self.token_id = token_id
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at
        self.is_used = is_used


class AuthRepository:
    """
    사용자 인증 관련 데이터 액세스
    Layer 4: Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: str) -> Optional[UserData]:
        """
        user_id로 사용자 조회

        Args:
            user_id: 사용자 ID (UUID)

        Returns:
            UserData 또는 None
        """
        query = text("SELECT user_id, username, password_hash, role, email, is_active FROM auth.users WHERE user_id = :user_id")
        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            logger.debug("get_user_by_id", f"User not found", user_id=user_id)
            return None

        logger.debug("get_user_by_id", f"User found", user_id=str(row.user_id))
        return UserData(
            user_id=str(row.user_id),
            username=row.username,
            password_hash=row.password_hash,
            role=row.role,
            email=row.email,
            is_active=row.is_active
        )

    async def get_user_by_username(self, username: str) -> Optional[UserData]:
        """
        username으로 사용자 조회

        Args:
            username: 사용자명

        Returns:
            UserData 또는 None
        """
        query = text("SELECT user_id, username, password_hash, role, email, is_active FROM auth.users WHERE username = :username")
        result = await self.db.execute(query, {"username": username})
        row = result.fetchone()

        if not row:
            logger.debug("get_user_by_username", f"User not found: {username}")
            return None

        logger.debug("get_user_by_username", f"User found: {username}", user_id=str(row.user_id))
        return UserData(
            user_id=str(row.user_id),
            username=row.username,
            password_hash=row.password_hash,
            role=row.role,
            email=row.email,
            is_active=row.is_active
        )

    async def get_user_by_email(self, email: str) -> Optional[UserData]:
        """
        email로 사용자 조회

        Args:
            email: 이메일

        Returns:
            UserData 또는 None
        """
        query = text("SELECT user_id, username, password_hash, role, email, is_active FROM auth.users WHERE email = :email")
        result = await self.db.execute(query, {"email": email})
        row = result.fetchone()

        if not row:
            logger.debug("get_user_by_email", f"User not found for email")
            return None

        logger.debug("get_user_by_email", f"User found", user_id=str(row.user_id))
        return UserData(
            user_id=str(row.user_id),
            username=row.username,
            password_hash=row.password_hash,
            role=row.role,
            email=row.email,
            is_active=row.is_active
        )

    async def username_exists(self, username: str) -> bool:
        """username 중복 체크"""
        query = text("SELECT EXISTS(SELECT 1 FROM auth.users WHERE username = :username)")
        result = await self.db.execute(query, {"username": username})
        return result.scalar()

    async def email_exists(self, email: str) -> bool:
        """email 중복 체크"""
        query = text("SELECT EXISTS(SELECT 1 FROM auth.users WHERE email = :email)")
        result = await self.db.execute(query, {"email": email})
        return result.scalar()

    async def create_user(
        self,
        username: str,
        password_hash: str,
        display_name: str,
        email: Optional[str] = None,
        role: str = "user"
    ) -> str:
        """
        새 사용자 생성

        Args:
            username: 사용자명
            password_hash: 해시된 비밀번호
            display_name: 표시 이름
            email: 이메일 (선택)
            role: 역할 (기본: user)

        Returns:
            생성된 user_id
        """
        user_id = str(uuid.uuid4())
        now = datetime.utcnow()

        query = text("""
            INSERT INTO auth.users (
                user_id, username, password_hash, display_name, email,
                is_active, is_verified, role, total_sessions, total_bubbles,
                created_at, updated_at
            ) VALUES (
                :user_id, :username, :password_hash, :display_name, :email,
                :is_active, :is_verified, :role, :total_sessions, :total_bubbles,
                :created_at, :updated_at
            )
        """)

        await self.db.execute(query, {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "display_name": display_name,
            "email": email,
            "is_active": True,
            "is_verified": False,
            "role": role,
            "total_sessions": 0,
            "total_bubbles": 0,
            "created_at": now,
            "updated_at": now
        })

        await self.db.commit()
        logger.info("create_user", f"User created", user_id=user_id, username=username)
        return user_id

    async def create_password_reset_token(
        self,
        user_id: str,
        token: str,
        expires_at: datetime
    ) -> str:
        """
        비밀번호 재설정 토큰 생성

        Args:
            user_id: 사용자 ID
            token: 재설정 토큰
            expires_at: 만료 시간

        Returns:
            생성된 token_id
        """
        token_id = str(uuid.uuid4())
        now = datetime.utcnow()

        query = text("""
            INSERT INTO auth.password_reset_tokens (
                token_id, user_id, token, expires_at, is_used, created_at
            ) VALUES (
                :token_id, :user_id, :token, :expires_at, :is_used, :created_at
            )
        """)

        await self.db.execute(query, {
            "token_id": token_id,
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at,
            "is_used": False,
            "created_at": now
        })

        await self.db.commit()
        logger.info("create_password_reset_token", "Reset token created", token_id=token_id)
        return token_id

    async def get_password_reset_token(self, token: str) -> Optional[PasswordResetTokenData]:
        """
        재설정 토큰 조회

        Args:
            token: 재설정 토큰

        Returns:
            PasswordResetTokenData 또는 None
        """
        query = text("""
            SELECT token_id, user_id, token, expires_at, is_used
            FROM auth.password_reset_tokens
            WHERE token = :token
        """)

        result = await self.db.execute(query, {"token": token})
        row = result.fetchone()

        if not row:
            return None

        return PasswordResetTokenData(
            token_id=str(row.token_id),
            user_id=str(row.user_id),
            token=row.token,
            expires_at=row.expires_at,
            is_used=row.is_used
        )

    async def mark_token_as_used(self, token: str):
        """토큰을 사용됨으로 표시"""
        query = text("UPDATE auth.password_reset_tokens SET is_used = true, used_at = :used_at WHERE token = :token")
        await self.db.execute(query, {"token": token, "used_at": datetime.utcnow()})
        await self.db.commit()
        logger.info("mark_token_as_used", "Token marked as used")

    async def update_user_password(self, user_id: str, new_password_hash: str):
        """
        사용자 비밀번호 업데이트

        Args:
            user_id: 사용자 ID
            new_password_hash: 새 비밀번호 해시
        """
        query = text("""
            UPDATE auth.users
            WHERE user_id = :user_id
        """)

        await self.db.execute(query, {
            "user_id": user_id,
            "password_hash": new_password_hash,
            "updated_at": datetime.utcnow()
        })

        await self.db.commit()
        logger.info("update_user_password", "Password updated", user_id=user_id)

    async def update_last_login(self, user_id: str):
        """
        마지막 로그인 시간 업데이트

        Args:
            user_id: 사용자 ID
        """
        query = text("""
            UPDATE auth.users
            SET last_login_at = :last_login_at
            WHERE user_id = :user_id
        """)

        await self.db.execute(query, {
            "user_id": user_id,
            "last_login_at": datetime.utcnow()
        })

        await self.db.commit()
        logger.debug("update_last_login", "Last login updated", user_id=user_id)
