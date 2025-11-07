"""
Chat Feature - Parent Agent
에이전트 파이프라인 조율 (스테이지 라우팅)

TODO: 향후 실제 Agent 로직 구현 필요
- Guardrail Agent (입출력 검증)
- Router Agent (토픽 분류)
- Stage Handlers (mission, scene, narrative 등)
- Children Agent (LLM 대사 생성)
"""
from typing import Dict, Any
from ..schemas import DialogueResult, ChatMessage
from app.core.logging import get_parent_logger, print_layer_debug

logger = get_parent_logger("Chat")


class ChatParent:
    """
    [Layer 3] Parent Agent
    책임: 에이전트 파이프라인 실행 순서 관리, 스테이지 라우팅
    금지: DB 접근 (Repository 사용 금지), 트랜잭션 관리

    현재 상태: 더미 응답 (실제 Agent 로직은 향후 구현)
    """

    def __init__(self):
        """
        ChatParent 초기화
        """
        logger.info("__init__", "ChatParent initialized (dummy mode)")

    async def execute(
        self,
        user_message: str,
        session_state: Dict[str, Any],
        scenario_id: str
    ) -> DialogueResult:
        """
        에이전트 파이프라인 실행 (현재: 더미 구현)

        TODO: 실제 로직 구현
        1. Guardrail Agent로 입력 검증
        2. Router Agent로 토픽 분류
        3. Stage Handler로 시나리오 진행
        4. Children Agent로 LLM 대사 생성

        Args:
            user_message: 사용자 메시지
            session_state: 세션 상태
            scenario_id: 시나리오 ID

        Returns:
            DialogueResult
        """
        print_layer_debug("PARENT", "Chat", "execute", "Pipeline started (dummy)", user_message_len=len(user_message))
        logger.info("execute", "Pipeline started (dummy mode)", scenario_id=scenario_id, current_stage=session_state.get("current_stage"))

        # 더미 응답 생성
        dummy_dialogues = [
            ChatMessage(
                speaker="tanjiro",
                text=f"안녕하세요! '{user_message}'라고 말씀하셨군요. (더미 응답입니다)",
                emotion="friendly"
            )
        ]

        result = DialogueResult(
            dialogues=dummy_dialogues,
            next_stage=session_state.get("current_stage", "intro"),
            stage_complete=False,
            updated_state=session_state,
            affinity_delta={}
        )

        logger.info("execute", "Dummy response generated", dialogues_count=len(result.dialogues))
        print_layer_debug("PARENT", "Chat", "execute", "✅ Dummy response completed", dialogues=len(result.dialogues))

        return result
