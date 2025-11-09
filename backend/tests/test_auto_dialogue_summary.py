"""
대화 자동 저장 및 요약 생성 테스트
"""
import requests
import json
import time

API_URL = "http://localhost:8000/api/chat"

# 테스트 대화 입력들
test_inputs = [
    "안녕하세요",
    "지금 어디 있어요?",
    "상현 삼이 나타났나요?",
    "렌고쿠는 어떻게 하고 있나요?",
    "탄지로와 대화하고 싶어요",
    "불의 호흡에 대해 알려주세요",
    "히노카미 카구라는 무엇인가요?",
    "아카자는 어디 있나요?",
    "우리는 어떻게 해야 하나요?",
    "모두를 지켜야 해요!",  # 10턴째 - 요약 생성 트리거
]

def send_chat_request(user_input, session_id=None):
    """챗 요청 전송"""
    payload = {
        "scenario_id": "cutscene5_llm_driven",
        "user_input": user_input,
        "user_name": "자동화테스트",
    }

    if session_id:
        payload["session_id"] = session_id

    try:
        print(f"\n{'='*60}")
        print(f"📤 요청: {user_input}")

        response = requests.post(API_URL, json=payload, timeout=120)

        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            turn_count = data.get("turn_count", 0)

            print(f"✅ 응답 성공 (Turn {turn_count})")
            print(f"📌 Session ID: {session_id}")

            # 에이전트 응답 출력
            agent_responses = data.get("agent_responses", [])
            for resp in agent_responses[:1]:  # 첫 응답만 출력
                speaker = resp.get("speaker", "Unknown")
                content = resp.get("content", "")[:100]  # 처음 100자만
                print(f"🗨️  {speaker}: {content}...")

            return session_id, turn_count
        else:
            print(f"❌ 에러: {response.status_code}")
            print(f"   {response.text}")
            return None, 0

    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return None, 0


def verify_dialogues(session_id):
    """dialogues 테이블 확인"""
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
            cur.execute("""
                SELECT turn_number, speaker, content
                FROM dialogues
                WHERE session_id = %s
                ORDER BY turn_number, dialogue_order
            """, (session_id,))

            dialogues = cur.fetchall()

            print(f"\n{'='*60}")
            print(f"📊 저장된 대화: {len(dialogues)}개")
            print(f"{'='*60}")

            for turn, speaker, content in dialogues[:5]:  # 처음 5개만
                print(f"Turn {turn} - {speaker}: {content[:50]}...")

            if len(dialogues) > 5:
                print(f"... (외 {len(dialogues) - 5}개)")

        conn.close()
        return len(dialogues)

    except Exception as e:
        print(f"❌ DB 조회 실패: {e}")
        return 0


def verify_summary(session_id):
    """conversation_summary 확인"""
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
            cur.execute("""
                SELECT conversation_summary, summary_turn_count, turn_count
                FROM sessions
                WHERE session_id = %s
            """, (session_id,))

            result = cur.fetchone()

            if result:
                summary, summary_turn, turn_count = result

                print(f"\n{'='*60}")
                print(f"📝 대화 요약 생성 결과")
                print(f"{'='*60}")
                print(f"현재 턴: {turn_count}")
                print(f"요약 시점: Turn {summary_turn}")
                print(f"요약 길이: {len(summary) if summary else 0}자")

                if summary:
                    print(f"\n📄 요약 내용:")
                    print(f"{summary[:300]}...")
                    return True
                else:
                    print("⚠️  요약이 아직 생성되지 않았습니다 (10턴 미만)")
                    return False

        conn.close()

    except Exception as e:
        print(f"❌ DB 조회 실패: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("🧪 대화 자동 저장 및 요약 생성 테스트")
    print("="*60)

    session_id = None

    # 10개의 대화 전송
    for i, user_input in enumerate(test_inputs, 1):
        session_id, turn_count = send_chat_request(user_input, session_id)

        if not session_id:
            print("❌ 테스트 중단")
            break

        # 각 요청 사이 약간의 대기
        time.sleep(1)

    if session_id:
        print("\n" + "="*60)
        print("🔍 결과 검증")
        print("="*60)

        # 1. 대화 저장 확인
        dialogue_count = verify_dialogues(session_id)

        # 2. 요약 생성 확인
        summary_generated = verify_summary(session_id)

        # 최종 결과
        print("\n" + "="*60)
        print("📊 최종 결과")
        print("="*60)
        print(f"✅ 대화 자동 저장: {'성공' if dialogue_count > 0 else '실패'} ({dialogue_count}개)")
        print(f"✅ 요약 자동 생성: {'성공' if summary_generated else '실패 (10턴 미만)'}")
        print("="*60)
