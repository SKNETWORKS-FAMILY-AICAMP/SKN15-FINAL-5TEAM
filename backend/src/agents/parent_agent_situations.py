"""
Parent Agent - Situations 처리 확장 모듈

기존 parent_agent.py에 추가할 situations 처리 로직
하드코딩된 대사 대신 상황 설명 기반 처리
"""

from typing import Dict, List, Optional
from src.core.graph_state import AgentState


def handle_situation_based_cutscene(state: AgentState, stage_data: Dict) -> AgentState:
    """
    🔥 새로운 방식: situations 기반 컷신 처리

    JSON에 하드코딩된 대사 대신 상황 설명을 읽어서
    Children Agent가 LLM으로 대사를 생성하도록 컨텍스트 전달

    Args:
        state: 현재 게임 상태
        stage_data: 스테이지 데이터 (situations 포함)

    Returns:
        업데이트된 state
    """
    print(f"[PARENT] Situation-based cutscene processing", flush=True)

    # situations 데이터 가져오기
    situations = stage_data.get("situations", [])
    if not situations:
        print(f"[PARENT] No situations found, falling back to legacy mode", flush=True)
        return state

    current_turn = state.game.turn

    # 현재 턴에 해당하는 situation 찾기
    turn_situation = next(
        (s for s in situations if s.get("turn") == current_turn),
        None
    )

    if not turn_situation:
        print(f"[PARENT] No situation for turn {current_turn}", flush=True)
        return state

    # 상황 정보 추출
    scene_description = turn_situation.get("scene_description", "")
    characters = turn_situation.get("characters", [])
    user_prompt = turn_situation.get("user_prompt", "")

    print(f"[PARENT] Scene: {scene_description[:50]}...", flush=True)
    print(f"[PARENT] Characters: {len(characters)}", flush=True)

    # Children Agent에게 전달할 dialogue_context 생성
    dialogue_context = []

    for char_info in characters:
        character_id = char_info.get("id")
        emotion = char_info.get("emotion", "neutral")
        order = char_info.get("order", 0)

        # 시스템 나레이터인 경우
        if character_id in ["system", "System", "시스템"]:
            dialogue_context.append({
                "speaker": "system",
                "situation": char_info.get("situation", scene_description),
                "emotion": emotion,
                "order": order
            })
        else:
            # 일반 캐릭터인 경우
            role = char_info.get("role", "")
            motivation = char_info.get("motivation", "")
            context = char_info.get("context", "")

            # Children Agent가 이해할 수 있는 상황 컨텍스트 구성
            situation_text = f"""
[상황] {scene_description}

[{character_id}의 역할] {role}

[{character_id}의 동기] {motivation}

[{character_id}의 상황] {context}

[감정] {emotion}
""".strip()

            dialogue_context.append({
                "speaker": character_id,
                "situation": situation_text,
                "emotion": emotion,
                "role": role,
                "motivation": motivation,
                "context": context,
                "order": order
            })

    # state에 저장
    if not state.parent_decisions:
        from src.core.graph_state import ParentDecisions
        state.parent_decisions = ParentDecisions()

    state.parent_decisions.dialogue_context = dialogue_context
    state.parent_decisions.speaking_rules = {
        "cutscene_mode": True,
        "situation_based": True,  # 새 방식임을 표시
        "current_turn": current_turn,
        "auto_dialogue": True,
        "mood": turn_situation.get("atmosphere", "neutral")
    }

    # 유저 프롬프트 설정
    if user_prompt:
        state.output.user_input_prompt = user_prompt

    print(f"[PARENT] Prepared {len(dialogue_context)} character contexts", flush=True)

    return state


def should_use_situations(stage_data: Dict) -> bool:
    """
    situations 처리를 사용할지 판단

    Args:
        stage_data: 스테이지 데이터

    Returns:
        True if situations should be used, False otherwise
    """
    # situations가 있으면 새 방식 사용
    if "situations" in stage_data:
        return True

    # 없으면 기존 dialogues 방식 사용
    return False


def process_cutscene_with_fallback(state: AgentState, stage_data: Dict) -> AgentState:
    """
    컷신 처리 - situations 우선, dialogues 폴백

    Args:
        state: 현재 게임 상태
        stage_data: 스테이지 데이터

    Returns:
        업데이트된 state
    """
    # 새 방식 (situations) 우선
    if should_use_situations(stage_data):
        print(f"[PARENT] Using situation-based processing", flush=True)
        return handle_situation_based_cutscene(state, stage_data)

    # 기존 방식 (dialogues) 폴백
    print(f"[PARENT] Falling back to dialogue-based processing", flush=True)
    # 기존 parent_agent.py의 로직 사용
    return state


# ===== Parent Agent 통합 가이드 =====
"""
기존 parent_agent.py의 563번 줄 근처에 다음과 같이 통합:

```python
# 기존 코드 (563번 줄 근처)
def _handle_cutscene_stage(self, state, stage_data):
    # 🔥 새로운 situations 처리 추가
    from src.agents.parent_agent_situations import process_cutscene_with_fallback

    # situations 우선, dialogues 폴백
    state = process_cutscene_with_fallback(state, stage_data)

    # 기존 로직은 situations가 없을 때만 실행됨
    # (process_cutscene_with_fallback가 내부적으로 처리)
```

또는 더 간단하게:

```python
# parent_agent.py 상단에 import 추가
from src.agents.parent_agent_situations import should_use_situations, handle_situation_based_cutscene

# 563번 줄 근처의 cutscene 처리 로직에서:
if should_use_situations(stage_data):
    return handle_situation_based_cutscene(state, stage_data)
else:
    # 기존 dialogues 처리 로직
    dialogues = stage_data.get("dialogues", [])
    # ... (기존 코드 유지)
```
"""
