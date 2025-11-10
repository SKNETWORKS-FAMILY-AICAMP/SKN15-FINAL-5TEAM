"""
Auth Schemas
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class LoginRequest(BaseModel):
    """로그인 요청"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """로그인 응답"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


class RegisterRequest(BaseModel):
    """회원가입 요청"""
    username: str = Field(..., min_length=3, max_length=50, description="사용자명 (3-50자)")
    password: str = Field(..., min_length=6, description="비밀번호 (최소 6자)")
    display_name: str = Field(..., min_length=1, max_length=100, description="표시 이름")
    email: Optional[EmailStr] = Field(None, description="이메일 (선택)")


class RegisterResponse(BaseModel):
    """회원가입 응답"""
    user_id: str
    username: str
    display_name: str
    message: str = "Registration successful"


class PasswordResetRequest(BaseModel):
    """비밀번호 재설정 요청"""
    email: EmailStr = Field(..., description="가입한 이메일 주소")


class PasswordResetConfirm(BaseModel):
    """비밀번호 재설정 확인"""
    token: str = Field(..., description="재설정 토큰")
    new_password: str = Field(..., min_length=6, description="새 비밀번호 (최소 6자)")


class PasswordResetResponse(BaseModel):
    """비밀번호 재설정 응답"""
    message: str


class RefreshTokenRequest(BaseModel):
    """토큰 갱신 요청"""
    refresh_token: str = Field(..., description="리프레시 토큰")


class RefreshTokenResponse(BaseModel):
    """토큰 갱신 응답"""
    access_token: str
    token_type: str = "bearer"
