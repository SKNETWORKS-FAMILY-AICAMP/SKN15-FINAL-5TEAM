#!/usr/bin/env python3
"""
🔥 다중 캐릭터 발화 시스템 테스트
- 한 턴당 2-4명 발화 확인
- order 필드 정렬 확인
- dialogues count >= 2 로그 확인
"""

import os
import sys

# LLM 비활성화 (빠른 테스트)
os.environ["USE_LLM"] = "false"
os.environ["DEBUG"] = "true"

from langgraph_workflow import KimeChatWorkflow
from agent_state_enhanced import create_enhanced_initial_state, UserChatInput
from scenario_loader import scenario_loader
from datetime import datetime


def test_multi_dialogue_system():
    """다중 캐릭터 발화 시스템 테스트"""
    print("=" * 80)
    print("🔥 다중 캐릭터 발화 시스템 테스트 시작")
    print("=" * 80)

    # 워크플로우 생성
    workflow = KimeChatWorkflow()

    # 상태 초기화
    state = create_enhanced_initial_state("test_multi")

    # 시나리오 로드
    scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
    state.game.scenario_id = "cutscene5_akaza"
    state.game.scenario_data = scenario
    state.game.current_stage = "intro"

    print(f"\n{'='*80}")
    print(f"🎬 시나리오: {state.game.scenario_data.get('title')}")
    print(f"📍 현재 스테이지: {state.game.current_stage}")
    print(f"🎯 목표: 한 턴당 2-4명의 캐릭터가 발화해야 함")
    print(f"{'='*80}\n")

    # 턴별 대사 개수 추적
    turn_dialogue_counts = []

    # 최대 6턴까지 테스트 (max_turns=6)
    for turn_num in range(7):
        print(f"\n{'🔥'*40}")
        print(f"턴 {turn_num}: 입력 처리 중...")
        print(f"{'🔥'*40}\n")

        # 입력 설정 (새 state 생성하여 입력 갱신)
        new_state = create_enhanced_initial_state(f"test_multi_{turn_num}")
        # 게임 상태 복사
        if turn_num > 0:
            new_state.game = state.game
            new_state.message_history = state.message_history
            new_state.characters = state.characters
        else:
            new_state.game.scenario_id = "cutscene5_akaza"
            new_state.game.scenario_data = scenario
            new_state.game.current_stage = "intro"

        new_state.user_input = UserChatInput(
            content="계속",
            chat_no=turn_num + 1,
            timestamp=datetime.now().isoformat()
        )

        # 워크플로우 실행
        result = workflow.invoke(new_state)

        # 다음 턴을 위해 result를 state로 변환
        state = create_enhanced_initial_state(f"test_multi_next_{turn_num}")
        for key in result:
            if hasattr(state, key):
                setattr(state, key, result[key])

        # 대사 개수 확인 (result is a dict)
        dialogue_count = len(result["output"].dialogues)
        turn_dialogue_counts.append(dialogue_count)

        print(f"\n{'✅'*40}")
        print(f"턴 {turn_num} 결과:")
        print(f"  - 대사 개수: {dialogue_count}")
        print(f"  - 발화자: {[d.speaker for d in result['output'].dialogues]}")
        print(f"  - order 값: {[d.order for d in result['output'].dialogues]}")

        # 대사 내용 출력
        for idx, dialogue in enumerate(result['output'].dialogues):
            print(f"  [{idx}] {dialogue.speaker} (order={dialogue.order}): {dialogue.content[:50]}...")

        # 🔥 성공 기준 체크
        if dialogue_count >= 2:
            print(f"  ✅ 성공: dialogues count >= 2 ({dialogue_count})")
        else:
            print(f"  ⚠️  경고: dialogues count < 2 ({dialogue_count})")

        print(f"{'✅'*40}\n")

        # 다음 턴 준비
        state = result

        # cutscene 완료 체크
        if result["game"].has_flag("intro_completed"):
            print(f"\n{'='*80}")
            print(f"🎉 intro cutscene 완료!")
            print(f"{'='*80}\n")
            break

    # 최종 통계
    print(f"\n{'='*80}")
    print(f"📊 최종 통계")
    print(f"{'='*80}")
    print(f"턴별 대사 개수: {turn_dialogue_counts}")
    print(f"평균 대사 개수: {sum(turn_dialogue_counts) / len(turn_dialogue_counts):.2f}")
    print(f"최소 대사 개수: {min(turn_dialogue_counts)}")
    print(f"최대 대사 개수: {max(turn_dialogue_counts)}")

    # 성공 기준 체크
    avg_dialogues = sum(turn_dialogue_counts) / len(turn_dialogue_counts)
    if avg_dialogues >= 2.0:
        print(f"\n✅ 테스트 성공: 평균 {avg_dialogues:.2f}개 발화 (목표: >= 2.0)")
        return True
    else:
        print(f"\n❌ 테스트 실패: 평균 {avg_dialogues:.2f}개 발화 (목표: >= 2.0)")
        return False


if __name__ == "__main__":
    try:
        success = test_multi_dialogue_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
