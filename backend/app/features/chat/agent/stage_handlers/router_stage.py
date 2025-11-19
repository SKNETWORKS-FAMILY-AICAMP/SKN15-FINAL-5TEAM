"""
Router Stage Handler - 라우팅 스테이지 처리

Features:
- 키워드 기반 사전 분류 (빠른 매칭)
- LLM 기반 Intent 분류 (유연한 이해)
- 하이브리드 접근으로 높은 정확도 달성
- **대화 생성 없이 즉시 라우팅** (stage_complete=True)
"""
from typing import Dict, Any, Optional

from app.core.logging import get_parent_logger
from app.core.llm import LLMClient

from . import StageResult

logger = get_parent_logger("RouterStageHandler")


class RouterStageHandler:
    """
    라우터 스테이지 핸들러

    Intent 매핑을 기반으로 다음 스테이지를 결정합니다.
    대화를 생성하지 않고 즉시 다음 스테이지로 라우팅합니다.
    """

    def __init__(self):
        """RouterStageHandler 초기화"""
        self.llm_client = LLMClient()
        logger.info("__init__", "RouterStageHandler initialized")

    async def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> StageResult:
        """
        라우터 스테이지 처리

        Args:
            state: 게임 상태
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            StageResult
        """
        stage_tag = stage.get("tag", "router")
        stage_turn = state.get("stage_turn", 0)
        user_input = state.get("user_input", "")

        # stage_turn == 0인 경우, 이전 턴의 입력을 사용 (스테이지 전환 직후)
        # StateService가 스테이지 전환 시 user_input을 cached_user_input에 저장함
        if stage_turn == 0:
            cached_input = state.get("cached_user_input", "")
            if cached_input:
                user_input = cached_input
                logger.info("handle", "Router stage starting with cached input",
                           cached_input=cached_input[:50])
            else:
                logger.warning("handle", "Router stage starting but no cached_user_input",
                              current_input=user_input[:50] if user_input else "empty")

        intent_mapping = stage.get("intent_mapping", {})

        logger.debug("handle", "Handling router stage",
                    stage_tag=stage_tag,
                    user_input_len=len(user_input),
                    stage_turn=stage_turn)

        # Intent 분류 (하이브리드: 키워드 + LLM)
        next_stage = await self._classify_intent(
            user_input=user_input,
            intent_mapping=intent_mapping,
            stage_tag=stage_tag,
            scenario=scenario
        )

        # next_by_outcome이 있으면 조건 기반 라우팅 (hidden ending 체크)
        next_by_outcome = stage.get("next_by_outcome")
        if next_by_outcome:
            outcome = self._check_ending_condition(state, scenario)
            next_stage = next_by_outcome.get(outcome) or stage.get("default_next")
            logger.info("handle", f"Outcome-based routing: {outcome} -> {next_stage}")
        elif not next_stage:
            # 기본 라우팅
            next_stage = stage.get("default_next") or stage.get("next")

        logger.info("handle", "Routing complete",
                   next_stage=next_stage)

        # Children context 구성
        children_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "router",
            "beats": stage.get("beats", []),
            "speaker_pool": stage.get("speaker_pool", []),
            "scenario_id": scenario.get("scenario_id", "unknown"),
        }

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=True,  # 항상 즉시 완료
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
        하이브리드 Intent 분류 (키워드 사전분류 + LLM)

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

        # === 1단계: 키워드 기반 사전 분류 (Critical cases) ===
        # 연애 관련 키워드 체크
        love_keywords = ["좋아하", "고백", "짝사랑", "썸", "데이트", "연애", "사랑", "호감"]
        if any(keyword in user_input for keyword in love_keywords):
            if "concern_love" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_love (keyword matched)")
                return intent_mapping["concern_love"]

        # 친구/외로움 관련 키워드 체크
        relationship_keywords = ["친구가 없", "친구 사귀", "외로", "소외", "어울리"]
        if any(keyword in user_input for keyword in relationship_keywords):
            if "concern_relationship" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_relationship (keyword matched)")
                return intent_mapping["concern_relationship"]

        # 진로 관련 키워드 체크
        career_keywords = ["진로", "취업", "직장", "커리어", "적성"]
        if any(keyword in user_input for keyword in career_keywords):
            if "concern_career" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_career (keyword matched)")
                return intent_mapping["concern_career"]

        # 자신감 관련 키워드 체크 (다른 맥락이 없을 때만)
        confidence_keywords = ["자신감", "자존감", "당당"]
        if any(keyword in user_input for keyword in confidence_keywords):
            has_other_context = (
                any(kw in user_input for kw in love_keywords) or
                any(kw in user_input for kw in relationship_keywords) or
                any(kw in user_input for kw in career_keywords)
            )
            if not has_other_context and "concern_confidence" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_confidence (keyword matched)")
                return intent_mapping["concern_confidence"]

        # 스트레스 관련 키워드 체크 (가장 일반적이므로 마지막에)
        stress_keywords = ["힘들", "무거", "스트레스", "우울", "무기력"]
        if any(keyword in user_input for keyword in stress_keywords):
            has_specific_context = (
                any(kw in user_input for kw in love_keywords) or
                any(kw in user_input for kw in relationship_keywords) or
                any(kw in user_input for kw in career_keywords) or
                any(kw in user_input for kw in confidence_keywords)
            )
            if not has_specific_context and "concern_stress" in intent_mapping:
                logger.info("_classify_intent", f"Pre-classified as concern_stress (keyword matched)")
                return intent_mapping["concern_stress"]

        # === 2단계: LLM 기반 분류 (키워드 매치 실패 시) ===
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
                temperature=0.3,
                max_tokens=300
            )

            selected_intent = response.get("intent")
            confidence = response.get("confidence", 0.0)
            reasoning = response.get("reasoning", "")

            logger.info("_classify_intent", f"Intent classified: {selected_intent}",
                       confidence=confidence,
                       reasoning=reasoning[:100])

            # Confidence threshold 체크
            CONFIDENCE_THRESHOLD = 0.5
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

    def _check_ending_condition(
        self,
        state: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> str:
        """
        엔딩 조건 확인

        recruit_order와 allies_recruited를 기반으로 hidden ending 조건 체크

        Args:
            state: 게임 상태
            scenario: 시나리오 데이터

        Returns:
            "HIDDEN" 또는 "BASIC"
        """
        # scenario.metadata.ending.hidden_condition 가져오기
        metadata = scenario.get("metadata", {})
        ending_config = metadata.get("ending", {})
        hidden_condition = ending_config.get("hidden_condition", {})
        required_order = hidden_condition.get("required_order", [])

        if not required_order:
            logger.debug("_check_ending_condition", "No required_order - defaulting to BASIC")
            return "BASIC"

        recruit_order = state.get("recruit_order", [])
        allies = state.get("allies_recruited", [])

        # 조건 1: recruit_order가 required_order와 일치
        order_match = recruit_order == required_order

        # 조건 2: required_order의 모든 타겟이 allies에 포함
        all_recruited = all(target in allies for target in required_order)

        logger.info("_check_ending_condition",
                   "Checking ending conditions",
                   recruit_order=recruit_order,
                   required_order=required_order,
                   allies=allies,
                   order_match=order_match,
                   all_recruited=all_recruited)

        if order_match and all_recruited:
            logger.info("_check_ending_condition", "🎉 HIDDEN ending unlocked!")
            return "HIDDEN"
        else:
            logger.info("_check_ending_condition", "BASIC ending")
            return "BASIC"


__all__ = ["RouterStageHandler"]
