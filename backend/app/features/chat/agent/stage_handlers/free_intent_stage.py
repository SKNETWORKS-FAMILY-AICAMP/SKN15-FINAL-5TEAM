"""
Free Intent Stage Handler - 자유 의도 스테이지 처리

Features:
- 사용자 자유 입력 기반 처리
- LLM 기반 Intent 분류 및 라우팅
- LLM 동적 beats 생성
"""
from typing import Dict, Any, Optional

from app.core.logging import get_parent_logger
from app.features.chat.services import ContextService
from app.core.llm import LLMClient

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
        self.llm_client = LLMClient()

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
        user_input = state.get("user_input", "")

        logger.debug("handle", "Handling free intent stage",
                    stage_tag=stage_tag)

        # 1. LLM 기반 Intent 분류 (intent_mapping이 있는 경우)
        next_stage = None
        intent_mapping = stage.get("intent_mapping", {})

        if intent_mapping:
            next_stage = await self._classify_intent(
                user_input=user_input,
                intent_mapping=intent_mapping,
                stage_tag=stage_tag,
                scenario=scenario
            )
            logger.info("handle", f"Intent classified: {next_stage or 'None'}")

        # 2. next_stage가 결정되지 않았으면 default_next 사용
        if not next_stage:
            next_stage = stage.get("default_next")
            logger.info("handle", f"Using default_next: {next_stage}")

        # 3. 기본 context 구성
        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "free_intent",
            "speaker_pool": speaker_pool,
            "scenario_id": scenario.get("scenario_id", "unknown"),
        }

        # 4. Context 빌딩
        children_ctx = self.context_service.build_children_context(
            base_ctx=base_ctx,
            state=state,
            scenario=scenario,
            stage=stage
        )

        # 5. LLM 기반 동적 beats 생성
        beats = await self.context_service.generate_beats(state, children_ctx)
        children_ctx["beats"] = beats

        logger.info("handle", "Free intent stage processed",
                   beats_count=len(beats),
                   next_stage=next_stage)

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=True if next_stage else False,
            next_stage=next_stage
        )

    async def _classify_intent(
        self,
        user_input: str,
        intent_mapping: Dict[str, str],
        stage_tag: str,
        scenario: Dict[str, Any]
    ) -> Optional[str]:
        """
        LLM을 사용하여 사용자 입력의 Intent를 분류합니다.

        Args:
            user_input: 사용자 입력
            intent_mapping: {intent_name: next_stage} 매핑
            stage_tag: 현재 스테이지 태그
            scenario: 시나리오 데이터

        Returns:
            다음 스테이지 이름 또는 None
        """
        if not user_input or not intent_mapping:
            return None

        # metadata에서 intent_examples 가져오기
        metadata = scenario.get("metadata", {})
        router_config = metadata.get("router", {})
        intent_examples = router_config.get("intent_examples", {})
        intents_config = metadata.get("intents", {})
        stage_intents = intents_config.get(stage_tag, {})
        options = stage_intents.get("options", {})

        # Intent 분류 프롬프트 생성
        system_prompt = self._build_intent_classification_prompt(
            intent_mapping=intent_mapping,
            intent_examples=intent_examples,
            options=options
        )

        user_prompt = f"사용자 입력: '{user_input}'\n\n위 입력에 가장 적합한 intent를 선택하세요."

        logger.debug("_classify_intent", "Classifying intent with LLM",
                    user_input=user_input[:50],
                    intents=list(intent_mapping.keys()))

        try:
            # LLM 호출 (JSON 모드)
            response = await self.llm_client.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,  # 일관성을 위해 낮춤
                max_tokens=300
            )

            selected_intent = response.get("intent")
            confidence = response.get("confidence", 0.0)
            reasoning = response.get("reasoning", "")

            logger.info("_classify_intent", f"Intent classified: {selected_intent}",
                       confidence=confidence,
                       reasoning=reasoning[:100])

            # Confidence threshold 체크
            CONFIDENCE_THRESHOLD = 0.7
            if confidence < CONFIDENCE_THRESHOLD:
                logger.warning("_classify_intent",
                             f"Low confidence ({confidence:.2f} < {CONFIDENCE_THRESHOLD}), using default_next",
                             intent=selected_intent,
                             reasoning=reasoning[:100])
                return None

            # intent_mapping에서 next_stage 찾기
            if selected_intent and selected_intent in intent_mapping:
                next_stage = intent_mapping[selected_intent]
                logger.info("_classify_intent", f"Routing to: {next_stage}",
                           intent=selected_intent,
                           confidence=confidence)
                return next_stage
            else:
                logger.warning("_classify_intent", f"Intent not in mapping: {selected_intent}")
                return None

        except Exception as e:
            logger.error("_classify_intent", f"Intent classification failed: {e}")
            return None

    def _build_intent_classification_prompt(
        self,
        intent_mapping: Dict[str, str],
        intent_examples: Dict[str, list],
        options: Dict[str, str]
    ) -> str:
        """
        Intent 분류를 위한 시스템 프롬프트를 생성합니다.

        Args:
            intent_mapping: {intent_name: next_stage} 매핑
            intent_examples: {intent_name: [example1, example2, ...]} 예시
            options: {intent_name: description} 설명

        Returns:
            시스템 프롬프트 문자열
        """
        prompt_parts = [
            "당신은 사용자의 입력을 분석하여 의도(intent)를 분류하는 전문가입니다.",
            "",
            "다음 중 하나의 intent를 선택해야 합니다:",
            ""
        ]

        # 각 intent에 대한 설명과 예시 추가
        for intent_name in intent_mapping.keys():
            description = options.get(intent_name, intent_name)
            examples = intent_examples.get(intent_name, [])

            prompt_parts.append(f"## {intent_name}")
            prompt_parts.append(f"설명: {description}")

            if examples:
                prompt_parts.append("예시:")
                for example in examples[:5]:  # 최대 5개 예시만 표시
                    prompt_parts.append(f"  - \"{example}\"")

            prompt_parts.append("")

        prompt_parts.extend([
            "응답 형식 (JSON):",
            "{",
            '  "intent": "선택한 intent 이름",',
            '  "confidence": 0.0~1.0 사이의 확신도,',
            '  "reasoning": "선택한 이유 (1-2문장)"',
            "}",
            "",
            "주의사항:",
            "- 사용자 입력의 의미를 파악하여 가장 적합한 intent를 선택하세요",
            "- 정확한 키워드 매칭이 아니라 문맥과 의미를 이해하세요",
            "- 확신이 없으면 confidence를 낮게 설정하세요",
            "",
            "우선순위 규칙 (반드시 따르세요):",
            "1. **연애/로맨스 키워드(좋아하다, 고백, 데이트, 썸, 짝사랑, 애인, 이성) 포함 시 → concern_love 최우선**",
            "   - '좋아하는 사람', '고백하다', '연애' 등이 있으면 무조건 concern_love",
            "   - 용기/자신감이 함께 나와도 연애 맥락이면 concern_love",
            "2. **친구/대인관계 키워드(친구, 사람들, 어울림, 외로움, 소외) 포함 시 → concern_relationship",
            "   - 단, 연애 키워드와 함께 나오면 concern_love 우선",
            "3. **진로/직업 키워드(진로, 취업, 직장, 커리어, 적성) 포함 시 → concern_career",
            "4. **자신감 키워드(자신감, 자존감, 용기)가 단독으로 나올 때만 → concern_confidence",
            "   - 다른 구체적 맥락(연애, 친구, 진로)이 있으면 그쪽으로 분류",
            "5. **일반적 감정(힘들다, 스트레스, 무기력, 우울)만 있으면 → concern_stress"
        ])

        return "\n".join(prompt_parts)


__all__ = ["FreeIntentStageHandler"]
