#!/usr/bin/env python3
"""
간단한 통합 테스트: 실제 로그인 → 채팅 → DB 확인
"""

import requests
import time
import uuid

print("=" * 70)
print("🧪 간단 통합 테스트: Workflow & Database")
print("=" * 70)

# Step 1: 회원가입 또는 로그인
print("\n📋 Step 1: 회원가입/로그인")
print("-" * 70)

# 회원가입 시도
test_username = f"integrationtest_{int(time.time())}"
test_password = "testpass123"

register_response = requests.post(
    "http://localhost:8000/api/auth/register",
    json={
        "username": test_username,
        "password": test_password,
        "display_name": "통합테스트"
    }
)

if register_response.status_code == 200:
    register_data = register_response.json()
    if register_data.get("success"):
        print(f"✅ 회원가입 성공: {test_username}")
        access_token = register_data.get("access_token")
        user_id = register_data.get("user_id")
        username = register_data.get("username")
    else:
        print(f"❌ 회원가입 실패: {register_data.get('message')}")
        exit(1)
else:
    print(f"❌ 회원가입 실패: {register_response.status_code}")
    exit(1)

print(f"✅ 로그인 성공")
print(f"   User: {username}")
print(f"   User ID: {user_id}")
print(f"   Token: {access_token[:20]}...")

# Step 2: User Memory 저장
print("\n📋 Step 2: User Memory 저장")
print("-" * 70)

from src.database.db_manager import DatabaseManager

db = DatabaseManager(
    host="localhost",
    port=5433,
    dbname="kimedb",
    user="kime",
    password="dev123"
)

# 기존 기억 삭제
with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM user_memories WHERE user_id = %s", (user_id,))

# 테스트 기억 저장
db.save_user_memory(
    user_id=user_id,
    memory_key="character_relationship:rengoku",
    memory_value="렌고쿠와 함께 많은 전투를 해왔다",
    memory_type="relationship",
    context={"character_name": "rengoku", "affinity_score": 85},
    importance=0.9,
    tags=["rengoku", "high_affinity"]
)

db.save_user_memory(
    user_id=user_id,
    memory_key="user_preference:battle_style",
    memory_value="공격적이고 적극적인 전투 스타일 선호",
    memory_type="preference",
    importance=0.7,
    tags=["battle", "preference"]
)

print(f"✅ User Memory 2개 저장 완료")

# Step 3: 새 세션 시작 (User Memory 로드 확인)
print("\n📋 Step 3: 새 세션 시작")
print("-" * 70)

test_session_id = str(uuid.uuid4())
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

chat_response = requests.post(
    "http://localhost:8000/api/chat",
    headers=headers,
    json={
        "session_id": test_session_id,
        "scenario_id": "cutscene5_llm_driven",
        "user_input": "시작",
        "user_name": "테스터"
    },
    timeout=120
)

if chat_response.status_code != 200:
    print(f"❌ 채팅 실패: {chat_response.status_code}")
    print(f"   {chat_response.text}")
else:
    result = chat_response.json()
    print(f"✅ 채팅 성공")
    print(f"   Session: {result.get('session_id')}")
    print(f"   Turn: {result.get('turn_count')}")
    print(f"   Stage: {result.get('current_stage')}")
    print(f"   Dialogues: {len(result.get('dialogues', []))}")
    print(f"\n💡 서버 로그에서 다음 메시지를 확인하세요:")
    print(f"   - '🧠 User memories loaded'")
    print(f"   - 'Relationships: 1'")
    print(f"   - 'Preferences: 1'")

time.sleep(1)

# Step 4: DB 확인
print("\n📋 Step 4: DB 확인")
print("-" * 70)

# 세션 확인
with db.get_connection() as conn:
    with conn.cursor() as cur:
        # 세션 user_id 확인
        cur.execute("""
            SELECT user_id, user_name, current_stage
            FROM sessions
            WHERE session_id = %s
        """, (test_session_id,))
        session = cur.fetchone()

        if session:
            sess_user_id, user_name, stage = session
            print(f"✅ 세션 저장됨")
            print(f"   User ID: {sess_user_id}")
            print(f"   User Name: {user_name}")
            print(f"   Stage: {stage}")

            if sess_user_id == user_id:
                print(f"   ✅✅✅ User ID가 올바르게 저장됨!")
            else:
                print(f"   ❌ User ID 불일치!")
        else:
            print(f"❌ 세션이 저장되지 않음")

        # 친밀도 기록 확인
        cur.execute("""
            SELECT COUNT(*) FROM affinity_records
            WHERE session_id = %s
        """, (test_session_id,))
        affinity_count = cur.fetchone()[0]
        print(f"\n친밀도 기록: {affinity_count}개")

        # 스테이지 기록 확인
        cur.execute("""
            SELECT COUNT(*) FROM stage_progression
            WHERE session_id = %s
        """, (test_session_id,))
        stage_count = cur.fetchone()[0]
        print(f"스테이지 기록: {stage_count}개")

print("\n" + "=" * 70)
print("🎉 테스트 완료!")
print("=" * 70)
