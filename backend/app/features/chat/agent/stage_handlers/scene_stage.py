"""
Scene Stage Handler - 씬 스테이지 처리

Features:
- 고정 beats 기반 씬 처리
- 스테이지 진행 관리
"""
from typing import Dict, Any

from app.core.logging import get_parent_logger

from . import StageResult

logger = get_parent_logger("SceneStageHandler")


class SceneStageHandler:
    """
    씬 스테이지 핸들러

    고정된 beats를 순차적으로 진행하는 일반 씬을 처리합니다.
    """

    def __init__(self):
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

        logger.debug("handle", "Handling scene stage",
                    stage_tag=stage_tag,
                    beats_count=len(beats))

        # Children context 구성
        children_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "scene",
            "beats": beats,
            "speaker_pool": speaker_pool,
            "scenario_id": scenario.get("scenario_id", "unknown"),
            "character_refs": scenario.get("character_refs", {}),
        }

        # 스테이지 완료 체크
        stage_complete = False
        next_stage = None

        stage_turn = state.get("stage_turn", 0)
        max_turns = stage.get("max_turns")
        loop_mode = stage.get("loop_mode", "micro_beat")

        # 1. Auto-advance 옵션이 있으면 자동 완료
        if stage.get("auto_advance"):
            stage_complete = True
            next_stage = stage.get("next")
            logger.info("handle", "Auto-advancing to next stage", next_stage=next_stage)

        # 2. loop_mode가 "none"이고 max_turns 도달 시 완료
        elif loop_mode == "none" and max_turns and stage_turn >= max_turns:
            stage_complete = True
            next_stage = stage.get("next")
            logger.info("handle", "Stage completed (loop_mode=none, max_turns reached)",
                       stage_turn=stage_turn, max_turns=max_turns, next_stage=next_stage)

        # 3. max_turns만 설정되어 있고 도달 시 완료
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
