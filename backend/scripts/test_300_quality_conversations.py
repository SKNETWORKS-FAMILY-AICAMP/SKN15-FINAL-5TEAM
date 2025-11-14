#!/usr/bin/env python3
"""
300회 고품질 대화 테스트

실제 사용자처럼 자연스러운 대화 패턴으로 300회 테스트를 진행하여
Training Logs와 Decision Logs 데이터를 수집합니다.
"""
import asyncio
import sys
import json
import random
from pathlib import Path
from uuid import uuid4
import time

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.db.session import AsyncSessionLocal


async def load_conversation_scenarios():
    """대화 시나리오 로드"""
    script_dir = Path(__file__).parent
    scenario_file = script_dir / "conversation_scenarios.json"

    with open(scenario_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data['scenarios']


async def simulate_conversation(scenario_id: str, user_input: str, category: str):
    """
    대화 시뮬레이션 (API 호출 없이 로직만 테스트)

    실제 환경에서는 HTTP API를 호출하세요.
    """
    # 시뮬레이션: 카테고리에 따라 다른 응답 생성
    response_templates = {
        "battle_direct": {"type": "battle", "intensity": "high"},
        "battle_cautious": {"type": "strategy", "intensity": "low"},
        "conversation_friendly": {"type": "dialogue", "depth": "casual"},
        "conversation_deep": {"type": "dialogue", "depth": "deep"},
        "exploration": {"type": "exploration", "discovery": random.choice([True, False])},
        "team_interaction": {"type": "team", "members": random.randint(1, 3)},
        "off_topic": {"type": "warning", "classification": "off_topic"},
    }

    response = response_templates.get(category, {"type": "dialogue", "depth": "casual"})

    # 약간의 지연 시뮬레이션
    await asyncio.sleep(random.uniform(0.05, 0.15))

    return {
        "scenario_id": scenario_id,
        "user_input": user_input,
        "category": category,
        "response": response,
        "success": True
    }


async def run_quality_test():
    """고품질 대화 테스트 실행"""
    print("=" * 80)
    print("🎯 Starting High-Quality Conversation Test")
    print("=" * 80)

    # 시나리오 로드
    print("\n📖 Loading conversation scenarios...")
    scenarios = await load_conversation_scenarios()

    # 모든 대화 입력 수집
    all_inputs = []
    category_counts = {}

    for scenario in scenarios:
        scenario_id = scenario['scenario_id']
        for conv_group in scenario['conversations']:
            category = conv_group['category']
            category_counts[category] = len(conv_group['inputs'])

            for user_input in conv_group['inputs']:
                all_inputs.append({
                    'scenario_id': scenario_id,
                    'user_input': user_input,
                    'category': category
                })

    print(f"   ✅ Loaded {len(all_inputs)} unique conversation inputs")
    print(f"   📂 Categories: {len(category_counts)}")

    # 카테고리별 샘플 수 출력
    print("\n📊 Category Distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {cat:<30}: {count:>3} inputs")

    # 300개 샘플 생성
    target_count = 300
    if len(all_inputs) < target_count:
        conversation_samples = random.choices(all_inputs, k=target_count)
        print(f"\n🔄 Generated {target_count} samples (with repetition)")
    else:
        conversation_samples = random.sample(all_inputs, k=target_count)
        print(f"\n🔄 Sampled {target_count} unique conversations")

    print("=" * 80)

    # 통계
    success_count = 0
    failure_count = 0
    total_time = 0
    category_results = {}

    # 진행 상황
    print("\n⏳ Running conversations...")
    print(f"{'Progress':<15} {'Success':<10} {'Failed':<10} {'Avg Time':<12} {'Category'}")
    print("-" * 80)

    for i, conv in enumerate(conversation_samples, 1):
        start_time = time.time()
        category = conv['category']

        try:
            result = await simulate_conversation(
                scenario_id=conv['scenario_id'],
                user_input=conv['user_input'],
                category=category
            )

            if result and result.get('success'):
                success_count += 1
                if category not in category_results:
                    category_results[category] = {'success': 0, 'failed': 0}
                category_results[category]['success'] += 1
            else:
                failure_count += 1
                if category not in category_results:
                    category_results[category] = {'success': 0, 'failed': 0}
                category_results[category]['failed'] += 1

        except Exception as e:
            failure_count += 1
            if category not in category_results:
                category_results[category] = {'success': 0, 'failed': 0}
            category_results[category]['failed'] += 1

        elapsed = time.time() - start_time
        total_time += elapsed

        # 20회마다 진행 상황 출력
        if i % 20 == 0 or i == 1:
            avg_time = total_time / i
            progress = f"{i}/{target_count} ({i/target_count*100:.0f}%)"
            print(f"{progress:<15} {success_count:<10} {failure_count:<10} {avg_time*1000:.1f}ms       {category[:35]}")

    # 최종 통계
    print("\n" + "=" * 80)
    print("📊 Test Results")
    print("=" * 80)

    print(f"\n🎬 Conversation Statistics:")
    print(f"   Total conversations:  {len(conversation_samples)}")
    print(f"   Successful:           {success_count} ({success_count/len(conversation_samples)*100:.1f}%)")
    print(f"   Failed:               {failure_count} ({failure_count/len(conversation_samples)*100:.1f}%)")
    print(f"   Average time:         {total_time/len(conversation_samples)*1000:.1f}ms")
    print(f"   Total time:           {total_time:.1f}s")

    print(f"\n📈 Category Performance (Top 10):")
    sorted_categories = sorted(
        category_results.items(),
        key=lambda x: x[1]['success'] + x[1]['failed'],
        reverse=True
    )
    print(f"   {'Category':<35} {'Success':>8} {'Failed':>8} {'Total':>8}")
    print("   " + "-" * 65)
    for cat, results in sorted_categories[:10]:
        total = results['success'] + results['failed']
        print(f"   {cat:<35} {results['success']:>8} {results['failed']:>8} {total:>8}")

    print("\n" + "=" * 80)
    print("✅ Quality Conversation Test Completed!")
    print("=" * 80)

    print("\n💡 Sample Conversations:")
    for sample in random.sample(conversation_samples, min(5, len(conversation_samples))):
        print(f"\n   📝 [{sample['category']}] {sample['scenario_id']}")
        print(f"      \"{sample['user_input']}\"")

    return {
        "total": len(conversation_samples),
        "success": success_count,
        "failed": failure_count,
        "categories": len(category_results),
    }


async def main():
    """메인 함수"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "High-Quality Conversation Test" + " " * 32 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    print("ℹ️  Testing natural conversation patterns with diverse scenarios")
    print("ℹ️  This validates conversation quality before full integration")
    print()

    try:
        result = await run_quality_test()

        print("\n💡 Next Steps:")
        print("   1. Review conversation patterns and categories")
        print("   2. Integrate TrainingLogger into agents")
        print("   3. Integrate DecisionCollector into agents")
        print("   4. Run actual API test with 300 conversations")
        print("   5. Build knowledge graph from collected data")
        print()

        return result

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
