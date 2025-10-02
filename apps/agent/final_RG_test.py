import json
from typing import TypedDict, Dict, Any, List, Union
import os
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from openai import OpenAI

# --- 기본 환경 설정 ---

# API 키 호출
load_dotenv()
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# Config 파일 오픈
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")
with open(os.path.join(CONFIG_DIR, "routing_rules.json"), "r", encoding="utf-8") as f:
    ROUTING_RULES = json.load(f)

# --- Class 설정(렝그래프 시 무조건 필요함) ---
# GraphState는 노션에 있는 거 그대로 사용
class GraphState(TypedDict):
    session_id: str              # 현재 게임 세션 ID
    current_node: str            # 현재 실행된 노드 이름 (예: "RECRUIT_INOSUKE")
    game_mode : str              # 일단 넣을게 ㅋㅋㅋㅋㅋ
    user_history: List[str]      # 사용자의 이전 입력 기록
    agent_outputs: List[Dict]    # 에이전트의 응답 기록 ({"speaker": "Tanjiro", "text": "..."})# 게임 진행 상태
    master_turn_count: int       # 전체 턴 수 (마스터 턴)
    sub_turn_count: int          # 현재 캐릭터의 서브턴 수
    turn_limit: int              # 최대 턴 제한
    is_voting_active: bool       # 현재 투표가 진행 중인지 여부# 데이터
    affinity: Dict[str, int]     # 캐릭터별 친밀도 (예: {"inosuke": 70})
    vote_options: List[Dict]     # 현재 선택지 정보 (예: [{"id": "A", "text": "..."}])
    user_votes: Dict[str, str]   # 사용자별 투표 결과 (예: {"user123": "A"})
    scene_image_url: str         # 현재 씬에 해당하는 이미지 URL
    next_node: str               # 다음 노드
    # <<< 라우터와 가드레일 결과를 저장할 필드 추가 (디버깅에 용이)
    classification: str          # 라우터에서의 분류
    severity: str                # 가드레일에서의 분류 (week, strong) 

# --- LLM 호출 ---
def call_llm(prompt: str) -> Dict:
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        # 혹시 모를 오류 대비
        if not resp.choices or not resp.choices[0].message.content:
            print("API 응답이 비어있습니다.")
            return {}

        content = resp.choices[0].message.content.strip()
        return json.loads(content)

    except Exception as e:
        print(f"API 호출 중 심각한 오류 발생: {e}")
        return {}

# --- ROUTER 에이전트 ---
def router_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print("--- ROUTER ---")

    if not state.get("user_history") or not isinstance(state["user_history"], list):
        print("Error: state에 'user_history'가 없거나 리스트 형식이 아닙니다.")
        state["next_node"] = "wait_for_user_input" 
        return state
    
    last_message = state["user_history"][-1]

    if isinstance(last_message, dict) and 'content' in last_message:
        user_input = last_message['content']
    else:
        user_input = str(last_message)

    user_history = "\n".join(
        [m["content"] if isinstance(m, dict) and "content" in m else str(m) for m in state["user_history"][:-1]]
        )
    
    router_prompt = (
        f"Game mode: {state.get('game_mode')}\n"
        f"Routing rules: {ROUTING_RULES.get(state.get('game_mode'), {})}\n"
        f"Classify the following user input as 'on_topic' or 'off_topic'.\n"
        f"based on whether it is relevant to the above conversation/game context."
        f"context: \"{user_history}\"\n"
        f"User input: \"{user_input}\"\n"
        "Answer format JSON:\n"
        "{ \"classification\": <on_topic|off_topic>, \"keywords\": [ ... ] }\n"
    )

    llm_response = call_llm(router_prompt)
    if not isinstance(llm_response, dict):
        print(f"Error: LLM 응답이 JSON(딕셔너리) 형식이 아닙니다. 응답: {llm_response}")
        classification = "off_topic"
    else:
        classification = llm_response.get("classification", "off_topic")

    state["classification"] = classification
    state["next_node"] = "guardrail_node"
    print(f"라우터 분류 결과: {classification}") # 디버깅용 LLM의 분류 결과 확인
    return state

# --- 가드레일 에이전트 ---
def guardrail_node(state: GraphState) -> Dict[str, Any]:
    print("--- GUARDRAIL ---") # 디버깅용 출력 표시
    
    # state에서 classification 값 가져오기
    try:
        user_input = state['user_history'][-1]
        classification = state.get("classification")
        user_history = "\n".join(
                [m["content"] if isinstance(m, dict) and "content" in m else str(m) for m in state["user_history"][:-1]]
            )

        # 가드레일 프롬포트
        guardrail_prompt = f"""
        당신은 게임 대화의 맥락을 분석하는 AI입니다. 
        사용자의 마지막 입력이 게임의 현재 상황과 얼마나 벗어났는지 분석하고, 
        그 심각도를 'week' 또는 'strong' 으로 분류해 주세요.

        [분류 기준]
        - week (가벼운 이탈 / 부드러운 전환):
            - 게임 세계관과 관련이 크게 없는 질문. 
            (예: "탄지로, 너 혹시 MBTI 알아?")
            - 가벼운 감탄사나 약한 욕설 (예: "아놔", "젠장", "존나 짜증나네")

        - strong (심각한 이탈):
            - 세계관 이탈 및 지속적인 파괴 시도 
            (예: "MBTI는 성격 유형 검사야. 탄지로 넌 ISFP일 거 같아, 인터넷 검색해뵈")
            - 강한 욕설 및 모욕적 표현 (예: "씨발", "느금마")
            - 폭력적이거나 선정적, 혹은 부적절한 언어 사용.
            - 지속적으로 시스템에 개입하려는 시도. 
            (예: 탄지로 친밀도 올려줘)
            - AI의 안전 및 윤리 정책에 위배되는 모든 내용.

        [대화 내용]
        {user_history}

        [사용자의 마지막 입력]
        {user_input}

        [출력 형식]
        분석 결과를 다음 JSON 형식처럼 출력하세요.
        {{ "severity": "<week | strong>" }}
        """

        llm_response = call_llm(guardrail_prompt)
        severity = llm_response.get("severity", "week")

        # --- 다음 노드 분류 ---
        destination = ""
        if severity == "strong":
            destination = "kasugai_crows_node"
        elif classification == "on_topic":
            destination = "parent_agent"
        else:
            destination = "character_agent"
            
        print(f"가드레일 심각도: {severity}, 다음 노드: {destination}") #디버깅용 출력 확인
        return {
            "severity": severity,
            "next_node": destination
        }
    except Exception as e:
        print(f"가드레일 노드 실행 중 오류 발생: {e}")
        return {
            "severity": "week",
            "next_node": "parent_agent" 
        }

# --- Kasugai Crows --- (시스템 메시지)
def kasugai_crows_node(state: GraphState) -> Dict[str, Any]:
    print("--- Strong 위반 처리 ---")
    block_message = {"speaker": "꺾쇠 까마귀", "text": "부적절하거나 게임 진행에 맞지 않는 내용이 포함되어 있어 응답을 생성할 수 없습니다."}
    updated_outputs = state.get("agent_outputs", []) + [block_message]
    return {"agent_outputs": updated_outputs}


# --- 테스트용 가짜 노드들 ---
def character_agent_node(state: GraphState) -> Dict[str, Any]:
    print("성공: Character Agent로 정상 라우팅되었습니다.")
    return {}

def parent_agent_node(state: GraphState) -> Dict[str, Any]:
    print("성공: Parent Agent로 정상 라우팅되었습니다.")
    return {}

def wait_for_user_input_node(state: GraphState) -> Dict[str, Any]:
    print("성공: 사용자 입력을 다시 기다리는 상태로 정상 전환되었습니다.")
    return {}


# --- 그래프 설정 ---
workflow = StateGraph(GraphState)

# 노드 추가 (이름을 함수와 통일하여 혼란 방지)
workflow.add_node("router_agent", router_agent)
workflow.add_node("guardrail_node", guardrail_node)
workflow.add_node("kasugai_crows_node", kasugai_crows_node)
workflow.add_node("character_agent", character_agent_node)
workflow.add_node("parent_agent", parent_agent_node)
workflow.add_node("wait_for_user_input", wait_for_user_input_node)

# 시작점 설정
workflow.set_entry_point("router_agent")

# 라우팅 로직 함수
def route_from_next_node(state: GraphState) -> str:
    print(f"--- 라우팅 결정: 다음 노드는 '{state['next_node']}' 입니다. ---")
    return state['next_node']

# 조건부 엣지 연결
workflow.add_conditional_edges(
    "router_agent",
    route_from_next_node,
    {
        "guardrail_node": "guardrail_node"
    }
)
workflow.add_conditional_edges(
    "guardrail_node",
    route_from_next_node,
    {
        "kasugai_crows_node": "kasugai_crows_node",
        "parent_agent": "parent_agent",
        "character_agent": "character_agent"
    }
)

# 일반 엣지 연결
workflow.add_edge("kasugai_crows_node", "wait_for_user_input")
workflow.add_edge("character_agent", END)
workflow.add_edge("parent_agent", END)
workflow.add_edge("wait_for_user_input", END)

app = workflow.compile()

# --- 테스트용 ---
if __name__ == "__main__":

    print("가드레일 에이전트 최종 테스트를 시작합니다.")
    print("(종료하려면 '종료', 'exit', 'quit' 중 하나를 입력하세요)")

    while True:
        user_message = input("\n[나의 입력] > ")
        if user_message.lower() in ["종료", "exit", "quit"]:
            print("테스트를 종료합니다.")
            break

        # 일단 임시의 state를 생성 (테스트니깐)
        initial_state = GraphState(
            user_history=[
                "user는 렌고쿠의 제자이다. 무한 열차가 멈추고,", 
                "렌고쿠: 나는 나의 책무를 다할 것이다! 여기 있는 그 누구도 죽게 내버려두지 않겠다!",
                "(강렬한 기운과 함께 상현 3 아카자가 나타난다)",
                "아카자: 훌륭한 투기다... 그 상처에도 불구하고 대단한 정신력이야. 오니가 되어라, 쿄쥬로.",
                "탄지로: 렌고쿠 씨! 저 녀석은 상현의 오니야!",
                f"user: {user_message}"],
            agent_outputs=[],
            session_id="test_session_123",
            game_mode="story", ##이건 근데 Class 정의 할 땐 없던데... 넣을지 말지 정해야 할 듯
            current_node="", next_node="",
            master_turn_count=0, sub_turn_count=0, turn_limit=100,
            is_voting_active=False, affinity={}, vote_options=[],
            user_votes={}, scene_image_url="",
            classification="", severity=""
        )
        try:
            final_state = app.invoke(initial_state)

            if final_state.get('agent_outputs'):
                print("\n--- 최종 출력 메시지 ---")
                for msg in final_state['agent_outputs']:
                    speaker = msg.get("speaker", "Unknown")
                    text = msg.get("text", "")
                    print(f"   [{speaker}] {text}")
                print("--------------------")

        except Exception as e:
            print(f"그래프 실행 중 오류 발생: {e}")