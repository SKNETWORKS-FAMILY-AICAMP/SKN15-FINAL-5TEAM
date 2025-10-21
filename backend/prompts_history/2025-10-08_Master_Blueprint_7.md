# 목표: Parent 에이전트의 '시나리오 진행' 인텔리전스 강화

현재 시스템이 시나리오 분기를 타지 못하고 일반적인 대화만 반복하는 문제를 해결한다. Parent 에이전트가 GraphState의 current_scene_id와 시나리오 데이터를 적극적으로 사용하여, 사용자의 입력에 따라 다음 씬으로 전환하거나 분기를 결정하는 등 게임의 서사를 실질적으로 진행시키는 '게임 마스터' 역할을 수행하도록 로직을 전면 강화한다.

# 작업 지시사항

## 단계 1: 시나리오 로더 강화 (src/utils/scenario_loader.py)

Parent 에이전트가 현재 씬의 정보를 쉽게 파악할 수 있도록, 특정 씬의 데이터를 가져오는 유틸리티 함수를 scenario_loader.py에 추가한다.

Python

# src/utils/scenario_loader.py 파일 하단에 추가

def get_current_scene_data(state: dict) -> dict:
    """GraphState에서 현재 시나리오와 씬 ID를 기반으로 해당 씬의 데이터를 반환합니다."""
    scenario_id = state.get("scenario_id")
    scene_id = state.get("current_scene_id")
    
    # load_scenario 함수는 이미 구현되어 있다고 가정
    full_scenario = load_scenario(scenario_id)
    
    if full_scenario and scene_id in full_scenario.get("scenes", {}):
        return full_scenario["scenes"][scene_id]
    return {}
## 단계 2: Parent 에이전트 프롬프트 및 로직 강화

Parent 에이전트가 시나리오 진행을 최우선으로 생각하도록 프롬프트와 로직을 수정한다.

configs/prompts.yaml 파일 수정:
agents.parent.system_prompt를 아래 내용으로 교체하여, 시나리오 진행의 책임을 명확히 부여한다.

YAML

# configs/prompts.yaml

parent:
  system_prompt: |
    당신은 이 게임의 총괄 디렉터이자 게임 마스터(Parent Agent)입니다.
    당신의 최우선 임무는 '현재 씬 정보'와 '사용자 입력'을 분석하여 **다음 씬(next_scene)을 결정**하는 것입니다.

    1.  **상황 분석:** 주어진 `current_scene_data`를 확인하여 현재 씬의 목표(goal), 선택지(choices), 분기 규칙(split_rules)을 파악합니다.
    2.  **사용자 의도 파악:** `user_input`이 주어진 `choices` 중 하나와 일치하는지, 혹은 분기 규칙에 해당하는 키워드인지 판단합니다.
    3.  **다음 행동 결정:**
        -   만약 사용자의 선택이 명확하다면, 해당 선택지의 `next_scene` 값을 상태에 업데이트해야 합니다.
        -   만약 현재 씬에 선택지가 없다면, 씬의 `next_scene`으로 바로 진행시켜야 합니다.
        -   만약 분기 조건에 해당한다면, 해당 `goto_scene_id`로 진행시켜야 합니다.
        -   위의 어느 경우도 아니라면, 일반 대화를 생성하도록 `children_agent`에게 지시합니다.

    당신은 **반드시 시나리오를 진행**시켜야 합니다.
src/agents/parent_agent.py 파일 수정:
run_parent_agent 함수가 실제로 get_current_scene_data를 호출하고, 그 정보를 LLM의 프롬프트에 포함시키도록 수정한다.

Python

# src/agents/parent_agent.py (수정 예시)
from src.utils.scenario_loader import get_current_scene_data
# ... 다른 import ...

def run_parent_agent(state: GraphState) -> dict:
    # ... 기존 코드 ...

    # 1. 현재 씬 데이터 가져오기
    current_scene_data = get_current_scene_data(state)

    # 2. LLM에 전달할 추가 컨텍스트 생성
    context_for_llm = f"""
    # 현재 씬 정보 (current_scene_data):
    {current_scene_data}

    # 사용자 입력 (user_input):
    {state['user_input']}
    """

    # 3. 이 컨텍스트를 HumanMessage 또는 시스템 프롬프트에 추가하여 LLM 호출
    # ... LLM 호출 로직 ...

    # 4. LLM의 응답(다음 씬 결정 등)을 분석하여 state 업데이트
    # new_scene_id = ... (LLM 응답에서 파싱)
    # state['current_scene_id'] = new_scene_id

    return state
## 단계 3: 최종 검증

모든 수정이 완료되면, 다시 python3 run_journey_tests.py를 실행한다. 이제 테스트 로그를 보면, [CHILDREN] Generated dialogue: 부분이 이전과 달리 시나리오에 맞는 구체적인 대사로 바뀌고, parent_agent가 current_scene_id를 변경하여 이야기가 실제로 진행되는 것을 확인할 수 있을 것이다.