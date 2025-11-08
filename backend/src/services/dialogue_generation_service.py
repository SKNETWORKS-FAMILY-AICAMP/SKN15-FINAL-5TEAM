"""
============================================================
🗣️ Dialogue Generation Service — 대사 생성 오케스트레이션
============================================================
ChildrenAgent의 대사 생성 핵심 로직을 서비스로 분리합니다.
DialogueFormatterService와 BeatsGeneratorService를 활용합니다.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.core import scene_dialogue_tools as dialogue_tools
from src.core.prompt_builder import DialoguePromptBuilder
from src.services.dialogue_formatter_service import DialogueFormatterService
from src.services.beats_generator_service import BeatsGeneratorService
from src.utils.llm_client import LLMClient, get_llm_client
from src.utils.logger import log
from src.utils.config_loader import get_config_loader
from src.database.session_manager import HybridSessionManager

_PROMPTS = get_config_loader().get_prompts()
_CHILDREN_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("children") or {})
_CHILDREN_DIALOGUE_PROMPT = (_CHILDREN_PROMPTS.get("dialogue_generation") or "").strip()

if not _CHILDREN_DIALOGUE_PROMPT:
    raise ValueError("ChildrenAgent dialogue_generation prompt missing in configs/prompts.yaml")


class DialogueGenerationService:
    """
    대사 생성 오케스트레이션 서비스

    책임:
    - 대사 생성 파이프라인 오케스트레이션
    - LLM 호출 및 재시도 로직
    - Formatter 및 BeatsGenerator 서비스 활용
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        session_manager: Optional[HybridSessionManager] = None,
        formatter: Optional[DialogueFormatterService] = None,
        beats_generator: Optional[BeatsGeneratorService] = None,
    ):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
            session_manager: 세션 매니저 (에러 로깅용)
            formatter: 대사 포맷터 서비스 (None이면 자동 생성)
            beats_generator: Beats 생성 서비스 (None이면 자동 생성)
        """
        self._llm = llm_client or get_llm_client()
        self._session_manager = session_manager
        self._formatter = formatter or DialogueFormatterService()
        self._beats_generator = beats_generator or BeatsGeneratorService(llm_client=self._llm, session_manager=session_manager)

        # Initialize session manager if not provided
        if not self._session_manager:
            try:
                from src.database.db_manager import DatabaseManager
                from src.database.cache_manager import CacheManager
                db = DatabaseManager()
                cache_manager = CacheManager()
                self._session_manager = HybridSessionManager(db_manager=db, cache_manager=cache_manager)
            except Exception as e:
                log("dialogue_generation", "session_manager_init_failed", error=str(e))

    def generate_dialogues(
        self,
        children_ctx: Dict[str, Any],
        state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        children_ctx와 state를 받아 대사 리스트를 생성합니다.

        Args:
            children_ctx: ParentAgent가 구성한 children context
            state: 전체 state 객체

        Returns:
            생성된 대사 리스트 [{"speaker": "...", "text": "..."}, ...]
        """
        # 1️⃣ 컨텍스트 추출
        character_refs = children_ctx.get("character_refs", {})
        beats = children_ctx.get("beats") or []
        stage_tag = children_ctx.get("stage_tag")
        stage_type = children_ctx.get("stage_type")
        stage_objective = children_ctx.get("stage_objective")
        intent_options = children_ctx.get("intent_options")
        latest_user_input = children_ctx.get("latest_user_input")
        recent_dialogues = children_ctx.get("recent_dialogues")
        prefetch_entries = children_ctx.get("prefetch_dialogues") or []

        # Prefetch 대사 렌더링
        prefetch_dialogues = self._formatter.render_dialogues(
            state,
            [dict(entry) for entry in prefetch_entries if isinstance(entry, dict)]
        ) if prefetch_entries else []

        def merge_with_prefetch(dialogues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """Prefetch 대사와 생성 대사를 병합"""
            if not prefetch_dialogues:
                return dialogues
            merged = []
            for item in prefetch_dialogues:
                merged.append(dict(item))
            for item in dialogues:
                merged.append(item)
            return merged

        # ⚠️ beats가 비어있으면 에러 반환 (LLM hallucination 방지)
        # 단, llm_beats=true인 경우는 LLM이 beats를 실시간 생성
        llm_beats_enabled = children_ctx.get("llm_beats", False)

        if not beats and not llm_beats_enabled:
            fallback = (children_ctx.get("fallback") or {}).get("dialogues") or []
            if fallback:
                log("dialogue_generation", "⚙️ Using provided fallback dialogues (no beats)")
                return merge_with_prefetch(self._formatter.render_dialogues(state, fallback))

            log("dialogue_generation", "⚠️ No beats provided - cannot generate dialogue")
            return merge_with_prefetch([{
                "speaker": "system",
                "text": "시나리오를 불러오는 중 문제가 발생했습니다. 다시 시도해주세요."
            }])

        # 🔧 OFF_TOPIC이나 system_notice는 LLM 우회하고 fallback 직접 사용
        if stage_type == "system_notice" or stage_tag == "OFF_TOPIC":
            log("dialogue_generation", f"⚙️ Bypassing LLM for {stage_type or stage_tag} - using fallback directly")

            # fallback에 dialogues가 있으면 우선 사용
            fallback = children_ctx.get("fallback", {})
            if isinstance(fallback, dict):
                fallback_dialogues = fallback.get("dialogues", [])
                if fallback_dialogues:
                    log("dialogue_generation", f"✅ Using {len(fallback_dialogues)} fallback dialogues")
                    return merge_with_prefetch(self._formatter.render_dialogues(state, fallback_dialogues))

            # fallback이 없으면 beats 그대로 사용
            log("dialogue_generation", f"✅ Using {len(beats)} beats as-is")
            normalized = self._formatter.normalize_dialogues(beats)
            return merge_with_prefetch(self._formatter.render_dialogues(state, normalized))

        # 🔍 LLM Beats 생성 (llm_beats=true인 경우)
        if llm_beats_enabled:
            log("dialogue_generation", f"🎭 LLM Beats mode enabled for stage={stage_tag}")

            if not beats:
                latest_user_input = children_ctx.get("latest_user_input", "").strip()
                user_input = state.get("user_input", "").strip()

                # 유저 입력이 있을 때만 beats 생성
                if latest_user_input or user_input:
                    beats = self._beats_generator.generate_beats_from_context(state, children_ctx)
                    log("dialogue_generation", f"✨ Generated {len(beats)} beats via LLM based on user input")
                else:
                    log("dialogue_generation", "⚠️ LLM Beats mode: No user input detected, skipping auto-generation")
        else:
            log("dialogue_generation", f"📋 Received {len(beats)} beats for stage={stage_tag}")
            for i, beat in enumerate(beats[:3]):  # 첫 3개만
                if isinstance(beat, dict):
                    goal = beat.get("goal", "")[:60]
                    log("dialogue_generation", f"  Beat[{i}]: {goal}...")

        # ✅ 시나리오 키 감지
        scenario_ref = state.get("scenario") or state.get("scenario_data") or {}
        metadata = scenario_ref.get("metadata") if isinstance(scenario_ref, dict) else {}
        tone_meta = metadata.get("tone") or {}
        scenario_key = tone_meta.get("scenario_key")

        # 2️⃣ 캐릭터 톤 + 관계 로드
        speaker_pool = children_ctx.get("speaker_pool", [])
        context_summary = children_ctx.get("context_summary")

        # 🔧 speaker_pool에 있는 캐릭터만 tone_profile 로드
        filtered_character_refs = {}
        for char in speaker_pool:
            if char in character_refs:
                filtered_character_refs[char] = character_refs[char]

        tone_profiles = dialogue_tools.load_tone_profiles(filtered_character_refs, scenario_key)

        # 3️⃣ LLM 프롬프트 생성 (DialoguePromptBuilder 사용)
        stage_turn = int(state.get("stage_turn", 0) or 0)

        # 🎨 프롬프트 빌더 사용
        llm_prompt = DialoguePromptBuilder.build(
            stage_tag=stage_tag,
            beats=beats,
            tone_profiles=tone_profiles,
            speaker_pool=speaker_pool,
            context_summary=context_summary,
            stage_turn=stage_turn,
            stage_type=stage_type or "",
            stage_objective=stage_objective,
            intent_options=intent_options if isinstance(intent_options, dict) else None,
            latest_user_input=latest_user_input if isinstance(latest_user_input, str) else None,
            recent_dialogues=recent_dialogues if isinstance(recent_dialogues, list) else None,
            conversation_summary=state.get("conversation_summary"),
        )

        # 4️⃣ LLM 호출 시도
        try:
            system_prompt = _CHILDREN_DIALOGUE_PROMPT
            primary_temperature = self._llm.get_agent_setting("children", "temperature", 0.8)
            retry_temperature = self._llm.get_agent_setting("children", "retry_temperature", 1.0)
            max_tokens = self._llm.get_agent_setting("children", "max_tokens", 1200)  # 🚀 Reduced from 2000 for faster generation

            response = self._llm.call_json(
                system_prompt=system_prompt,
                user_prompt=llm_prompt,
                temperature=primary_temperature,
                max_tokens=max_tokens,
                agent="children",
            )
            log("dialogue_generation", f"LLM raw response: {json.dumps(response, ensure_ascii=False)[:500]}")

            dialogue_payload = None
            if isinstance(response, dict):
                dialogue_payload = response.get("dialogues")

            # 1차 응답 검증
            if not isinstance(dialogue_payload, list) or not dialogue_payload:
                log("dialogue_generation", "⚠️ LLM response invalid or empty → retrying once")
                retry_resp = self._llm.call_json(
                    system_prompt=system_prompt,
                    user_prompt=llm_prompt,
                    temperature=retry_temperature,
                    max_tokens=max_tokens,
                    agent="children",
                )
                log("dialogue_generation", f"LLM retry response: {json.dumps(retry_resp, ensure_ascii=False)[:500]}")

                if isinstance(retry_resp, dict):
                    dialogue_payload = retry_resp.get("dialogues")

            if isinstance(dialogue_payload, list) and dialogue_payload:
                dialogues = self._formatter.normalize_dialogues(dialogue_payload)
                if dialogues:
                    log("dialogue_generation", f"✅ Generated {len(dialogues)} tone-aware dialogues.")
                    return merge_with_prefetch(self._formatter.render_dialogues(state, dialogues))

            log("dialogue_generation", f"⚠️ LLM invalid response → {type(response)} {response}")
        except Exception as exc:
            log("dialogue_generation", f"❌ LLM call failed: {exc}")

            # 🚨 LLM 호출 실패 에러 로깅
            if self._session_manager:
                try:
                    session_id = state.get("session_id")
                    if session_id:
                        self._session_manager.save_error_log(
                            error_type="children_llm_call_failed",
                            error_message=str(exc),
                            session_id=session_id,
                            metadata={
                                "agent": "children",
                                "stage_tag": children_ctx.get("stage_tag"),
                                "stage_type": children_ctx.get("stage_type"),
                                "speaker_pool": children_ctx.get("speaker_pool")
                            }
                        )
                except Exception as e:
                    log("dialogue_generation", "error_log_save_failed", error=str(e))

        # 5️⃣ Fallback: beats 그대로 사용
        log("dialogue_generation", "⚙️ Using beats fallback (no LLM response).")

        children_ctx.setdefault("fallback_count", 0)
        children_ctx["fallback_count"] += 1
        if children_ctx["fallback_count"] > 3:
            log("dialogue_generation", "❌ Too many fallback calls → forcing stage advance")
            state["stage_turn"] = int(state.get("stage_turn", 0) or 0) + 1
            state.setdefault("temp_data", {})["force_story_resume"] = True

        # beats가 비어있으면 에러 메시지 반환
        if not beats:
            log("dialogue_generation", "⚠️ No beats available for fallback")
            return merge_with_prefetch([{
                "speaker": "system",
                "text": "시나리오를 불러오는 중 문제가 발생했습니다. 다시 시도해주세요."
            }])

        fallback_dialogues = self._formatter.normalize_dialogues(beats)
        fallback = (children_ctx.get("fallback") or {}).get("dialogues") or []
        if fallback:
            log("dialogue_generation", "⚙️ Using provided fallback dialogues for this stage")
            fallback_dialogues = self._formatter.normalize_dialogues(fallback)
        return merge_with_prefetch(self._formatter.render_dialogues(state, fallback_dialogues))


__all__ = ["DialogueGenerationService"]
