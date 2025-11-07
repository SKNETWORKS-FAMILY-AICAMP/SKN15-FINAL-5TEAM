"""
Auth Schemas
"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """로그인 요청"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """로그인 응답"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str
