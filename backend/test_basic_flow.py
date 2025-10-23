#!/usr/bin/env python3
"""
간단한 기본 플로우 테스트
Parent Agent와 Children Agent가 올바르게 연동되는지 확인
"""

import json
from src.agents.parent_agent import run_parent_agent
from src.agents.children_agent import run_children_agent

# 테스트용 최소 시나리오 데이터
test_scenario = {
    "scenario_id": "test_basic",
    "title": "기본 테스트",
    "stages": {
        "intro": {
            "type": "cutscene",
            "next_stage": "end",
            "situations": [
                {
                    "turn": 0,
                    "scene_description": "테스트 시작",
                    "characters": [
                        {
                            "id": "system",
                            "order": 0,
                            "role": "나레이터",
                            "emotion": "neutral",
                            "situation": "🎬 테스트 시나리오가 시작됩니다."
                        },
                        {
                            "id": "tanjiro",
                            "order": 1,
                            "role": "주인공",
                            "emotion": "happy",
                            "motivation": "플레이어를 환영하고 싶다",
                            "context": "새로운 여행자를 만났다"
                        }
                    ]
                }
            ]
        }
    }
}

# 테스트용 초기 상태
test_state = {
    "scenario_data": test_scenario,
    "current_stage": "intro",
    "stage_states": {},
    "user_input": "시작",
    "agent_responses": [],
    "runtime": {},
    "affinity": {}
}

print("=" * 60)
print("🧪 기본 플로우 테스트 시작")
print("=" * 60)

# 1. Parent Agent 실행
print("\n[TEST] Step 1: Running Parent Agent...")
state_after_parent = run_parent_agent(test_state)

print(f"\n[TEST] Parent Agent 결과:")
print(f"  - runtime.children_context 존재: {bool(state_after_parent.get('runtime', {}).get('children_context'))}")

ctx = state_after_parent.get('runtime', {}).get('children_context')
if ctx:
    print(f"  - characters 개수: {len(ctx.get('characters', []))}")
    print(f"  - candidates: {ctx.get('candidates', [])}")
    for char in ctx.get('characters', []):
        print(f"    - {char.get('id')}: {char.get('role', 'N/A')}")

# 2. Children Agent 실행
print("\n[TEST] Step 2: Running Children Agent...")
state_after_children = run_children_agent(state_after_parent)

print(f"\n[TEST] Children Agent 결과:")
agent_responses = state_after_children.get('agent_responses', [])
print(f"  - agent_responses 개수: {len(agent_responses)}")
for resp in agent_responses:
    speaker = resp.get('speaker', 'unknown')
    text = resp.get('text', '')
    emotion = resp.get('emotion', '')
    print(f"    - {speaker} ({emotion}): {text[:80]}")

print("\n" + "=" * 60)
if agent_responses:
    print("✅ 테스트 성공: Children Agent가 대사를 생성했습니다!")
else:
    print("❌ 테스트 실패: Children Agent가 대사를 생성하지 못했습니다.")
print("=" * 60)
