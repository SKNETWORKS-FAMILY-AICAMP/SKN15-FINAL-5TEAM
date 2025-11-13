"""
Parent Agent - 스테이지 라우팅 및 파이프라인 조율

Features:
- StageHandlers를 사용한 스테이지별 처리
- ChildrenAgent를 통한 대화 생성
- AffinityService를 통한 친밀도 업데이트
- MemoryService를 통한 메모리 추출
- DialogueAgent를 통한 대화 검증 (선택적)

Architecture:
- Layer 3 (Agent)
- 의존성: Services (State, Stage, Scenario, Affinity, Memory, Context, Dialogue)
- 의존성: Agents (Children, Dialogue)
- 의존성: StageHandlers (Mission, Scene, Router, FreeIntent, OpenNarrative)
"""
from typing import Dict, Any, List, Optional

from app.core.logging import get_parent_logger
from app.features.chat.services import (
    StateService,
    StageService,
    ScenarioService,
    AffinityService,
    MemoryService,
    ContextService,
    DialogueService,
)
from app.features.chat.schemas import DialogueResult, ChatMessage

from .stage_handlers import (
    MissionStageHandler,
    SceneStageHandler,
    RouterStageHandler,
    FreeIntentStageHandler,
    OpenNarrativeStageHandler,
)
from .children import ChildrenAgent
from .dialogue import DialogueAgent

logger = get_parent_logger("ParentAgent")


class ParentAgent:
    """
    Parent Agent - 스테이지 라우팅 및 파이프라인 조율 (Layer 3 - Agent)

    책임:
    - 현재 스테이지 결정
    - 적절한 StageHandler 선택 및 실행
    - ChildrenAgent를 통한 대화 생성
    - DialogueAgent를 통한 대화 검증 (선택적)
    - AffinityService를 통한 친밀도 업데이트
    - MemoryService를 통한 메모리 추출
    - 스테이지 진행 관리

    금지:
    - DB 직접 접근 (Repository 사용 금지)
    - 트랜잭션 관리
    """

    def __init__(
        self,
        state_service: Optional[StateService] = None,
        stage_service: Optional[StageService] = None,
        scenario_service: Optional[ScenarioService] = None,
        affinity_service: Optional[AffinityService] = None,
        memory_service: Optional[MemoryService] = None,
        context_service: Optional[ContextService] = None,
        dialogue_service: Optional[DialogueService] = None,
        mission_handler: Optional[MissionStageHandler] = None,
        scene_handler: Optional[SceneStageHandler] = None,
        router_handler: Optional[RouterStageHandler] = None,
        free_intent_handler: Optional[FreeIntentStageHandler] = None,
        open_narrative_handler: Optional[OpenNarrativeStageHandler] = None,
        children_agent: Optional[ChildrenAgent] = None,
        dialogue_agent: Optional[DialogueAgent] = None,
        enable_dialogue_validation: bool = False,
    ):
        """
        Args:
            state_service: State 관리 서비스
            stage_service: Stage 관리 서비스
            scenario_service: Scenario 관리 서비스
            affinity_service: 친밀도 관리 서비스
            memory_service: 메모리 추출 서비스
            context_service: Context 구성 서비스
            dialogue_service: 대화 관리 서비스
            mission_handler: Mission 스테이지 핸들러
            scene_handler: Scene 스테이지 핸들러
            router_handler: Router 스테이지 핸들러
            free_intent_handler: FreeIntent 스테이지 핸들러
            open_narrative_handler: OpenNarrative 스테이지 핸들러
            children_agent: Children Agent (대화 생성)
            dialogue_agent: Dialogue Agent (대화 검증)
            enable_dialogue_validation: 대화 검증 활성화 여부
        """
        # Services
        self.state_service = state_service or StateService()
        self.stage_service = stage_service or StageService()
        self.scenario_service = scenario_service or ScenarioService()
        self.affinity_service = affinity_service or AffinityService()
        self.memory_service = memory_service or MemoryService()
        self.context_service = context_service or ContextService()
        self.dialogue_service = dialogue_service or DialogueService()

        # StageHandlers
        self.handlers = {
            "mission": mission_handler or MissionStageHandler(),
            "scene": scene_handler or SceneStageHandler(),
            "router": router_handler or RouterStageHandler(),
            "free_intent": free_intent_handler or FreeIntentStageHandler(),
            "open_narrative": open_narrative_handler or OpenNarrativeStageHandler(),
        }

        # Agents
        self.children_agent = children_agent or ChildrenAgent()
        self.dialogue_agent = dialogue_agent or DialogueAgent()

        # Options
        self.enable_dialogue_validation = enable_dialogue_validation

        logger.info("__init__", "ParentAgent initialized with all services and handlers")

    async def run(
        self,
        user_message: str,
        session_state: Dict[str, Any],
        scenario_id: str,
    ) -> DialogueResult:
        """
        ParentAgent 메인 파이프라인

        1. State 준비
        2. 시나리오 및 현재 스테이지 로드
        3. StageHandler 선택 및 실행 → children_ctx 생성
        4. ChildrenAgent로 대화 생성
        5. DialogueAgent로 대화 검증 (선택적)
        6. AffinityService로 친밀도 업데이트
        7. MemoryService로 메모리 추출
        8. State 업데이트
        9. DialogueResult 반환

        Args:
            user_message: 사용자 메시지
            session_state: 세션 상태
            scenario_id: 시나리오 ID

        Returns:
            DialogueResult
        """
        logger.info("run", "Pipeline started", scenario_id=scenario_id)

        try:
            # 1. State 준비
            state = self.state_service.prepare_state(session_state, scenario_id, user_message)

            # 2. 시나리오 로드
            scenario = self.scenario_service.load_scenario(scenario_id)
            if not scenario:
                logger.error("run", "Scenario not found", scenario_id=scenario_id)
                return self._fallback_response(state, "시나리오를 찾을 수 없습니다.")

            # 3. 현재 스테이지 결정
            current_stage_tag = self._resolve_current_stage(state, scenario)
            stage_def = self._get_stage_definition(scenario, current_stage_tag)

            # Mountable 시나리오 (stages가 없는 경우) 처리
            if not stage_def and scenario.get("mountable", False):
                logger.info("run", "Mountable scenario without stages - using freeform", scenario_id=scenario_id)
                stage_def = {
                    "tag": current_stage_tag,
                    "type": "freeform",
                    "description": scenario.get("description", "Free conversation"),
                    "character_refs": scenario.get("character_refs", {})
                }

            if not stage_def:
                logger.error("run", "Stage not found", stage_tag=current_stage_tag)
                return self._fallback_response(state, f"스테이지 '{current_stage_tag}'를 찾을 수 없습니다.")

            logger.info("run", f"Current stage: {current_stage_tag} (type: {stage_def.get('type', 'scene')})")

            # 4. StageHandler 선택 및 실행 → children_ctx 생성
            stage_result = await self._execute_stage_handler(state, stage_def, scenario)
            children_ctx = stage_result.children_ctx

            logger.info("run", "StageHandler executed",
                       stage_type=children_ctx.get("stage_type"),
                       beats_count=len(children_ctx.get("beats", [])))

            # 5. ChildrenAgent로 대화 생성
            state["children_ctx"] = children_ctx
            state = await self.children_agent.run(state)
            agent_responses = state.get("agent_responses", [])

            logger.info("run", "Dialogues generated", count=len(agent_responses))

            # 6. DialogueAgent로 대화 검증 (선택적)
            if self.enable_dialogue_validation and agent_responses:
                agent_responses = await self._validate_dialogues(agent_responses, state)
                state["agent_responses"] = agent_responses

            # 7. 대화 포맷팅 및 ChatMessage 변환
            dialogues = self._format_dialogues(agent_responses, state)

            # 8. AffinityService로 친밀도 업데이트
            affinity_delta = {}
            if dialogues and user_message:
                affinity_delta = await self._update_affinity(state, user_message, agent_responses)

            # 9. MemoryService로 메모리 추출 (비동기, 논블로킹)
            # TODO: 실제 구현에서는 백그라운드 태스크로 처리
            # await self._extract_memories(state, user_message, agent_responses)

            # 10. 스테이지 진행 관리
            stage_complete = stage_result.stage_complete
            next_stage = stage_result.next_stage

            # 11. State 업데이트
            updated_state = self.state_service.update_state(
                state,
                dialogues=[msg.dict() if hasattr(msg, "dict") else msg for msg in dialogues],
                next_stage=next_stage,
                stage_complete=stage_complete
            )

            # 12. DialogueResult 반환
            result = DialogueResult(
                dialogues=dialogues,
                next_stage=next_stage or current_stage_tag,
                stage_complete=stage_complete,
                updated_state=updated_state,
                affinity_delta=affinity_delta,
                affinity_scores=updated_state.get("affinity_scores", {})  # 현재 친밀도 포함
            )

            logger.info("run", "Pipeline completed",
                       dialogues_count=len(dialogues),
                       stage_complete=stage_complete,
                       next_stage=next_stage)

            return result

        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            logger.error("run", f"Pipeline failed: {e}\n{tb_str}")
            return self._fallback_response(session_state, f"오류가 발생했습니다: {str(e)[:50]}")

    def _resolve_current_stage(self, state: Dict[str, Any], scenario: Dict[str, Any]) -> str:
        """
        현재 스테이지 결정

        Args:
            state: 게임 상태
            scenario: 시나리오 데이터

        Returns:
            현재 스테이지 태그
        """
        # 1. state에서 current_stage 확인
        current_stage = state.get("current_stage")
        if current_stage:
            return current_stage

        # 2. 시나리오의 첫 스테이지 사용
        stages = scenario.get("stages", [])
        if stages:
            first_stage = stages[0]
            if isinstance(first_stage, dict):
                return first_stage.get("tag", "intro")
            return str(first_stage)

        # 3. 기본값
        return "intro"

    def _get_stage_definition(
        self,
        scenario: Dict[str, Any],
        stage_tag: str
    ) -> Optional[Dict[str, Any]]:
        """
        스테이지 정의 가져오기

        Args:
            scenario: 시나리오 데이터
            stage_tag: 스테이지 태그

        Returns:
            스테이지 정의 dict 또는 None
        """
        stages = scenario.get("stages", [])
        for stage in stages:
            if isinstance(stage, dict) and stage.get("tag") == stage_tag:
                # beats_i18n이 있으면 i18n에서 beats를 로드
                if "beats_i18n" in stage and "beats" not in stage:
                    beats_key = stage["beats_i18n"]
                    scenario_id = scenario.get("scenario_id", "unknown")
                    beats = self.scenario_service.get_beats_for_stage(scenario_id, stage_tag.lower())
                    if beats:
                        stage = dict(stage)  # 원본 수정 방지
                        stage["beats"] = beats
                        logger.debug("_get_stage_definition",
                                   f"Loaded {len(beats)} beats from i18n key: {beats_key}")
                    else:
                        logger.warning("_get_stage_definition",
                                     f"No beats found for i18n key: {beats_key}")
                return stage

        return None

    async def _execute_stage_handler(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ):
        """
        StageHandler 실행

        Args:
            state: 게임 상태
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            StageResult
        """
        stage_type = stage.get("type", "scene").lower()
        # Freeform을 open_narrative로 매핑 (mountable 시나리오용)
        if stage_type == "freeform":
            stage_type = "open_narrative"
        handler = self.handlers.get(stage_type, self.handlers["scene"])

        logger.debug("_execute_stage_handler", f"Using handler: {stage_type}")

        # Handler 실행 (async/sync 모두 지원)
        if hasattr(handler.handle, "__call__"):
            result = handler.handle(state, stage, scenario)
            # async handler인 경우
            if hasattr(result, "__await__"):
                result = await result
            return result
        else:
            raise ValueError(f"Handler {stage_type} has no handle() method")

    async def _validate_dialogues(
        self,
        dialogues: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        DialogueAgent를 사용한 대화 검증 및 수정

        Args:
            dialogues: 대화 리스트
            state: 게임 상태

        Returns:
            검증/수정된 대화 리스트
        """
        validated_dialogues = []

        for dialogue in dialogues:
            text = dialogue.get("text", "")
            speaker = dialogue.get("speaker", "narr")

            if not text:
                continue

            # DialogueAgent로 검증 및 수정
            result = await self.dialogue_agent.validate_and_correct(
                dialogue_text=text,
                speaker=speaker,
                state=state,
                max_retries=1
            )

            if result["is_valid"]:
                validated_dialogues.append(dialogue)
            else:
                # 수정된 대화 사용
                corrected_text = result.get("corrected_text") or text
                dialogue["text"] = corrected_text
                dialogue["validation_issues"] = result.get("issues", [])
                validated_dialogues.append(dialogue)

        return validated_dialogues

    def _format_dialogues(
        self,
        dialogues: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> List[ChatMessage]:
        """
        대화 포맷팅 및 ChatMessage 변환

        Note: 렌더링({user} → 실제 이름)은 하지 않음!
        DB에는 {user} 플레이스홀더가 저장되어야 함.
        렌더링은 Controller에서 응답 반환 시에만 수행.

        Args:
            dialogues: 대화 리스트 (dict, {user} 플레이스홀더 포함)
            state: 게임 상태

        Returns:
            ChatMessage 리스트 ({user} 플레이스홀더 유지)
        """
        # ChatMessage로 변환만 수행 (렌더링 없음)
        messages = []
        for d in dialogues:
            messages.append(ChatMessage(
                speaker=d.get("speaker", "narr"),
                text=d.get("text", ""),
                emotion=d.get("emotion", "neutral"),
                fx=d.get("fx"),
                image=d.get("image")
            ))

        return messages

    async def _update_affinity(
        self,
        state: Dict[str, Any],
        user_input: str,
        dialogues: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        AffinityService를 통한 친밀도 업데이트

        Args:
            state: 게임 상태
            user_input: 사용자 입력
            dialogues: 생성된 대화 리스트

        Returns:
            친밀도 변화량 (character_id -> delta)
        """
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
            old_affinity = state.get("affinity_scores", {})  # Use affinity_scores, not affinity
            affinity_delta = {}

            for char, new_score in updated_affinity.items():
                old_score = old_affinity.get(char, 0)  # 기본값 0 (500은 너무 높음)
                delta = new_score - old_score
                if delta != 0:
                    affinity_delta[char] = delta
                    logger.info("_update_affinity", f"{char}: {old_score} → {new_score} ({delta:+d})")

            # state 업데이트 (affinity_scores로 저장)
            state["affinity_scores"] = updated_affinity

            return affinity_delta

        except Exception as e:
            logger.error("_update_affinity", f"Affinity update failed: {e}", exc_info=True)
            return {}

    def _extract_participating_characters(self, dialogues: List[Dict[str, Any]]) -> List[str]:
        """
        대화에서 등장 캐릭터 추출

        Args:
            dialogues: 대화 리스트

        Returns:
            캐릭터 ID 리스트
        """
        characters = set()

        for dialogue in dialogues:
            speaker = dialogue.get("speaker", "")
            if speaker and speaker != "narr" and speaker != "시스템":
                characters.add(speaker)

        return list(characters)

    async def _extract_memories(
        self,
        state: Dict[str, Any],
        user_input: str,
        dialogues: List[Dict[str, Any]]
    ) -> None:
        """
        MemoryService를 통한 메모리 추출

        TODO: 백그라운드 태스크로 처리

        Args:
            state: 게임 상태
            user_input: 사용자 입력
            dialogues: 생성된 대화 리스트
        """
        try:
            # 대화 텍스트 결합
            combined_text = f"사용자: {user_input}\n"
            for d in dialogues:
                speaker = d.get("speaker", "")
                text = d.get("text", "")
                combined_text += f"{speaker}: {text}\n"

            # MemoryService로 메모리 추출
            result = await self.memory_service.process_conversation_turn(
                user_input=user_input,
                assistant_response="\n".join([d.get("text", "") for d in dialogues]),
                context={"scenario_id": state.get("scenario_id")}
            ) 

            logger.info("_extract_memories",
                       entities=len(result["entities"]),
                       relationships=len(result["relationships"]))

            # TODO: 추출된 메모리를 Repository를 통해 저장
            # (UseCase 레이어에서 처리해야 함)

        except Exception as e:
            logger.error("_extract_memories", f"Memory extraction failed: {e}", exc_info=True)

    def _fallback_response(
        self,
        state: Dict[str, Any],
        message: str
    ) -> DialogueResult:
        """
        폴백 응답 생성

        Args:
            state: 게임 상태
            message: 오류 메시지

        Returns:
            DialogueResult
        """
        fallback_dialogues = [
            ChatMessage(
                speaker="시스템",
                text=message,
                emotion="neutral"
            )
        ]

        return DialogueResult(
            dialogues=fallback_dialogues,
            next_stage=state.get("current_stage", "intro"),
            stage_complete=False,
            updated_state=state,
            affinity_delta={},
            affinity_scores=state.get("affinity_scores", {})  # 현재 친밀도 포함
        )


# 싱글톤 인스턴스
_default_parent_agent: Optional[ParentAgent] = None


def get_parent_agent() -> ParentAgent:
    """ParentAgent 싱글톤"""
    global _default_parent_agent
    if _default_parent_agent is None:
        _default_parent_agent = ParentAgent()
    return _default_parent_agent


async def run_parent_agent(
    user_message: str,
    session_state: Dict[str, Any],
    scenario_id: str
) -> DialogueResult:
    """
    ParentAgent 실행 헬퍼

    Args:
        user_message: 사용자 메시지
        session_state: 세션 상태
        scenario_id: 시나리오 ID

    Returns:
        DialogueResult
    """
    agent = get_parent_agent()
    return await agent.run(user_message, session_state, scenario_id)


__all__ = ["ParentAgent", "get_parent_agent", "run_parent_agent"]
