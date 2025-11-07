"""
Chat Feature - Parent Agent
에이전트 파이프라인 조율 (스테이지 라우팅)

Phase 1: LLM 대사 생성 연동 완료
Phase 2: State & Stage Management 연동 완료
TODO: 향후 구현 필요
- Guardrail Agent (입출력 검증)
- Router Agent (토픽 분류)
- Beat 기반 대화 생성
"""
from typing import Dict, Any
from ..schemas import DialogueResult, ChatMessage
from ..services import LLMService, StateService, StageService
from app.core.logging import get_parent_logger, print_layer_debug

logger = get_parent_logger("Chat")


class ChatParent:
    """
    [Layer 3] Parent Agent
    책임: 에이전트 파이프라인 실행 순서 관리, 스테이지 라우팅
    금지: DB 접근 (Repository 사용 금지), 트랜잭션 관리

    현재 상태:
    - Phase 1: LLM 대사 생성 ✅
    - Phase 2: State & Stage Management ✅
    """

    def __init__(self):
        """
        ChatParent 초기화
        """
        self.llm_service = LLMService()
        self.state_service = StateService()
        self.stage_service = StageService()
        logger.info("__init__", "ChatParent initialized with all services")

    async def execute(
        self,
        user_message: str,
        session_state: Dict[str, Any],
        scenario_id: str
    ) -> DialogueResult:
        """
        에이전트 파이프라인 실행 (Phase 2: State & Stage 연동)

        현재 구현:
        1. State Service를 통한 상태 관리
        2. Stage Service를 통한 스테이지 진행 관리
        3. LLM Service를 통한 실제 대사 생성
        4. 스테이지 전환 로직

        TODO: 향후 구현
        5. Guardrail Agent로 입력 검증
        6. Router Agent로 토픽 분류
        7. Beat 기반 대화 생성

        Args:
            user_message: 사용자 메시지
            session_state: 세션 상태
            scenario_id: 시나리오 ID

        Returns:
            DialogueResult
        """
        print_layer_debug("PARENT", "Chat", "execute", "🚀 Pipeline started (Phase 2)", user_message_len=len(user_message))
        logger.info("execute", "Pipeline started", scenario_id=scenario_id, current_stage=session_state.get("current_stage"))

        try:
            # 1. State 준비
            state = self.state_service.prepare_state(session_state, scenario_id, user_message)

            # 2. 현재 Stage 결정
            current_stage = self.stage_service.resolve_stage(state)
            logger.info("execute", f"Current stage: {current_stage.stage_id} ({current_stage.stage_type})")

            # 3. LLM 대사 생성
            # 캐릭터 설정 (하드코딩, 향후 시나리오에서 로드)
            character_name = "탄지로"
            personality = "정의롭고 친절하며, 가족을 소중히 여기는 검사. 항상 긍정적이고 따뜻한 말투를 사용한다."

            # 스테이지별 감정 설정
            emotion_map = {
                "intro": "friendly",
                "main": "neutral",
            }
            emotion = emotion_map.get(current_stage.stage_id, "neutral")

            # 대화 이력
            conversation_history = state.get("conversation_history", [])

            # LLM 대사 생성
            dialogues = await self.llm_service.generate_simple_dialogue(
                character_name=character_name,
                user_input=user_message,
                emotion=emotion,
                personality=personality,
                conversation_history=conversation_history
            )

            # 4. 스테이지 완료 확인
            stage_complete = self.stage_service.check_stage_complete(current_stage, state)

            # 5. 다음 스테이지 결정
            next_stage_id = None
            if stage_complete:
                next_stage_id = self.stage_service.get_next_stage(current_stage, state)
                if next_stage_id:
                    logger.info("execute", f"Stage transition: {current_stage.stage_id} → {next_stage_id}")

            # 6. State 업데이트
            updated_state = self.state_service.update_state(
                state,
                dialogues=[msg.dict() for msg in dialogues],
                next_stage=next_stage_id,
                stage_complete=stage_complete
            )

            # 7. Result 생성
            result = DialogueResult(
                dialogues=dialogues,
                next_stage=next_stage_id or updated_state.get("current_stage"),
                stage_complete=stage_complete,
                updated_state=updated_state,
                affinity_delta={}
            )

            logger.info(
                "execute",
                "✅ Pipeline completed",
                dialogues_count=len(result.dialogues),
                stage_complete=stage_complete,
                next_stage=next_stage_id
            )
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
