"""
테스트용 dialogues 데이터 생성 스크립트

대화 요약 기능을 시연하기 위한 실제 대화 데이터를 생성합니다.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DatabaseManager


def create_test_session_with_dialogues(db: DatabaseManager):
    """
    테스트 세션과 대화 데이터 생성

    시나리오: 귀멸의 칼날 - 무한열차 편
    """
    # 새로운 테스트 세션 생성
    session_id = str(uuid.uuid4())
    user_id = None  # 익명 사용자

    print(f"🆕 테스트 세션 생성 중: {session_id[:8]}...")

    # 세션 생성
    session_data = {
        "session_id": session_id,
        "scenario_id": "mugen_train",
        "user_id": user_id,
        "user_name": "테스터",
        "current_stage": "train_prelude",
        "turn_count": 12,
        "stage_turn": 12,
        "final_ending": None,
        "is_active": True,
        "conversation_summary": "",
        "summary_turn_count": 0
    }

    success = db.save_session(session_data)
    if not success:
        print("❌ 세션 생성 실패")
        return None

    print(f"✅ 세션 생성 완료: {session_id[:8]}")

    # 12턴의 대화 생성 (귀멸의 칼날 무한열차 스토리)
    conversations = [
        # Turn 1
        {
            "turn": 1,
            "dialogues": [
                {"speaker": "user", "content": "안녕하세요, 처음 만나뵙겠습니다."},
                {"speaker": "탄지로", "content": "안녕하세요! 저는 카마도 탄지로입니다. 만나서 반갑습니다!",
                 "emotion": "기쁨", "emotion_intensity": "중간"}
            ]
        },
        # Turn 2
        {
            "turn": 2,
            "dialogues": [
                {"speaker": "user", "content": "이 열차는 어디로 가나요?"},
                {"speaker": "탄지로", "content": "이 열차는 무한열차라고 불립니다. 최근 40명 이상이 실종된 곳이죠. 우리는 이 사건을 조사하러 왔습니다.",
                 "emotion": "심각함", "emotion_intensity": "강함"},
                {"speaker": "렌고쿠", "content": "맞습니다! 염주 렌고쿠 쿄쥬로입니다! 함께 귀신을 물리칩시다!",
                 "emotion": "열정", "emotion_intensity": "매우 강함"}
            ]
        },
        # Turn 3
        {
            "turn": 3,
            "dialogues": [
                {"speaker": "user", "content": "렌고쿠님, 당신은 어떤 호흡법을 사용하시나요?"},
                {"speaker": "렌고쿠", "content": "나는 염의 호흡을 사용합니다! 염주로서 사람들을 지키는 것이 나의 사명입니다!",
                 "emotion": "자신감", "emotion_intensity": "강함"}
            ]
        },
        # Turn 4
        {
            "turn": 4,
            "dialogues": [
                {"speaker": "user", "content": "열차에 이상한 기운이 느껴지는데요..."},
                {"speaker": "탄지로", "content": "네, 저도 느꼈습니다. 귀신의 냄새가 점점 강해지고 있어요...",
                 "emotion": "긴장", "emotion_intensity": "중간"},
                {"speaker": "이노스케", "content": "크크큭! 귀신이라면 내가 먼저 찾아서 베어버리겠어!",
                 "emotion": "흥분", "emotion_intensity": "강함"}
            ]
        },
        # Turn 5
        {
            "turn": 5,
            "dialogues": [
                {"speaker": "user", "content": "조심하세요! 뭔가 이상해요!"},
                {"speaker": "탄지로", "content": "앗, 졸음이... 이건 혈귀술인가?!",
                 "emotion": "놀람", "emotion_intensity": "강함"}
            ]
        },
        # Turn 6
        {
            "turn": 6,
            "dialogues": [
                {"speaker": "user", "content": "탄지로님! 정신 차리세요!"},
                {"speaker": "네즈코", "content": "으응... 오빠...",
                 "emotion": "걱정", "emotion_intensity": "중간"},
                {"speaker": "탄지로", "content": "네즈코! 꿈속이었구나... 모두를 깨워야 해!",
                 "emotion": "결의", "emotion_intensity": "매우 강함"}
            ]
        },
        # Turn 7
        {
            "turn": 7,
            "dialogues": [
                {"speaker": "user", "content": "하현의 일이 나타났어요!"},
                {"speaker": "엔무", "content": "후후후... 좋은 꿈 꾸고 계셨나요? 영원히 꿈속에서 사시는 게 행복하지 않으신가요?",
                 "emotion": "교활함", "emotion_intensity": "강함"},
                {"speaker": "탄지로", "content": "우리는 꿈이 아닌 현실을 살아갑니다! 물의 호흡, 일의 형!",
                 "emotion": "분노", "emotion_intensity": "강함"}
            ]
        },
        # Turn 8
        {
            "turn": 8,
            "dialogues": [
                {"speaker": "user", "content": "승객들을 구해야 해요!"},
                {"speaker": "렌고쿠", "content": "그렇습니다! 승객들을 절대 다치게 할 수 없습니다! 염의 호흡, 오의 형!",
                 "emotion": "보호 본능", "emotion_intensity": "매우 강함"}
            ]
        },
        # Turn 9
        {
            "turn": 9,
            "dialogues": [
                {"speaker": "user", "content": "이노스케, 젠이츠도 깨어났네요!"},
                {"speaker": "이노스케", "content": "크하하! 이제 제대로 싸울 수 있어! 짐승의 호흡!",
                 "emotion": "전투 열망", "emotion_intensity": "매우 강함"},
                {"speaker": "젠이츠", "content": "으아아... 무서워... 하지만 도망칠 순 없어! 뇌의 호흡, 일의 형!",
                 "emotion": "공포와 용기", "emotion_intensity": "중간"}
            ]
        },
        # Turn 10
        {
            "turn": 10,
            "dialogues": [
                {"speaker": "user", "content": "엔무가 열차와 융합했어요!"},
                {"speaker": "탄지로", "content": "열차 전체가 귀신이 된 건가?! 핵을 찾아야 해!",
                 "emotion": "당혹", "emotion_intensity": "강함"},
                {"speaker": "렌고쿠", "content": "탄지로! 네가 목을 베어라! 나는 승객들을 지키겠다!",
                 "emotion": "신뢰", "emotion_intensity": "강함"}
            ]
        },
        # Turn 11
        {
            "turn": 11,
            "dialogues": [
                {"speaker": "user", "content": "탄지로님! 목뼈를 찾았어요!"},
                {"speaker": "탄지로", "content": "히노카미 카구라... 원무!",
                 "emotion": "집중", "emotion_intensity": "매우 강함"},
                {"speaker": "엔무", "content": "으악... 그럴 수가... 무한님...",
                 "emotion": "절망", "emotion_intensity": "강함"}
            ]
        },
        # Turn 12
        {
            "turn": 12,
            "dialogues": [
                {"speaker": "user", "content": "해냈어요! 엔무를 쓰러뜨렸어요!"},
                {"speaker": "렌고쿠", "content": "훌륭합니다! 모두들 잘 싸웠어요! 하지만... 아직 끝나지 않았습니다. 더 강한 기운이 느껴집니다...",
                 "emotion": "경계", "emotion_intensity": "강함"},
                {"speaker": "탄지로", "content": "이 기운은... 상현의 귀신?!",
                 "emotion": "충격", "emotion_intensity": "매우 강함"}
            ]
        }
    ]

    print("\n💬 대화 데이터 삽입 중...")

    total_dialogues = 0
    for conv in conversations:
        turn = conv["turn"]
        dialogues = conv["dialogues"]

        for idx, dialogue in enumerate(dialogues):
            try:
                with db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO dialogues
                            (session_id, turn_number, speaker, content,
                             emotion, emotion_intensity, order_index, timestamp)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            session_id,
                            turn,
                            dialogue.get("speaker"),
                            dialogue.get("content"),
                            dialogue.get("emotion"),
                            dialogue.get("emotion_intensity"),
                            idx
                        ))

                total_dialogues += 1

            except Exception as e:
                print(f"  ❌ Turn {turn} 대화 {idx} 삽입 실패: {e}")
                return None

        print(f"  ✅ Turn {turn}: {len(dialogues)}개 대화 삽입")

    print(f"\n✅ 총 {total_dialogues}개 대화 삽입 완료!")
    print(f"📊 세션 ID: {session_id}")
    print(f"📊 턴 수: {len(conversations)}")

    return session_id


def verify_dialogues(db: DatabaseManager, session_id: str):
    """생성된 대화 데이터 검증"""
    print("\n" + "=" * 60)
    print("🔍 생성된 대화 데이터 검증")
    print("=" * 60)

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # 총 대화 수
            cur.execute("""
                SELECT COUNT(*) FROM dialogues WHERE session_id = %s
            """, (session_id,))
            total = cur.fetchone()[0]

            # 턴별 대화 수
            cur.execute("""
                SELECT turn_number, COUNT(*)
                FROM dialogues
                WHERE session_id = %s
                GROUP BY turn_number
                ORDER BY turn_number
            """, (session_id,))
            turns = cur.fetchall()

            print(f"📊 총 대화 수: {total}개")
            print(f"📊 턴 수: {len(turns)}개")
            print("\n턴별 대화 수:")
            for turn, count in turns:
                print(f"  Turn {turn}: {count}개")

    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("테스트 dialogues 데이터 생성 스크립트")
    print("=" * 60)

    # DatabaseManager 초기화
    db = DatabaseManager(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5433")),
        dbname=os.getenv("DB_NAME", "kimedb"),
        user=os.getenv("DB_USER", "kime"),
        password=os.getenv("DB_PASSWORD", "dev123")
    )

    # 테스트 데이터 생성
    session_id = create_test_session_with_dialogues(db)

    if session_id:
        # 검증
        verify_dialogues(db, session_id)

        print("\n" + "=" * 60)
        print("✅ 테스트 데이터 생성 완료!")
        print("=" * 60)
        print(f"\n다음 명령으로 대화 요약을 생성할 수 있습니다:")
        print(f"python scripts/backfill_conversation_summaries.py --min-turns 10")
        print("=" * 60)
    else:
        print("\n❌ 테스트 데이터 생성 실패")
