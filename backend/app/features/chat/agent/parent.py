"""
Chat Feature - Parent Agent
에이전트 파이프라인 조율 (스테이지 라우팅)

Phase 1: LLM 대사 생성 연동 완료
TODO: 향후 구현 필요
- Guardrail Agent (입출력 검증)
- Router Agent (토픽 분류)
- Stage Handlers (mission, scene, narrative 등)
"""
from typing import Dict, Any
from ..schemas import DialogueResult, ChatMessage
from ..services import LLMService
from app.core.logging import get_parent_logger, print_layer_debug

logger = get_parent_logger("Chat")


class ChatParent:
    """
    [Layer 3] Parent Agent
    책임: 에이전트 파이프라인 실행 순서 관리, 스테이지 라우팅
    금지: DB 접근 (Repository 사용 금지), 트랜잭션 관리

    현재 상태: Phase 1 - LLM 대사 생성 연동
    """

    def __init__(self):
        """
        ChatParent 초기화
        """
        self.llm_service = LLMService()
        logger.info("__init__", "ChatParent initialized with LLMService")

    async def execute(
        self,
        user_message: str,
        session_state: Dict[str, Any],
        scenario_id: str
    ) -> DialogueResult:
        """
        에이전트 파이프라인 실행 (Phase 1: LLM 연동)

        현재 구현:
        1. LLM Service를 통한 실제 대사 생성

        TODO: 향후 구현
        2. Guardrail Agent로 입력 검증
        3. Router Agent로 토픽 분류
        4. Stage Handler로 시나리오 진행

        Args:
            user_message: 사용자 메시지
            session_state: 세션 상태
            scenario_id: 시나리오 ID

        Returns:
            DialogueResult
        """
        print_layer_debug("PARENT", "Chat", "execute", "🚀 Pipeline started (LLM mode)", user_message_len=len(user_message))
        logger.info("execute", "Pipeline started with LLM", scenario_id=scenario_id, current_stage=session_state.get("current_stage"))

        # Phase 1: LLM을 사용한 실제 대사 생성
        try:
            # 캐릭터 설정 (하드코딩, 향후 시나리오에서 로드)
            character_name = "탄지로"
            personality = "정의롭고 친절하며, 가족을 소중히 여기는 검사. 항상 긍정적이고 따뜻한 말투를 사용한다."
            emotion = "friendly"

            # 대화 이력 (세션 상태에서 가져오기, 있다면)
            conversation_history = session_state.get("conversation_history", [])

            # LLM 대사 생성
            dialogues = await self.llm_service.generate_simple_dialogue(
                character_name=character_name,
                user_input=user_message,
                emotion=emotion,
                personality=personality,
                conversation_history=conversation_history
            )

            # 세션 상태 업데이트
            updated_state = {
                **session_state,
                "last_user_input": user_message,
                "turn_count": session_state.get("turn_count", 0) + 1
            }

            result = DialogueResult(
                dialogues=dialogues,
                next_stage=session_state.get("current_stage", "intro"),
                stage_complete=False,
                updated_state=updated_state,
                affinity_delta={}
            )

            logger.info("execute", "✅ LLM dialogue generated", dialogues_count=len(result.dialogues))
            print_layer_debug("PARENT", "Chat", "execute", "✅ Pipeline completed", dialogues=len(result.dialogues))

            return result

        except Exception as e:
            # Fallback: 에러 발생 시 더미 응답
            logger.error("execute", f"❌ Pipeline failed: {e}")

            fallback_dialogues = [
                ChatMessage(
                    speaker="탄지로",
                    text=f"죄송합니다. 지금은 응답하기 어렵네요. (에러: {str(e)[:50]})",
                    emotion="apologetic"
                )
            ]

            return DialogueResult(
                dialogues=fallback_dialogues,
                next_stage=session_state.get("current_stage", "intro"),
                stage_complete=False,
                updated_state=session_state,
                affinity_delta={}
            )
