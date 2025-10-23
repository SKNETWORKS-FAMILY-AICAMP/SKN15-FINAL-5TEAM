# LangGraph 워크플로우 통합
"""
LangGraph를 사용한 에이전트 워크플로우 구현
- Guardrail → Router → Parent → Children → Dialogue 순서
- 각 노드는 기존 에이전트 활용
- 상태는 AgentState로 관리
"""

from typing import Literal
import threading
from langgraph.graph import StateGraph, END
from src.core.graph_state import GraphState, AgentState, NodeType

# 기존 에이전트 임포트
from src.agents.router_agent import run_router_agent
from src.agents.guardrail_agent import run_guardrail_agent
from src.agents.parent_agent import run_parent_agent, parent_after_dialogue
# from src.agents.children_agent_llm import run_children_agent # LLM 기반 버전 사용
from src.agents.children_agent import run_children_agent 
from src.utils.dialogue_agent import run_dialogue_agent
from src.tools.state_tools import StateTools
from src.tools import scene_tools
# from router_agent import get_intent


# Thread-safe global variable lock
_global_lock = threading.Lock()

class KimeChatWorkflow:
    """Kime Chat 워크플로우 관리자"""
    """키메 채팅 에이전트 워크플로우"""

    def __init__(self, debug: bool = False):
        """
        워크플로우 초기화

        Args:
            debug: 디버그 모드 (로깅 활성화)
        """
        self.debug = debug
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구축 (Generic + Scenario-Specific)"""
        # StateGraph 생성 (GraphState 사용 - play.py와 일치)
        workflow = StateGraph(GraphState)

        # ===== Generic 노드 (모든 시나리오에서 사용) =====
        workflow.add_node("guardrail", self._guardrail_node)
        workflow.add_node("router", self._router_node)
        workflow.add_node("parent_agent", self._parent_node)
        workflow.add_node("children_agent", self._children_node)
        workflow.add_node("dialogue_agent", self._dialogue_node)
        workflow.add_node("state_tools", self._state_tools_node)
        workflow.add_node("scene_tools", self._scene_tools_node)

        # ===== Scenario-Specific 노드 (cutscene5_akaza) =====
        workflow.add_node("run_cutscene_intro", self._run_cutscene_intro)
        workflow.add_node("present_fork_1", self._present_fork_1)
        workflow.add_node("run_recruit_inosuke", self._run_recruit_inosuke)
        workflow.add_node("run_recruit_zenitsu", self._run_recruit_zenitsu)
        workflow.add_node("trigger_original_ending", self._trigger_original_ending)
        workflow.add_node("trigger_hidden_ending", self._trigger_hidden_ending)

        # 시작점: Guardrail이 먼저 실행
        workflow.set_entry_point("guardrail")

        # 가드레일 → 라우터 또는 차단
        workflow.add_conditional_edges(
            "guardrail",
            self._route_after_guardrail,
            {
                "router": "router",
                "dialogue_agent": "dialogue_agent",
                "wait_user_input": END,
                "blocked": END
            }
        )

        # 라우터 → Parent Agent 분기 (scenario-aware)
        workflow.add_conditional_edges(
            "router",
            self._route_after_router,
            {
                "parent_agent": "parent_agent",
                "children_agent": "children_agent",
                "run_cutscene_intro": "run_cutscene_intro",
                "present_fork_1": "present_fork_1",
                "run_recruit_inosuke": "run_recruit_inosuke",
                "run_recruit_zenitsu": "run_recruit_zenitsu",
                "trigger_original_ending": "trigger_original_ending",
                "trigger_hidden_ending": "trigger_hidden_ending",
                "warning_handler": END
            }
        )

        # Parent → State Tools → Scene Tools → Children
        workflow.add_edge("parent_agent", "state_tools")
        workflow.add_edge("state_tools", "scene_tools")
        workflow.add_edge("scene_tools", "children_agent")

        # Children → Dialogue → 종료
        workflow.add_edge("children_agent", "dialogue_agent")
        workflow.add_edge("dialogue_agent", END)

        # Scenario-specific nodes → dialogue → END
        for node in ["run_cutscene_intro", "present_fork_1", "run_recruit_inosuke",
                     "run_recruit_zenitsu", "trigger_original_ending", "trigger_hidden_ending"]:
            workflow.add_edge(node, "dialogue_agent")

        # 컴파일
        return workflow.compile()

    # ===== 노드 함수들 =====

    def _router_node(self, state: GraphState) -> GraphState:
        """Router Agent 노드"""
        if (state.get("final_ending") or (state.get("temp_data") or {}).get("session_end")) and not state.get("has_more_dialogues", False):
            print(f"[WORKFLOW] → router (skipped: session already ended)", flush=True)
            state["next_node"] = END
            return state

        print(f"[WORKFLOW] → router", flush=True)
        user_input = state.get("user_input", "")
        result = run_router_agent(state, user_input)
        print(f"[WORKFLOW] ← router (next: {result.get('next_node', 'unknown')})", flush=True)
        return result


    def _guardrail_node(self, state: GraphState) -> GraphState:
        """Guardrail Agent 노드"""
        print(f"[WORKFLOW] → guardrail", flush=True)
        result = run_guardrail_agent(state)
        print(f"[WORKFLOW] ← guardrail (next: {result.get('next_node', 'unknown')})", flush=True)
        return result

    def _parent_node(self, state: GraphState) -> GraphState:
        """Parent Agent 노드"""
        print(f"[WORKFLOW] → parent_agent (stage: {state.get('current_stage', 'unknown')})", flush=True)
        result = run_parent_agent(state)
        print(f"[WORKFLOW] ← parent_agent (next: {result.get('next_node', 'unknown')})", flush=True)
        return result

    def _children_node(self, state: GraphState) -> GraphState:
        """Children Agent 노드"""
        print(f"[WORKFLOW] → children_agent", flush=True)

        # agent_responses 초기화 (새로운 대사 생성을 위해)
        state["agent_responses"] = []

        # ★ 브릿지: agent_inputs가 비었으면 백업에서 복구
        try:
            ai = state.get("agent_inputs", {}) if hasattr(state, "get") else {}
            if (not isinstance(ai, dict)) or ("children" not in ai):
                backup = state.get("children_ctx") if hasattr(state, "get") else None
                if backup:
                    if not isinstance(ai, dict):
                        ai = {}
                    ai["children"] = backup
                    # set back
                    try:
                        state["agent_inputs"] = ai
                    except Exception:
                        try:
                            setattr(state, "agent_inputs", ai)
                        except Exception:
                            pass
        except Exception:
            pass

        result = run_children_agent(state)
        print(f"[WORKFLOW] ← children_agent", flush=True)
        return result



    def _dialogue_node(self, state: GraphState) -> GraphState:
        """Dialogue Agent 노드"""
        print(f"[WORKFLOW] → dialogue_agent", flush=True)
        result = run_dialogue_agent(state)
        # 대화 생성 후 parent_after_dialogue 호출 (스테이지 전환 로직)
        result = parent_after_dialogue(result)
        print(f"[WORKFLOW] ← dialogue_agent", flush=True)
        return result

    def _state_tools_node(self, state: GraphState) -> GraphState:
        """State Tools 노드 (Simplified for Blueprint 5)"""
        print(f"[WORKFLOW] → state_tools", flush=True)
        # 간소화: 아무것도 하지 않고 통과
        print(f"[WORKFLOW] ← state_tools", flush=True)
        return state

    def _scene_tools_node(self, state: GraphState) -> GraphState:
        """Scene Tools 노드 (Simplified for Blueprint 5)"""
        print(f"[WORKFLOW] → scene_tools", flush=True)
        # 간소화: 아무것도 하지 않고 통과
        print(f"[WORKFLOW] ← scene_tools", flush=True)
        return state

    # ===== Scenario-Specific 노드 구현 =====

    def _run_cutscene_intro(self, state: GraphState) -> GraphState:
        """
        Cutscene Intro 전용 노드 (cutscene5_akaza의 intro 스테이지)
        Parent Agent를 사용하되, intro 스테이지만 처리
        """
        if state.get("current_stage") == "intro":
            state = run_parent_agent(state)
            state = self._state_tools_node(state)
            state = self._scene_tools_node(state)
            state = run_children_agent(state)
        return state

    def _present_fork_1(self, state: GraphState) -> GraphState:
        """
        Fork Choice 전용 노드 (운명의 갈림길)
        """
        if state.get("current_stage") == "fork":
            state = run_parent_agent(state)
            state = self._state_tools_node(state)
            state = self._scene_tools_node(state)
            state = run_children_agent(state)
        return state

    def _run_recruit_inosuke(self, state: GraphState) -> GraphState:
        """
        이노스케 리크루트 전용 노드
        """
        current_stage = state.get("current_stage")
        system_flags = state.get("system_flags", [])
        if current_stage == "recruit_mission" and "inosuke_recruited" not in system_flags:
            state = run_parent_agent(state)
            state = self._state_tools_node(state)
            state = self._scene_tools_node(state)
            state = run_children_agent(state)
        return state

    def _run_recruit_zenitsu(self, state: GraphState) -> GraphState:
        """
        젠이츠 리크루트 전용 노드
        """
        current_stage = state.get("current_stage")
        system_flags = state.get("system_flags", [])
        if current_stage == "recruit_mission" and "inosuke_recruited" in system_flags:
            state = run_parent_agent(state)
            state = self._state_tools_node(state)
            state = self._scene_tools_node(state)
            state = run_children_agent(state)
        return state

    def _trigger_original_ending(self, state: GraphState) -> GraphState:
        """
        기존 원작 엔딩 트리거 (실패 시)
        """
        current_stage = state.get("current_stage")
        if current_stage in ["end_bad", "end_timeout", "reckless_sacrifice_scene"]:
            state = run_parent_agent(state)
            state = self._state_tools_node(state)
            state = self._scene_tools_node(state)
            state = run_children_agent(state)
        return state

    def _trigger_hidden_ending(self, state: GraphState) -> GraphState:
        """
        히든 엔딩 트리거 (성공 시)
        """
        if state.get("current_stage") == "end_hidden":
            state = run_parent_agent(state)
            state = self._state_tools_node(state)
            state = self._scene_tools_node(state)
            state = run_children_agent(state)
        return state

    # ===== 라우팅 함수들 =====

    def _route_after_guardrail(self, state: GraphState) -> str:
        """
        Guardrail 이후 라우팅
        - blocked: 차단된 입력 → END
        - wait_user_input: 재입력 요청 → END
        - router: 정상 입력 → Router로 진행
        """
        next_node = state.get("next_node", "router")
        if next_node in ["blocked", "wait_user_input"]:
            return next_node
        if next_node == "dialogue_agent":
            return "dialogue_agent"
        return "router"

    def _route_after_router(self, state: GraphState) -> str:
        """
        Router 이후 라우팅

        🔥 모든 스테이지는 generic parent_agent로 처리
        (scenario-specific 노드는 사용하지 않음 - 무한 루프 방지)
        """
        next_node = state.get("next_node", "parent_agent")
        if next_node != "parent_agent":
            return next_node

        # 모든 시나리오는 generic parent_agent 사용
        return "parent_agent"

    # ===== Conditional Edge Functions (사용자 요구사항) =====

    def decide_fork_1_path(self, state: GraphState) -> str:
        """
        Fork 스테이지에서 사용자 선택에 따라 분기

        Returns:
            "recruit_mission": 동료 규합 선택
            "reckless_sacrifice": 혼자 돌진 선택
        """
        user_choice = state.get("temp_data", {}).get("user_choice")

        if user_choice == "recruit_allies":
            return "recruit_mission"
        elif user_choice == "reckless_sacrifice":
            return "reckless_sacrifice"

        return "recruit_mission"  # default

    def check_persuasion_result(self, state: GraphState) -> str:
        """
        설득 결과 체크

        Returns:
            "success": 둘 다 설득 성공
            "failure": 설득 실패 또는 시간 초과
        """
        system_flags = state.get("system_flags", [])
        inosuke_recruited = "inosuke_recruited" in system_flags
        zenitsu_recruited = "zenitsu_recruited" in system_flags

        if inosuke_recruited and zenitsu_recruited:
            return "success"
        else:
            return "failure"

    def check_time_or_turn_limit(self, state: GraphState) -> str:
        """
        턴 제한 체크

        Returns:
            "within_limit": 제한 내
            "exceeded": 제한 초과
        """
        scenario_data = state.get("scenario_data", {})
        current_stage = state.get("current_stage")
        turn_count = state.get("turn_count", 0)
        max_turns = scenario_data.get("stages", {}).get(current_stage, {}).get("max_turns", 999)

        if turn_count < max_turns:
            return "within_limit"
        else:
            return "exceeded"

    # ===== 실행 함수 =====

    def invoke(self, state: GraphState) -> GraphState:
        """워크플로우 실행 (동기)"""
        result = self.graph.invoke(state)
        return result

    async def ainvoke(self, state: GraphState) -> GraphState:
        """워크플로우 실행 (비동기)"""
        result = await self.graph.ainvoke(state)
        return result

    def stream(self, state: GraphState):
        """워크플로우 스트리밍"""
        for output in self.graph.stream(state):
            yield output

# 싱글톤 인스턴스
_workflow: KimeChatWorkflow = None

def get_workflow() -> KimeChatWorkflow:
    """워크플로우 싱글톤 인스턴스"""
    global _workflow  # TODO: Use with _global_lock: for thread safety
    if _workflow is None:
        _workflow = KimeChatWorkflow()
    return _workflow

def create_workflow():
    """
    워크플로우 생성 및 컴파일
    Blueprint 3 호환성을 위한 함수

    Returns:
        컴파일된 워크플로우 (app.stream() 사용 가능)
    """
    workflow = KimeChatWorkflow()
    return workflow.graph

# 테스트
async def test_workflow():
    from agent_state_enhanced import create_enhanced_initial_state

    workflow = get_workflow()

    # 테스트 상태 생성
    state = create_enhanced_initial_state("test_workflow")
    state.user_input.content = "이노스케야, 함께 싸우자!"
    state.game.scenario_data = {
        "title": "테스트 시나리오",
        "stages": {
            "intro": {
                "type": "cutscene",
                "dialogues": [
                    {"turn": 0, "speaker": "tanjiro", "content": "안녕!", "emotion": "happy"}
                ],
                "next_stage": "mission"
            }
        }
    }
    state.game.current_stage = "intro"

    # 워크플로우 실행
    result = await workflow.ainvoke(state)

    print("=== 워크플로우 실행 결과 ===")
    print(f"최종 노드: {result.next_node}")
    print(f"대사 수: {len(result.output.dialogues)}")
    for dialogue in result.output.dialogues:
        print(f"{dialogue.speaker}: {dialogue.content}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_workflow())

# Alias for compatibility
WorkflowManager = KimeChatWorkflow
