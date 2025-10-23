# 목표: 에이전트 내부 로직과 GraphState 완전 동기화

play.py 실행 시 발생하는 워크플로우 내부 오류를 해결하기 위해, src/agents/ 와 src/tools/ 폴더의 모든 파이썬 파일 내부 로직을 수정한다. 각 함수가 src/core/graph_state.py에 정의된 새로운 GraphState의 구조와 변수명을 완벽하게 이해하고 값을 읽고 쓰도록 코드를 전면 수정하여, 워크플로우가 최소 1턴 이상 오류 없이 실행되도록 만든다.

# 작업 지시사항

## 단계 1: Router 에이전트 수정 (src/agents/router_agent.py)

가장 먼저 실행되는 router_agent.py부터 수정한다. 이 에이전트의 함수는 GraphState에서 사용자 입력을 읽어와야 한다.

run_router_agent (또는 유사한 이름의 함수) 내부의 state.get("user_input")과 같은 코드를 GraphState의 정확한 변수명(user_input)을 사용하도록 수정한다.

RoutingResult와 같은 반환 데이터 클래스가 graph_state.py에 정의된 것과 일치하는지 확인하고 수정한다.

## 단계 2: Parent 및 Children 에이전트 수정 (src/agents/*.py)

두 에이전트는 GraphState의 다양한 정보를 읽고 결과를 다시 GraphState에 기록해야 하므로 가장 복잡하다.

run_parent_agent 함수를 분석하여, affinity_scores, current_scene_id, system_flags 등 GraphState의 여러 값을 참조하는 모든 부분을 새로운 변수명에 맞게 수정한다.

run_children_agent 함수를 분석하여, active_character나 mission_result 같은 상태 값을 올바르게 참조하도록 수정한다.

에이전트가 처리 결과를 GraphState에 다시 쓸 때, agent_responses와 같은 정확한 키에 값을 추가하도록 로직을 수정한다. (예: state["agent_responses"].append(new_dialogue))

## 단계 3: Tools 수정 (src/tools/*.py)

scene_tools.py와 state_tools.py가 GraphState를 참조하는 부분이 있다면, 해당 부분도 새로운 변수명 규칙에 맞게 모두 수정한다. (예: state.get("session_id"))

## 단계 4: 최소 기능 테스트 스크립트 작성 (test_single_turn.py)

모든 수정이 완료되었는지 확인하기 위해, 루트 디렉토리에 test_single_turn.py 라는 이름의 간단한 테스트 파일을 생성한다. 이 파일은 play.py와 유사하지만, 사용자 입력 없이 단 한 턴만 실행하여 워크플로우가 성공적으로 완료되는지만 확인하는 것을 목표로 한다.

Python

# test_single_turn.py
import uuid
from langchain_core.messages import HumanMessage
from src.core.workflow import create_workflow
from src.core.graph_state import GraphState

def test_run():
    """워크플로우가 최소 1턴 동안 오류 없이 실행되는지 검증합니다."""
    app = create_workflow()
    session_id = str(uuid.uuid4())

    # play.py와 동일한 구조의 초기 상태
    initial_state: GraphState = {
        "messages": [HumanMessage(content="시작")],
        "next_node": "router",
        "session_id": session_id,
        "current_scene_id": "intro",
        "turn_count": 0,
        "is_timeout": False,
        "user_input": "시작",
        # ... (play.py의 initial_state와 동일하게 나머지 필드 채우기) ...
    }
    
    print("--- 워크플로우 단일 턴 실행 테스트 시작 ---")
    try:
        # invoke를 사용하여 단 한 번만 실행
        final_state = app.invoke(initial_state, {"recursion_limit": 100})
        
        print("\n--- 최종 상태 ---")
        # 중요한 최종 상태 값 몇 개를 출력하여 확인
        print(f"다음 노드: {final_state.get('next_node')}")
        print(f"에이전트 응답 수: {len(final_state.get('agent_responses', []))}")
        print(f"오류 메시지: {final_state.get('error_message')}")
        
        print("\n✅ 테스트 성공: 워크플로우가 오류 없이 1턴을 완료했습니다.")

    except Exception as e:
        print(f"\n❌ 테스트 실패: 워크플로우 실행 중 오류가 발생했습니다.")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_run()
