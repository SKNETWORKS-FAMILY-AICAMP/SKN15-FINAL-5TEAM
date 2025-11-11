"""
ContextBuilder - Children Agent 컨텍스트 구성 서비스
"""
from typing import Dict, Any, Optional, List
from app.core.tools import scene_tools


class ContextBuilderService:
    """Children Agent에게 전달할 컨텍스트 구성"""

    @staticmethod
    def build_children_ctx(
        base_ctx: Dict[str, Any],
        state: Dict[str, Any],
        scenario: Dict[str, Any],
        stage: Dict[str, Any],
        next_stage: Optional[str] = None,
        immediate_advance: bool = False
    ) -> Dict[str, Any]:
        """
        Children Agent 컨텍스트 구성

        Args:
            base_ctx: 기본 컨텍스트 (Handler에서 생성)
            state: GraphState
            scenario: 시나리오 데이터
            stage: 현재 스테이지
            next_stage: 다음 스테이지 (있을 경우)
            immediate_advance: 즉시 전환 여부

        Returns:
            완전한 Children 컨텍스트
        """
        if not base_ctx:
            base_ctx = {}

        # 기본 정보
        ctx = {
            **base_ctx,
            "scenario_id": scenario.get("scenario_id"),
            "stage_tag": state.get("stage_tag") or state.get("current_stage"),
            "stage_type": scene_tools.get_stage_type(stage),
            "turn_count": state.get("turn_count", 0),
            "stage_turn": state.get("stage_turn", 0),
        }

        # Beats (대화 목표)
        if "beats" not in ctx and stage:
            beats = stage.get("beats")
            if not beats and stage.get("beats_i18n"):
                beats = scene_tools.resolve_i18n_beats(stage, scenario)
            ctx["beats"] = beats or []

        # Speaker pool (등장 캐릭터)
        if "speaker_pool" not in ctx:
            if stage and stage.get("characters"):
                ctx["speaker_pool"] = stage["characters"]
            else:
                ctx["speaker_pool"] = scene_tools.get_character_pool(scenario)

        # 다음 스테이지 정보
        if next_stage:
            ctx["next_stage"] = next_stage
            ctx["immediate_advance"] = immediate_advance

        # 사용자 정보
        ctx["user_name"] = state.get("user_name", "사용자")
        ctx["user_input"] = state.get("user_input", "")

        # 친밀도
        ctx["affinity_scores"] = state.get("affinity_scores", {})

        # Mission 정보 (mission stage용)
        if ctx["stage_type"] == "mission":
            ctx["mission"] = {
                "target": state.get("mission_target"),
                "active": state.get("mission", {}).get("active", False)
            }

        # Fallback 대화 (beats가 없을 경우)
        if not ctx.get("beats") and stage:
            fallback = stage.get("fallback")
            if fallback:
                ctx["fallback"] = fallback

        return ctx
