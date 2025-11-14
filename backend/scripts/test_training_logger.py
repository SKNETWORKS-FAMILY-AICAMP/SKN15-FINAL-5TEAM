#!/usr/bin/env python3
"""
TrainingLogger 테스트 스크립트

목적: TrainingLogger가 제대로 작동하고 DB에 데이터가 쌓이는지 확인
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.db.session import get_db_context
from app.features.logging import TrainingLogger


async def test_training_logger():
    """TrainingLogger 테스트"""
    print("=" * 80)
    print("🧪 TrainingLogger Test")
    print("=" * 80)

    async with get_db_context() as db:
        logger = TrainingLogger(db)

        # 1. Router Agent 로그 테스트 (성공 케이스)
        print("\n📝 Test 1: Router Agent (Success Case)")
        session_id = uuid4()

        log_id = await logger.log_agent_execution(
            session_id=session_id,
            turn_count=1,
            agent_name="router_agent",
            user_input="렌고쿠와 싸운다",
            context={
                "scenario_id": "mugen-train",
                "current_stage": "battle",
                "user_input": "렌고쿠와 싸운다",
            },
            model_output={
                "classification": "on_topic",
                "next_node": "parent_agent",
                "confidence": 0.92,
            },
            latency_ms=150,
            llm_model="gpt-4",
            scenario_id="mugen-train",
            current_stage="battle",
        )

        print(f"   ✅ Router log created: ID={log_id}")

        # 2. Router Agent 로그 테스트 (실패 케이스)
        print("\n📝 Test 2: Router Agent (Failure Case)")
        log_id2 = await logger.log_agent_execution(
            session_id=session_id,
            turn_count=2,
            agent_name="router_agent",
            user_input="그냥 말 걸기",
            context={
                "scenario_id": "mugen-train",
                "current_stage": "battle",
                "user_input": "그냥 말 걸기",
            },
            model_output={
                "classification": "off_topic",  # off_topic인데
                "next_node": "parent_agent",    # parent로 보냄 (잘못됨!)
                "confidence": 0.25,
            },
            latency_ms=180,
            llm_model="gpt-4",
            scenario_id="mugen-train",
            current_stage="battle",
        )

        print(f"   ✅ Router log created: ID={log_id2}")

        # 3. Parent Agent 로그 테스트 (성공)
        print("\n📝 Test 3: Parent Agent (Success Case)")
        log_id3 = await logger.log_agent_execution(
            session_id=session_id,
            turn_count=3,
            agent_name="parent_agent",
            user_input="렌고쿠와 대화한다",
            context={
                "scenario_id": "mugen-train",
                "current_stage": "conversation",
            },
            model_output={
                "beats": [
                    {"type": "dialogue", "speaker": "렌고쿠"},
                    {"type": "dialogue", "speaker": "탄지로"},
                ],
                "stage_complete": True,
                "next_stage": "next_scene",
            },
            latency_ms=250,
            llm_model="gpt-4o",
            scenario_id="mugen-train",
            current_stage="conversation",
        )

        print(f"   ✅ Parent log created: ID={log_id3}")

        # 4. Children Agent 로그 테스트
        print("\n📝 Test 4: Children Agent (Success Case)")
        log_id4 = await logger.log_agent_execution(
            session_id=session_id,
            turn_count=4,
            agent_name="children_agent",
            user_input="안녕하세요",
            context={
                "beats": [
                    {"type": "dialogue"},
                    {"type": "dialogue"},
                ],
            },
            model_output={
                "dialogues": [
                    {"speaker": "렌고쿠", "text": "안녕!"},
                    {"speaker": "탄지로", "text": "반가워요!"},
                ],
            },
            latency_ms=300,
            llm_model="gpt-4o",
            scenario_id="mugen-train",
            current_stage="conversation",
        )

        print(f"   ✅ Children log created: ID={log_id4}")

        # 5. DB에 저장되었는지 확인
        print("\n" + "=" * 80)
        print("🔍 Checking Database")
        print("=" * 80)

        # 방금 생성한 로그 조회
        result = await db.execute(
            text("""
                SELECT
                    id,
                    agent_name,
                    outcome,
                    outcome_reason,
                    ROUND(feedback_score::numeric, 2) as score
                FROM ml.training_logs
                WHERE session_id = :session_id
                ORDER BY turn_count
            """),
            {"session_id": str(session_id)}
        )

        logs = result.fetchall()

        if not logs:
            print("   ❌ No logs found in database!")
            return False

        print(f"\n   ✅ Found {len(logs)} logs in database:")
        print(f"   {'ID':<10} {'Agent':<20} {'Outcome':<10} {'Score':>6} {'Reason'}")
        print("   " + "-" * 80)

        for log in logs:
            print(f"   {log.id:<10} {log.agent_name:<20} {log.outcome:<10} {log.score:>6} {log.outcome_reason[:40]}")

        # 6. Auto-labeling 결과 검증
        print("\n" + "=" * 80)
        print("✅ Auto-labeling Results")
        print("=" * 80)

        # Test 1: Router success (should be "success")
        assert logs[0].outcome == "success", f"Expected 'success', got '{logs[0].outcome}'"
        assert logs[0].score >= 0.75, f"Expected score >= 0.75, got {logs[0].score}"
        print("   ✅ Test 1 (Router Success): PASSED")

        # Test 2: Router failure (should be "failure")
        assert logs[1].outcome == "failure", f"Expected 'failure', got '{logs[1].outcome}'"
        assert logs[1].score < 0.5, f"Expected score < 0.5, got {logs[1].score}"
        print("   ✅ Test 2 (Router Failure): PASSED")

        # Test 3: Parent success
        assert logs[2].outcome in ["success", "partial"], f"Expected 'success' or 'partial', got '{logs[2].outcome}'"
        print("   ✅ Test 3 (Parent Success): PASSED")

        # Test 4: Children success
        assert logs[3].outcome in ["success", "partial"], f"Expected 'success' or 'partial', got '{logs[3].outcome}'"
        print("   ✅ Test 4 (Children Success): PASSED")

        # 7. 통계 확인
        print("\n" + "=" * 80)
        print("📊 Statistics")
        print("=" * 80)

        stats = await logger.get_training_statistics(hours=24)
        print(f"   Total logs: {stats['total_logs']}")
        print(f"   By outcome: {stats['by_outcome']}")
        print(f"   Success rate: {stats['success_rate']:.1%}")
        print(f"   Avg feedback score: {stats['avg_feedback_score']:.2f}")
        print(f"   Avg latency: {stats['avg_latency_ms']:.0f}ms")

        print("\n" + "=" * 80)
        print("🎉 All Tests PASSED!")
        print("=" * 80)

        return True


async def main():
    """메인 함수"""
    try:
        success = await test_training_logger()
        if success:
            print("\n✅ TrainingLogger is working correctly!")
            print("   - Auto-labeling ✅")
            print("   - Database storage ✅")
            print("   - Statistics ✅")
        else:
            print("\n❌ TrainingLogger test failed!")
            sys.exit(1)

    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
