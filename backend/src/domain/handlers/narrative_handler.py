# ============================================================
# 📜 내러티브 핸들러 — 오픈 내러티브 장면 처리
# ============================================================
from __future__ import annotations
from typing import Any, Dict
from src.domain.services.orchestration.story_orchestrator import get_story_orchestrator
from src.core.utils.logger import log
from . import StageResult


class OpenNarrativeHandler:
    """
    Open Narrative 스테이지를 처리하는 핸들러.
    유저의 자유 입력을 기반으로 LLM이 즉흥적으로 서사를 생성.
    """

    def __init__(self, locale: str = "ko"):
        self.locale = locale
        self._orchestrator = get_story_orchestrator()

    def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
    ) -> StageResult:
        """
        Open Narrative 스테이지 처리 메인 함수.
        """
        log.info(f"🎭 Processing open narrative stage: {stage.get('tag')}")

        # 1️⃣ 스테이지 메타
        stage_tag = stage.get("tag", "UNKNOWN")
        context = stage.get("context", "")
        speaker_pool = stage.get("speaker_pool", ["narr", "tanjiro"])
        next_stage = stage.get("next")
        min_turns = stage.get("min_turns", 2)
        max_turns = stage.get("max_turns", 5)

        # 2️⃣ 상태 초기화
        self._initialize_narrative_state(state)

        turn_count = int(state.get("turn_count", 0))
        stage_turn = int(state.get("stage_turn", 0))
        user_input = (state.get("user_input") or "").strip()
        has_user_input = bool(user_input and user_input != "__AUTO_CONTINUE__")

        log.info(f"📊 Stage={stage_tag}, turn={stage_turn}, min={min_turns}, max={max_turns}")

        # 3️⃣ 스테이지 완료 조건
        stage_complete = False
        if stage_turn >= max_turns:
            stage_complete = True
            log.info(f"⚠️ Max turns reached ({stage_turn}/{max_turns}), force advancing")
        elif stage_turn >= min_turns and has_user_input:
            stage_complete = True
            log.info(f"✅ Min turns reached ({stage_turn}/{min_turns}) with user input, auto-advancing")

        # 4️⃣ 유저 입력이 없을 때 → 프롬프트 안내
        if not user_input:
            prompt_dialogue = self._create_prompt_dialogue(context, speaker_pool)
            return StageResult(
                children_ctx={
                    "stage_tag": stage_tag,
                    "stage_type": "open_narrative",
                    "speaker_pool": speaker_pool,
                    "beats": prompt_dialogue,  # ✅ fallback 대신 beats로 전달
                    "character_refs": scenario.get("character_refs", {}),
                    "scenario_id": scenario.get("scenario_id", "unknown"),
                },
                stage_complete=False,
            )

        # 5️⃣ LLM(or stub) 기반 내러티브 생성
        narrative_result = self._orchestrator.generate_narrative(
            state=state,
            user_input=user_input,
            context=context,
            speaker_pool=speaker_pool,
            turn_count=turn_count,
        )

        beats = narrative_result.get("beats", [])
        state_update = narrative_result.get("state_update", {})

        if user_input:
            state_update["last_user_input"] = user_input
            log.info(f"📝 Saved last_user_input to state_update: '{user_input[:50]}...'")

        if "story_summary" in state_update:
            prev_summary = state.get("story_summary", "")
            new_summary = state_update["story_summary"]
            state["story_summary"] = f"{prev_summary}\n{new_summary}" if prev_summary else new_summary

        if "world_state" in state_update:
            state.setdefault("world_state", {}).update(state_update["world_state"])

        state["turn_count"] = turn_count + 1
        log.info(f"✅ Generated {len(beats)} dialogues, turn={turn_count + 1}/{max_turns}")

        children_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "open_narrative",
            "speaker_pool": speaker_pool,
            "beats": beats,  # ✅ 핵심: beats로 직접 전달
            "character_refs": scenario.get("character_refs", {}),
            "scenario_id": scenario.get("scenario_id", "unknown"),
            "latest_user_input": user_input,
        }

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage,
        )

    # ------------------------------------------------------------
    def _initialize_narrative_state(self, state: Dict[str, Any]) -> None:
        """Open Narrative 전용 상태 필드 초기화"""
        state.setdefault("story_summary", "")
        state.setdefault("turn_count", 0)
        state.setdefault("world_state", {})

    def _create_prompt_dialogue(self, context: str, speaker_pool: list) -> list:
        """유저 입력이 없을 때 프롬프트 대사 생성"""
        speaker = speaker_pool[0] if speaker_pool and speaker_pool[0] != "narr" else "tanjiro"
        if len(speaker_pool) > 1 and speaker_pool[1] != "narr":
            speaker = speaker_pool[1]

        return [
            {"speaker": "narr", "text": context or "주변은 고요하다..."},
            {"speaker": speaker, "text": "무슨 생각을 하고 있어? 어떻게 할 거야?"},
        ]


__all__ = ["OpenNarrativeHandler"]
