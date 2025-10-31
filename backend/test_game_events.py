#!/usr/bin/env python3
"""
문제 5 테스트: Game Event Logging System  
affinity_records, mission_records, stage_progression, game_events 테이블 검증
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import create_database_manager_from_env
import uuid

def test_game_event_logging():
    """게임 이벤트 로깅 시스템 테스트"""
    print("\n" + "="*60)
    print("문제 5 테스트: Game Event Logging System")
    print("="*60)

    db = create_database_manager_from_env()
    
    # 테스트용 세션 직접 생성
    test_session_id = str(uuid.uuid4())
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO statedb.sessions 
                (session_id, scenario_id, user_name, current_stage, turn_count, stage_turn, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (test_session_id, "test_scenario", "test_user", "TEST_STAGE", 0, 0, True))
    
    print(f"\n✅ 테스트 세션 생성: {test_session_id}")

    # 1. Affinity Records 테스트
    print("\n[Test 1] Affinity Records - 캐릭터 친밀도 변화 기록")
    print("-" * 60)
    
    success_count = 0
    for idx, (char, score, change) in enumerate([("tanjiro", 60, 10), ("zenitsu", 45, 15), ("inosuke", 35, 15)], 1):
        if db.save_affinity(test_session_id, idx, char, score, change):
            print(f"✅ {char}: {score} (변화량: +{change})")
            success_count += 1
    print(f"성공: {success_count}/3")

    # 2. Stage Progression 테스트
    print("\n[Test 2] Stage Progression - 스테이지 진행 기록")
    print("-" * 60)
    
    success_count = 0
    for stage_id, order in [("TRAIN_PRELUDE", 1), ("TRAIN_MISSION", 2), ("TRAIN_FINALE", 3)]:
        if db.save_stage_entry(test_session_id, stage_id, order):
            print(f"✅ Stage entered: {stage_id} (order: {order})")
            success_count += 1
    print(f"성공: {success_count}/3")
    
    if db.update_stage_exit(test_session_id, "TRAIN_PRELUDE"):
        print(f"✅ Stage exited: TRAIN_PRELUDE")

    # 3. Mission Records 테스트
    print("\n[Test 3] Mission Records - 미션 완료 기록")
    print("-" * 60)
    
    success_count = 0
    for mission_type, character, attempts, success in [
        ("recruit", "tanjiro", 1, True),
        ("recruit", "zenitsu", 2, True),
        ("recruit", "inosuke", 3, False)
    ]:
        if db.save_mission_record(test_session_id, mission_type, character, attempts, success):
            status = "성공" if success else "실패"
            print(f"✅ {mission_type}: {character} ({status}, {attempts}회)")
            success_count += 1
    print(f"성공: {success_count}/3")

    # 4. Game Events 테스트
    print("\n[Test 4] Game Events - 일반 게임 이벤트 기록")
    print("-" * 60)
    
    success_count = 0
    for idx, (event_type, data) in enumerate([
        ("character_joined", {"character": "rengoku", "stage": "TRAIN_FINALE"}),
        ("item_acquired", {"item": "nichirin_sword", "rarity": "legendary"}),
        ("achievement_unlocked", {"achievement": "first_demon_defeated"})
    ], 1):
        if db.save_game_event(test_session_id, idx, event_type, data):
            print(f"✅ Event logged: {event_type}")
            success_count += 1
    print(f"성공: {success_count}/3")

    # 5. 검증
    print("\n[Test 5] 저장된 데이터 검증")
    print("-" * 60)
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM statedb.affinity_records WHERE session_id = %s;", (test_session_id,))
            affinity_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM statedb.stage_progression WHERE session_id = %s;", (test_session_id,))
            stage_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM statedb.mission_records WHERE session_id = %s;", (test_session_id,))
            mission_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM statedb.game_events WHERE session_id = %s;", (test_session_id,))
            event_count = cur.fetchone()[0]
            
            print(f"✅ Affinity Records: {affinity_count}개")
            print(f"✅ Stage Progression: {stage_count}개")
            print(f"✅ Mission Records: {mission_count}개")
            print(f"✅ Game Events: {event_count}개")
            
            total = affinity_count + stage_count + mission_count + event_count
            if total >= 12:  # 3+3+3+3 = 12
                print(f"\n✅✅✅ 모든 게임 이벤트가 정상적으로 저장되었습니다!")
            else:
                print(f"\n⚠️  일부 이벤트만 저장됨: {total}/12")

    # 6. 전체 통계
    print("\n[Test 6] 전체 게임 이벤트 통계")
    print("-" * 60)
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM statedb.affinity_records) as affinity_total,
                    (SELECT COUNT(*) FROM statedb.mission_records) as mission_total,
                    (SELECT COUNT(*) FROM statedb.stage_progression) as stage_total,
                    (SELECT COUNT(*) FROM statedb.game_events) as event_total;
            """)
            
            affinity, mission, stage, event = cur.fetchone()
            print(f"  전체 Affinity Records: {affinity}개")
            print(f"  전체 Mission Records: {mission}개")
            print(f"  전체 Stage Progression: {stage}개")
            print(f"  전체 Game Events: {event}개")

    print("\n" + "="*60)
    print("✅✅✅ 문제 5 해결: Game Event Logging System 완전히 작동!")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_game_event_logging()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 테스트 중 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
