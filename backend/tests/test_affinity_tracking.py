#!/usr/bin/env python3
"""
Affinity 자동 추적 검증 테스트

친밀도를 직접 변경하고 자동 추적이 작동하는지 확인
"""

import requests
import time
import uuid
from src.database.db_manager import DatabaseManager

print("=" * 80)
print("🧪 Affinity 자동 추적 검증 테스트")
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

test_username = f"affinitytest_{int(time.time())}"
test_password = "testpass123"

register_response = requests.post(
    "http://localhost:8000/api/auth/register",
    json={
        "username": test_username,
        "password": test_password,
        "display_name": "친밀도테스트"
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
# Step 2: 첫 세션 시작 (초기 친밀도 확인)
# ============================================================================
print("\n📋 Step 2: 첫 세션 시작")
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
    initial_affinity = result.get('affinity_scores', {})
    print(f"✅ Turn 1 성공")
    print(f"   초기 친밀도: {initial_affinity}")
else:
    print(f"❌ Turn 1 실패: {chat_response.status_code}")
    exit(1)

time.sleep(2)

# ============================================================================
# Step 3: 친밀도 직접 변경 (DB에서)
# ============================================================================
print("\n📋 Step 3: 친밀도 강제 변경")
print("-" * 80)

# 세션 스냅샷에서 state 가져오기
with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT state_json
            FROM session_snapshots
            WHERE session_id = %s
            ORDER BY turn_number DESC
            LIMIT 1
        """, (test_session_id,))

        snapshot = cur.fetchone()
        if snapshot:
            import json
            state = snapshot[0]

            # 친밀도 변경
            if 'affinity_scores' in state:
                print(f"   변경 전: {state['affinity_scores']}")
                state['affinity_scores']['tanjiro'] += 50  # +50
                state['affinity_scores']['zenitsu'] -= 30  # -30
                print(f"   변경 후: {state['affinity_scores']}")

                # 스냅샷 업데이트
                cur.execute("""
                    UPDATE session_snapshots
                    SET state_json = %s
                    WHERE session_id = %s AND turn_number = (
                        SELECT MAX(turn_number)
                        FROM session_snapshots
                        WHERE session_id = %s
                    )
                """, (json.dumps(state), test_session_id, test_session_id))

                print(f"✅ 친밀도 변경 완료:")
                print(f"   - tanjiro: {initial_affinity['tanjiro']} → {state['affinity_scores']['tanjiro']} (+50)")
                print(f"   - zenitsu: {initial_affinity['zenitsu']} → {state['affinity_scores']['zenitsu']} (-30)")

time.sleep(1)

# ============================================================================
# Step 4: 다음 턴 진행 (자동 추적 트리거)
# ============================================================================
print("\n📋 Step 4: 다음 턴 진행 (자동 추적 트리거)")
print("-" * 80)

chat_response = requests.post(
    "http://localhost:8000/api/chat",
    headers=headers,
    json={
        "session_id": test_session_id,
        "scenario_id": "cutscene5_llm_driven",
        "user_input": "알겠어",
        "user_name": "테스터"
    },
    timeout=120
)

if chat_response.status_code == 200:
    result = chat_response.json()
    new_affinity = result.get('affinity_scores', {})
    print(f"✅ Turn 2 성공")
    print(f"   현재 친밀도: {new_affinity}")
    print(f"\n💡 서버 로그에서 다음 메시지 확인:")
    print(f"   - '💞 Affinity tracked: tanjiro (... → ..., +50)'")
    print(f"   - '💞 Affinity tracked: zenitsu (... → ..., -30)'")
else:
    print(f"❌ Turn 2 실패: {chat_response.status_code}")
    exit(1)

time.sleep(2)

# ============================================================================
# Step 5: DB 검증
# ============================================================================
print("\n📋 Step 5: DB에서 Affinity 기록 확인")
print("-" * 80)

with db.get_connection() as conn:
    with conn.cursor() as cur:
        # 친밀도 기록 조회
        cur.execute("""
            SELECT
                character_name,
                affinity_score,
                change_amount,
                turn_number,
                timestamp
            FROM affinity_records
            WHERE session_id = %s
            ORDER BY timestamp DESC
        """, (test_session_id,))

        records = cur.fetchall()

        if records:
            print(f"✅ 친밀도 기록 발견: {len(records)}개")
            print()
            for character, score, change, turn, recorded_at in records:
                sign = "+" if change >= 0 else ""
                print(f"   📊 {character}")
                print(f"      현재 친밀도: {score}")
                print(f"      변화량: {sign}{change}")
                print(f"      턴: {turn}")
                print(f"      기록 시간: {recorded_at}")
                print()

            # 검증
            tanjiro_found = any(r[0] == 'tanjiro' and r[2] == 50 for r in records)
            zenitsu_found = any(r[0] == 'zenitsu' and r[2] == -30 for r in records)

            if tanjiro_found and zenitsu_found:
                print("✅✅✅ Affinity 자동 추적이 정상 작동합니다!")
            else:
                print("⚠️ 일부 친밀도 변화가 기록되지 않았습니다")
                if not tanjiro_found:
                    print("   - tanjiro +50 기록 없음")
                if not zenitsu_found:
                    print("   - zenitsu -30 기록 없음")
        else:
            print("❌ 친밀도 기록이 없습니다")
            print("   자동 추적이 작동하지 않았거나, 친밀도 변화가 감지되지 않았습니다")

print("\n" + "=" * 80)
print("🎉 Affinity 추적 검증 테스트 완료!")
print("=" * 80)
