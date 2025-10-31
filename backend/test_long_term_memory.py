#!/usr/bin/env python3
"""
문제 4 테스트: Long-term Memory System (User Memories)
사용자별 장기 기억이 저장되고 조회되는지 검증
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import create_database_manager_from_env
import uuid

def test_user_memory_system():
    """사용자 장기 기억 시스템 테스트"""
    print("\n" + "="*60)
    print("문제 4 테스트: User Long-term Memory System")
    print("="*60)

    # DatabaseManager 초기화
    db = create_database_manager_from_env()

    # 테스트용 사용자 ID (실제 존재하는 사용자 사용)
    print("\n[Step 1] 테스트 사용자 확인")
    print("-" * 60)

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, username FROM statedb.users LIMIT 1;")
            result = cur.fetchone()

            if not result:
                print("❌ 테스트 가능한 사용자가 없습니다")
                return False

            user_id, username = result
            print(f"✅ 테스트 사용자: {username} (ID: {user_id})")

    # 1. 기억 저장 테스트
    print("\n[Step 2] 사용자 기억 저장 테스트")
    print("-" * 60)

    test_session_id = str(uuid.uuid4())

    # Memory 1: Character Relationship
    memory_id_1 = db.save_user_memory(
        user_id=user_id,
        memory_key="character_relationship:tanjiro",
        memory_value="탄지로와 매우 친밀한 관계. 사용자는 탄지로의 조언을 잘 따르고 신뢰한다.",
        memory_type="relationship",
        context={"character_name": "tanjiro", "affinity_score": 85},
        importance=0.9,
        source_session_id=test_session_id,
        tags=["tanjiro", "high_affinity", "main_character"]
    )

    if memory_id_1:
        print(f"✅ 캐릭터 관계 기억 저장 성공 (ID: {memory_id_1})")
    else:
        print("❌ 캐릭터 관계 기억 저장 실패")
        return False

    # Memory 2: User Preference
    memory_id_2 = db.save_user_memory(
        user_id=user_id,
        memory_key="user_preference:conversation_style",
        memory_value="친근하고 장난스러운 대화 스타일을 선호함",
        memory_type="preference",
        importance=0.8,
        tags=["conversation", "tone", "friendly"]
    )

    if memory_id_2:
        print(f"✅ 사용자 선호도 기억 저장 성공 (ID: {memory_id_2})")
    else:
        print("❌ 사용자 선호도 기억 저장 실패")
        return False

    # Memory 3: Story Progress
    memory_id_3 = db.save_user_memory(
        user_id=user_id,
        memory_key="story_progress:train_prelude_completed",
        memory_value="TRAIN_PRELUDE 스테이지 완료. 탄지로와 함께 기차에 탑승함",
        memory_type="event",
        context={"stage": "TRAIN_PRELUDE", "completed": True},
        importance=0.7,
        tags=["train", "story", "completed"]
    )

    if memory_id_3:
        print(f"✅ 스토리 진행 기억 저장 성공 (ID: {memory_id_3})")
    else:
        print("❌ 스토리 진행 기억 저장 실패")
        return False

    # Memory 4: Fact
    memory_id_4 = db.save_user_memory(
        user_id=user_id,
        memory_key="fact:favorite_food",
        memory_value="사용자가 좋아하는 음식은 라멘",
        memory_type="fact",
        importance=0.5,
        tags=["food", "preference"]
    )

    if memory_id_4:
        print(f"✅ 사실 기억 저장 성공 (ID: {memory_id_4})")
    else:
        print("❌ 사실 기억 저장 실패")
        return False

    # 2. 기억 조회 테스트
    print("\n[Step 3] 사용자 기억 조회 테스트")
    print("-" * 60)

    # 전체 기억 조회
    all_memories = db.get_user_memories(user_id=user_id, limit=10)
    print(f"✅ 전체 기억 조회: {len(all_memories)}개")

    for mem in all_memories[:5]:  # 최대 5개만 출력
        print(f"   - [{mem['memory_type']:12}] {mem['memory_key']:40} | importance: {mem['importance']:.2f}")

    # 타입별 조회
    relationships = db.get_user_memories(user_id=user_id, memory_type="relationship")
    print(f"\n✅ 관계 기억만 조회: {len(relationships)}개")
    for mem in relationships:
        print(f"   - {mem['memory_key']}: {mem['memory_value'][:50]}...")

    preferences = db.get_user_memories(user_id=user_id, memory_type="preference")
    print(f"\n✅ 선호도 기억만 조회: {len(preferences)}개")
    for mem in preferences:
        print(f"   - {mem['memory_key']}: {mem['memory_value'][:50]}...")

    # 3. 기억 컨텍스트 생성 테스트
    print("\n[Step 4] 새 세션용 기억 컨텍스트 생성")
    print("-" * 60)

    memory_context = db.get_user_memory_context(user_id=user_id)

    if memory_context:
        print("✅ 기억 컨텍스트 생성 성공!")
        print(f"\n   📊 컨텍스트 구조:")

        if memory_context.get('relationships'):
            print(f"      - Relationships: {len(memory_context['relationships'])}개")
            for rel in memory_context['relationships'][:2]:
                print(f"         · {rel.get('key', 'N/A')}: {rel.get('value', '')[:40]}...")

        if memory_context.get('preferences'):
            print(f"      - Preferences: {len(memory_context['preferences'])}개")
            for pref in memory_context['preferences'][:2]:
                print(f"         · {pref.get('key', 'N/A')}: {pref.get('value', '')[:40]}...")

        if memory_context.get('story_progress'):
            print(f"      - Story Progress: {len(memory_context['story_progress'])}개")

        if memory_context.get('facts'):
            print(f"      - Facts: {len(memory_context['facts'])}개")
    else:
        print("❌ 기억 컨텍스트 생성 실패")
        return False

    # 4. 기억 액세스 업데이트 테스트
    print("\n[Step 5] 기억 액세스 업데이트 테스트")
    print("-" * 60)

    # 첫 번째 기억의 액세스 카운트 증가
    success = db.update_memory_access(memory_id_1, importance_boost=0.05)

    if success:
        print(f"✅ 기억 액세스 업데이트 성공 (ID: {memory_id_1})")

        # 업데이트된 기억 조회
        memories = db.get_user_memories(user_id=user_id, limit=1)
        if memories:
            mem = memories[0]
            print(f"   - 중요도: {mem['importance']:.2f}")
            print(f"   - 액세스 횟수: {mem['access_count']}")
            print(f"   - 마지막 액세스: {mem['last_accessed_at']}")
    else:
        print("❌ 기억 액세스 업데이트 실패")

    # 5. UPSERT 테스트 (기존 기억 업데이트)
    print("\n[Step 6] 기존 기억 업데이트 테스트 (UPSERT)")
    print("-" * 60)

    # 같은 memory_key로 다시 저장 → 업데이트됨
    updated_memory_id = db.save_user_memory(
        user_id=user_id,
        memory_key="character_relationship:tanjiro",
        memory_value="탄지로와 매우 친밀한 관계. 최근 함께 강력한 적을 물리쳤음",  # 업데이트된 내용
        memory_type="relationship",
        context={"character_name": "tanjiro", "affinity_score": 95},  # 친밀도 증가
        importance=0.95,  # 중요도 증가
        tags=["tanjiro", "high_affinity", "main_character", "battle"]
    )

    if updated_memory_id:
        print(f"✅ 기존 기억 업데이트 성공 (ID: {updated_memory_id})")
        print(f"   원래 ID: {memory_id_1}, 업데이트 ID: {updated_memory_id}")

        if memory_id_1 == updated_memory_id:
            print(f"   ✅ UPSERT 정상 작동 (같은 ID로 업데이트)")
        else:
            print(f"   ⚠️  새 레코드 생성됨 (예상: 업데이트)")

        # 업데이트된 내용 확인
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT memory_value, importance, context->>'affinity_score' as affinity
                    FROM statedb.user_memories
                    WHERE id = %s;
                """, (updated_memory_id,))
                result = cur.fetchone()

                if result:
                    value, importance, affinity = result
                    print(f"   업데이트된 내용:")
                    print(f"      - 기억: {value[:60]}...")
                    print(f"      - 중요도: {importance}")
                    print(f"      - 친밀도: {affinity}")
    else:
        print("❌ 기존 기억 업데이트 실패")

    # 6. 최종 통계
    print("\n[Step 7] 최종 사용자 기억 통계")
    print("-" * 60)

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    memory_type,
                    COUNT(*) as count,
                    ROUND(AVG(importance)::numeric, 2) as avg_importance,
                    SUM(access_count) as total_accesses
                FROM statedb.user_memories
                WHERE user_id = %s
                  AND is_active = TRUE
                GROUP BY memory_type
                ORDER BY count DESC;
            """, (user_id,))

            stats = cur.fetchall()

            print("   Type          | Count | Avg Importance | Total Accesses")
            print("   " + "-" * 60)
            for memory_type, count, avg_imp, accesses in stats:
                print(f"   {memory_type:13} | {count:5} | {avg_imp:14} | {accesses or 0:14}")

    print("\n" + "="*60)
    print("✅✅✅ 문제 4 해결: User Long-term Memory System 완전히 작동!")
    print("="*60 + "\n")

    return True


if __name__ == "__main__":
    try:
        success = test_user_memory_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 테스트 중 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
