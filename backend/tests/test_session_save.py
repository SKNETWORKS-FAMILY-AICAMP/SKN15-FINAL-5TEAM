#!/usr/bin/env python3
"""간단한 세션 저장 테스트"""
import requests
import time

API_URL = "http://localhost:8000/api/chat"

def send_message(session_id, user_input):
    payload = {
        "scenario_id": "cutscene5_llm_driven",
        "user_input": user_input,
        "user_name": "세션저장테스트"
    }
    if session_id:
        payload["session_id"] = session_id

    response = requests.post(API_URL, json=payload, timeout=60)
    return response.json()

print("=" * 60)
print("🧪 세션 저장 테스트 (5턴)")
print("=" * 60)

# 5턴만 테스트
test_inputs = [
    "안녕하세요",
    "주변을 살펴봅니다",
    "뭔가 이상한데요",
    "조심해야겠어요",
    "함께 가요",
]

session_id = None

for i, user_input in enumerate(test_inputs, 1):
    print(f"\n📤 턴 {i}: '{user_input}'")

    try:
        result = send_message(session_id, user_input)

        if not session_id:
            session_id = result.get("session_id")
            print(f"🆕 세션 생성: {session_id}")

        turn_count = result.get("turn_count", 0)
        print(f"📊 Turn Count: {turn_count}")

    except Exception as e:
        print(f"❌ 에러: {e}")
        break

    time.sleep(1)

print(f"\n{'='*60}")
print(f"✅ 최종 Session ID: {session_id}")
print(f"{'='*60}")

with open("/tmp/test_session_save_id.txt", "w") as f:
    f.write(session_id or "")

print(f"💾 Session ID 저장됨: /tmp/test_session_save_id.txt")
