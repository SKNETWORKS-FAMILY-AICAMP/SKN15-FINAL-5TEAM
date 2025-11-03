"""
LangGraph 워크플로우 통합

리팩터링 요약:
1. 시나리오 특화 노드 제거 (Generic 워크플로우로 통합)
2. 불필요한 조건 분기 로직 제거
3. 사용하지 않는 imports 제거
4. 중복된 docstring 제거
5. Thread-safe global variable 관리 개선
"""

import threading
import time

from langgraph.graph import END, StateGraph

from src.agents.children_agent import run_children_agent
from src.agents.dialogue_agent import run_dialogue_agent
from src.agents.guardrail_agent import run_guardrail_agent
from src.agents.parent_agent import parent_after_dialogue, run_parent_agent
from src.agents.router_agent import run_router_agent
from src.core.graph_state import GraphState

# Thread-safe global variable lock
_global_lock = threading.Lock()


class KimeChatWorkflow:
    """Kime Chat 워크플로우 관리자"""

    def __init__(self, debug: bool = False):
        """
        워크플로우 초기화

        Args:
            debug: 디버그 모드 (로깅 활성화)
        """
        self.debug = debug
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구축 (Generic)"""
        workflow = StateGraph(GraphState)

        # Generic 노드 추가
        workflow.add_node("guardrail", self._guardrail_node)
        workflow.add_node("router", self._router_node)
        workflow.add_node("parent_agent", self._parent_node)
        workflow.add_node("children_agent", self._children_node)
        workflow.add_node("dialogue_agent", self._dialogue_node)

        # 시작점: Guardrail이 먼저 실행
        workflow.set_entry_point("guardrail")

        # Guardrail → Router 또는 차단
        workflow.add_conditional_edges(
            "guardrail",
            self._route_after_guardrail,
            {
                "router": "router",
                "dialogue_agent": "dialogue_agent",
                "wait_user_input": END,
                "blocked": END,
            },
        )

        # Router → Parent Agent 분기
        workflow.add_conditional_edges(
            "router",
            self._route_after_router,
            {
                "parent_agent": "parent_agent",
                "children_agent": "children_agent",
                "warning_handler": END,
            },
        )

        # Parent → Children
        workflow.add_edge("parent_agent", "children_agent")

        # Children → Dialogue → 종료
        workflow.add_edge("children_agent", "dialogue_agent")
        workflow.add_edge("dialogue_agent", END)

        return workflow.compile()

    # ==================== 노드 함수들 ====================

    def _guardrail_node(self, state: GraphState) -> GraphState:
        """Guardrail Agent 노드"""
        if self.debug:
            print("[WORKFLOW] → guardrail", flush=True)
        started = time.perf_counter()
        result = run_guardrail_agent(state)
        duration_ms = (time.perf_counter() - started) * 1000.0
        if self.debug:
            print(f"[WORKFLOW] ← guardrail (next: {result.get('next_node', 'unknown')})", flush=True)
        print(f"⏱️ [guardrail] duration={duration_ms:.2f} ms", flush=True)
        return result

    def _router_node(self, state: GraphState) -> GraphState:
        """Router Agent 노드"""
        # 세션 종료 체크
        if (
            state.get("final_ending")
            or (state.get("temp_data") or {}).get("session_end")
        ) and not state.get("has_more_dialogues", False):
            if self.debug:
                print("[WORKFLOW] → router (skipped: session already ended)", flush=True)
            print("⏱️ [router] skipped (session already ended)", flush=True)
            state["next_node"] = END
            return state

        if self.debug:
            print("[WORKFLOW] → router", flush=True)
        user_input = state.get("user_input", "")
        started = time.perf_counter()
        result = run_router_agent(state, user_input)
        if self.debug:
            print(f"[WORKFLOW] ← router (next: {result.get('next_node', 'unknown')})", flush=True)
        duration_ms = (time.perf_counter() - started) * 1000.0
        print(f"⏱️ [router] duration={duration_ms:.2f} ms", flush=True)
        return result

    def _parent_node(self, state: GraphState) -> GraphState:
        """Parent Agent 노드"""
        if self.debug:
            print(
                f"[WORKFLOW] → parent_agent (stage: {state.get('current_stage', 'unknown')})",
                flush=True,
            )
        started = time.perf_counter()
        result = run_parent_agent(state)
        duration_ms = (time.perf_counter() - started) * 1000.0
        if self.debug:
            print(f"[WORKFLOW] ← parent_agent (next: {result.get('next_node', 'unknown')})", flush=True)
        print(f"⏱️ [parent_agent] duration={duration_ms:.2f} ms", flush=True)
        return result

    def _children_node(self, state: GraphState) -> GraphState:
        """Children Agent 노드"""
        if self.debug:
            print("[WORKFLOW] → children_agent", flush=True)

        # agent_responses 초기화 (새로운 대사 생성을 위해)
        state["agent_responses"] = []

        # agent_inputs가 비었으면 백업에서 복구
        try:
            agent_inputs = state.get("agent_inputs", {})
            if not isinstance(agent_inputs, dict) or "children" not in agent_inputs:
                backup = state.get("children_ctx")
                if backup:
                    if not isinstance(agent_inputs, dict):
                        agent_inputs = {}
                    agent_inputs["children"] = backup
                    state["agent_inputs"] = agent_inputs
        except Exception:
            pass

        started = time.perf_counter()
        result = run_children_agent(state)
        duration_ms = (time.perf_counter() - started) * 1000.0
        if self.debug:
            print("[WORKFLOW] ← children_agent", flush=True)
        print(f"⏱️ [children_agent] duration={duration_ms:.2f} ms", flush=True)
        return result

    def _dialogue_node(self, state: GraphState) -> GraphState:
        """Dialogue Agent 노드"""
        if self.debug:
            print("[WORKFLOW] → dialogue_agent", flush=True)
        started = time.perf_counter()
        result = run_dialogue_agent(state)
        # 대화 생성 후 parent_after_dialogue 호출 (스테이지 전환 로직)
        result = parent_after_dialogue(result)
        duration_ms = (time.perf_counter() - started) * 1000.0
        if self.debug:
            print("[WORKFLOW] ← dialogue_agent", flush=True)
        print(f"⏱️ [dialogue_agent] duration={duration_ms:.2f} ms", flush=True)
        return result

    # ==================== 라우팅 함수들 ====================

    def _route_after_guardrail(self, state: GraphState) -> str:
        """
        Guardrail 이후 라우팅
        - blocked: 차단된 입력 → END
        - wait_user_input: 재입력 요청 → END
        - dialogue_agent: 대화 에이전트로 직접 이동
        - router: 정상 입력 → Router로 진행
        """
        next_node = state.get("next_node", "router")
        if next_node in ["blocked", "wait_user_input", "dialogue_agent"]:
            return next_node
        return "router"

    def _route_after_router(self, state: GraphState) -> str:
        """
        Router 이후 라우팅
        모든 스테이지는 generic parent_agent로 처리
        """
        next_node = state.get("next_node", "parent_agent")
        if next_node in ["warning_handler", "children_agent"]:
            return next_node
        return "parent_agent"

    # ==================== 실행 함수 ====================

    def invoke(self, state: GraphState) -> GraphState:
        """워크플로우 실행 (동기)"""
        return self.graph.invoke(state)

    async def ainvoke(self, state: GraphState) -> GraphState:
        """워크플로우 실행 (비동기)"""
        return await self.graph.ainvoke(state)

    def stream(self, state: GraphState):
        """워크플로우 스트리밍"""
        for output in self.graph.stream(state):
            yield output


# 싱글톤 인스턴스
_workflow: KimeChatWorkflow = None


def get_workflow() -> KimeChatWorkflow:
    """워크플로우 싱글톤 인스턴스 (Thread-safe)"""
    global _workflow
    with _global_lock:
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


# Alias for compatibility
WorkflowManager = KimeChatWorkflow
