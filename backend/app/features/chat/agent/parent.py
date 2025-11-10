"""
Chat Feature - Parent Agent
에이전트 파이프라인 조율 (스테이지 라우팅)

Phase 1: LLM 대사 생성 연동 완료
Phase 2: State & Stage Management 연동 완료
Phase 3: Guardrail & Router Agents 연동 완료
Phase 4: Beat 기반 대화 생성 완료
Phase 6: Scenario & Character 동적 로드 완료
TODO: 향후 구현 필요
- 임베딩 기반 검증/분류
"""
from typing import Dict, Any
from ..schemas import DialogueResult, ChatMessage
from ..services.llm_service import LLMService
from ..services.state_service import StateService
from ..services.stage_service import StageService
from ..services.scenario_service import ScenarioService
from .guards import GuardrailAgent, RouterAgent
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
    - Phase 3: Guardrail & Router Agents ✅
    - Phase 4: Beat 기반 대화 생성 ✅
    - Phase 6: Scenario & Character 동적 로드 ✅
    """

    def __init__(self):
        """
        ChatParent 초기화
        """
        self.llm_service = LLMService()
        self.state_service = StateService()
        self.stage_service = StageService()
        self.scenario_service = ScenarioService()
        self.guardrail_agent = GuardrailAgent()
        self.router_agent = RouterAgent()
        logger.info("__init__", "ChatParent initialized with all services and agents")

    async def execute(
        self,
        user_message: str,
        session_state: Dict[str, Any],
        scenario_id: str
    ) -> DialogueResult:
        """
        에이전트 파이프라인 실행 (Phase 4: Beat 기반 대화 완성)

        현재 구현:
        1. State 준비
        2. Guardrail Agent로 입력 검증
        3. Router Agent로 토픽 분류
        4. Stage Service를 통한 스테이지 진행 관리
        5. Scenario Service로 시나리오/캐릭터 로드
        6. LLM Service를 통한 실제 대사 생성
           - Beat 기반 대화 (Beats 있을 때)
           - Simple 대화 (Beats 없을 때, 폴백)
        7. 스테이지 완료 확인
        8. 다음 스테이지 결정
        9. State 업데이트
        10. Result 생성

        TODO: 향후 구현
        - 임베딩 기반 검증/분류

        Args:
            user_message: 사용자 메시지
            session_state: 세션 상태
            scenario_id: 시나리오 ID

        Returns:
            DialogueResult
        """
        print_layer_debug("PARENT", "Chat", "execute", "🚀 Pipeline started (Phase 4)", user_message_len=len(user_message))
        logger.info("execute", "Pipeline started", scenario_id=scenario_id, current_stage=session_state.get("current_stage"))

        try:
            # 1. State 준비 (먼저 준비 - 검증에서 state 필요)
            state = self.state_service.prepare_state(session_state, scenario_id, user_message)

            # 2. Guardrail: 입력 검증
            validation_result = self.guardrail_agent.validate(user_message, state)
            if not validation_result.is_valid:
                logger.warning(
                    "execute",
                    f"❌ Input validation failed: {validation_result.reason}",
                    severity=validation_result.severity
                )
                # 검증 실패 시 에러 메시지 반환
                error_dialogues = [
                    ChatMessage(
                        speaker="시스템",
                        text=validation_result.message or "입력을 확인해주세요.",
                        emotion="neutral"
                    )
                ]
                return DialogueResult(
                    dialogues=error_dialogues,
                    next_stage=state.get("current_stage", "intro"),
                    stage_complete=False,
                    updated_state=state,
                    affinity_delta={}
                )

            # 3. Router: 토픽 분류
            route_result = self.router_agent.classify(user_message, state)
            response_strategy = self.router_agent.get_response_strategy(route_result)
            logger.info(
                "execute",
                f"Topic: {route_result.topic} (confidence: {route_result.confidence:.2f})",
                strategy_emotion=response_strategy["emotion"]
            )

            # 4. 현재 Stage 결정 (State 준비 완료 후)
            current_stage = self.stage_service.resolve_stage(state)
            logger.info("execute", f"Current stage: {current_stage.stage_id} ({current_stage.stage_type})")

            # 5. 시나리오 및 캐릭터 로드
            scenario = self.scenario_service.load_scenario(scenario_id)

            # 기본 캐릭터 설정 (폴백)
            character_id = "tanjiro"
            character_name = "탄지로"

            # 시나리오에서 world_id 가져오기
            world_id = None
            if scenario:
                world_id = scenario.get("world_id")
                logger.info("execute", f"Scenario loaded: {scenario_id}, world: {world_id}")

            # 캐릭터 정보 로드
            personality = self.scenario_service.get_character_personality(character_id, scenario_id)

            # 친밀도 (state에서 가져오거나 기본값 사용)
            affinity = state.get("affinity", {}).get(character_id, 500)

            # Router 전략에서 감정 가져오기 (우선순위: Router > Character > Stage)
            emotion = response_strategy.get("emotion", "neutral")

            # 캐릭터 친밀도 기반 감정으로 보정
            if emotion == "neutral":
                emotion = self.scenario_service.get_character_emotion(character_id, affinity)

            # 스테이지별 감정으로 최종 폴백
            if emotion == "neutral":
                emotion_map = {
                    "intro": "friendly",
                    "main": "neutral",
                }
                emotion = emotion_map.get(current_stage.stage_id, "neutral")

            # 대화 이력
            conversation_history = state.get("conversation_history", [])

            # 6. LLM 대사 생성 (Beat 기반 vs Simple vs Hardcoded Intro)
            # 특수 케이스: intro 스테이지의 첫 턴일 때 하드코딩된 프롤로그
            if current_stage.stage_id == "intro" and state.get("turn_count", 0) == 0:
                logger.info("execute", "Using hardcoded intro prologue (no spoilers)")

                # 하드코딩된 프롤로그 (스포일러 없이 무한열차 배경 설명)
                dialogues = [
                    ChatMessage(
                        speaker="꺾쇠까마귀",
                        text=(
                            "까악! 까악! 임무를 전달한다!\n\n"
                            "최근 무한열차에서 40명 이상의 승객이 실종되는 사건이 발생했다! "
                            "귀살대 본부는 염주 렌고쿠 쿄쥬로를 현장에 파견했다!\n\n"
                            "너는 렌고쿠의 츠구코로서 스승을 보좌하라! "
                            "무한열차에 탑승하여 실종 사건의 진상을 밝혀내고 승객들을 보호하라!\n\n"
                            "까악! 출발이다! 까악까악!"
                        ),
                        emotion="urgent"
                    )
                ]

                # 다음 스테이지로 자동 전환 준비 (사용자가 입력하면 TRAIN_PRELUDE로)
                next_stage_id = "TRAIN_PRELUDE"
                stage_complete = True

            else:
                # Beats가 있으면 Beat 기반 대화, 없으면 Simple 대화
                beats = self.scenario_service.get_beats_for_stage(scenario_id, current_stage.stage_id)

                if beats and len(beats) > 0:
                    # Beat 기반 대화 생성
                    logger.info("execute", f"Using beat-based dialogue for stage {current_stage.stage_id}", beats_count=len(beats))

                    dialogues = await self.llm_service.generate_beat_dialogue(
                        beats=beats,
                        character_name=character_name,
                        user_input=user_message,
                        emotion=emotion,
                        personality=personality,
                        conversation_history=conversation_history
                    )
                else:
                    # Simple 대화 생성 (폴백)
                    logger.info("execute", f"Using simple dialogue for stage {current_stage.stage_id} (no beats found)")

                    dialogues = await self.llm_service.generate_simple_dialogue(
                        character_name=character_name,
                        user_input=user_message,
                        emotion=emotion,
                        personality=personality,
                        conversation_history=conversation_history
                    )

                # 일반 케이스: 스테이지 완료 확인 및 다음 스테이지 결정
                stage_complete = self.stage_service.check_stage_complete(current_stage, state)
                next_stage_id = None
                if stage_complete:
                    next_stage_id = self.stage_service.get_next_stage(current_stage, state)
                    if next_stage_id:
                        logger.info("execute", f"Stage transition: {current_stage.stage_id} → {next_stage_id}")

            # 9. State 업데이트
            updated_state = self.state_service.update_state(
                state,
                dialogues=[msg.dict() for msg in dialogues],
                next_stage=next_stage_id,
                stage_complete=stage_complete
            )

            # 10. Result 생성
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
