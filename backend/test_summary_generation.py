"""
대화 요약 생성 테스트 (Turn 10에서 자동 생성)
"""
import requests
import json
import time

API_URL = "http://localhost:8000/api/chat"

# 새로운 세션 ID
test_session_id = None

# 10개의 테스트 대화
test_conversations = [
    "안녕하세요",
    "무한열차에 대해 알려주세요",
    "렌고쿠는 어떤 사람인가요?",
    "아카자와 싸워야 하나요?",
    "불의 호흡을 배우고 싶어요",
    "히노카미 카구라는 무엇인가요?",
    "우리는 어디로 가야 하나요?",
    "승객들이 이상해요",
    "이 상황을 어떻게 해결해야 할까요?",
    "모두를 지켜야 해요",  # 10턴째 - 요약 생성 트리거
]

print("="*70)
print("🧪 대화 요약 자동 생성 테스트")
print("="*70)

for i, user_input in enumerate(test_conversations, 1):
    print(f"\n{'='*70}")
    print(f"📤 Turn {i}: {user_input}")
    print(f"{'='*70}")

    payload = {
        "scenario_id": "cutscene5_llm_driven",
        "user_input": user_input,
        "user_name": "요약테스트",
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

            if turn_count >= 10:
                print("🎯 Turn 10 도달! 대화 요약이 생성되었을 것입니다.")

        else:
            print(f"❌ 에러: {response.status_code}")
            print(f"   {response.text}")
            break

    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        break

    # 요청 사이 약간의 대기
    time.sleep(1)

# 요약 생성 확인
if test_session_id:
    print(f"\n{'='*70}")
    print("🔍 데이터베이스 검증")
    print(f"{'='*70}")

    import psycopg2

    try:
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5433,
            dbname="kimedb",
            user="kime",
            password="dev123"
        )

        with conn.cursor() as cur:
            # 세션 정보 확인
            cur.execute("""
                SELECT
                    turn_count,
                    summary_turn_count,
                    LENGTH(conversation_summary) as summary_length,
                    LEFT(conversation_summary, 100) as summary_preview
                FROM statedb.sessions
                WHERE session_id = %s
            """, (test_session_id,))

            result = cur.fetchone()

            if result:
                turn_count, summary_turn, summary_len, summary_preview = result

                print(f"\n세션 정보:")
                print(f"  - 현재 턴: {turn_count}")
                print(f"  - 요약 시점: Turn {summary_turn}")
                print(f"  - 요약 길이: {summary_len}자")

                if summary_len and summary_len > 0:
                    print(f"\n✅ 대화 요약 생성 성공!")
                    print(f"\n요약 미리보기:")
                    print(f"  {summary_preview}...")
                else:
                    print(f"\n⚠️ 대화 요약이 아직 생성되지 않았습니다.")

            # 저장된 대화 수 확인
            cur.execute("""
                SELECT COUNT(*) FROM statedb.dialogues
                WHERE session_id = %s
            """, (test_session_id,))

            dialogue_count = cur.fetchone()[0]
            print(f"\n저장된 대화: {dialogue_count}개")

        conn.close()

        print(f"\n{'='*70}")
        print("✅ 테스트 완료!")
        print(f"{'='*70}")

    except Exception as e:
        print(f"❌ DB 조회 실패: {e}")
