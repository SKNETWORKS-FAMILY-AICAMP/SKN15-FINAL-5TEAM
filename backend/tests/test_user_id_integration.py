#!/usr/bin/env python3
"""
문제 1 테스트: 세션-사용자 연결 검증
user_id가 제대로 세션에 저장되는지 확인
"""
import requests
import sys
import json
from datetime import datetime

API_URL = "http://localhost:8000"

# PostgreSQL 확인 함수
def check_db(session_id):
    """PostgreSQL에서 세션의 user_id 확인"""
    import subprocess
    cmd = f'docker exec kime-postgres psql -U kime -d kimedb -t -c "SELECT user_id, user_name FROM sessions WHERE session_id = \'{session_id}\';"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

print("\n" + "="*60)
print("문제 1 테스트: 세션-사용자 user_id 연결")
print("="*60)

# 테스트 1: 익명 사용자 (JWT 없이)
print("\n[테스트 1] 익명 사용자 테스트")
print("-" * 60)

anon_data = {
    "scenario_id": "cutscene5_llm_driven",
    "user_input": "시작",
    "user_name": "익명테스트1"
}

try:
    response = requests.post(f"{API_URL}/api/chat", json=anon_data, timeout=120)
    result = response.json()

    if response.status_code == 200:
        session_id = result.get('session_id')
        print(f"✅ API 응답 성공")
        print(f"   Session ID: {session_id}")

        # DB 확인
        db_result = check_db(session_id)
        print(f"\n📊 PostgreSQL 조회 결과:")
        print(f"   {db_result}")

        if "익명테스트1" in db_result:
            if "|" in db_result and db_result.strip().startswith("|"):
                print(f"✅ user_id = NULL (익명 사용자, 예상된 동작)")
            else:
                print(f"⚠️  user_id 컬럼 확인 필요")
        else:
            print(f"❌ 세션이 DB에 저장되지 않음")
    else:
        print(f"❌ API 실패: {result}")
except Exception as e:
    print(f"❌ 에러 발생: {e}")

# 테스트 2: 인증된 사용자 (JWT와 함께)
print("\n\n[테스트 2] 인증된 사용자 테스트")
print("-" * 60)

# 먼저 로그인해서 JWT 토큰 획득
login_data = {
    "username": "finaltest001",
    "password": "test1234"
}

try:
    login_response = requests.post(f"{API_URL}/api/auth/login", json=login_data, timeout=10)
    login_result = login_response.json()

    if login_response.status_code == 200 and login_result.get('success'):
        access_token = login_result.get('access_token')
        user_id = login_result.get('user_id')
        username = login_result.get('username')

        print(f"✅ 로그인 성공")
        print(f"   사용자: {username}")
        print(f"   User ID: {user_id}")

        # JWT 토큰과 함께 채팅 요청
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        auth_chat_data = {
            "scenario_id": "cutscene5_llm_driven",
            "user_input": "시작",
            "user_name": username
        }

        chat_response = requests.post(
            f"{API_URL}/api/chat",
            json=auth_chat_data,
            headers=headers,
            timeout=120
        )

        chat_result = chat_response.json()

        if chat_response.status_code == 200:
            session_id = chat_result.get('session_id')
            print(f"\n✅ 인증된 채팅 성공")
            print(f"   Session ID: {session_id}")

            # DB 확인
            db_result = check_db(session_id)
            print(f"\n📊 PostgreSQL 조회 결과:")
            print(f"   {db_result}")

            if user_id in db_result:
                print(f"✅✅✅ user_id가 세션에 저장됨! (문제 1 해결)")
            elif username in db_result:
                if "|" in db_result and not db_result.strip().startswith("|"):
                    print(f"❓ user_name은 있지만 user_id 확인 필요")
                else:
                    print(f"❌ user_id가 NULL (문제 1 미해결)")
            else:
                print(f"❌ 세션이 DB에 저장되지 않음")
        else:
            print(f"❌ 채팅 실패: {chat_result}")
    else:
        print(f"❌ 로그인 실패: {login_result}")
        print(f"   힌트: finaltest001 계정이 없으면 test_auth_system.py로 먼저 생성하세요")
except Exception as e:
    print(f"❌ 에러 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("테스트 완료")
print("="*60 + "\n")
