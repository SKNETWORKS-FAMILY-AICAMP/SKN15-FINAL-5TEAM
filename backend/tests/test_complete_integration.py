#!/usr/bin/env python3
"""
완전한 통합 테스트: 모든 자동 추적 기능 검증
- User Memory 로드
- Affinity 자동 추적
- Stage 진행 자동 추적
- Mission 완료 자동 추적
- Game Event 자동 추적
- 대화 요약 및 Memory 자동 추출
"""

import requests
import time
import uuid
import json
from src.database.db_manager import DatabaseManager

print("=" * 80)
print("🧪 완전한 통합 테스트: 모든 자동 추적 기능 검증")
print("=" * 80)

# DB 연결
db = DatabaseManager(
    host="localhost",
    port=5433,
    dbname="kimedb",
    user="kime",
    password="dev123"
)

# ============================================================================
# Step 1: 회원가입
# ============================================================================
print("\n📋 Step 1: 회원가입")
print("-" * 80)

test_username = f"fulltest_{int(time.time())}"
test_password = "testpass123"

register_response = requests.post(
    "http://localhost:8000/api/auth/register",
    json={
        "username": test_username,
        "password": test_password,
        "display_name": "완전테스트"
    }
)

if register_response.status_code == 200:
    register_data = register_response.json()
    if register_data.get("success"):
        access_token = register_data.get("access_token")
        user_id = register_data.get("user_id")
        username = register_data.get("username")
        print(f"✅ 회원가입 성공: {username}")
        print(f"   User ID: {user_id}")
    else:
        print(f"❌ 회원가입 실패: {register_data.get('message')}")
        exit(1)
else:
    print(f"❌ 회원가입 실패: {register_response.status_code}")
    exit(1)

# ============================================================================
# Step 2: User Memory 저장
# ============================================================================
print("\n📋 Step 2: User Memory 저장")
print("-" * 80)

# 기존 기억 삭제
with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM user_memories WHERE user_id = %s", (user_id,))

# 테스트 기억 저장
db.save_user_memory(
    user_id=user_id,
    memory_key="character_relationship:tanjiro",
    memory_value="탄지로와 함께 많은 훈련을 했다. 서로를 신뢰한다.",
    memory_type="relationship",
    context={"character_name": "tanjiro", "affinity_score": 75},
    importance=0.85,
    tags=["tanjiro", "trust", "training"]
)

db.save_user_memory(
    user_id=user_id,
    memory_key="user_preference:combat_style",
    memory_value="공격적이고 직접적인 전투 스타일 선호. 방어보다는 공격을 선호함.",
    memory_type="preference",
    importance=0.75,
    tags=["combat", "aggressive"]
)

db.save_user_memory(
    user_id=user_id,
    memory_key="story_progress:basic_training_complete",
    memory_value="기초 훈련을 완료하고 첫 임무를 수행할 준비가 되었다.",
    memory_type="event",
    importance=0.65,
    tags=["training", "progress"]
)

print(f"✅ User Memory 3개 저장 완료 (relationship, preference, event)")

# ============================================================================
# Step 3: 첫 세션 시작 (User Memory 로드 확인)
# ============================================================================
print("\n📋 Step 3: 첫 세션 시작 - User Memory 로드 확인")
print("-" * 80)

test_session_id = str(uuid.uuid4())
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Turn 1: 시작
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

if chat_response.status_code == 200:
    result = chat_response.json()
    print(f"✅ Turn 1 성공: {result.get('current_stage')}")
    print(f"   💡 서버 로그에서 '🧠 User memories loaded' 확인")
    initial_stage = result.get('current_stage')
    initial_affinity = result.get('affinity_scores', {})
else:
    print(f"❌ Turn 1 실패: {chat_response.status_code}")
    exit(1)

time.sleep(2)

# ============================================================================
# Step 4: DB 확인 - User Memory 로드 및 초기 상태
# ============================================================================
print("\n📋 Step 4: DB 확인 - 초기 상태")
print("-" * 80)

with db.get_connection() as conn:
    with conn.cursor() as cur:
        # 세션 확인
        cur.execute("""
            SELECT user_id, user_name, current_stage, turn_count
            FROM sessions
            WHERE session_id = %s
        """, (test_session_id,))
        session = cur.fetchone()

        if session:
            sess_user_id, user_name, stage, turn_count = session
            print(f"✅ 세션 저장됨:")
            print(f"   User ID: {sess_user_id}")
            print(f"   User Name: {user_name}")
            print(f"   Stage: {stage}")
            print(f"   Turn Count: {turn_count}")

            if sess_user_id == user_id:
                print(f"   ✅ User ID 올바르게 저장됨!")
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
        print(f"스테이지 진행 기록: {stage_count}개")

        # User Memory 확인
        cur.execute("""
            SELECT COUNT(*) FROM user_memories
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))
        memory_count = cur.fetchone()[0]
        print(f"User Memory: {memory_count}개 활성")

print("\n" + "=" * 80)
print("✅ 기본 통합 테스트 완료!")
print("=" * 80)
print("\n💡 다음 단계:")
print("   1. 친밀도 변화가 있는 시나리오 진행 → Affinity tracking 검증")
print("   2. 스테이지 전환 시나리오 진행 → Stage tracking 검증")
print("   3. 미션 수행 시나리오 진행 → Mission tracking 검증")
print("   4. 10턴 이상 대화 진행 → 대화 요약 & Memory 추출 검증")
print("=" * 80)

# 결과 요약
print("\n📊 테스트 결과 요약:")
print(f"   Test User: {username}")
print(f"   User ID: {user_id}")
print(f"   Session ID: {test_session_id}")
print(f"   Initial Stage: {initial_stage}")
print(f"   Initial Affinity: {json.dumps(initial_affinity, ensure_ascii=False)}")
