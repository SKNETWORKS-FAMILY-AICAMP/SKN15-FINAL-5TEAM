# 목표: GraphState 강화 및 play.py 안정화

리팩토링된 시스템의 핵심 두뇌인 GraphState를 보강하여 복잡한 게임 상태를 모두 관리할 수 있도록 확장한다. 또한, 게임의 시작점이자 사용자 인터페이스인 play.py에 강력한 에러 처리, 사용자 입력 관리, 명확한 출력 로직을 추가하여 어떤 상황에서도 프로그램이 멈추지 않는 안정적인 실행 환경을 구축한다.

# 작업 지시사항

## 단계 1: GraphState 기능 확장 (src/core/graph_state.py)

src/core/graph_state.py 파일을 열고, GraphState 클래스를 아래와 같이 확장하여 시스템의 모든 상황을 추적할 수 있도록 보강한다.

Python

# src/core/graph_state.py

from typing import TypedDict, List, Dict, Optional, Any
from langchain_core.messages import BaseMessage
from typing_extensions import Annotated

class GraphState(TypedDict):
    """
    LangGraph의 모든 노드가 공유하는 중앙 데이터 저장소(State).
    시스템의 모든 상태를 추적하고 관리할 수 있도록 확장됨.
    """
    # LangGraph 표준
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    
    # 워크플로우 제어
    next_node: str

    # 세션 및 시나리오 정보
    session_id: str
    current_scene_id: str
    
    # 턴 및 시간 관리
    turn_count: int
    is_timeout: bool

    # 사용자 상호작용
    user_input: str
    user_inputs_history: List[str]
    available_choices: List[Dict] # 예: [{"id": "A", "text": "..."}]

    # 에이전트 출력
    agent_responses: List[Dict] # 예: {"speaker": "Tanjiro", "text": "..."}
    
    # 캐릭터 및 관계
    active_character: str
    affinity_scores: Dict[str, int] # 예: {"inosuke": 70}

    # 미션 및 플래그
    mission_result: Optional[str] # 'success', 'failure'
    system_flags: List[str] # 예: ["rengoku_arrived", "mission_started"]

    # 에러 및 예외 처리
    error_message: Optional[str]
    
    # (옵션) 툴 실행 결과
    tool_outputs: Optional[Dict[str, Any]]
## 단계 2: play.py 안정성 강화 (Robust Execution)

루트 폴더의 play.py 파일을 아래의 내용으로 전체 교체한다. 이 코드는 무한 루프, 사용자 입력 처리, 예외 처리, 명확한 상태 출력을 포함하여 안정성을 극대화했다.

Python

# play.py

import uuid
from langchain_core.messages import HumanMessage
from src.core.workflow import create_workflow
from src.core.graph_state import GraphState

def main():
    """
    KIME-CHAT-AGENT의 메인 실행 함수.
    안정적인 게임 루프와 예외 처리를 포함합니다.
    """
    # 1. 워크플로우 컴파일
    app = create_workflow()
    session_id = str(uuid.uuid4())
    print("==============================================")
    print(" KIME 대화형 에이전트에 오신 것을 환영합니다!")
    print(f" 새로운 세션이 시작되었습니다: {session_id}")
    print("==============================================")
    print("게임을 종료하려면 'exit' 또는 'quit'을 입력하세요.")

    # 2. 초기 상태 정의
    initial_state: GraphState = {
        "messages": [],
        "next_node": "router",
        "session_id": session_id,
        "current_scene_id": "intro", # 시작 씬 ID
        "turn_count": 0,
        "is_timeout": False,
        "user_input": "시작", # 첫 입력을 "시작"으로 고정
        "user_inputs_history": [],
        "available_choices": [],
        "agent_responses": [],
        "active_character": "system",
        "affinity_scores": {"tanjiro": 50, "inosuke": 50, "zenitsu": 50}, # 초기 호감도
        "mission_result": None,
        "system_flags": [],
        "error_message": None,
        "tool_outputs": None,
    }
    
    # 3. 안정적인 메인 게임 루프
    while True:
        try:
            # 4. 워크플로우 실행 및 결과 스트리밍
            events = app.stream(initial_state, {"recursion_limit": 100})
            final_state = None

            print("\n--- [시스템 처리중...] ---")
            for event in events:
                if "messages" in event:
                    # 'messages' 이벤트는 LangChain 내부 이벤트이므로, 사용자에게 직접 표시하지 않음
                    pass
                else:
                    # 다른 모든 노드의 출력을 명확하게 표시 (디버깅에 유용)
                    node_name = list(event.keys())[0]
                    node_output = event[node_name]
                    # print(f"Node '{node_name}':") # 상세 디버깅 시 주석 해제
                    # print(f"  - Output: {node_output}")
                
                # 마지막 이벤트의 상태를 저장
                final_state = event.get(list(event.keys())[-1])

            # 5. 최종 결과 출력 및 상태 업데이트
            if final_state and final_state.get("agent_responses"):
                # 마지막 응답만 출력
                last_response = final_state["agent_responses"][-1]
                speaker = last_response.get("speaker", "나레이션")
                text = last_response.get("text", "")
                
                print("\n----------------------------------------------")
                print(f"[{speaker}]: {text}")
                print("----------------------------------------------")

                # 다음 루프를 위해 상태 업데이트
                initial_state = final_state
                initial_state["agent_responses"] = [] # 응답 기록 초기화

            # 6. 사용자 입력 처리
            user_input = input("\n[당신]: ").strip()

            if user_input.lower() in ["exit", "quit", "종료", "나가기"]:
                print("게임을 종료합니다. 이용해주셔서 감사합니다.")
                break

            # 다음 턴을 위해 사용자 입력을 상태에 추가
            initial_state["user_input"] = user_input
            initial_state["messages"] = [HumanMessage(content=user_input)]


        except Exception as e:
            print(f"\n🚨 치명적인 오류가 발생했습니다: {e}")
            print("안전 모드로 전환합니다. 10초 후 재시작하거나, 'exit'로 종료할 수 있습니다.")
            # 실제 프로덕션에서는 여기에 에러 로그를 기록하는 로직 추가
            # from src.utils.logger import log_error
            # log_error(e)
            try:
                # 10초 대기 또는 사용자 입력 기다리기
                import time
                time.sleep(10)
            except KeyboardInterrupt:
                print("\n게임을 강제 종료합니다.")
                break

if __name__ == "__main__":
    main()
