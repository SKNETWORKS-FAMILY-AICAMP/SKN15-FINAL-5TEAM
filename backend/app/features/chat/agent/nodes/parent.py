"""
Parent Agent Node - 세션 검증 및 컨텍스트 준비 (LangGraph 노드)

역할:
- 1~4단계: State 준비, 시나리오 로드, 스테이지 결정, StageHandler 실행
- children_ctx 생성하여 다음 노드로 전달
"""
from typing import Dict, Any, Optional
from ..graph_state import GraphState
from app.core.logging import get_parent_logger as get_service_logger
from app.features.chat.services import ScenarioService, StateService

from ..stage_handlers import (
    MissionStageHandler,
    SceneStageHandler,
    RouterStageHandler,
    FreeIntentStageHandler,
    OpenNarrativeStageHandler,
)

logger = get_service_logger("ParentNode")


class ParentAgent:
    """Parent Agent Node - 오케스트레이션 (1~4단계)"""

    def __init__(
        self,
        scenario_service: Optional[ScenarioService] = None,
        state_service: Optional[StateService] = None,
        mission_handler: Optional[MissionStageHandler] = None,
        scene_handler: Optional[SceneStageHandler] = None,
        router_handler: Optional[RouterStageHandler] = None,
        free_intent_handler: Optional[FreeIntentStageHandler] = None,
        open_narrative_handler: Optional[OpenNarrativeStageHandler] = None,
    ):
        self.scenario_service = scenario_service or ScenarioService()
        self.state_service = state_service or StateService()

        # StageHandlers
        self.handlers = {
            "mission": mission_handler or MissionStageHandler(),
            "scene": scene_handler or SceneStageHandler(),
            "router": router_handler or RouterStageHandler(),
            "free_intent": free_intent_handler or FreeIntentStageHandler(),
            "open_narrative": open_narrative_handler or OpenNarrativeStageHandler(),
        }

    async def execute(self, state: GraphState) -> GraphState:
        """
        Parent Agent 실행 (1~4단계)

        1. State 준비
        2. 시나리오 로드
        3. 스테이지 결정
        4. StageHandler 실행 → children_ctx 생성
        """
        logger.info("execute", "Parent node started")

        # 세션 검증
        required = ["session_id", "user_id", "scenario_id", "user_input"]
        for field in required:
            if not state.get(field):
                state["error"] = f"Missing: {field}"
                return state

        scenario_id = state["scenario_id"]
        user_input = state.get("user_input", "")

        # 1. State 준비
        session_state = {
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
            "scenario_id": scenario_id,
            "user_name": state.get("user_name", "User"),
            "current_stage": state.get("current_stage"),
            "turn_count": state.get("turn_count", 0),
            "stage_turn": state.get("stage_turn", 0),
            "affinity_scores": state.get("affinity_scores", {}),
            "conversation_summary": state.get("conversation_summary", ""),
            # 미션 관련 상태 (세션 간 유지 필요)
            "temp_data": state.get("temp_data", {}),
            "mission": state.get("mission", {}),
            "recruit_attempts": state.get("recruit_attempts", {}),
            "allies_recruited": state.get("allies_recruited", []),
            "recruit_order": state.get("recruit_order", []),
            # ✅ counseling 시나리오용
            "active_counselor": state.get("active_counselor"),
        }

        prepared_state = self.state_service.prepare_state(session_state, scenario_id, user_input)

        # GraphState 업데이트
        for key, value in prepared_state.items():
            state[key] = value

        # 2. 시나리오 로드
        scenario = self.scenario_service.load_scenario(scenario_id)
        if not scenario:
            logger.error("execute", "Scenario not found", scenario_id=scenario_id)
            state["error"] = f"Scenario not found: {scenario_id}"
            return state

        state["scenario"] = scenario
        logger.info("execute", "Scenario loaded", scenario_id=scenario_id)

        # 3. 현재 스테이지 결정
        current_stage_tag = self._resolve_current_stage(state, scenario)
        stage_def = self._get_stage_definition(scenario, current_stage_tag)

        # Mountable 시나리오 (stages가 없는 경우) 처리
        if not stage_def and scenario.get("mountable", False):
            logger.info("execute", "Mountable scenario without stages - using freeform", scenario_id=scenario_id)
            stage_def = {
                "tag": current_stage_tag,
                "type": "freeform",
                "description": scenario.get("description", "Free conversation"),
                "character_refs": scenario.get("character_refs", {})
            }

        if not stage_def:
            logger.error("execute", "Stage not found", stage_tag=current_stage_tag)
            state["error"] = f"Stage '{current_stage_tag}' not found"
            return state

        state["current_stage"] = current_stage_tag
        state["stage_type"] = stage_def.get("type", "scene")

        logger.info("execute", f"Current stage: {current_stage_tag} (type: {stage_def.get('type', 'scene')})")

        # 4. StageHandler 선택 및 실행 → children_ctx 생성
        try:
            stage_result = await self._execute_stage_handler(state, stage_def, scenario)
            children_ctx = stage_result.children_ctx

            logger.info("execute", "StageHandler executed",
                       stage_type=children_ctx.get("stage_type"),
                       beats_count=len(children_ctx.get("beats", [])))

            # children_ctx를 state에 저장
            state["children_ctx"] = children_ctx

            # ✅ stage_type을 state에도 저장 (controller에서 router 판별용)
            stage_type = children_ctx.get("stage_type", "scene")
            state["stage_type"] = stage_type

            # stage_result 정보도 저장 (dialogue 노드에서 사용)
            state["stage_complete"] = stage_result.stage_complete
            state["next_stage"] = stage_result.next_stage

            # ✅ state_updates 병합 (active_counselor 등)
            if stage_result.state_updates:
                for key, value in stage_result.state_updates.items():
                    state[key] = value
                logger.info("execute", f"Merged state_updates: {list(stage_result.state_updates.keys())}")

            logger.info("execute", "Stage transition info set",
                       stage_complete=stage_result.stage_complete,
                       next_stage=stage_result.next_stage,
                       current_stage=current_stage_tag)

            # ✅ CRITICAL FIX: Router 스테이지가 완료되고 next_stage가 설정된 경우,
            # 즉시 다음 스테이지로 전환하여 대화를 생성
            if (stage_type == "router" and
                stage_result.stage_complete and
                stage_result.next_stage and
                stage_result.next_stage != current_stage_tag):

                logger.info("execute", f"🔄 Router stage complete - immediately advancing to {stage_result.next_stage}")

                # 다음 스테이지로 state 업데이트
                state["current_stage"] = stage_result.next_stage

                # 다음 스테이지 정의 가져오기
                next_stage_def = self._get_stage_definition(scenario, stage_result.next_stage)

                if next_stage_def:
                    # 다음 스테이지의 핸들러 실행
                    next_stage_result = await self._execute_stage_handler(state, next_stage_def, scenario)
                    next_children_ctx = next_stage_result.children_ctx

                    logger.info("execute", f"✅ Advanced to {stage_result.next_stage}",
                               stage_type=next_children_ctx.get("stage_type"),
                               beats_count=len(next_children_ctx.get("beats", [])))

                    # next_stage의 children_ctx로 덮어쓰기
                    state["children_ctx"] = next_children_ctx
                    state["stage_type"] = next_children_ctx.get("stage_type", "scene")
                    state["stage_complete"] = next_stage_result.stage_complete
                    state["next_stage"] = next_stage_result.next_stage

                    # ✅ next_stage의 state_updates도 병합
                    if next_stage_result.state_updates:
                        for key, value in next_stage_result.state_updates.items():
                            state[key] = value
                        logger.info("execute", f"Merged next_stage state_updates: {list(next_stage_result.state_updates.keys())}")
                else:
                    logger.error("execute", f"Next stage not found: {stage_result.next_stage}")

        except Exception as e:
            logger.error("execute", f"StageHandler failed: {e}", exc_info=True)
            state["error"] = f"StageHandler failed: {str(e)}"
            return state

        logger.info("execute", "Parent node completed")
        return state

    def _resolve_current_stage(self, state: Dict[str, Any], scenario: Dict[str, Any]) -> str:
        """현재 스테이지 결정"""
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
        """스테이지 정의 가져오기"""
        stages = scenario.get("stages", [])
        for stage in stages:
            if isinstance(stage, dict) and stage.get("tag") == stage_tag:
                # beats_i18n이 있으면 i18n에서 beats를 로드
                if "beats_i18n" in stage and "beats" not in stage:
                    beats_key = stage["beats_i18n"]
                    scenario_id = scenario.get("scenario_id", "unknown")
                    # beats_key에서 "beats_" 접두사 제거하여 stage_id 추출
                    stage_id = beats_key.replace("beats_", "") if beats_key.startswith("beats_") else beats_key
                    beats = self.scenario_service.get_beats_for_stage(scenario_id, stage_id)
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
        """StageHandler 실행"""
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
