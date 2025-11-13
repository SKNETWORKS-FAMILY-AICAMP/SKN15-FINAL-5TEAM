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
    - collect_recent_dialogues(): 최근 대화 수집
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

        # Beats 및 speaker_pool
        if stage:
            if not children_ctx.get("beats"):
                children_ctx["beats"] = stage.get("beats", [])
            if not children_ctx.get("speaker_pool"):
                children_ctx["speaker_pool"] = stage.get("speaker_pool", [])

            objective = stage.get("objective")
            if objective:
                children_ctx["stage_objective"] = objective

        else:
            children_ctx.setdefault("beats", [])
            children_ctx.setdefault("speaker_pool", [])

        # Context summary 및 최근 대화
        children_ctx["context_summary"] = self.build_context_summary(state)
        children_ctx["latest_user_input"] = state.get("user_input", "")
        children_ctx["recent_dialogues"] = self.collect_recent_dialogues(state, current_stage_tag=stage_tag)

        # Character refs 및 scenario_id
        children_ctx.setdefault("character_refs", scenario.get("character_refs", {}))
        children_ctx.setdefault("scenario_id", scenario.get("scenario_id", "unknown"))

        logger.debug("build_children_context", "Context built",
                    stage_tag=stage_tag,
                    beats_count=len(children_ctx.get("beats", [])))

        return children_ctx

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
            for entry in message_history[-4:]:
                if not isinstance(entry, dict):
                    continue
                speaker = entry.get("speaker") or entry.get("role") or "unknown"
                text = (entry.get("text") or entry.get("content") or "").strip()
                if text:
                    summary_lines.append(f"{speaker}: {text[:50]}...")

        summary = "\n".join(summary_lines) if summary_lines else None

        logger.debug("build_context_summary", "Summary built",
                    lines=len(summary_lines))

        return summary

    def collect_recent_dialogues(self, state: Dict[str, Any], current_stage_tag: Optional[str] = None) -> List[str]:
        """
        최근 대화 수집 (현재 스테이지의 대화만)

        Args:
            state: 전체 state 객체
            current_stage_tag: 현재 스테이지 태그 (필터링용)

        Returns:
            최근 대화 리스트
        """
        recent_dialogues: List[str] = []

        message_history = state.get("message_history") or []
        logger.info("collect_recent_dialogues", f"🔍 DEBUG: message_history count = {len(message_history)}, filtering by stage_tag={current_stage_tag}")
        if message_history:
            logger.info("collect_recent_dialogues", f"🔍 DEBUG: First message = {message_history[0]}")

        if isinstance(message_history, list):
            # 현재 스테이지의 대화만 필터링
            stage_filtered = []
            for entry in message_history:
                if not isinstance(entry, dict):
                    continue
                # stage_tag가 제공되고, 메시지에 stage_tag가 있으면 필터링
                if current_stage_tag and entry.get("stage_tag"):
                    if entry.get("stage_tag") == current_stage_tag:
                        stage_filtered.append(entry)
                else:
                    # stage_tag 정보가 없으면 모든 대화 포함 (하위 호환성)
                    stage_filtered.append(entry)

            logger.info("collect_recent_dialogues", f"🔍 DEBUG: After stage filtering = {len(stage_filtered)} messages")

            # 최근 5개만 선택
            for entry in stage_filtered[-5:]:
                speaker = entry.get("speaker") or "unknown"
                text = (entry.get("text") or "").strip()
                if text:
                    recent_dialogues.append(f"{speaker}: {text}")

        logger.debug("collect_recent_dialogues", "Recent dialogues collected",
                    count=len(recent_dialogues))

        return recent_dialogues

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
        recent_history = "\n".join(recent_dialogues[-3:]) if recent_dialogues else "(대화 없음)"

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
