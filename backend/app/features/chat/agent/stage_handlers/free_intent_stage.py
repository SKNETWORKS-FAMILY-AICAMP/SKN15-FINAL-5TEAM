"""
Free Intent Stage Handler - 자유 의도 스테이지 처리

Features:
- 사용자 자유 입력 기반 처리
- LLM 동적 beats 생성
- 임베딩 기반 Intent 라우팅
"""
from typing import Dict, Any, Optional

from app.core.logging import get_parent_logger
from app.features.chat.services import ContextService
from app.core.embeddings import EmbeddingMatcher

from . import StageResult

logger = get_parent_logger("FreeIntentStageHandler")


class FreeIntentStageHandler:
    """
    자유 의도 스테이지 핸들러

    사용자가 자유롭게 행동을 선택할 수 있는 스테이지를 처리합니다.
    LLM을 사용하여 동적으로 beats를 생성합니다.
    """

    def __init__(self, context_service: ContextService = None):
        """
        Args:
            context_service: ContextService 인스턴스
        """
        self.context_service = context_service or ContextService()

        logger.info("__init__", "FreeIntentStageHandler initialized")

    async def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> StageResult:
        """
        자유 의도 스테이지 처리

        Args:
            state: 게임 상태
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            StageResult
        """
        stage_tag = stage.get("tag", "free_intent")
        speaker_pool = stage.get("speaker_pool", [])

        logger.debug("handle", "Handling free intent stage",
                    stage_tag=stage_tag)

        # 기본 context 구성
        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "free_intent",
            "speaker_pool": speaker_pool,
            "scenario_id": scenario.get("scenario_id", "unknown"),
        }

        # Context 빌딩
        children_ctx = self.context_service.build_children_context(
            base_ctx=base_ctx,
            state=state,
            scenario=scenario,
            stage=stage
        )

        # Intent 매핑 기반 라우팅 (임베딩 활용)
        intent_mapping = stage.get("intent_mapping", {})
        next_stage = None
        stage_complete = False

        # Beats 생성 또는 스킵
        if intent_mapping:
            # Intent-mapped stage: beats 없이 context 기반 LLM 자율 생성 모드
            # (SceneStageHandler의 beats 없음 모드와 동일)
            beats = []
            children_ctx["beats"] = []
            logger.info("handle", "Intent-mapped stage: using context-based generation (no beats)")
            
            # 사용자 입력 기반 라우팅 시도
            try:
                user_input = state.get("user_input", "")
                next_stage = await self._route_by_intent(
                    user_input,
                    intent_mapping,
                    scenario
                )

                if next_stage:
                    # 라우팅 성공 → 스테이지 완료
                    stage_complete = True
                    logger.info("handle", "Intent matched, routing to next stage",
                               next_stage=next_stage)
                else:
                    # 라우팅 실패 → 같은 스테이지 유지 (질문 반복)
                    logger.debug("handle", "No intent matched, staying at current stage")
            except Exception as e:
                logger.error("handle", f"Intent routing failed: {e}", exc_info=True)
                # 라우팅 실패 시에도 계속 진행 (같은 스테이지 반복)
                next_stage = None
                stage_complete = False
        else:
            # 일반 free_intent: LLM 기반 동적 beats 생성
            beats = await self.context_service.generate_beats(state, children_ctx)
            children_ctx["beats"] = beats
            logger.info("handle", "Generated beats for free intent stage",
                       beats_count=len(beats))

        logger.info("handle", "Free intent stage processed",
                   beats_count=len(beats) if isinstance(beats, list) else 0,
                   stage_complete=stage_complete,
                   next_stage=next_stage)

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage
        )

    async def _route_by_intent(
        self,
        user_input: str,
        intent_mapping: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> Optional[str]:
        """
        임베딩 기반 Intent 라우팅

        1. scenario.router.intent_examples에서 예시 문장 로드
        2. EmbeddingMatcher로 의미 유사도 매칭
        3. 매칭된 intent의 next_stage 반환

        Fallback: router.intent_examples 없으면 키워드 매칭

        Args:
            user_input: 사용자 입력
            intent_mapping: intent → next_stage 매핑 dict
            scenario: 시나리오 데이터

        Returns:
            next_stage 또는 None
        """
        if not user_input or not user_input.strip():
            return None

        # 1. scenario.metadata.router.intent_examples 가져오기
        # router는 metadata 안에 있음
        metadata = scenario.get("metadata", {})
        router_config = metadata.get("router", {})
        intent_examples = router_config.get("intent_examples", {})
        embedding_threshold = router_config.get("embedding_threshold", 0.7)
        logger.debug("_route_by_intent",
                    f"Router config loaded | intent_examples_count={len(intent_examples)} | threshold={embedding_threshold}")

        # 2. 임베딩 매칭 시도
        if intent_examples:
            try:
                # EmbeddingMatcher 생성
                matcher = EmbeddingMatcher(
                    label_terms=intent_examples,
                    threshold=embedding_threshold
                )

                # 매칭
                result = matcher.match(user_input)

                # 🔍 DEBUG: 매칭 결과 상세 로깅
                print(f"🔍 Match result: label={result.label}, score={result.score:.4f}, threshold={embedding_threshold}")
                logger.info("_route_by_intent",
                           f"Match result | label={result.label} | score={result.score:.4f} | threshold={embedding_threshold}",
                           user_input=user_input[:50])

                if result.label:
                    print(f"🔍 result.label in intent_mapping: {result.label in intent_mapping}")
                    print(f"🔍 intent_mapping keys: {list(intent_mapping.keys())}")

                    # intent → next_stage 매핑
                    # JSON 구조: {"choose_allies_path": "RECRUIT"} (간단한 str 값)
                    if result.label in intent_mapping:
                        next_stage = intent_mapping[result.label]
                        logger.info("_route_by_intent",
                                   f"✅ Embedding match: '{result.label}' (score={result.score:.2f})",
                                   user_input=user_input[:50],
                                   next_stage=next_stage)
                        return next_stage
                    else:
                        logger.warning("_route_by_intent",
                                      f"Label '{result.label}' not found in intent_mapping",
                                      available_intents=list(intent_mapping.keys()))

                logger.info("_route_by_intent",
                           f"No embedding match above threshold ({embedding_threshold})",
                           best_score=result.score if result else 0.0)

            except Exception as e:
                logger.warning("_route_by_intent",
                              f"Embedding matching failed: {e}")

        # 임베딩 매칭 실패 시 None 반환
        return None


__all__ = ["FreeIntentStageHandler"]
