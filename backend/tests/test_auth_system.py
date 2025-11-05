#!/usr/bin/env python3
"""
자체 회원가입 및 로그인 시스템 테스트
"""
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"

def print_section(title):
    """섹션 헤더 출력"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(label, data):
    """결과 출력"""
    print(f"\n✅ {label}:")
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ['access_token', 'refresh_token']:
                # 토큰은 앞부분만 표시
                print(f"  {key}: {value[:50]}..." if value else f"  {key}: None")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"  {data}")

def test_register():
    """회원가입 테스트"""
    print_section("1️⃣  회원가입 테스트")

    # 고유한 사용자명 생성
    timestamp = datetime.now().strftime("%H%M%S")
    test_user = {
        "username": f"testuser{timestamp}",
        "password": "test1234",
        "email": f"test{timestamp}@example.com",
        "display_name": f"테스트유저{timestamp}"
    }

    print(f"\n📤 회원가입 요청:")
    print(f"  Username: {test_user['username']}")
    print(f"  Email: {test_user['email']}")
    print(f"  Display Name: {test_user['display_name']}")

    try:
        response = requests.post(
            f"{API_URL}/api/auth/register",
            json=test_user,
            timeout=10
        )

        result = response.json()

        if response.status_code == 200 and result.get('success'):
            print_result("회원가입 성공", result)
            return test_user, result
        else:
            print(f"\n❌ 회원가입 실패:")
            print(f"  Status: {response.status_code}")
            print(f"  Message: {result.get('message', 'Unknown error')}")
            return None, None

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        return None, None

def test_login(username, password):
    """로그인 테스트"""
    print_section("2️⃣  로그인 테스트")

    login_data = {
        "username": username,
        "password": password
    }

    print(f"\n📤 로그인 요청:")
    print(f"  Username: {username}")
    print(f"  Password: {'*' * len(password)}")

    try:
        response = requests.post(
            f"{API_URL}/api/auth/login",
            json=login_data,
            timeout=10
        )

        result = response.json()

        if response.status_code == 200 and result.get('success'):
            print_result("로그인 성공", result)
            return result
        else:
            print(f"\n❌ 로그인 실패:")
            print(f"  Status: {response.status_code}")
            print(f"  Message: {result.get('message', 'Unknown error')}")
            return None

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        return None

def test_duplicate_register(username):
    """중복 회원가입 테스트"""
    print_section("3️⃣  중복 회원가입 방지 테스트")

    duplicate_user = {
        "username": username,
        "password": "different_password",
        "email": "different@example.com",
        "display_name": "다른이름"
    }

    print(f"\n📤 동일한 사용자명으로 재가입 시도:")
    print(f"  Username: {username}")

    try:
        response = requests.post(
            f"{API_URL}/api/auth/register",
            json=duplicate_user,
            timeout=10
        )

        result = response.json()

        if not result.get('success'):
            print(f"\n✅ 중복 방지 정상 작동:")
            print(f"  Message: {result.get('message')}")
            return True
        else:
            print(f"\n❌ 중복 방지 실패 (중복 가입이 허용됨)")
            return False

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        return False

def test_wrong_password(username):
    """잘못된 비밀번호 테스트"""
    print_section("4️⃣  잘못된 비밀번호 로그인 테스트")

    wrong_login = {
        "username": username,
        "password": "wrong_password"
    }

    print(f"\n📤 잘못된 비밀번호로 로그인 시도:")
    print(f"  Username: {username}")
    print(f"  Password: wrong_password")

    try:
        response = requests.post(
            f"{API_URL}/api/auth/login",
            json=wrong_login,
            timeout=10
        )

        result = response.json()

        if not result.get('success'):
            print(f"\n✅ 비밀번호 검증 정상 작동:")
            print(f"  Message: {result.get('message')}")
            return True
        else:
            print(f"\n❌ 비밀번호 검증 실패 (잘못된 비밀번호 허용됨)")
            return False

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        return False

def test_protected_api(access_token):
    """JWT 토큰으로 보호된 API 테스트"""
    print_section("5️⃣  JWT 토큰 인증 테스트")

    # 보호된 API 엔드포인트가 있다면 테스트
    # 예: /api/auth/me (현재 사용자 정보 조회)

    print(f"\n📤 토큰 인증 테스트:")
    print(f"  Access Token: {access_token[:50]}...")

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        # /api/auth/me 엔드포인트가 있는지 확인
        response = requests.get(
            f"{API_URL}/api/auth/me",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print_result("인증 성공 - 사용자 정보 조회", result)
            return True
        else:
            print(f"\n⚠️  /api/auth/me 엔드포인트가 없거나 접근 불가")
            print(f"  Status: {response.status_code}")
            return False

    except Exception as e:
        print(f"\n⚠️  보호된 API 테스트 건너뜀: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("\n" + "🔐" * 35)
    print("     자체 회원가입 & 로그인 시스템 테스트")
    print("🔐" * 35)

    # 1. 회원가입
    test_user, register_result = test_register()
    if not test_user or not register_result:
        print("\n❌ 회원가입 실패 - 테스트 중단")
        return

    # 2. 로그인
    login_result = test_login(test_user['username'], test_user['password'])
    if not login_result:
        print("\n❌ 로그인 실패 - 테스트 중단")
        return

    # 3. 중복 회원가입 방지
    test_duplicate_register(test_user['username'])

    # 4. 잘못된 비밀번호
    test_wrong_password(test_user['username'])

    # 5. JWT 토큰 인증 (선택)
    if login_result.get('access_token'):
        test_protected_api(login_result['access_token'])

    # 최종 요약
    print_section("✅ 테스트 완료")
    print(f"\n📊 생성된 사용자:")
    print(f"  Username: {test_user['username']}")
    print(f"  Password: {test_user['password']}")
    print(f"  User ID: {register_result.get('user_id')}")
    print(f"  Display Name: {register_result.get('display_name')}")

    print(f"\n💾 DBeaver에서 확인:")
    print(f"  SELECT * FROM statedb.users WHERE username = '{test_user['username']}';")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
