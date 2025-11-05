"""
데이터 적재 플로우 테스트
"""
import requests
import json
import time
import uuid

API_URL = "http://localhost:8000/api/chat"

# 새로운 세션 ID 생성
test_session_id = None

# 테스트 대화들
test_conversations = [
    "안녕하세요, 렌고쿠님",
    "지금 무엇을 하고 계신가요?",
    "아카자에 대해 알려주세요",
    "우리가 어떻게 대응해야 할까요?",
    "불의 호흡을 가르쳐주실 수 있나요?",
]

print("="*60)
print("🧪 데이터 적재 플로우 테스트 시작")
print("="*60)

for i, user_input in enumerate(test_conversations, 1):
    print(f"\n{'='*60}")
    print(f"📤 Turn {i}: {user_input}")
    print(f"{'='*60}")

    payload = {
        "scenario_id": "cutscene5_llm_driven",
        "user_input": user_input,
        "user_name": "플로우테스트",
    }

    if test_session_id:
        payload["session_id"] = test_session_id

    try:
        response = requests.post(API_URL, json=payload, timeout=120)

        if response.status_code == 200:
            data = response.json()
            test_session_id = data.get("session_id")
            turn_count = data.get("turn_count", 0)

            print(f"✅ 응답 성공 (Turn {turn_count})")
            print(f"📌 Session ID: {test_session_id}")

            # 첫 번째 응답만 출력
            agent_responses = data.get("agent_responses", [])
            if agent_responses:
                first_response = agent_responses[0]
                speaker = first_response.get("speaker", "Unknown")
                content = first_response.get("content", "")[:150]
                print(f"🗨️  {speaker}: {content}...")
        else:
            print(f"❌ 에러: {response.status_code}")
            print(f"   {response.text}")

    except Exception as e:
        print(f"❌ 예외 발생: {e}")

    # 요청 사이 약간의 대기
    time.sleep(1)

print(f"\n{'='*60}")
print(f"✅ 테스트 완료! Session ID: {test_session_id}")
print(f"{'='*60}")
print("\n이제 데이터베이스를 확인하여 데이터 적재를 검증합니다...\n")
