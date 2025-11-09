#!/usr/bin/env python3
"""
문제 2 테스트: 대화 기록 로깅 시스템 검증
dialogues와 user_inputs 테이블에 데이터가 저장되는지 확인
"""
import requests
import subprocess
import sys

API_URL = "http://localhost:8000"

def check_db(query):
    """PostgreSQL 쿼리 실행"""
    cmd = f'docker exec kime-postgres psql -U kime -d kimedb -t -c "{query}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

print("\n" + "="*60)
print("문제 2 테스트: 대화 기록 로깅 시스템")
print("="*60)

# 테스트: 인증된 사용자로 채팅
print("\n[테스트] 대화 로깅 확인")
print("-" * 60)

# 로그인
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

        print(f"✅ 로그인 성공: {username}")

        # 채팅 요청
        headers = {"Authorization": f"Bearer {access_token}"}
        chat_data = {
            "scenario_id": "cutscene5_llm_driven",
            "user_input": "대화 로깅 테스트",
            "user_name": username
        }

        print(f"\n📤 채팅 요청 중...")
        chat_response = requests.post(
            f"{API_URL}/api/chat",
            json=chat_data,
            headers=headers,
            timeout=120
        )

        if chat_response.status_code == 200:
            result = chat_response.json()
            session_id = result.get('session_id')
            dialogues = result.get('dialogues', [])

            print(f"✅ 채팅 성공")
            print(f"   Session ID: {session_id}")
            print(f"   응답 대화 수: {len(dialogues)}")

            # DB 확인 - user_inputs
            user_inputs_query = f"""
                SELECT COUNT(*) FROM user_inputs
                WHERE session_id = '{session_id}';
            """
            user_inputs_count = check_db(user_inputs_query).strip()

            print(f"\n📊 user_inputs 테이블 확인:")
            print(f"   세션의 user_input 레코드: {user_inputs_count}개")

            if int(user_inputs_count) > 0:
                print(f"   ✅ user_input이 저장됨!")

                # 실제 데이터 조회
                user_input_data = check_db(f"""
                    SELECT turn_number, user_input FROM user_inputs
                    WHERE session_id = '{session_id}' ORDER BY turn_number DESC LIMIT 1;
                """)
                print(f"   최근 입력: {user_input_data}")
            else:
                print(f"   ❌ user_input이 저장 안 됨 (문제 2-1 미해결)")

            # DB 확인 - dialogues
            dialogues_query = f"""
                SELECT COUNT(*) FROM dialogues
                WHERE session_id = '{session_id}';
            """
            dialogues_count = check_db(dialogues_query).strip()

            print(f"\n📊 dialogues 테이블 확인:")
            print(f"   세션의 dialogue 레코드: {dialogues_count}개")

            if int(dialogues_count) > 0:
                print(f"   ✅✅✅ dialogues가 저장됨! (문제 2 해결)")

                # 실제 대화 데이터 조회
                dialogue_data = check_db(f"""
                    SELECT turn_number, speaker, LEFT(content, 50) as content_preview
                    FROM dialogues
                    WHERE session_id = '{session_id}'
                    ORDER BY turn_number DESC, order_index
                    LIMIT 3;
                """)
                print(f"\n   최근 대화 미리보기:")
                for line in dialogue_data.split('\n'):
                    if line.strip():
                        print(f"   {line}")
            else:
                print(f"   ❌ dialogues가 저장 안 됨 (문제 2-2 미해결)")

            # 전체 통계
            print(f"\n📊 전체 DB 통계:")
            total_users = check_db("SELECT COUNT(*) FROM user_inputs;").strip()
            total_dialogues = check_db("SELECT COUNT(*) FROM dialogues;").strip()

            print(f"   전체 user_inputs: {total_users}개")
            print(f"   전체 dialogues: {total_dialogues}개")

        else:
            print(f"❌ 채팅 실패: {chat_response.text}")
    else:
        print(f"❌ 로그인 실패: {login_result}")

except Exception as e:
    print(f"❌ 에러 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("테스트 완료")
print("="*60 + "\n")
