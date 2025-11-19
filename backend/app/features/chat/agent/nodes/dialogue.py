"""
Dialogue Agent Node - 대화 후처리 (LangGraph 노드)

역할:
- 6~12단계: 검증(선택적), 포맷팅, 친밀도, 메모리, State 업데이트, output 생성
"""
from typing import Dict, Any, List, Optional
from ..graph_state import GraphState
from app.core.logging import get_parent_logger as get_service_logger
from app.features.chat.services import (
    StateService,
    AffinityService,
    MemoryService,
)
from app.features.chat.schemas import ChatMessage

logger = get_service_logger("DialogueNode")


class DialogueAgent:
    """Dialogue Agent Node - 후처리 (6~12단계)"""

    def __init__(
        self,
        state_service: Optional[StateService] = None,
        affinity_service: Optional[AffinityService] = None,
        memory_service: Optional[MemoryService] = None,
        enable_validation: bool = False,  # 검증 기능 (현재 미사용)
    ):
        self.state_service = state_service or StateService()
        self.affinity_service = affinity_service or AffinityService()
        self.memory_service = memory_service or MemoryService()
        self.enable_validation = enable_validation

        logger.info("__init__", "DialogueAgent initialized",
                   enable_validation=enable_validation)

    async def generate_dialogue(self, state: GraphState) -> GraphState:
        """
        Dialogue Agent 실행 (6~12단계)

        6. (선택적) 대화 검증
        7. 대화 포맷팅
        8. 친밀도 업데이트
        9. 메모리 추출
        10. 스테이지 진행
        11. State 업데이트
        12. output 생성
        """
        logger.info("generate_dialogue", "Dialogue node started")

        try:
            # agent_responses 가져오기
            agent_responses = state.get("agent_responses", [])

            # ✅ Router stage는 대화 생성 없이 즉시 라우팅하므로 빈 agent_responses 허용
            stage_type = state.get("stage_type", "scene")
            if not agent_responses:
                if stage_type == "router":
                    # Router는 대화 없이 라우팅만 수행 - 빈 대화 리스트로 진행
                    logger.info("generate_dialogue", "Router stage - no dialogues needed")
                    agent_responses = []
                else:
                    logger.warning("generate_dialogue", "No agent_responses found - returning fallback")
                    state["output"] = self._create_fallback_output(state)
                    return state

            logger.info("generate_dialogue", f"Processing {len(agent_responses)} dialogues")

            # 6. (선택적) 대화 검증 - 현재 비활성화
            # if self.enable_validation:
            #     agent_responses = await self._validate_dialogues(agent_responses, state)

            # 7. 대화 포맷팅 및 ChatMessage 변환
            dialogues = self._format_dialogues(agent_responses, state)

            # 8. AffinityService로 친밀도 업데이트
            user_input = state.get("user_input", "")
            affinity_delta = {}
            if dialogues and user_input:
                affinity_delta = await self._update_affinity(state, user_input, agent_responses)

            # 9. MemoryService로 메모리 추출 (비동기, 논블로킹)
            # TODO: 실제 구현에서는 백그라운드 태스크로 처리
            # await self._extract_memories(state, user_input, agent_responses)

            # 10. 스테이지 진행 관리
            # Parent 노드에서 설정된 stage_complete가 중간 단계에서 누락되는 경우가 있어,
            # next_stage가 현재 스테이지와 다르면 완료로 간주하여 복구한다.
            current_stage = state.get("current_stage", "intro")
            next_stage = state.get("next_stage")
            stage_complete = state.get("stage_complete", False)
            if not stage_complete and next_stage and next_stage != current_stage:
                stage_complete = True

            logger.info("generate_dialogue", "Stage transition info from state",
                       stage_complete=stage_complete,
                       next_stage=next_stage,
                       current_stage=current_stage)

            # 11. State 업데이트
            dict_state = dict(state)  # GraphState → dict 변환
            logger.info("generate_dialogue", "🔍 Before update_state",
                       turn_count=dict_state.get("turn_count"),
                       stage_turn=dict_state.get("stage_turn"))

            updated_state = self.state_service.update_state(
                dict_state,
                dialogues=[self._dialogue_to_dict(msg) for msg in dialogues],
                next_stage=next_stage,
                stage_complete=stage_complete
            )

            logger.info("generate_dialogue", "🔍 After update_state",
                       turn_count=updated_state.get("turn_count"),
                       stage_turn=updated_state.get("stage_turn"))

            # GraphState에 반영
            for key, value in updated_state.items():
                state[key] = value

            logger.info("generate_dialogue", "🔍 After GraphState update",
                       turn_count=state.get("turn_count"),
                       stage_turn=state.get("stage_turn"))

            # 12. output 생성 (DialogueResult 형식)
            # ✅ 엔딩 스테이지 감지 (stage_complete=True이고 next_stage=None이면 세션 종료)
            is_ending = stage_complete and not next_stage and current_stage.startswith("END_")

            state["output"] = {
                "dialogues": [self._dialogue_to_dict(msg) for msg in dialogues],
                "next_stage": next_stage or current_stage,
                "stage_complete": stage_complete,
                "affinity_delta": affinity_delta,
                "affinity_scores": updated_state.get("affinity_scores", {}),
                "session_ended": is_ending,  # ✅ 세션 종료 플래그
            }

            if is_ending:
                logger.info("generate_dialogue", f"🏁 Session ending detected: {current_stage}")

            # messages 추가 (LangGraph 히스토리용)
            if "messages" not in state:
                state["messages"] = []

            for dialogue_dict in state["output"]["dialogues"]:
                message = {
                    "role": "assistant" if dialogue_dict.get("speaker") != "user" else "user",
                    "content": dialogue_dict.get("text", ""),
                    "speaker": dialogue_dict.get("speaker", "ai"),
                    "emotion": dialogue_dict.get("emotion", "neutral")
                }
                state["messages"].append(message)

            logger.info("generate_dialogue", "Dialogue node completed",
                       dialogues_count=len(dialogues),
                       stage_complete=stage_complete,
                       next_stage=next_stage)

        except Exception as e:
            logger.error("generate_dialogue", f"Dialogue processing failed: {e}", exc_info=True)
            state["output"] = self._create_fallback_output(state, error_message=str(e))

        return state

    def _format_dialogues(
        self,
        dialogues: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> List[ChatMessage]:
        """
        대화 포맷팅 및 ChatMessage 변환

        Note: 렌더링({user} → 실제 이름)은 하지 않음!
        DB에는 {user} 플레이스홀더가 저장되어야 함.
        """
        messages = []
        for d in dialogues:
            messages.append(ChatMessage(
                speaker=d.get("speaker", "narr"),
                text=d.get("text", ""),
                emotion=d.get("emotion", "neutral"),
                fx=d.get("fx"),
                image_index=d.get("image") or d.get("image_index")  # image → image_index
            ))

        return messages

    async def _update_affinity(
        self,
        state: Dict[str, Any],
        user_input: str,
        dialogues: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """AffinityService를 통한 친밀도 업데이트"""
        try:
            # 등장 캐릭터 추출
            participating_characters = self._extract_participating_characters(dialogues)

            if not participating_characters:
                logger.debug("_update_affinity", "No participating characters found")
                return {}

            # AffinityService로 친밀도 업데이트
            updated_affinity = await self.affinity_service.update_affinity(
                state=state,
                user_input=user_input,
                dialogues=dialogues,
                participating_characters=participating_characters
            )

            # 변화량 계산
            old_affinity = state.get("affinity_scores", {})
            affinity_delta = {}

            for char, new_score in updated_affinity.items():
                old_score = old_affinity.get(char, 0)
                delta = new_score - old_score
                if delta != 0:
                    affinity_delta[char] = delta
                    logger.info("_update_affinity", f"{char}: {old_score} → {new_score} ({delta:+d})")

            # state 업데이트
            state["affinity_scores"] = updated_affinity

            return affinity_delta

        except Exception as e:
            logger.error("_update_affinity", f"Affinity update failed: {e}", exc_info=True)
            return {}

    def _extract_participating_characters(self, dialogues: List[Dict[str, Any]]) -> List[str]:
        """대화에서 등장 캐릭터 추출"""
        characters = set()

        for dialogue in dialogues:
            speaker = dialogue.get("speaker", "")
            if speaker and speaker != "narr" and speaker != "시스템":
                characters.add(speaker)

        return list(characters)

    def _dialogue_to_dict(self, dialogue: ChatMessage) -> Dict[str, Any]:
        """ChatMessage → dict 변환"""
        if hasattr(dialogue, '__dict__'):
            result = {
                "speaker": dialogue.speaker,
                "text": dialogue.text,
                "emotion": dialogue.emotion,
            }
            # Optional 필드는 있을 때만 추가
            if hasattr(dialogue, 'fx') and dialogue.fx:
                result["fx"] = dialogue.fx
            if hasattr(dialogue, 'image_index') and dialogue.image_index:
                result["image"] = dialogue.image_index  # dict에서는 image로 저장
            return result
        elif isinstance(dialogue, dict):
            return dialogue
        else:
            return {
                "speaker": "narr",
                "text": str(dialogue),
                "emotion": "neutral"
            }

    def _create_fallback_output(
        self,
        state: Dict[str, Any],
        error_message: str = "응답 생성에 실패했습니다."
    ) -> Dict[str, Any]:
        """Fallback output 생성"""
        current_stage = state.get("current_stage", "intro")

        return {
            "dialogues": [{
                "speaker": "시스템",
                "text": f"죄송합니다. {error_message}",
                "emotion": "neutral"
            }],
            "next_stage": current_stage,
            "stage_complete": False,
            "affinity_delta": {},
            "affinity_scores": state.get("affinity_scores", {}),
        }

    async def _handle_free_intent_transition(
        self,
        state: GraphState,
        next_stage: str,
        dialogues: List[ChatMessage]
    ) -> None:
        """
        Free Intent 스테이지 전환 시 자동으로 선택지 대사 생성

        Args:
            state: 현재 상태
            next_stage: 전환될 스테이지
            dialogues: 현재 생성된 대사 목록 (여기에 추가됨)
        """
        from app.features.chat.services import ScenarioService
        from .parent import ParentAgent

        try:
            # 다음 스테이지 정보 가져오기
            scenario_service = ScenarioService()
            scenario_id = state.get("scenario_id")
            scenario = scenario_service.load_scenario(scenario_id)

            # 다음 스테이지 설정 찾기
            next_stage_config = None
            for stage in scenario.get("stages", []):
                if stage.get("tag") == next_stage:
                    next_stage_config = stage
                    break

            if not next_stage_config:
                logger.warning("_handle_free_intent_transition",
                             f"Next stage config not found: {next_stage}")
                return

            # Free Intent 스테이지가 아니면 리턴
            if next_stage_config.get("type") != "free_intent":
                logger.info("_handle_free_intent_transition",
                          f"Next stage is not free_intent: {next_stage_config.get('type')}")
                return

            logger.info("_handle_free_intent_transition",
                       f"Generating transition dialogues for free_intent stage: {next_stage}")

            # ParentAgent를 사용하여 선택지 대사 생성
            parent_agent = ParentAgent()

            # state의 stage_turn이 이미 0으로 업데이트됨
            # ParentNode를 호출하여 선택지 생성
            updated_state = await parent_agent.execute(state)

            # 생성된 대사를 현재 dialogues에 추가
            additional_responses = updated_state.get("agent_responses", [])
            if additional_responses:
                logger.info("_handle_free_intent_transition",
                          f"Added {len(additional_responses)} transition dialogues")

                # ChatMessage로 변환하여 추가
                for resp in additional_responses:
                    dialogue = ChatMessage(
                        speaker=resp.get("speaker", "narr"),
                        text=resp.get("text", ""),
                        emotion=resp.get("emotion", "neutral")
                    )
                    dialogues.append(dialogue)

                # stage_turn 증가 (선택지를 보여줬으므로)
                state["stage_turn"] = state.get("stage_turn", 0) + 1
                logger.info("_handle_free_intent_transition",
                          f"Incremented stage_turn to {state['stage_turn']}")

        except Exception as e:
            logger.error("_handle_free_intent_transition",
                        f"Failed to generate transition dialogues: {e}",
                        exc_info=True)

    