# ============================================================
# 🎭 OpenNarrativeHandler — Open Narrative 스테이지 처리
# ============================================================
from __future__ import annotations

from typing import Any, Dict

from src.core.story_orchestrator import get_story_orchestrator
from src.utils.logger import log

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

        Args:
            state: 현재 게임 상태
            stage: 현재 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            StageResult with generated narrative
        """
        log("open_narrative", f"🎭 Processing open narrative stage: {stage.get('tag')}")

        # 1. 스테이지 정보 추출
        stage_tag = stage.get("tag", "UNKNOWN")
        context = stage.get("context", "")
        speaker_pool = stage.get("speaker_pool", ["narr", "tanjiro"])
        next_stage = stage.get("next")
        max_turns = stage.get("max_turns", 5)  # 기본 5턴

        # 2. 상태 초기화
        self._initialize_narrative_state(state)

        # 3. 현재 턴 수 확인
        turn_count = int(state.get("turn_count", 0))
        stage_turn = int(state.get("stage_turn", 0))

        # 4. 유저 입력 가져오기
        user_input = state.get("user_input", "").strip()

        # 5. 턴 수 기반 자동 전환 체크 (비활성화)
        # 문제: 유저 입력과 관계없이 max_turns 도달 시 자동 진행하여 캐릭터들이 알아서 대화 진행
        # 해결: max_turns 체크를 제거하고, 유저가 직접 스테이지를 진행하도록 함
        stage_complete = False

        # max_turns 경고만 출력 (자동 진행 안 함)
        if turn_count >= max_turns or stage_turn >= max_turns:
            log("open_narrative", f"⚠️  Turn limit reached: {turn_count}/{max_turns} (auto-advance disabled)")

        # 자동 진행 로직 제거됨 - 유저가 명시적으로 다음 스테이지로 가는 입력을 해야 진행

        # 6. 유저 입력이 없으면 프롬프트 제공
        if not user_input:
            prompt_dialogue = self._create_prompt_dialogue(context, speaker_pool)

            return StageResult(
                children_ctx={
                    "stage_tag": stage_tag,
                    "stage_type": "open_narrative",
                    "speaker_pool": speaker_pool,
                    "beats": [],
                    "fallback": {"dialogues": prompt_dialogue},
                    "character_refs": scenario.get("character_refs", {}),
                    "scenario_id": scenario.get("scenario_id", "unknown"),
                },
                stage_complete=False,
            )

        # 7. LLM을 통한 서사 생성
        narrative_result = self._orchestrator.generate_narrative(
            state=state,
            user_input=user_input,
            context=context,
            speaker_pool=speaker_pool,
            turn_count=turn_count,
        )

        # 8. 상태 업데이트
        dialogues = narrative_result.get("dialogues", [])
        state_update = narrative_result.get("state_update", {})

        # story_summary 업데이트
        if "story_summary" in state_update:
            current_summary = state.get("story_summary", "")
            new_summary = state_update["story_summary"]
            if current_summary:
                state["story_summary"] = f"{current_summary}\n{new_summary}"
            else:
                state["story_summary"] = new_summary

        # world_state 업데이트
        if "world_state" in state_update:
            world_state = state.setdefault("world_state", {})
            world_state.update(state_update["world_state"])

        # turn_count 증가
        state["turn_count"] = turn_count + 1

        log("open_narrative", f"✅ Generated {len(dialogues)} dialogues, turn={turn_count + 1}/{max_turns}")

        # 9. children_ctx 구성
        children_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "open_narrative",
            "speaker_pool": speaker_pool,
            "beats": [],
            "fallback": {"dialogues": dialogues},
            "character_refs": scenario.get("character_refs", {}),
            "scenario_id": scenario.get("scenario_id", "unknown"),
            "latest_user_input": user_input,
        }

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage,  # parent_agent가 auto_advance 판단하므로 항상 제공
        )

    def _initialize_narrative_state(self, state: Dict[str, Any]) -> None:
        """Open Narrative 전용 상태 필드 초기화"""
        state.setdefault("story_summary", "")
        state.setdefault("turn_count", 0)
        state.setdefault("world_state", {})

    def _create_prompt_dialogue(
        self,
        context: str,
        speaker_pool: list,
    ) -> list:
        """유저 입력이 없을 때 프롬프트 대사 생성"""
        speaker = speaker_pool[0] if speaker_pool and speaker_pool[0] != "narr" else "tanjiro"
        if len(speaker_pool) > 1 and speaker_pool[1] != "narr":
            speaker = speaker_pool[1]

        return [
            {"speaker": "narr", "text": context},
            {
                "speaker": speaker,
                "text": "무슨 생각을 하고 있어? 어떻게 할 거야?",
            },
        ]

    def _create_transition_dialogue(
        self,
        state: Dict[str, Any],
        context: str,
        speaker_pool: list,
        next_stage: str | None,
    ) -> list:
        """스테이지 전환 시 대사 생성"""
        speaker = speaker_pool[0] if speaker_pool and speaker_pool[0] != "narr" else "tanjiro"
        if len(speaker_pool) > 1 and speaker_pool[1] != "narr":
            speaker = speaker_pool[1]

        story_summary = state.get("story_summary", "")
        transition_text = (
            f"지금까지 일어난 일들이 머릿속을 스쳐지나간다. "
            f"이제 다음 단계로 나아가야 할 때다."
        )

        return [
            {"speaker": "narr", "text": transition_text},
            {
                "speaker": speaker,
                "text": "자, 이제 다음으로 나아가자.",
            },
        ]


__all__ = ["OpenNarrativeHandler"]
