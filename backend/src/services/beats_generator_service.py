"""
============================================================
🎭 Beats Generator Service — 동적 Beats 생성
============================================================
llm_beats=true일 때 LLM을 사용하여 실시간으로 beats를 생성합니다.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.prompt_builder import LLMBeatsPromptBuilder
from src.utils.llm_client import LLMClient, get_llm_client
from src.utils.logger import log
from src.utils.config_loader import get_config_loader
from src.database.session_manager import HybridSessionManager

_PROMPTS = get_config_loader().get_prompts()
_LLM_BEATS_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("llm_beats") or {})
_LLM_BEATS_SYSTEM = (_LLM_BEATS_PROMPTS.get("system") or "").strip()

if not _LLM_BEATS_SYSTEM:
    raise ValueError("LLM beats system prompt missing in configs/prompts.yaml")


class BeatsGeneratorService:
    """
    동적 Beats 생성 서비스

    책임:
    - LLM을 사용하여 context 기반 beats 생성
    - Fallback beats 제공
    """

    def __init__(self, llm_client: Optional[LLMClient] = None, session_manager: Optional[HybridSessionManager] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
            session_manager: 세션 매니저 (에러 로깅용)
        """
        self._llm = llm_client or get_llm_client()
        self._session_manager = session_manager

        # Initialize session manager if not provided
        if not self._session_manager:
            try:
                from src.database.db_manager import DatabaseManager
                from src.database.cache_manager import CacheManager
                db = DatabaseManager()
                cache_manager = CacheManager()
                self._session_manager = HybridSessionManager(db_manager=db, cache_manager=cache_manager)
            except Exception as e:
                log("beats_generator", "session_manager_init_failed", error=str(e))

    def generate_beats_from_context(
        self,
        state: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        context를 기반으로 LLM이 beats를 실시간 생성

        Args:
            state: 전체 state 객체
            ctx: children_ctx (stage_tag, speaker_pool 등 포함)

        Returns:
            생성된 beats 리스트 또는 fallback beats
        """
        stage_tag = ctx.get("stage_tag", "unknown")
        speaker_pool = ctx.get("speaker_pool", [])
        latest_user_input = ctx.get("latest_user_input", "")
        recent_dialogues = ctx.get("recent_dialogues", [])

        # 시나리오 context 추출
        scenario_ref = state.get("scenario") or state.get("scenario_data") or {}
        stage_context = ""

        # 현재 스테이지의 context 찾기
        stages = scenario_ref.get("stages", [])
        for stage in stages:
            if isinstance(stage, dict) and stage.get("tag") == stage_tag:
                stage_context = stage.get("context", "")
                break

        if not stage_context:
            stage_context = f"현재 {stage_tag} 장면이 진행 중입니다."

        # 이전 스테이지 요약 추출
        previous_summary = state.get("state_update", {}).get("scene_summary", "")
        if not previous_summary:
            previous_summary = "(이전 장면 정보 없음)"

        # 🎨 LLMBeatsPromptBuilder 사용
        user_prompt = LLMBeatsPromptBuilder.build(
            previous_stage_summary=previous_summary,
            stage_context=stage_context,
            recent_history=recent_dialogues,
            latest_user_input=latest_user_input,
            speaker_pool=speaker_pool,
        )

        try:
            response = self._llm.call_json(
                system_prompt=_LLM_BEATS_SYSTEM,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=600,  # 🚀 Reduced from 1000 for faster generation
            )

            if isinstance(response, list) and response:
                log("beats_generator", f"✅ Generated {len(response)} beats via LLM")
                return response
            elif isinstance(response, dict) and response.get("beats"):
                beats = response["beats"]
                if isinstance(beats, list):
                    return beats

            log("beats_generator", "⚠️ LLM beats generation returned invalid format")
            return self.create_fallback_beats(stage_context, speaker_pool)

        except Exception as exc:
            log("beats_generator", f"❌ LLM beats generation failed: {exc}")

            # 🚨 LLM beats 생성 실패 에러 로깅
            if self._session_manager:
                try:
                    session_id = state.get("session_id")
                    if session_id:
                        self._session_manager.save_error_log(
                            error_type="children_llm_beats_failed",
                            error_message=str(exc),
                            session_id=session_id,
                            metadata={
                                "agent": "children",
                                "operation": "llm_beats_generation",
                                "stage_tag": stage_tag,
                                "speaker_pool": speaker_pool
                            }
                        )
                except Exception as e:
                    log("beats_generator", "error_log_save_failed", error=str(e))

            return self.create_fallback_beats(stage_context, speaker_pool)

    def create_fallback_beats(self, context: str, speaker_pool: list) -> List[Dict[str, Any]]:
        """
        LLM beats 생성 실패 시 기본 beats 반환

        Args:
            context: 현재 스테이지 context
            speaker_pool: 화자 풀

        Returns:
            Fallback beats
        """
        fallback_speaker = speaker_pool[0] if speaker_pool else "narr"

        return [
            {
                "goal": context,
                "speaker_hint": ["narr"],
            },
            {
                "goal": "상황을 파악하고 다음 행동을 결정한다.",
                "speaker_hint": [fallback_speaker],
            },
        ]


__all__ = ["BeatsGeneratorService"]
