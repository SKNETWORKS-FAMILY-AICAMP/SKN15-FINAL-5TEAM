"""
LangGraph Workflow 정의
멀티에이전트 워크플로우 구성
"""
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .graph_state import GraphState
from .nodes.parent import ParentAgent
from .nodes.children import ChildrenAgent
from .nodes.dialogue import DialogueAgent
from .nodes.router import RouterAgent
from .guards.guardrail import GuardrailAgent
from app.core.logging import get_parent_logger as get_service_logger

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
        workflow.add_node("children", self._children_node)
        workflow.add_node("dialogue", self._dialogue_node)
        workflow.add_node("output_guardrail", self._output_guardrail_node)

        # 엣지 정의
        workflow.set_entry_point("input_guardrail")

        # input_guardrail -> router or END
        workflow.add_conditional_edges(
            "input_guardrail",
            self._should_route,
            {
                "route": "router",
                "end": END
            }
        )

        # router -> parent or END (off_topic이면 END)
        workflow.add_conditional_edges(
            "router",
            self._should_continue_to_dialogue,
            {
                "continue": "parent",
                "end": END
            }
        )

        # parent -> children
        workflow.add_edge("parent", "children")

        # children -> dialogue
        workflow.add_edge("children", "dialogue")

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

        # 그래프 컴파일 (체크포인터 비활성화 - 성능 개선)
        # memory = MemorySaver()
        # self.compiled_graph = workflow.compile(checkpointer=memory)
        self.compiled_graph = workflow.compile()

        logger.info("_build_graph", "LangGraph workflow compiled successfully")

    # ========================================
    # 노드 구현
    # ========================================

    async def _parent_node(self, state: GraphState) -> GraphState:
        """Parent Agent 노드"""
        logger.debug("_parent_node", "Executing parent agent")
        state["agent_trace"].append("parent")

        agent = ParentAgent()
        # ParentAgent.execute()는 async 함수이므로 await 필요
        result = await agent.execute(state)

        return result

    async def _input_guardrail_node(self, state: GraphState) -> GraphState:
        """입력 가드레일 노드"""
        logger.debug("_input_guardrail_node", "Executing input guardrail")
        state["agent_trace"].append("input_guardrail")

        agent = GuardrailAgent()
        result = agent.check_input(state)

        return result

    async def _router_node(self, state: GraphState) -> GraphState:
        """Router Agent 노드"""
        logger.debug("_router_node", "Executing router agent")
        state["agent_trace"].append("router")

        agent = RouterAgent()
        result = await agent.route(state)

        return result

    async def _children_node(self, state: GraphState) -> GraphState:
        """Children Agent 노드"""
        logger.debug("_children_node", "Executing children agent")
        state["agent_trace"].append("children")

        agent = ChildrenAgent()
        result = await agent.run(state)

        return result

    async def _dialogue_node(self, state: GraphState) -> GraphState:
        """Dialogue Agent 노드"""
        logger.debug("_dialogue_node", "Executing dialogue agent")
        state["agent_trace"].append("dialogue")

        agent = DialogueAgent()
        result = await agent.generate_dialogue(state)

        return result

    async def _output_guardrail_node(self, state: GraphState) -> GraphState:
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
            "route" - Router로 진행
            "end" - 종료 (가드레일 차단)
        """
        # 가드레일 실패 시 차단 메시지 생성 후 종료
        if not state.get("is_safe", True):
            logger.warning("_should_route", f"Guardrail blocked input: {state.get('violation_type')}")

            # 차단 메시지 생성
            violation_type = state.get("violation_type", "unknown")
            block_messages = {
                "forbidden": "까악— 까악— ⚠️ 금지된 주제입니다. 까악—",
                "meta_talk": "까악— 까악— ⚠️ 게임 밖 이야기는 할 수 없습니다. 까악—",
            }

            block_message = block_messages.get(violation_type, "까악— 까악— ⚠️ 입력이 차단되었습니다. 까악—")

            # 차단 메시지를 output에 추가
            state["output"] = {
                "dialogues": [{
                    "speaker": "kasugai_crow",
                    "text": block_message,
                    "emotion": "neutral"
                }],
                "next_stage": state.get("current_stage", "intro"),
                "stage_complete": False,
                "affinity_delta": {},
                "affinity_scores": state.get("affinity_scores", {}),
            }

            logger.info("_should_route", f"Guardrail block message generated for {violation_type}")
            return "end"

        # 모든 입력은 Router를 거쳐 주제 분류 수행
        return "route"

    def _should_continue_to_dialogue(self, state: GraphState) -> str:
        """
        Router 이후 Parent로 진행할지 결정

        Returns:
            "continue" - Parent Agent 실행
            "end" - 종료 (Fallback이 이미 응답 생성 완료)
        """
        # off_topic이면 Fallback이 이미 응답을 생성했으므로 종료
        if state.get("is_off_topic", False):
            logger.info("_should_continue_to_dialogue", "Off-topic detected, ending workflow (Fallback already handled)")
            return "end"

        # on_topic이면 Parent Agent로 진행
        logger.info("_should_continue_to_dialogue", "On-topic, proceeding to Parent")
        return "continue"

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
        if "is_off_topic" not in input_state:
            input_state["is_off_topic"] = False
        if "off_topic_count" not in input_state:
            input_state["off_topic_count"] = 0
        if "children_ctx" not in input_state:
            input_state["children_ctx"] = None
        if "agent_responses" not in input_state:
            input_state["agent_responses"] = []

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
        if "is_off_topic" not in input_state:
            input_state["is_off_topic"] = False
        if "off_topic_count" not in input_state:
            input_state["off_topic_count"] = 0
        if "children_ctx" not in input_state:
            input_state["children_ctx"] = None
        if "agent_responses" not in input_state:
            input_state["agent_responses"] = []

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
