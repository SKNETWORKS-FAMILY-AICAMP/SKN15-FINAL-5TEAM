"""
Kakao OAuth 2.0 인증 핸들러
"""

import os
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlencode

# Kakao OAuth 설정
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI", "http://localhost:8000/api/auth/kakao/callback")

# Kakao OAuth URLs
KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"


def get_kakao_oauth_url() -> Optional[str]:
    """
    Kakao OAuth 로그인 URL 생성

    Returns:
        str: OAuth 로그인 URL
    """
    if not KAKAO_CLIENT_ID:
        raise ValueError("Kakao OAuth credentials not configured")

    params = {
        'client_id': KAKAO_CLIENT_ID,
        'redirect_uri': KAKAO_REDIRECT_URI,
        'response_type': 'code',
    }

    return f"{KAKAO_AUTH_URL}?{urlencode(params)}"


def get_kakao_access_token(code: str) -> Optional[str]:
    """
    Kakao OAuth 인증 코드로 액세스 토큰 가져오기

    Args:
        code: OAuth authorization code

    Returns:
        str: 액세스 토큰
    """
    if not KAKAO_CLIENT_ID:
        raise ValueError("Kakao OAuth credentials not configured")

    try:
        data = {
            'grant_type': 'authorization_code',
            'client_id': KAKAO_CLIENT_ID,
            'redirect_uri': KAKAO_REDIRECT_URI,
            'code': code,
        }

        response = requests.post(KAKAO_TOKEN_URL, data=data)
        response.raise_for_status()

        token_data = response.json()
        return token_data.get('access_token')

    except Exception as e:
        print(f"Error getting Kakao access token: {e}")
        return None


def get_kakao_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Kakao 액세스 토큰으로 사용자 정보 가져오기

    Args:
        access_token: Kakao 액세스 토큰

    Returns:
        Dict: 사용자 정보
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
        }

        response = requests.get(KAKAO_USER_INFO_URL, headers=headers)
        response.raise_for_status()

        user_data = response.json()

        # 사용자 정보 추출
        kakao_account = user_data.get('kakao_account', {})
        profile = kakao_account.get('profile', {})

        return {
            'id': str(user_data.get('id')),  # Kakao User ID
            'email': kakao_account.get('email'),
            'nickname': profile.get('nickname'),
            'profile_image': profile.get('profile_image_url'),
            'email_verified': kakao_account.get('is_email_valid', False),
        }

    except Exception as e:
        print(f"Error getting Kakao user info: {e}")
        return None


def verify_kakao_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Kakao OAuth 인증 코드로 사용자 정보 가져오기 (통합 함수)

    Args:
        code: OAuth authorization code

    Returns:
        Dict: 사용자 정보
    """
    # 액세스 토큰 획득
    access_token = get_kakao_access_token(code)
    if not access_token:
        return None

    # 사용자 정보 획득
    return get_kakao_user_info(access_token)


def create_or_get_kakao_user(db_manager, kakao_user_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Kakao 사용자 정보로 DB에 사용자 생성 또는 가져오기

    Args:
        db_manager: DatabaseManager 인스턴스
        kakao_user_info: Kakao에서 받은 사용자 정보

    Returns:
        Dict: 사용자 정보 (user_id, username, email, etc.)
    """
    email = kakao_user_info.get('email')
    kakao_id = kakao_user_info.get('id')
    nickname = kakao_user_info.get('nickname', 'KakaoUser')

    if not kakao_id:
        return None

    # 이메일이 있으면 이메일로 찾고, 없으면 kakao_{id}로 username 생성
    if email:
        user = db_manager.get_user_by_username(email)
        username = email.split('@')[0]
    else:
        username = f"kakao_{kakao_id}"
        user = db_manager.get_user_by_username(username)

    if user:
        # 기존 사용자 - 마지막 로그인 업데이트
        db_manager.update_user_last_login(str(user['user_id']))
        return user

    # 새 사용자 생성
    display_name = nickname

    user_id = db_manager.create_user(
        username=username,
        password_hash='',  # OAuth 사용자는 비밀번호 없음
        email=email,
        provider='kakao',
        display_name=display_name
    )

    if user_id:
        return {
            'user_id': user_id,
            'username': username,
            'email': email,
            'display_name': display_name,
            'provider': 'kakao',
        }

    return None
