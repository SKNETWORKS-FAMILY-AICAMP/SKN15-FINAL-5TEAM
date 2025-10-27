from __future__ import annotations

from typing import Any, Dict

from src.tools import state_tools
from src.tools.scene_tools import (
    get_next_stage_tag,
    get_stage_atmosphere,
    get_stage_beats,
    get_stage_type,
    get_speaker_pool,
)
from src.utils.logger import log
from . import StageResult


class SceneHandler:
    """Render linear scene beats while honoring simple turn constraints."""

    def __init__(self, locale: str = "ko"):
        self.locale = locale

    def handle(self, state: Dict[str, Any], stage: Dict[str, Any], scenario: Dict[str, Any]) -> StageResult:
        stage_tag = stage.get("tag") or stage.get("id") or "scene"
        scene_state = state_tools.get_scene_state(state)
        speaker_fallback = scene_state.get("speaker_pool", [])

        beats = get_stage_beats(stage, scenario, locale=self.locale)
        speaker_pool = get_speaker_pool(stage, speaker_fallback)
        constraints = stage.get("constraints") or {}

        ctx = {
            "stage_tag": stage_tag,
            "stage_type": get_stage_type(stage),
            "speaker_pool": speaker_pool,
            "beats": beats,
            "constraints": constraints,
            "atmosphere": get_stage_atmosphere(stage),
        }

        stage_turn = int(state.get("stage_turn", 0) or 0)
        min_turns = int(constraints.get("min_turns", 1) or 1)
        max_turns = int(constraints.get("max_turns", min_turns) or min_turns)

        log("scene", f"📊 Stage={stage_tag}, turn={stage_turn}, min={min_turns}, max={max_turns}")

        temp = state_tools.get_temp_data(state)
        forced = temp.pop(f"{stage_tag}_complete", False)

        complete = forced or stage_turn >= max_turns
        if not complete and stage_turn >= min_turns and constraints.get("auto_advance"):
            complete = True

        # INTRO stage는 첫 입력("시작")에는 beats를 보여주고, 두 번째 입력부터 다음 스테이지로 진행
        if not complete and stage_tag == "INTRO":
            user_input = state.get("user_input", "")
            log("scene", f"🔍 INTRO check: turn={stage_turn}, user_input='{user_input}'")

            # turn=0: 첫 입력 (보통 "시작") → INTRO beats 표시
            # turn>=1: 두 번째 입력 → ROUTE_CHOICE로 진행
            if user_input and user_input != "__AUTO_CONTINUE__":
                if stage_turn >= 1:
                    complete = True
                    log("scene", "✅ INTRO stage auto-advancing after second user input", turn=stage_turn)
                else:
                    log("scene", "📖 INTRO stage showing beats on first input", turn=stage_turn)
                    # 다음 입력에서는 ROUTE_CHOICE로 전환되도록 강제 완료 플래그 설정
                    temp[f"{stage_tag}_complete"] = True
            elif stage_turn >= 1:
                # 사용자 입력이 빈 상태로 두 번째 턴에 진입한 경우에도 자동으로 다음 스테이지로 전환
                complete = True
                log("scene", "✅ INTRO stage auto-advancing on empty follow-up turn", turn=stage_turn)

        next_stage = get_next_stage_tag(stage) if complete else None
        if complete:
            log("scene", "Scene constraints satisfied", current=stage_tag, next=next_stage)
        return StageResult(
            children_ctx=ctx,
            stage_complete=complete,
            next_stage=next_stage,
        )
