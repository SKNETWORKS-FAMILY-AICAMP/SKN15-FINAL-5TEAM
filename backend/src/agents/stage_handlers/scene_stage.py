from __future__ import annotations

from typing import Any, Dict

# ============================================================
# 🎬 SceneHandler — 선형 장면(beats)을 렌더링하고 진행 조건을 관리
#  - stage_turn, min/max 턴, auto_advance 조건을 확인
#  - INTRO 스테이지는 첫 입력/두 번째 입력 흐름을 별도로 처리
#  - 장면 완료 시 beats를 정리하여 ParentAgent가 다음 스테이지로 이동하도록 지원
# ============================================================

from src.tools import state_tools
from src.tools.scene_tools import (
    get_next_stage_tag,
    get_stage_atmosphere,
    get_stage_beats,
    get_stage_type,
    get_speaker_pool,
)
from src.utils.logger import log
from src.config.constants import INTRO_STAGE_TAGS
from . import StageResult


class SceneHandler:
    """Render linear scene beats while honoring simple turn constraints."""

    def __init__(self, locale: str = "ko"):
        self.locale = locale
        self._config_loader = None
        self._llm = None

    def handle(self, state: Dict[str, Any], stage: Dict[str, Any], scenario: Dict[str, Any]) -> StageResult:
        stage_tag = stage.get("tag") or stage.get("id") or "scene"
        scene_state = state_tools.get_scene_state(state)
        speaker_fallback = scene_state.get("speaker_pool", [])

        beats = get_stage_beats(stage, scenario, locale=self.locale)
        speaker_pool = get_speaker_pool(stage, speaker_fallback)
        constraints = stage.get("constraints") or {}

        # llm_beats 플래그 확인
        llm_beats_enabled = stage.get("llm_beats", False)

        # 🆕 loop_mode 확인 (micro_beat, none 등)
        loop_mode = stage.get("loop_mode", "none")

        # stage.context 추출 (장면 전환 시 narr 생성용)
        stage_context = stage.get("context")

        ctx = {
            "stage_tag": stage_tag,
            "stage_type": get_stage_type(stage),
            "speaker_pool": speaker_pool,
            "beats": beats,
            "constraints": constraints,
            "atmosphere": get_stage_atmosphere(stage),
            "llm_beats": llm_beats_enabled,
            "loop_mode": loop_mode,
            "stage_context": stage_context if isinstance(stage_context, str) else None,
        }

        stage_turn = int(state.get("stage_turn", 0) or 0)

        # min_turns/max_turns 우선순위: constraints > stage 레벨 > 기본값
        min_turns = int(
            constraints.get("min_turns")
            or stage.get("min_turns")
            or 1
        )
        max_turns = int(
            constraints.get("max_turns")
            or stage.get("max_turns")
            or 3
        )

        log("scene", f"📊 Stage={stage_tag}, turn={stage_turn}, min={min_turns}, max={max_turns}")

        temp = state_tools.get_temp_data(state)
        forced = temp.pop(f"{stage_tag}_complete", False)

        # 유저 입력 확인
        user_input = state.get("user_input", "").strip()
        has_user_input = bool(user_input and user_input != "__AUTO_CONTINUE__")

        # Stage 완료 조건
        complete = False

        if forced:
            complete = True
            log("scene", "✅ Stage forced complete")
        elif stage_turn >= max_turns:
            complete = True
            log("scene", f"⚠️ Max turns reached ({stage_turn}/{max_turns}), force advancing")
        elif stage_turn >= min_turns and has_user_input:
            # 🆕 Micro-beat Loop: min_turns 도달 시 LLM이 종료 시점 판단
            if loop_mode == "micro_beat":
                should_end = self._check_scene_completion(state, stage, stage_context, stage_turn, min_turns)
                if should_end:
                    complete = True
                    log("scene", f"✅ Micro-beat loop: Scene naturally completed at turn {stage_turn}")
                else:
                    log("scene", f"🔄 Micro-beat loop: Continuing scene (turn {stage_turn}/{max_turns})")
            else:
                # 기존 로직: min_turns 도달 + 유저 입력 → 자동 전환
                complete = True
                log("scene", f"✅ Min turns reached ({stage_turn}/{min_turns}) with user input, auto-advancing")

        # 인트로 스테이지 특수 처리 (첫 입력에는 beats 표시, 두 번째 입력부터 진행)
        intro_stage_aliases = {tag.upper() for tag in INTRO_STAGE_TAGS}
        if not complete and stage_tag.upper() in intro_stage_aliases:
            log("scene", f"🔍 INTRO check: turn={stage_turn}, has_input={has_user_input}")

            # turn=0: 첫 입력 (보통 "시작") → INTRO beats 표시
            # turn>=1: 두 번째 입력 → ROUTE_CHOICE로 진행
            if has_user_input:
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
            should_trim = (
                bool(constraints.get("auto_advance"))
                or stage_tag.upper() in intro_stage_aliases
                or (next_stage is not None)
            )
            if should_trim and stage_turn >= max_turns:
                ctx["beats"] = []
        return StageResult(
            children_ctx=ctx,
            stage_complete=complete,
            next_stage=next_stage,
        )

    def _check_scene_completion(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        stage_context: str,
        stage_turn: int,
        min_turns: int
    ) -> bool:
        """
        LLM을 사용하여 장면이 자연스럽게 마무리되었는지 판단합니다.

        Returns:
            True: 장면 종료 가능
            False: 대화 계속 진행
        """
        # LLM 및 config_loader 초기화 (lazy loading)
        if self._config_loader is None:
            from src.utils.config_loader import ConfigLoader
            self._config_loader = ConfigLoader()

        if self._llm is None:
            from src.utils.llm_client import LLMClient
            self._llm = LLMClient()

        # prompts.yaml에서 scene_completion_check 프롬프트 로드
        prompts = self._config_loader.get_prompts().get("llm_prompts", {}).get("children", {})
        prompt_template = prompts.get("scene_completion_check", "")

        if not prompt_template:
            log("scene", "⚠️ scene_completion_check prompt not found, defaulting to continue")
            return False

        # 최근 대화 기록 가져오기
        recent_dialogues = state.get("recent_dialogues", [])
        recent_history = "\n".join(recent_dialogues[-5:]) if recent_dialogues else "(대화 없음)"

        # 프롬프트 포맷팅
        prompt = prompt_template.format(
            stage_context=stage_context or "(장면 설명 없음)",
            min_turns=min_turns,
            stage_turn=stage_turn,
            recent_dialogues=recent_history
        )

        try:
            # LLM 호출
            response = self._llm.call_text(
                system_prompt="You are a scene completion judge. Only output 'ready' or 'continue'.",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=10
            )

            result = response.strip().lower()
            log("scene", f"🤖 Scene completion check: {result}")

            return result == "ready"

        except Exception as e:
            log("scene", f"❌ Scene completion check failed: {e}")
            # 에러 시 안전하게 대화 계속
            return False
