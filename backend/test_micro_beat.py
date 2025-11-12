#!/usr/bin/env python3
"""
micro_beat 모드 직접 테스트 스크립트
인증 없이 ChildrenAgent를 직접 호출하여 대화 생성 확인
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(override=True)

from app.features.chat.agent.children import ChildrenAgent
from app.features.chat.services import LLMService, DialogueService
from app.core.logging import setup_logging

setup_logging("DEBUG")


async def test_micro_beat():
    """
    micro_beat 모드에서 유저 입력에 따라 대화가 달라지는지 테스트
    """
    print("=" * 60)
    print("🧪 Testing micro_beat Mode")
    print("=" * 60)

    # 서비스 초기화
    llm_service = LLMService()
    dialogue_service = DialogueService()
    agent = ChildrenAgent(llm_service=llm_service, dialogue_service=dialogue_service)

    # 공통 컨텍스트
    beat = {
        "goal": "렌고쿠가 도시락을 먹으며 '우마이!'를 연발한다. 츠구코가 말을 걸면 자연스럽게 대화한다.",
        "speaker_hint": ["rengoku", "narr"]
    }

    speaker_pool = ["rengoku", "narr"]

    # ============================================================
    # Turn 0: 초기 대화 (유저 입력 없음)
    # ============================================================
    print("\n" + "=" * 60)
    print("🎬 Turn 0: 초기 대화")
    print("=" * 60)

    state_turn0 = {
        "children_ctx": {
            "stage_tag": "TRAIN_PRELUDE",
            "stage_type": "scene",
            "beats": [beat],  # ✅ 단일 beat만
            "speaker_pool": speaker_pool,
            "loop_mode": "micro_beat",
            "scenario_id": "mugen-train",
            "character_refs": {}
        },
        "recent_dialogues": [],
        "user_input": "",
        "turn_count": 0,
        "user_name": "츠구코"
    }

    result_turn0 = await agent.run(state_turn0)
    dialogues_turn0 = result_turn0.get("agent_responses", [])

    print(f"\n✅ Generated {len(dialogues_turn0)} dialogues:")
    for d in dialogues_turn0:
        print(f"   🔹 {d['speaker']}: {d['text']}")

    # ============================================================
    # Turn 1: 유저가 "배고프지 않으세요?" 입력
    # ============================================================
    print("\n" + "=" * 60)
    print("🎬 Turn 1: 유저 입력 '배고프지 않으세요?'")
    print("=" * 60)

    # recent_dialogues 업데이트
    recent_dialogues_turn1 = dialogues_turn0.copy()

    state_turn1 = {
        "children_ctx": {
            "stage_tag": "TRAIN_PRELUDE",
            "stage_type": "scene",
            "beats": [beat],  # ✅ 동일한 beat
            "speaker_pool": speaker_pool,
            "loop_mode": "micro_beat",
            "scenario_id": "mugen-train",
            "character_refs": {}
        },
        "recent_dialogues": recent_dialogues_turn1,
        "user_input": "배고프지 않으세요?",  # ⚡ 유저 입력
        "turn_count": 1,
        "user_name": "츠구코"
    }

    result_turn1 = await agent.run(state_turn1)
    dialogues_turn1 = result_turn1.get("agent_responses", [])

    print(f"\n✅ Generated {len(dialogues_turn1)} dialogues:")
    for d in dialogues_turn1:
        print(f"   🔹 {d['speaker']}: {d['text']}")

    # ============================================================
    # Turn 2: 유저가 "감사합니다!" 입력
    # ============================================================
    print("\n" + "=" * 60)
    print("🎬 Turn 2: 유저 입력 '감사합니다!'")
    print("=" * 60)

    # recent_dialogues 업데이트
    recent_dialogues_turn2 = recent_dialogues_turn1 + dialogues_turn1

    state_turn2 = {
        "children_ctx": {
            "stage_tag": "TRAIN_PRELUDE",
            "stage_type": "scene",
            "beats": [beat],  # ✅ 동일한 beat
            "speaker_pool": speaker_pool,
            "loop_mode": "micro_beat",
            "scenario_id": "mugen-train",
            "character_refs": {}
        },
        "recent_dialogues": recent_dialogues_turn2,
        "user_input": "감사합니다!",  # ⚡ 유저 입력
        "turn_count": 2,
        "user_name": "츠구코"
    }

    result_turn2 = await agent.run(state_turn2)
    dialogues_turn2 = result_turn2.get("agent_responses", [])

    print(f"\n✅ Generated {len(dialogues_turn2)} dialogues:")
    for d in dialogues_turn2:
        print(f"   🔹 {d['speaker']}: {d['text']}")

    # ============================================================
    # 결과 비교
    # ============================================================
    print("\n" + "=" * 60)
    print("📊 Results")
    print("=" * 60)

    print("\n🔍 Turn 0 (no user input):")
    for d in dialogues_turn0:
        print(f"   {d['speaker']}: {d['text'][:50]}...")

    print("\n🔍 Turn 1 (user: '배고프지 않으세요?'):")
    for d in dialogues_turn1:
        print(f"   {d['speaker']}: {d['text'][:50]}...")

    print("\n🔍 Turn 2 (user: '감사합니다!'):")
    for d in dialogues_turn2:
        print(f"   {d['speaker']}: {d['text'][:50]}...")

    # 대화 내용이 다른지 확인
    text_turn0 = " ".join([d['text'] for d in dialogues_turn0])
    text_turn1 = " ".join([d['text'] for d in dialogues_turn1])
    text_turn2 = " ".join([d['text'] for d in dialogues_turn2])

    if text_turn0 == text_turn1 == text_turn2:
        print("\n❌ FAIL: All turns generated identical dialogues!")
        return False
    else:
        print("\n✅ PASS: Dialogues are different across turns!")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_micro_beat())
    sys.exit(0 if success else 1)
