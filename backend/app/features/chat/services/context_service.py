"""
Context Service - 컨텍스트 빌딩 및 Beats 생성 통합 서비스

Features:
- children_ctx 구성 (공통 정보 추가)
- context_summary 생성
- recent_dialogues 수집
- LLM 기반 동적 beats 생성
- Fallback beats 제공

Combines 2 services:
1. ContextBuilderService - Context 구성
2. BeatsGeneratorService - Beats 생성
"""
from typing import List, Dict, Any, Optional

from app.core.config import get_settings
from app.core.llm.client import LLMClient
from app.core.logging import get_parent_logger

settings = get_settings()
logger = get_parent_logger("ContextService")


# LLM Beats 생성 프롬프트
LLM_BEATS_SYSTEM_PROMPT = """당신은 스토리 진행 전문가입니다.

현재 장면에서 필요한 대화 목표(beats)를 JSON 배열로 생성하세요.

각 beat는 다음 형식을 가집니다:
{{
  "goal": "목표 설명",
  "speaker_hint": ["가능한_화자1", "가능한_화자2"]
}}

3-5개의 beats를 생성하세요. 자연스러운 스토리 흐름을 유지하세요."""


class ContextService:
    """
    컨텍스트 빌딩 및 Beats 생성 통합 서비스 (Layer 3 - Service)

    Features:
    - build_children_context(): 핸들러 ctx에 공통 정보 추가
    - build_context_summary(): 최근 대화 요약
    - generate_beats(): LLM 기반 동적 beats 생성
    - create_fallback_beats(): Fallback beats

    Example:
        service = ContextService(llm_client=llm)

        # Context 구성
        children_ctx = service.build_children_context(
            base_ctx={"stage_tag": "intro"},
            state=state,
            scenario=scenario
        )

        # Beats 생성
        beats = await service.generate_beats(
            state=state,
            ctx=children_ctx
        )
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enable_llm: bool = True
    ):
        """
        Args:
            llm_client: LLM 클라이언트
            enable_llm: LLM 사용 여부
        """
        self.llm_client = llm_client or LLMClient()
        self.enable_llm = enable_llm

        logger.info("__init__", "ContextService initialized",
                   enable_llm=enable_llm)

    # ========== 1. Context Building ==========

    def build_children_context(
        self,
        base_ctx: Dict[str, Any],
        state: Dict[str, Any],
        scenario: Dict[str, Any],
        stage: Optional[Dict[str, Any]] = None,
        next_stage: Optional[str] = None,
        immediate_advance: bool = False
    ) -> Dict[str, Any]:
        """
        핸들러가 생성한 기본 ctx에 공통 정보 추가

        Args:
            base_ctx: 핸들러가 생성한 기본 context
            state: 전체 state 객체
            scenario: 시나리오 정보
            stage: 현재 스테이지 정의
            next_stage: 다음 스테이지 태그
            immediate_advance: 즉시 전환 여부

        Returns:
            완성된 children_ctx
        """
        children_ctx = dict(base_ctx)

        # Stage tag 결정
        stage_tag = base_ctx.get("stage_tag") or (stage.get("tag") if stage else "unknown")
        if next_stage and immediate_advance:
            stage_tag = next_stage
            children_ctx["stage_tag"] = stage_tag

        # Stage type 결정
        if stage:
            stage_type_value = stage.get("type", "scene")
        else:
            stage_type_value = base_ctx.get("stage_type", "scene")

        children_ctx.setdefault("stage_type", stage_type_value)

        # Beats, speaker_pool, context
        if stage:
            if not children_ctx.get("beats"):
                children_ctx["beats"] = stage.get("beats", [])
            if not children_ctx.get("speaker_pool"):
                children_ctx["speaker_pool"] = stage.get("speaker_pool", [])

            # ✅ stage context 추가 (beats 없을 때 LLM 자율 생성용)
            # 단, base_ctx에서 이미 설정된 stage_context가 있으면 덮어쓰지 않음 (MissionStageHandler 우선)
            if "stage_context" not in children_ctx:
                stage_context = stage.get("context", "")
                if stage_context:
                    children_ctx["stage_context"] = stage_context

            objective = stage.get("objective")
            if objective:
                children_ctx["stage_objective"] = objective

        else:
            children_ctx.setdefault("beats", [])
            children_ctx.setdefault("speaker_pool", [])

        # Context summary 및 최근 대화
        children_ctx["context_summary"] = self.build_context_summary(state)
        children_ctx["latest_user_input"] = state.get("user_input", "")

        # 최근 8~10개 메시지 추출 (MessageHistoryService 직접 사용)
        from .message_history_service import get_message_history_service
        message_history_service = get_message_history_service()
        children_ctx["recent_dialogues"] = message_history_service.select_recent_messages(
            message_history=state.get("message_history", []),
            keep_count=10  # v2: 8~10개
        )

        # v2: User Profile (항상)
        children_ctx["user_profile"] = state.get("user_profile", "")

        # v2: STM (항상)
        children_ctx["stm_summary"] = state.get("stm_summary", "")

        # v2: Long-term memories (자유대화만) 또는 Scenario Buffer (시나리오만)
        scenario_id = scenario.get("scenario_id", "unknown")
        if scenario_id == "free-talk":
            children_ctx["long_term_memories"] = state.get("long_term_memories", [])
            children_ctx["scenario_buffer"] = None
        else:
            children_ctx["long_term_memories"] = []
            children_ctx["scenario_buffer"] = state.get("scenario_buffer", "")

        # Character refs 및 scenario_id
        children_ctx.setdefault("character_refs", scenario.get("character_refs", {}))
        children_ctx.setdefault("scenario_id", scenario.get("scenario_id", "unknown"))

        logger.debug("build_children_context", "Context built",
                    stage_tag=stage_tag,
                    beats_count=len(children_ctx.get("beats", [])))

        return children_ctx

    def get_all_previous_stage_tags(
        self,
        current_stage_tag: str,
        scenario: Dict[str, Any]
    ) -> List[str]:
        """
        현재 스테이지 이전의 모든 스테이지 태그 찾기

        Args:
            current_stage_tag: 현재 스테이지 태그
            scenario: 시나리오 데이터

        Returns:
            이전 스테이지 태그 리스트 (순서 유지)

        Example:
            TRAIN_PRELUDE -> HEROES_ARRIVE -> USER_INTRODUCTION
            current = USER_INTRODUCTION이면 [TRAIN_PRELUDE, HEROES_ARRIVE] 반환
        """
        logger.debug("get_all_previous_stage_tags",
                    f"🔍 INPUT: current_stage_tag={current_stage_tag}, scenario keys={list(scenario.keys()) if scenario else None}")

        if not current_stage_tag or not scenario:
            logger.warning("get_all_previous_stage_tags", "❌ Missing current_stage_tag or scenario")
            return []

        stages = scenario.get("stages", [])
        logger.debug("get_all_previous_stage_tags",
                    f"🔍 stages type={type(stages)}, is_list={isinstance(stages, list)}, len={len(stages) if isinstance(stages, list) else 'N/A'}")

        if not isinstance(stages, list):
            logger.warning("get_all_previous_stage_tags", f"❌ stages is not a list: {type(stages)}")
            return []

        # 스테이지 순서대로 태그 수집
        stage_order = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            tag = stage.get("tag")
            if tag:
                stage_order.append(tag)
            # 현재 스테이지를 만나면 중단
            if tag == current_stage_tag:
                break

        # 현재 스테이지 제외하고 반환
        previous_tags = stage_order[:-1] if len(stage_order) > 1 else []

        logger.debug("get_all_previous_stage_tags",
                    f"Current: {current_stage_tag}, Previous: {previous_tags}")

        return previous_tags

    def build_context_summary(self, state: Dict[str, Any]) -> Optional[str]:
        """
        최근 사용자 입력과 대화 요약

        Args:
            state: 전체 state 객체

        Returns:
            Context 요약 문자열
        """
        summary_lines: List[str] = []

        user_input = (state.get("user_input") or "").strip()
        if user_input:
            summary_lines.append(f"사용자: {user_input}")

        message_history = state.get("message_history") or []
        if isinstance(message_history, list):
            for entry in message_history[-10:]:
                if not isinstance(entry, dict):
                    continue
                speaker = entry.get("speaker") or entry.get("role") or "unknown"
                text = (entry.get("text") or entry.get("content") or "").strip()
                if text:
                    summary_lines.append(f"{speaker}: {text[:150]}...")

        summary = "\n".join(summary_lines) if summary_lines else None

        logger.debug("build_context_summary", "Summary built",
                    lines=len(summary_lines))

        return summary

    # ========== 2. Beats Generation ==========

    async def generate_beats(
        self,
        state: Dict[str, Any],
        ctx: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        LLM 기반 동적 beats 생성

        Args:
            state: 전체 state 객체
            ctx: children_ctx

        Returns:
            생성된 beats 리스트 또는 fallback beats
        """
        if not self.enable_llm:
            stage_context = ctx.get("stage_objective", "장면 진행 중")
            speaker_pool = ctx.get("speaker_pool", [])
            return self.create_fallback_beats(stage_context, speaker_pool)

        stage_tag = ctx.get("stage_tag", "unknown")
        speaker_pool = ctx.get("speaker_pool", [])
        latest_user_input = ctx.get("latest_user_input", "")
        recent_dialogues = ctx.get("recent_dialogues", [])

        # 시나리오 context 추출
        scenario = state.get("scenario_data") or state.get("scenario") or {}
        stages = scenario.get("stages", {})

        if isinstance(stages, dict):
            stage_data = stages.get(stage_tag, {})
        elif isinstance(stages, list):
            stage_data = next((s for s in stages if s.get("tag") == stage_tag), {})
        else:
            stage_data = {}

        stage_context = stage_data.get("context", f"현재 {stage_tag} 장면이 진행 중입니다.")

        # 사용자 프롬프트 구성
        # Beats 생성 시에는 최근 6개 대화를 참고 (맥락 유지)
        if recent_dialogues:
            formatted_dialogues = []
            for d in recent_dialogues[-6:]:
                if isinstance(d, dict):
                    speaker = d.get("speaker", "unknown")
                    text = d.get("text", "")
                    formatted_dialogues.append(f"{speaker}: {text}")
                else:
                    formatted_dialogues.append(str(d))
            recent_history = "\n".join(formatted_dialogues)
        else:
            recent_history = "(대화 없음)"

        user_prompt = f"""이전 대화:
{recent_history}

사용자 입력: {latest_user_input}

현재 장면: {stage_context}

사용 가능한 화자: {", ".join(speaker_pool) if speaker_pool else "narr"}

위 정보를 바탕으로 3-5개의 beats를 생성하세요."""

        try:
            response_text = await self.llm_client.call(
                system_prompt=LLM_BEATS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=600
            )

            # JSON 파싱
            import json
            response = json.loads(response_text)

            if isinstance(response, list) and response:
                logger.info("generate_beats", f"✅ Generated {len(response)} beats via LLM")
                return response
            elif isinstance(response, dict) and response.get("beats"):
                beats = response["beats"]
                if isinstance(beats, list):
                    return beats

            logger.warning("generate_beats", "LLM beats invalid format, using fallback")
            return self.create_fallback_beats(stage_context, speaker_pool)

        except Exception as exc:
            logger.error("generate_beats", f"LLM beats generation failed: {exc}")
            return self.create_fallback_beats(stage_context, speaker_pool)

    def create_fallback_beats(
        self,
        context: str,
        speaker_pool: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Fallback beats 생성

        Args:
            context: 현재 스테이지 context
            speaker_pool: 화자 풀

        Returns:
            Fallback beats
        """
        fallback_speaker = speaker_pool[0] if speaker_pool else "narr"

        beats = [
            {
                "goal": context,
                "speaker_hint": ["narr"],
            },
            {
                "goal": "상황을 파악하고 다음 행동을 결정한다.",
                "speaker_hint": [fallback_speaker],
            },
        ]

        logger.debug("create_fallback_beats", "Fallback beats created",
                    count=len(beats))

        return beats


__all__ = ["ContextService"]
