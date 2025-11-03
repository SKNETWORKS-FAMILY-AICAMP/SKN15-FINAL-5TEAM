"""
Google OAuth 2.0 인증 핸들러
"""

import os
from typing import Optional, Dict, Any
from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow

# Google OAuth 설정
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

# OAuth 2.0 스코프
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


def get_google_oauth_url() -> Optional[str]:
    """
    Google OAuth 로그인 URL 생성

    Returns:
        str: OAuth 로그인 URL
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError("Google OAuth credentials not configured")

    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        return authorization_url, state
    except Exception as e:
        print(f"Error generating Google OAuth URL: {e}")
        return None, None


def verify_google_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Google OAuth 인증 코드로 사용자 정보 가져오기

    Args:
        code: OAuth authorization code

    Returns:
        Dict: 사용자 정보 {email, name, picture, sub}
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError("Google OAuth credentials not configured")

    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI

        # 토큰 교환
        flow.fetch_token(code=code)

        # ID 토큰 검증
        credentials = flow.credentials
        request = requests.Request()

        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request,
            GOOGLE_CLIENT_ID
        )

        # 사용자 정보 반환
        return {
            'sub': id_info.get('sub'),  # Google User ID
            'email': id_info.get('email'),
            'name': id_info.get('name'),
            'picture': id_info.get('picture'),
            'email_verified': id_info.get('email_verified'),
        }

    except Exception as e:
        print(f"Error verifying Google token: {e}")
        return None


def create_or_get_google_user(db_manager, google_user_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Google 사용자 정보로 DB에 사용자 생성 또는 가져오기

    Args:
        db_manager: DatabaseManager 인스턴스
        google_user_info: Google에서 받은 사용자 정보

    Returns:
        Dict: 사용자 정보 (user_id, username, email, etc.)
    """
    email = google_user_info.get('email')
    google_id = google_user_info.get('sub')

    if not email or not google_id:
        return None

    # 이메일로 기존 사용자 찾기
    user = db_manager.get_user_by_username(email)

    if user:
        # 기존 사용자 - 마지막 로그인 업데이트
        db_manager.update_user_last_login(str(user['user_id']))
        return user

    # 새 사용자 생성
    username = email.split('@')[0]  # 이메일의 로컬 파트를 username으로 사용
    display_name = google_user_info.get('name', username)

    user_id = db_manager.create_user(
        username=username,
        password_hash='',  # OAuth 사용자는 비밀번호 없음
        email=email,
        provider='google',
        display_name=display_name
    )

    if user_id:
        return {
            'user_id': user_id,
            'username': username,
            'email': email,
            'display_name': display_name,
            'provider': 'google',
        }

    return None
