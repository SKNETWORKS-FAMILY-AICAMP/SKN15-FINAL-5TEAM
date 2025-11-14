#!/usr/bin/env python3
"""
두 로깅 시스템 통합 테스트

1. Training Logs (Auto-labeling)
2. Decision Logs (GraphRAG)

두 시스템이 DB에 제대로 저장되는지 확인합니다.
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4
import time

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.db.session import AsyncSessionLocal
from app.features.logging import TrainingLogger
from app.features.ml.services import DecisionCollector, KeywordExtractor


async def test_training_logs():
    """Training Logs 테스트"""
    print("=" * 80)
    print("📋 Test 1: Training Logs (Auto-labeling System)")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        logger = TrainingLogger(db)
        session_id = uuid4()

        print("\n🔹 Logging Router Agent execution (Success)...")
        log_id1 = await logger.log_agent_execution(
            session_id=session_id,
            turn_count=1,
            agent_name="router_agent",
            user_input="렌고쿠와 싸운다",
            context={
                "scenario_id": "mugen-train",
                "current_stage": "battle",
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
        print(f"   ✅ Created log ID: {log_id1}")

        print("\n🔹 Logging Router Agent execution (Failure)...")
        log_id2 = await logger.log_agent_execution(
            session_id=session_id,
            turn_count=2,
            agent_name="router_agent",
            user_input="이상한 말",
            context={
                "scenario_id": "mugen-train",
                "current_stage": "battle",
            },
            model_output={
                "classification": "off_topic",
                "next_node": "parent_agent",  # 잘못된 라우팅!
                "confidence": 0.25,
            },
            latency_ms=180,
            llm_model="gpt-4",
            scenario_id="mugen-train",
            current_stage="battle",
        )
        print(f"   ✅ Created log ID: {log_id2}")

        print("\n🔹 Logging Parent Agent execution...")
        log_id3 = await logger.log_agent_execution(
            session_id=session_id,
            turn_count=3,
            agent_name="parent_agent",
            user_input="렌고쿠와 대화한다",
            context={
                "scenario_id": "mugen-train",
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
            scenario_id="mugen-train",
            current_stage="conversation",
        )
        print(f"   ✅ Created log ID: {log_id3}")

        # DB에서 확인
        print("\n🔍 Checking database...")
        result = await db.execute(
            text("""
                SELECT id, agent_name, outcome, ROUND(feedback_score::numeric, 2) as score
                FROM ml.training_logs
                WHERE session_id = :session_id
                ORDER BY turn_count
            """),
            {"session_id": str(session_id)}
        )
        logs = result.fetchall()

        print(f"\n   ✅ Found {len(logs)} training logs in database:")
        print(f"   {'ID':<10} {'Agent':<20} {'Outcome':<10} {'Score':>6}")
        print("   " + "-" * 50)
        for log in logs:
            print(f"   {log.id:<10} {log.agent_name:<20} {log.outcome:<10} {log.score:>6}")

        return session_id, len(logs)


async def test_decision_logs():
    """Decision Logs 테스트"""
    print("\n\n" + "=" * 80)
    print("📋 Test 2: Decision Logs (GraphRAG System)")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        collector = DecisionCollector(db)
        extractor = KeywordExtractor()
        session_id = uuid4()

        # Create a test session first (to satisfy foreign key constraint)
        print("\n🔹 Creating test session...")
        await db.execute(
            text("""
                INSERT INTO conversation.sessions (session_id, user_id, scenario_id, created_at)
                VALUES (:session_id, 'd51aa5f6-b9c4-4974-bbda-fff5b027119a'::uuid, 'mugen-train', NOW())
            """),
            {"session_id": str(session_id)}
        )
        await db.commit()
        print(f"   ✅ Created session: {session_id}")

        print("\n🔹 Extracting keywords from user input...")
        user_input = "렌고쿠와 강하게 싸운다"
        keywords = await extractor.extract(
            text=user_input,
            context={"stage": "mugen_train", "scenario_id": "mugen-train"}
        )
        print(f"   ✅ Extracted: {keywords}")

        print("\n🔹 Collecting decision data (Parent Agent)...")
        start_time = time.time()
        decision_id1 = await collector.collect_with_timing(
            session_id=session_id,
            agent_name="parent_agent",
            decision_type="stage_selection",
            decision_output={
                "selected_stage": "battle",
                "handler_type": "scene",
            },
            start_time=start_time,
            turn_number=1,
            user_input=user_input,
            extracted_keywords=keywords,
            context_state={
                "stage": "battle",
                "scenario_id": "mugen-train",
                "affinity": {"렌고쿠": 50},
            },
            confidence=0.85,
        )
        print(f"   ✅ Created decision ID: {decision_id1}")

        print("\n🔹 Collecting decision data (Children Agent)...")
        start_time2 = time.time()
        decision_id2 = await collector.collect_with_timing(
            session_id=session_id,
            agent_name="children_agent",
            decision_type="dialogue_generation",
            decision_output={
                "dialogue_count": 3,
                "speakers": ["렌고쿠", "탄지로", "렌고쿠"],
            },
            start_time=start_time2,
            turn_number=2,
            user_input="대화를 계속한다",
            extracted_keywords={"verbs": ["계속한다"], "targets": []},
            context_state={
                "stage": "conversation",
            },
            llm_prompt="Generate dialogues...",
            llm_parameters={"temperature": 0.8, "max_tokens": 2000},
            llm_model="gpt-4o",
        )
        print(f"   ✅ Created decision ID: {decision_id2}")

        # DB에서 확인
        print("\n🔍 Checking database...")
        result = await db.execute(
            text("""
                SELECT decision_id, agent_name, decision_type,
                       ROUND(confidence::numeric, 2) as conf,
                       extracted_keywords
                FROM ml.decision_logs
                WHERE session_id = :session_id
                ORDER BY decision_id DESC
                LIMIT 10
            """),
            {"session_id": str(session_id)}
        )
        logs = result.fetchall()

        print(f"\n   ✅ Found {len(logs)} decision logs in database:")
        print(f"   {'ID':<15} {'Agent':<20} {'Type':<25} {'Conf':>6}")
        print("   " + "-" * 70)
        for log in logs:
            conf_str = f"{log.conf:>6}" if log.conf is not None else "  N/A"
            print(f"   {log.decision_id:<15} {log.agent_name:<20} {log.decision_type:<25} {conf_str}")

        # 키워드 확인
        if logs:
            print(f"\n   📌 First log keywords: {logs[0].extracted_keywords}")

        # 데이터 확인을 위해 커밋
        await db.commit()
        print("\n   💾 Data committed to database")

        return session_id, len(logs)


async def verify_both_systems():
    """두 시스템 통합 검증"""
    print("\n\n" + "=" * 80)
    print("🔍 Final Verification")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        # Training logs 전체 개수
        result1 = await db.execute(text("SELECT COUNT(*) FROM ml.training_logs"))
        training_count = result1.scalar()

        # Decision logs 전체 개수
        result2 = await db.execute(text("SELECT COUNT(*) FROM ml.decision_logs"))
        decision_count = result2.scalar()

        # Graph nodes 개수
        result3 = await db.execute(text("SELECT COUNT(*) FROM knowledge.graph_nodes"))
        node_count = result3.scalar()

        # Graph edges 개수
        result4 = await db.execute(text("SELECT COUNT(*) FROM knowledge.graph_edges"))
        edge_count = result4.scalar()

        print(f"\n📊 Database Statistics:")
        print(f"   ml.training_logs:     {training_count:>6} rows")
        print(f"   ml.decision_logs:     {decision_count:>6} rows")
        print(f"   knowledge.graph_nodes: {node_count:>6} rows")
        print(f"   knowledge.graph_edges: {edge_count:>6} rows")

        # Auto-labeling 통계
        result5 = await db.execute(text("""
            SELECT outcome, COUNT(*) as count
            FROM ml.training_logs
            GROUP BY outcome
            ORDER BY count DESC
        """))
        outcomes = result5.fetchall()

        if outcomes:
            print(f"\n📈 Auto-labeling Outcomes:")
            for row in outcomes:
                print(f"   {row.outcome or 'null':<10}: {row.count:>4}")

        return training_count, decision_count


async def main():
    """메인 함수"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "Dual Logging System Integration Test" + " " * 25 + "║")
    print("╚" + "═" * 78 + "╝")

    try:
        # Test 1: Training Logs
        training_session, training_logs = await test_training_logs()

        # Test 2: Decision Logs
        decision_session, decision_logs = await test_decision_logs()

        # Final verification
        total_training, total_decision = await verify_both_systems()

        print("\n" + "=" * 80)
        print("✅ All Tests PASSED!")
        print("=" * 80)
        print(f"\n📝 Test Summary:")
        print(f"   Training Logs created: {training_logs}")
        print(f"   Decision Logs created: {decision_logs}")
        print(f"   Total training logs in DB: {total_training}")
        print(f"   Total decision logs in DB: {total_decision}")
        print()
        print("💡 Next Steps:")
        print("   1. Integrate TrainingLogger into ParentAgent")
        print("   2. Integrate DecisionCollector into ParentAgent")
        print("   3. Run 300 conversation test")
        print("   4. Build knowledge graph from collected data")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
