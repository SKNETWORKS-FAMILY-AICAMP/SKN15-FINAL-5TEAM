#!/usr/bin/env python3
"""
지식 그래프 구축 스크립트

수집된 의사결정 로그(ml.decision_logs)로부터 지식 그래프를 구축합니다.
"""
import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.db import get_async_session
from app.features.ml.services import GraphBuilder, KeywordExtractor
from app.features.ml.repository import DecisionLogRepository


async def check_decision_logs():
    """의사결정 로그 확인"""
    print("=" * 80)
    print("📊 Step 1: Checking Decision Logs")
    print("=" * 80)

    async with get_async_session() as db:
        # 전체 개수
        result = await db.execute(text("SELECT COUNT(*) FROM ml.decision_logs"))
        total_count = result.scalar()
        print(f"\n✅ Total decision logs: {total_count}")

        if total_count == 0:
            print("\n⚠️  No decision logs found!")
            print("   Please run test_300_conversations.py first to collect data.")
            return False

        # 에이전트별 통계
        result = await db.execute(text("""
            SELECT
                agent_name,
                decision_type,
                COUNT(*) as count,
                AVG(execution_time_ms) as avg_time,
                AVG(confidence) as avg_confidence
            FROM ml.decision_logs
            WHERE created_at > NOW() - INTERVAL '1 day'
            GROUP BY agent_name, decision_type
            ORDER BY count DESC
            LIMIT 10
        """))

        print("\n📈 Recent Decision Statistics (Last 24h):")
        print(f"{'Agent':<20} {'Type':<25} {'Count':>8} {'Avg Time':>10} {'Avg Conf':>10}")
        print("-" * 80)

        for row in result:
            avg_time_str = f"{row.avg_time:.1f}ms" if row.avg_time else "N/A"
            avg_conf_str = f"{row.avg_confidence:.2f}" if row.avg_confidence else "N/A"
            print(f"{row.agent_name:<20} {row.decision_type:<25} {row.count:>8} {avg_time_str:>10} {avg_conf_str:>10}")

        # 키워드가 추출된 로그 개수
        result = await db.execute(text("""
            SELECT COUNT(*)
            FROM ml.decision_logs
            WHERE extracted_keywords IS NOT NULL
            AND extracted_keywords != '{}'::jsonb
        """))
        keyword_count = result.scalar()
        print(f"\n✅ Logs with extracted keywords: {keyword_count}/{total_count} "
              f"({keyword_count/total_count*100:.1f}%)")

        return True


async def build_graph():
    """그래프 구축"""
    print("\n" + "=" * 80)
    print("🔨 Step 2: Building Knowledge Graph")
    print("=" * 80)

    async with get_async_session() as db:
        builder = GraphBuilder(db)

        print("\n🔄 Building graph from recent decisions (last 24 hours)...")
        print("   This may take a few minutes...\n")

        result = await builder.build_from_recent_decisions(
            hours=24,
            limit=5000  # 최대 5000개
        )

        print("\n✅ Graph building completed!")
        print(f"   📦 Nodes created/updated: {result['nodes_created']}")
        print(f"   🔗 Edges created/updated: {result['edges_created']}")
        print(f"   📝 Decisions processed: {result['decisions_processed']}")

        return result


async def show_graph_statistics():
    """그래프 통계 출력"""
    print("\n" + "=" * 80)
    print("📊 Step 3: Knowledge Graph Statistics")
    print("=" * 80)

    async with get_async_session() as db:
        builder = GraphBuilder(db)
        stats = await builder.get_graph_statistics()

        print(f"\n📦 Total Nodes: {stats['nodes']['total']}")
        print(f"   - Verbs (동사): {stats['nodes']['by_type']['verb']}")
        print(f"   - Characters (캐릭터): {stats['nodes']['by_type']['character']}")
        print(f"   - Stages (스테이지): {stats['nodes']['by_type']['stage']}")
        print(f"   - Contexts (상황): {stats['nodes']['by_type']['context']}")

        print("\n🔝 Top 10 Verbs:")
        for i, verb in enumerate(stats['top_verbs'][:10], 1):
            print(f"   {i:2d}. {verb['value']:<20} (frequency: {verb['frequency']})")

        print("\n🔝 Top 10 Characters:")
        for i, char in enumerate(stats['top_characters'][:10], 1):
            print(f"   {i:2d}. {char['value']:<20} (frequency: {char['frequency']})")

        # 엣지 통계
        result = await db.execute(text("""
            SELECT
                edge_type,
                COUNT(*) as count,
                SUM(occurrence_count) as total_occurrences,
                AVG(success_count::float / NULLIF(occurrence_count, 0)) as avg_success_rate
            FROM knowledge.graph_edges
            GROUP BY edge_type
            ORDER BY count DESC
        """))

        print("\n🔗 Edge Statistics:")
        print(f"{'Edge Type':<20} {'Count':>10} {'Occurrences':>15} {'Avg Success':>15}")
        print("-" * 60)
        for row in result:
            success_rate = f"{row.avg_success_rate*100:.1f}%" if row.avg_success_rate else "N/A"
            print(f"{row.edge_type:<20} {row.count:>10} {row.total_occurrences:>15} {success_rate:>15}")


async def show_sample_patterns():
    """샘플 패턴 출력"""
    print("\n" + "=" * 80)
    print("🔍 Step 4: Sample Knowledge Patterns")
    print("=" * 80)

    async with get_async_session() as db:
        # 가장 빈도가 높은 패턴 10개
        result = await db.execute(text("""
            SELECT
                n1.node_value as source,
                e.edge_type,
                n2.node_value as target,
                e.occurrence_count,
                e.success_count,
                ROUND((e.success_count::float / NULLIF(e.occurrence_count, 0) * 100)::numeric, 1) as success_rate
            FROM knowledge.graph_edges e
            JOIN knowledge.graph_nodes n1 ON e.source_node_id = n1.node_id
            JOIN knowledge.graph_nodes n2 ON e.target_node_id = n2.node_id
            WHERE e.occurrence_count >= 3
            ORDER BY e.occurrence_count DESC, success_rate DESC
            LIMIT 15
        """))

        print("\n📈 Top Patterns (by occurrence):")
        print(f"{'Source':<20} {'→':^5} {'Target':<20} {'Type':<15} {'Count':>8} {'Success':>10}")
        print("-" * 90)

        for row in result:
            success_display = f"{row.success_count}/{row.occurrence_count}"
            if row.success_rate is not None:
                success_display += f" ({row.success_rate}%)"

            print(f"{row.source:<20} {'→':^5} {row.target:<20} {row.edge_type:<15} "
                  f"{row.occurrence_count:>8} {success_display:>10}")


async def test_graphrag_prediction():
    """GraphRAG 예측 테스트"""
    print("\n" + "=" * 80)
    print("🧪 Step 5: Testing GraphRAG Prediction")
    print("=" * 80)

    async with get_async_session() as db:
        from app.features.ml.services import GraphRAG

        graph_rag = GraphRAG(db)

        test_inputs = [
            ("무잔과 싸운다", {"stage": "infinity_castle", "affinity": {}}),
            ("무잔을 설득한다", {"stage": "infinity_castle", "affinity": {}}),
            ("도망친다", {"stage": "infinity_castle", "affinity": {}}),
        ]

        for user_input, context in test_inputs:
            print(f"\n🔮 Testing: '{user_input}'")
            print(f"   Context: {context}")

            prediction = await graph_rag.predict_decision(
                user_input=user_input,
                context_state=context,
                decision_type="routing",
                threshold=0.75,
            )

            print(f"   Result:")
            print(f"      Use LLM: {prediction['use_llm']}")
            print(f"      Confidence: {prediction['confidence']:.2%}")
            print(f"      Reasoning: {prediction['reasoning'][:100]}...")

            if prediction['similar_cases']:
                print(f"      Similar cases found: {len(prediction['similar_cases'])}")
                for i, case in enumerate(prediction['similar_cases'][:3], 1):
                    pattern = case.get('pattern', {})
                    print(f"         {i}. {pattern.get('verb', 'N/A')} + {pattern.get('character', 'N/A')} "
                          f"(success: {case.get('success_rate', 0):.0%})")


async def main():
    """메인 함수"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "Knowledge Graph Builder" + " " * 35 + "║")
    print("╚" + "═" * 78 + "╝")

    try:
        # 1. 의사결정 로그 확인
        has_data = await check_decision_logs()
        if not has_data:
            return

        # 2. 그래프 구축
        await build_graph()

        # 3. 통계 출력
        await show_graph_statistics()

        # 4. 샘플 패턴
        await show_sample_patterns()

        # 5. GraphRAG 테스트
        await test_graphrag_prediction()

        print("\n" + "=" * 80)
        print("✅ All steps completed successfully!")
        print("=" * 80)
        print("\n💡 Next steps:")
        print("   1. Integrate DecisionCollector into agents")
        print("   2. Enable GraphRAG in RouterAgent")
        print("   3. Monitor LLM call reduction")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
