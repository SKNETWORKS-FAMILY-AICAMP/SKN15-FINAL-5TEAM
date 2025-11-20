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
        speaker_pool = list(stage.get("speaker_pool", []))  # Copy to avoid mutation
        stage_turn = state.get("stage_turn", 0)

        # ✅ active_counselor 동적 치환
        if "active_counselor" in speaker_pool:
            active_counselor = state.get("active_counselor")
            if active_counselor:
                speaker_pool = [active_counselor if s == "active_counselor" else s for s in speaker_pool]
                logger.info("handle", f"Replaced active_counselor with {active_counselor} in speaker_pool")

        # Dynamic speaker stages 처리
        dynamic_config = stage.get("dynamic_speaker_stages", {})
        if dynamic_config.get("allies_recruited"):
            # allies_recruited에 있는 캐릭터들을 speaker_pool에 추가
            allies = state.get("allies_recruited", [])
            for ally in allies:
                if ally not in speaker_pool:
                    speaker_pool.append(ally)
                    logger.info("handle", f"Added ally '{ally}' to speaker_pool dynamically")

        logger.debug("handle", "Handling scene stage",
                    stage_tag=stage_tag,
                    beats_count=len(beats),
                    stage_turn=stage_turn,
                    speaker_pool=speaker_pool)

        # Beats 전달 방식: beats 개수로 자동 판단
        # - beats 1개: 반복 (사용자 상호작용 모드)
        # - beats 여러 개: 순차 소비 (stage_turn 기반)
        stage_turn = state.get("stage_turn", 0)
        max_turns = stage.get("max_turns", 3)

        if len(beats) == 0:
            # Beats 없음 → LLM 자율 생성 모드 (context 기반)
            # context에 상세한 설명이 있으면 LLM이 자연스러운 대화 생성
            beats_for_children = []
            logger.info("handle", "No beats - using LLM autonomous generation mode", stage_tag=stage_tag)
        elif len(beats) == 1:
            # 단일 beat → 반복 전달 (유저 상호작용 모드)
            beats_for_children = beats
            logger.info("handle",
                f"[Single Beat Mode] Repeating beat (turn={stage_turn}/{max_turns})",
                stage_tag=stage_tag,
                beat_goal=beats[0].get("goal", "")[:50]
            )
        else:
            # 복수 beats → 순차 소비
            if stage_turn < len(beats):
                beats_for_children = [beats[stage_turn]]
                logger.info("handle",
                    f"[Sequential Mode] Beat {stage_turn + 1}/{len(beats)} (turn={stage_turn}/{max_turns})",
                    stage_tag=stage_tag,
                    beat_goal=beats[stage_turn].get("goal", "")[:50]
                )
            else:
                # Beats 소진 후 마지막 beat 반복
                beats_for_children = [beats[-1]]
                logger.info("handle",
                    f"[Sequential Mode] Repeating last beat (turn={stage_turn}/{max_turns})",
                    stage_tag=stage_tag
                )

        # Base context 생성
        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "scene",
            "beats": beats_for_children,
            "speaker_pool": speaker_pool,
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
        min_turns = stage.get("min_turns", 0)

        # ✅ 엔딩 스테이지 체크 (END_로 시작)
        is_ending_stage = stage_tag.startswith("END_")

        # 1. Auto-advance 옵션이 있으면 자동 완료
        if stage.get("auto_advance"):
            stage_complete = True
            next_stage = stage.get("next")
            logger.info("handle", "Auto-advancing to next stage", next_stage=next_stage)

        # 2. min_turns 미달이면 계속 진행
        # stage_turn=0은 1번째 턴, stage_turn=1은 2번째 턴
        # min_turns=2이면 stage_turn이 0,1일 때 계속 진행 (stage_turn+1 < min_turns 아님!)
        elif stage_turn + 1 < min_turns:
            stage_complete = False
            logger.info("handle", "Still under min_turns",
                       current_turn=stage_turn + 1, min_turns=min_turns, max_turns=max_turns)

        # 3. max_turns 도달 시 완료
        # max_turns=3이면 stage_turn=2까지 진행 (stage_turn=0,1,2 = 3턴)
        elif max_turns and stage_turn + 1 >= max_turns:
            stage_complete = True
            next_stage = stage.get("next")

            # ✅ 엔딩 스테이지는 next가 없어도 완료 처리
            if is_ending_stage:
                logger.info("handle", "🏁 Ending stage completing (max_turns reached)",
                           stage_tag=stage_tag,
                           current_turn=stage_turn + 1,
                           max_turns=max_turns)
            else:
                logger.info("handle", "Stage completing (max_turns reached)",
                           current_turn=stage_turn + 1, max_turns=max_turns, next_stage=next_stage)

        # 4. min_turns를 만족했고 max_turns가 없거나 아직 도달하지 않은 경우 완료
        # 예: min_turns=2, max_turns=None → stage_turn >= 1이면 완료
        elif stage_turn + 1 >= min_turns:
            stage_complete = True
            next_stage = stage.get("next")
            logger.info("handle", "Stage completing (min_turns satisfied)",
                       current_turn=stage_turn + 1, min_turns=min_turns, max_turns=max_turns, next_stage=next_stage)

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage
        )


__all__ = ["SceneStageHandler"]
