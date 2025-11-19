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
from app.features.chat.services.message_history_service import MessageHistoryService
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
        self.message_history_service = MessageHistoryService()
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
        stage_turn = state.get("stage_turn", 0)
        user_input = state.get("user_input", "")

        # ✅ 수정: stage_turn > 0일 때만 사용자 입력이 유효함
        # stage_turn == 0: 첫 진입, 아직 선택지 제시만 하고 사용자 입력 없음
        # stage_turn >= 1: 사용자가 선택지에 대해 응답한 상태
        logger.debug("handle", f"Stage turn: {stage_turn}, user_input: {user_input[:50] if user_input else 'None'}")

        logger.debug("handle", "Handling free intent stage",
                    stage_tag=stage_tag,
                    user_input_preview=user_input[:30])

        # 1. Intent 분류 및 라우팅 로직
        next_stage = None
        intent_mapping = stage.get("intent_mapping", {})

        # ✅ stage_turn > 0일 때만 intent 분류 수행 (사용자가 선택한 경우)
        if stage_turn > 0 and intent_mapping and user_input:
            next_stage = await self._classify_intent(
                user_input=user_input,
                intent_mapping=intent_mapping,
                stage_tag=stage_tag,
                scenario=scenario
            )
            logger.info("handle", f"Intent classified: {next_stage or 'None'}")

        # 2. next_stage 결정 로직
        if stage_turn == 0:
            # 첫 진입: 선택지 제시만 하고 대기
            logger.info("handle", "First entry - presenting choices, no routing yet")
            next_stage = None
        elif not next_stage:
            # stage_turn > 0이지만 intent가 명확하지 않음
            # default_next 사용 (보통 가장 안전한 경로)
            next_stage = stage.get("default_next")
            logger.warning("handle", f"No clear intent detected, using default_next: {next_stage}")

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

        # beats 없음 → LLM 자율 생성 모드 (stage_context 기반)
        children_ctx["beats"] = []

        # 5. Stage 결과 반환
        if stage_turn == 0:
            # 첫 진입: 선택지 제시만
            logger.info("handle", "Free intent stage - presenting choices",
                       beats_count=0,
                       stage_turn=stage_turn)

            return StageResult(
                children_ctx=children_ctx,
                stage_complete=False,  # 계속 진행 (사용자 입력 대기)
                next_stage=None
            )
        elif next_stage:
            # Intent 분류 성공: 라우팅
            logger.info("handle", "Free intent stage - intent classified, routing",
                       stage_turn=stage_turn,
                       next_stage=next_stage,
                       beats_count=0)

            return StageResult(
                children_ctx=children_ctx,
                stage_complete=True,  # 스테이지 완료
                next_stage=next_stage
            )
        else:
            # Intent 분류 실패: default_next 사용 (이미 위에서 설정됨)
            # next_stage는 default_next 값이 들어있음
            logger.info("handle", "Free intent stage - using default routing",
                       stage_turn=stage_turn,
                       next_stage=next_stage,
                       beats_count=0)

            return StageResult(
                children_ctx=children_ctx,
                stage_complete=True,  # 스테이지 완료
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

        # 키워드 기반 사전 분류 (scenario-specific + counseling)
        # metadata에서 intent_examples 가져오기 (더 정확한 키워드 매칭을 위해)
        metadata = scenario.get("metadata", {})
        router_config = metadata.get("router", {})
        intent_examples_config = router_config.get("intent_examples", {})

        # intent_examples를 키워드로 활용
        for intent_name, examples in intent_examples_config.items():
            if intent_name in intent_mapping:
                # 예시들을 키워드로 활용 (부분 매칭)
                for example in examples:
                    # 예시 문장에서 핵심 키워드 추출 (3글자 이상)
                    keywords = [word for word in example.split() if len(word) >= 3]
                    if any(keyword in user_input for keyword in keywords):
                        logger.info("_classify_intent",
                                   f"Pre-classified as {intent_name} (keyword from examples: matched)",
                                   matched_example=example[:30])
                        return intent_mapping[intent_name]

        # Counseling 시나리오 전용 키워드 체크
        # 연애 관련 키워드 체크
        love_keywords = ["좋아하", "고백", "짝사랑", "썸", "데이트", "연애", "사랑", "호감"]
        if any(keyword in user_input for keyword in love_keywords):
            if "concern_love" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_love (keyword: matched)")
                return intent_mapping["concern_love"]

        # 친구/외로움 관련 키워드 체크
        relationship_keywords = ["친구가 없", "친구 사귀", "외로", "소외", "어울리"]
        if any(keyword in user_input for keyword in relationship_keywords):
            if "concern_relationship" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_relationship (keyword: matched)")
                return intent_mapping["concern_relationship"]

        # 진로 관련 키워드 체크
        career_keywords = ["진로", "취업", "직장", "커리어", "적성"]
        if any(keyword in user_input for keyword in career_keywords):
            if "concern_career" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_career (keyword: matched)")
                return intent_mapping["concern_career"]

        # 자신감 관련 키워드 체크 (단, 다른 맥락이 없을 때만)
        confidence_keywords = ["자신감", "자존감", "당당"]
        if any(keyword in user_input for keyword in confidence_keywords):
            # 연애, 친구, 진로 키워드가 없을 때만 자신감으로 분류
            has_other_context = (
                any(kw in user_input for kw in love_keywords) or
                any(kw in user_input for kw in relationship_keywords) or
                any(kw in user_input for kw in career_keywords)
            )
            if not has_other_context and "concern_confidence" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_confidence (keyword: matched)")
                return intent_mapping["concern_confidence"]

        # 스트레스 관련 키워드 체크 (가장 일반적이므로 마지막에)
        stress_keywords = ["힘들", "무거", "스트레스", "우울", "무기력"]
        if any(keyword in user_input for keyword in stress_keywords):
            # 다른 구체적인 키워드가 없을 때만 스트레스로 분류
            has_specific_context = (
                any(kw in user_input for kw in love_keywords) or
                any(kw in user_input for kw in relationship_keywords) or
                any(kw in user_input for kw in career_keywords) or
                any(kw in user_input for kw in confidence_keywords)
            )
            if not has_specific_context and "concern_stress" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_stress (keyword: matched)")
                return intent_mapping["concern_stress"]

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
                temperature=0.3,  # 너무 낮으면 과적합 위험
                max_tokens=300
            )

            selected_intent = response.get("intent")
            confidence = response.get("confidence", 0.0)
            reasoning = response.get("reasoning", "")

            logger.info("_classify_intent", f"Intent classified: {selected_intent}",
                       confidence=confidence,
                       reasoning=reasoning[:100])

            # Confidence threshold 체크
            CONFIDENCE_THRESHOLD = 0.75  # 명확한 선택만 허용
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
            "우선순위:",
            "- 연애 관련 표현(좋아하다, 고백, 썸 등)이 있으면 concern_love 우선",
            "- 친구/대인관계 표현이 있으면 concern_relationship",
            "- 진로/직업 표현이 있으면 concern_career",
            "- 자신감/자존감이 주제면 concern_confidence",
            "- 일반적인 힘듦/스트레스면 concern_stress"
        ])

        return "\n".join(prompt_parts)


__all__ = ["FreeIntentStageHandler"]
