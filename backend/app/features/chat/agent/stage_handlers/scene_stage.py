"""
Scene Stage Handler - 씬 스테이지 처리

Features:
- 고정 beats 기반 씬 처리
- 스테이지 진행 관리
"""
from typing import Dict, Any

from app.core.logging import get_parent_logger
from app.features.chat.services import ContextService

from . import StageResult

logger = get_parent_logger("SceneStageHandler")


class SceneStageHandler:
    """
    씬 스테이지 핸들러

    고정된 beats를 순차적으로 진행하는 일반 씬을 처리합니다.
    """

    def __init__(self, context_service: ContextService = None):
        """
        Args:
            context_service: ContextService 인스턴스
        """
        self.context_service = context_service or ContextService()
        logger.info("__init__", "SceneStageHandler initialized")

    def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> StageResult:
        """
        씬 스테이지 처리

        Args:
            state: 게임 상태
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            StageResult
        """
        stage_tag = stage.get("tag", "scene")
        beats = stage.get("beats", [])
        speaker_pool = stage.get("speaker_pool", [])
        loop_mode = stage.get("loop_mode", "micro_beat")
        stage_turn = state.get("stage_turn", 0)

        logger.debug("handle", "Handling scene stage",
                    stage_tag=stage_tag,
                    beats_count=len(beats),
                    loop_mode=loop_mode,
                    stage_turn=stage_turn)

        # loop_mode="micro_beat"일 때: Beat를 반복하며 유저와 상호작용
        # - stage_turn이 증가하더라도 같은 beat를 유지 (컨텍스트)
        # - max_turns 도달 시에만 다음 스테이지로
        if loop_mode == "micro_beat" and beats:
            # 항상 동일한 beat 유지 (의도) - 첫 번째 beat만 전달
            beats_for_children = [beats[0]]  # ✅ 첫 번째 beat만

            # 단, stage_turn 기반으로 stage_complete 관리
            stage_turn = state.get("stage_turn", 0)
            max_turns = stage.get("max_turns", 3)

            logger.info("handle",
                f"[micro_beat] Looping same beat (turn={stage_turn}/{max_turns})",
                stage_tag=stage_tag,
                beat_goal=beats[0].get("goal", "")[:50]
            )

            if stage_turn + 1 >= max_turns:
                stage_complete = True
                next_stage = stage.get("next")
        else:
            # loop_mode="none": 모든 beats를 한 번에 처리
            beats_for_children = beats
            logger.info("handle", f"[{loop_mode}] Sending all {len(beats)} beats",
                       stage_tag=stage_tag)

        # Base context 생성
        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "scene",
            "beats": beats_for_children,
            "speaker_pool": speaker_pool,
            "loop_mode": loop_mode,
        }

        # ContextService로 공통 정보 추가 (recent_dialogues 등)
        children_ctx = self.context_service.build_children_context(
            base_ctx=base_ctx,
            state=state,
            scenario=scenario,
            stage=stage
        )

        # 스테이지 완료 체크
        stage_complete = False
        next_stage = None
        max_turns = stage.get("max_turns")
        min_turns = stage.get("min_turns", 0)

        # 1. Auto-advance 옵션이 있으면 자동 완료
        if stage.get("auto_advance"):
            stage_complete = True
            next_stage = stage.get("next")
            logger.info("handle", "Auto-advancing to next stage", next_stage=next_stage)

        # 2. min_turns 미달이면 계속 진행
        elif stage_turn < min_turns:
            stage_complete = False
            logger.info("handle", f"[{loop_mode}] Still under min_turns",
                       stage_turn=stage_turn, min_turns=min_turns, max_turns=max_turns)

        # 3. loop_mode="none"이고 beats 모두 소진 시 완료
        elif loop_mode == "none" and stage_turn >= len(beats):
            stage_complete = True
            next_stage = stage.get("next")
            logger.info("handle", "Stage completed (loop_mode=none, all beats consumed)",
                       stage_turn=stage_turn, beats_count=len(beats), next_stage=next_stage)

        # 4. max_turns 도달 시 완료
        elif max_turns and stage_turn >= max_turns:
            stage_complete = True
            next_stage = stage.get("next")
            logger.info("handle", "Stage completed (max_turns reached)",
                       stage_turn=stage_turn, max_turns=max_turns, next_stage=next_stage)

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage
        )


__all__ = ["SceneStageHandler"]
