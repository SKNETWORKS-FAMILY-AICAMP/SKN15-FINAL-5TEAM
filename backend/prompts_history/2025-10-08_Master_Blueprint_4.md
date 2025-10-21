알겠습니다. 요구사항을 명확히 이해했습니다. Anthropic 대신 OpenAI를 사용하도록 시스템을 수정하는 것은 매우 중요한 변경점이며, 이를 최우선으로 반영하여 오늘 구현 목표를 달성할 수 있는 최종 설계도를 드리겠습니다.

작업 로그와 완벽하게 정리된 새 파일 구조 모두 잘 확인했습니다. 이처럼 체계적인 기반 위에서 안정성을 더하는 것은 매우 올바른 개발 순서입니다.

GraphState의 역할을 보강하고 play.py를 안정화하여, 조원들에게 자신 있게 공유할 수 있는 실행 가능한 데모 버전을 완성하는 데 집중하겠습니다.

👉 Claude에게 내릴 명령 (복사해서 사용)
# 목표: OpenAI 클라이언트 전환 및 시스템 안정화

시스템의 LLM 공급자를 Anthropic에서 OpenAI로 완전히 전환한다. 이와 함께, GraphState의 역할을 확장하여 복잡한 게임 상태를 모두 관리할 수 있도록 보강하고, play.py에 강력한 예외 처리 및 실행 로직을 추가하여 안정적인 데모 버전을 완성한다.

# 작업 지시사항

## 단계 1: LLM 공급자 변경 (OpenAI 전환)

configs/settings.yaml 파일 수정:
llm_client 설정을 아래와 같이 OpenAI 기준으로 변경한다. default_model은 사용 가능한 최신 GPT 모델로 지정한다.

YAML

# configs/settings.yaml

llm_client:
  provider: "openai"  # anthropic -> openai 로 변경
  default_model: "gpt-4-turbo" # claude -> gpt 모델로 변경
  temperature: 0.7
  max_tokens: 4000
src/utils/llm_client.py 파일 수정:
config_loader를 통해 provider 설정을 읽고, openai일 경우 ChatOpenAI 클라이언트를 생성하도록 로직을 수정한다.

Python

# src/utils/llm_client.py (수정 예시)
from langchain_openai import ChatOpenAI
# from langchain_anthropic import ChatAnthropic <- 이 부분은 삭제되거나 주석 처리
from .config_loader import get_setting

def get_llm_client():
    """설정 파일에 따라 적절한 LLM 클라이언트를 반환합니다."""
    provider = get_setting('llm_client.provider')
    model_name = get_setting('llm_client.default_model')
    temperature = get_setting('llm_client.temperature')

    if provider == "openai":
        # OPENAI_API_KEY는 환경 변수에서 자동으로 읽어옵니다.
        return ChatOpenAI(model=model_name, temperature=temperature)
    # elif provider == "anthropic":
    #     return ChatAnthropic(model=model_name, temperature=temperature)
    else:
        raise ValueError(f"지원하지 않는 LLM 공급자입니다: {provider}")

## 단계 2: GraphState 기능 확장 (src/core/graph_state.py)

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
## 단계 3: play.py 안정성 강화 (Robust Execution)

루트 폴더의 play.py 파일을 아래의 내용으로 전체 교체한다. 이 코드는 OpenAI 환경에 맞춰져 있으며, 안정적인 게임 루프와 강력한 예외 처리를 포함한다.

Python

# play.py

import uuid
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from src.core.workflow import create_workflow
from src.core.graph_state import GraphState

def main():
    """
    KIME-CHAT-AGENT의 메인 실행 함수.
    OpenAI 환경을 지원하며, 안정적인 게임 루프와 예외 처리를 포함합니다.
    """
    # .env 파일에서 환경 변수 로드 (OPENAI_API_KEY)
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("🚨 오류: OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        print(".env 파일에 'OPENAI_API_KEY=your_key' 형식으로 키를 추가해주세요.")
        return

    # 1. 워크플로우 컴파일
    app = create_workflow()
    session_id = str(uuid.uuid4())
    print("==============================================")
    print(" KIME 대화형 에이전트에 오신 것을 환영합니다! (OpenAI ver.)")
    print(f" 새로운 세션이 시작되었습니다: {session_id}")
    print("==============================================")
    print("게임을 종료하려면 'exit' 또는 'quit'을 입력하세요.")

    # 2. 초기 상태 정의
    initial_state: GraphState = {
        "messages": [],
        "next_node": "router",
        "session_id": session_id,
        "current_scene_id": "intro",
        "turn_count": 0,
        "is_timeout": False,
        "user_input": "시작",
        "user_inputs_history": [],
        "available_choices": [],
        "agent_responses": [],
        "active_character": "system",
        "affinity_scores": {"tanjiro": 50, "inosuke": 50, "zenitsu": 50},
        "mission_result": None,
        "system_flags": [],
        "error_message": None,
        "tool_outputs": None,
    }
    
    # 3. 안정적인 메인 게임 루프
    while True:
        try:
            events = app.stream(initial_state, {"recursion_limit": 100})
            final_state = None

            print("\n--- [시스템 처리중...] ---")
            for event in events:
                if not ("messages" in event):
                    node_name = list(event.keys())[0]
                final_state = event.get(list(event.keys())[-1])

            if final_state and final_state.get("agent_responses"):
                last_response = final_state["agent_responses"][-1]
                speaker = last_response.get("speaker", "나레이션")
                text = last_response.get("text", "")
                
                print("\n----------------------------------------------")
                print(f"[{speaker}]: {text}")
                print("----------------------------------------------")

                initial_state = final_state
                initial_state["agent_responses"] = [] 

            user_input = input("\n[당신]: ").strip()

            if user_input.lower() in ["exit", "quit", "종료", "나가기"]:
                print("게임을 종료합니다. 이용해주셔서 감사합니다.")
                break

            initial_state["user_input"] = user_input
            initial_state["messages"] = [HumanMessage(content=user_input)]

        except Exception as e:
            print(f"\n🚨 치명적인 오류가 발생했습니다: {e}")
            import traceback
            traceback.print_exc() # 상세한 에러 로그 출력
            print("오류가 발생하여 게임을 종료합니다.")
            break

if __name__ == "__main__":
    main()