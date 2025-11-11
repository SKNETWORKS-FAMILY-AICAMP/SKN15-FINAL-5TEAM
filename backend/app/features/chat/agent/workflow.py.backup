"""
LangGraph Workflow 정의
멀티에이전트 워크플로우 구성
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .graph_state import GraphState
from .parent_agent import ParentAgent
from .dialogue_agent import DialogueAgent
from .router_agent import RouterAgent
from .guardrail_agent import GuardrailAgent
from app.core.logging import get_service_logger

logger = get_service_logger("Workflow")


class ChatWorkflow:
    """
    LangGraph 기반 대화 워크플로우

    에이전트 실행 순서:
    1. Parent Agent - 전체 조율 및 컨텍스트 준비
    2. Guardrail Agent - 입력 검증
    3. Router Agent - 스테이지 라우팅 (필요 시)
    4. Dialogue Agent - 대화 생성
    5. Guardrail Agent - 출력 검증
    """

    def __init__(self):
        """워크플로우 초기화"""
        self.graph = None
        self.compiled_graph = None
        self._build_graph()

    def _build_graph(self):
        """그래프 구성"""
        # StateGraph 생성
        workflow = StateGraph(GraphState)

        # 노드 추가
        workflow.add_node("parent", self._parent_node)
        workflow.add_node("input_guardrail", self._input_guardrail_node)
        workflow.add_node("router", self._router_node)
        workflow.add_node("dialogue", self._dialogue_node)
        workflow.add_node("output_guardrail", self._output_guardrail_node)

        # 엣지 정의
        workflow.set_entry_point("parent")

        # parent -> input_guardrail
        workflow.add_edge("parent", "input_guardrail")

        # input_guardrail -> router or dialogue
        workflow.add_conditional_edges(
            "input_guardrail",
            self._should_route,
            {
                "route": "router",
                "dialogue": "dialogue",
                "end": END
            }
        )

        # router -> dialogue
        workflow.add_edge("router", "dialogue")

        # dialogue -> output_guardrail
        workflow.add_edge("dialogue", "output_guardrail")

        # output_guardrail -> END
        workflow.add_conditional_edges(
            "output_guardrail",
            self._check_safety,
            {
                "safe": END,
                "unsafe": "dialogue"  # 재생성
            }
        )

        # 그래프 컴파일 (메모리 체크포인트 사용)
        memory = MemorySaver()
        self.compiled_graph = workflow.compile(checkpointer=memory)

        logger.info("_build_graph", "LangGraph workflow compiled successfully")

    # ========================================
    # 노드 구현
    # ========================================

    def _parent_node(self, state: GraphState) -> GraphState:
        """Parent Agent 노드"""
        logger.debug("_parent_node", "Executing parent agent")
        state["agent_trace"].append("parent")

        agent = ParentAgent()
        result = agent.execute(state)

        return result

    def _input_guardrail_node(self, state: GraphState) -> GraphState:
        """입력 가드레일 노드"""
        logger.debug("_input_guardrail_node", "Executing input guardrail")
        state["agent_trace"].append("input_guardrail")

        agent = GuardrailAgent()
        result = agent.check_input(state)

        return result

    def _router_node(self, state: GraphState) -> GraphState:
        """Router Agent 노드"""
        logger.debug("_router_node", "Executing router agent")
        state["agent_trace"].append("router")

        agent = RouterAgent()
        result = agent.route(state)

        return result

    def _dialogue_node(self, state: GraphState) -> GraphState:
        """Dialogue Agent 노드"""
        logger.debug("_dialogue_node", "Executing dialogue agent")
        state["agent_trace"].append("dialogue")

        agent = DialogueAgent()
        result = agent.generate_dialogue(state)

        return result

    def _output_guardrail_node(self, state: GraphState) -> GraphState:
        """출력 가드레일 노드"""
        logger.debug("_output_guardrail_node", "Executing output guardrail")
        state["agent_trace"].append("output_guardrail")

        agent = GuardrailAgent()
        result = agent.check_output(state)

        return result

    # ========================================
    # 조건부 엣지 함수
    # ========================================

    def _should_route(self, state: GraphState) -> str:
        """
        라우팅 필요 여부 결정

        Returns:
            "route" - 라우팅 필요
            "dialogue" - 대화 생성으로 직행
            "end" - 종료 (가드레일 실패)
        """
        # 가드레일 실패 시 종료
        if not state.get("is_safe", True):
            return "end"

        # router 타입 스테이지인 경우 라우팅
        if state.get("stage_type") == "router":
            return "route"

        # 그 외는 대화 생성
        return "dialogue"

    def _check_safety(self, state: GraphState) -> str:
        """
        출력 안전성 확인

        Returns:
            "safe" - 안전, 종료
            "unsafe" - 불안전, 재생성
        """
        if state.get("is_safe", True):
            return "safe"
        else:
            logger.warning("_check_safety", "Unsafe output detected, regenerating")
            return "unsafe"

    # ========================================
    # 실행 메서드
    # ========================================

    async def ainvoke(
        self,
        input_state: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> GraphState:
        """
        워크플로우 비동기 실행

        Args:
            input_state: 초기 상태
            config: 실행 설정

        Returns:
            최종 상태
        """
        logger.info("ainvoke", "Starting workflow execution")

        # 초기 상태 보정
        if "messages" not in input_state:
            input_state["messages"] = []
        if "agent_trace" not in input_state:
            input_state["agent_trace"] = []
        if "is_safe" not in input_state:
            input_state["is_safe"] = True
        if "guardrail_warnings" not in input_state:
            input_state["guardrail_warnings"] = []
        if "mission_completed" not in input_state:
            input_state["mission_completed"] = False

        # 실행
        result = await self.compiled_graph.ainvoke(input_state, config)

        logger.info("ainvoke", "Workflow execution completed", trace=result.get("agent_trace"))
        return result

    async def astream(
        self,
        input_state: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ):
        """
        워크플로우 스트리밍 실행

        Args:
            input_state: 초기 상태
            config: 실행 설정

        Yields:
            중간 상태 스트림
        """
        logger.info("astream", "Starting workflow streaming")

        # 초기 상태 보정
        if "messages" not in input_state:
            input_state["messages"] = []
        if "agent_trace" not in input_state:
            input_state["agent_trace"] = []
        if "is_safe" not in input_state:
            input_state["is_safe"] = True
        if "guardrail_warnings" not in input_state:
            input_state["guardrail_warnings"] = []
        if "mission_completed" not in input_state:
            input_state["mission_completed"] = False

        # 스트리밍
        async for chunk in self.compiled_graph.astream(input_state, config):
            yield chunk


# 싱글톤 인스턴스
_workflow_instance = None


def get_workflow() -> ChatWorkflow:
    """워크플로우 싱글톤"""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = ChatWorkflow()
    return _workflow_instance
