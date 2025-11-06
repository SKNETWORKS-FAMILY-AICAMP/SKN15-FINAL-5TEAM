# ============================================================
# 🎭 StoryOrchestrator — Open Narrative용 LLM 기반 서사 생성
# ============================================================
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.utils.llm_client import get_llm_client
from src.utils.logger import log
from src.utils.config_loader import get_config_loader


class StoryOrchestrator:
    """
    Open Narrative 스테이지에서 유저 입력을 기반으로
    LLM이 즉흥적으로 사건/대사를 생성하고 state에 누적 저장하는 컴포넌트.
    """

    def __init__(self):
        self._llm = get_llm_client()
        config = get_config_loader()
        prompts = config.get_prompts()
        open_narrative_prompts = prompts.get("llm_prompts", {}).get("open_narrative", {})
        self._system_prompt_template = open_narrative_prompts.get("system", "")
        self._user_prompt_template = open_narrative_prompts.get("user", "")

        if not self._system_prompt_template or not self._user_prompt_template:
            raise ValueError("Open Narrative prompts missing in configs/prompts.yaml")

    def generate_narrative(
        self,
        state: Dict[str, Any],
        user_input: str,
        context: str,
        speaker_pool: List[str],
        turn_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Open Narrative 턴에서 LLM을 호출하여 대사 및 상태 업데이트를 생성.
        유저 입력을 받아서 LLM 호출 → 대사(dialogues) 생성 → state 업데이트까지 함.

        Args:
            state: 현재 게임 상태
            user_input: 유저의 자유 입력
            context: 현재 스테이지의 맥락 설명
            speaker_pool: 등장 가능한 캐릭터 리스트
            turn_count: 현재 턴 수

        Returns:
            {"dialogues": [...], "state_update": {...}}
        """
        story_summary = state.get("story_summary", "")
        world_state = state.get("world_state", {})

        # 🌍 world_context 로드
        world_context = self._load_world_context(state)

        # 🎭 tone_profiles 로드
        tone_profiles = self._load_tone_profiles(state, speaker_pool)

        # 최근 대화 히스토리 추출
        recent_history = self._extract_recent_history(state, limit=4)

        # LLM 프롬프트 구성
        system_prompt = self._build_system_prompt(
            world_context=world_context,
            tone_profiles=tone_profiles,
        )
        user_prompt = self._build_user_prompt(
            context=context,
            story_summary=story_summary,
            user_input=user_input,
            speaker_pool=speaker_pool,
            turn_count=turn_count,
            recent_history=recent_history,
            world_state=world_state,
        )

        try:
            response = self._llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                max_tokens=1500,
            )

            log("story_orchestrator", f"✅ Generated narrative response: {json.dumps(response, ensure_ascii=False)[:200]}...")

            # 응답 검증
            if not isinstance(response, dict):
                log("story_orchestrator", f"⚠️ Invalid response type: {type(response)}")
                return self._create_fallback_response(context, speaker_pool)

            dialogues = response.get("dialogues", [])
            state_update = response.get("state_update", {})

            if not isinstance(dialogues, list) or not dialogues:
                log("story_orchestrator", "⚠️ Empty or invalid dialogues")
                return self._create_fallback_response(context, speaker_pool)

            # 🔗 state_update를 state에 저장 (다음 스테이지로 전달하기 위함)
            if isinstance(state_update, dict) and state_update:
                state["previous_state_update"] = state_update
                log("story_orchestrator", f"💾 Saved state_update for next stage: {list(state_update.keys())}")

            return {
                "dialogues": dialogues,
                "state_update": state_update if isinstance(state_update, dict) else {},
            }

        except Exception as exc:
            log("story_orchestrator", f"❌ LLM call failed: {exc}")
            return self._create_fallback_response(context, speaker_pool)

    def _build_system_prompt(
        self,
        world_context: Optional[str] = None,
        tone_profiles: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Open Narrative용 시스템 프롬프트 생성

        Args:
            world_context: 세계관 정보
            tone_profiles: 캐릭터별 tone_profile 딕셔너리

        Returns:
            포맷팅된 시스템 프롬프트
        """
        # 🌍 world_context 섹션
        world_context_section = ""
        if world_context:
            world_context_section = f"\n\n### 세계관\n{world_context}"

        # 🎭 tone_profiles 섹션
        tone_profiles_section = ""
        if tone_profiles:
            tone_profiles_section = self._format_tone_profiles(tone_profiles)

        return self._system_prompt_template.format(
            world_context_section=world_context_section,
            tone_profiles_section=tone_profiles_section,
        )

    def _build_user_prompt(
        self,
        context: str,
        story_summary: str,
        user_input: str,
        speaker_pool: List[str],
        turn_count: int,
        recent_history: str,
        world_state: Dict[str, Any],
    ) -> str:
        """Open Narrative용 유저 프롬프트 생성"""
        speakers_str = ", ".join(speaker_pool) if speaker_pool else "narr, tanjiro"

        return self._user_prompt_template.format(
            context=context,
            story_summary=story_summary if story_summary else "(이야기 시작)",
            recent_history=recent_history if recent_history else "(없음)",
            user_input=user_input,
            turn_count=f"{turn_count + 1}",
            speaker_pool=speakers_str,
        )

    def _load_world_context(self, state: Dict[str, Any]) -> Optional[str]:
        """
        세계관 정보 로드

        Returns:
            world_context 문자열 (없으면 None)
        """
        try:
            from src.utils.world_loader import WorldLoader

            # scenario에서 world_id 가져오기
            scenario = state.get("scenario_data", {}) or state.get("scenario", {})
            world_id = scenario.get("world_id")

            if not world_id:
                log("story_orchestrator", "⚠️ No world_id in scenario")
                return None

            # WorldLoader로 world_context 로드
            world_context = WorldLoader.get_world_context(world_id)

            if world_context:
                log("story_orchestrator", f"🌍 Loaded world context: {world_id}")
                return world_context
            else:
                log("story_orchestrator", f"⚠️ Empty world_context for {world_id}")
                return None

        except Exception as e:
            log("story_orchestrator", f"⚠️ Failed to load world_context: {e}")
            return None

    def _load_tone_profiles(
        self,
        state: Dict[str, Any],
        speaker_pool: List[str],
    ) -> Dict[str, Any]:
        """
        speaker_pool에 있는 캐릭터들의 tone_profiles 로드

        Returns:
            { "char_id": { "tone": {...}, "relationships": {...} }, ... }
        """
        try:
            from src.core.scene_dialogue_tools import load_tone_profiles

            # scenario에서 character_refs 가져오기
            scenario = state.get("scenario_data", {}) or state.get("scenario", {})
            character_refs = scenario.get("character_refs", {})

            # speaker_pool에 해당하는 character_refs만 필터링
            filtered_refs = {}
            for char in speaker_pool:
                if char in character_refs:
                    filtered_refs[char] = character_refs[char]

            if not filtered_refs:
                log("story_orchestrator", "⚠️ No character_refs found for speaker_pool")
                return {}

            # scenario_key 추출
            metadata = scenario.get("metadata", {})
            tone_meta = metadata.get("tone", {})
            scenario_key = tone_meta.get("scenario_key")

            # load_tone_profiles 호출
            tone_profiles = load_tone_profiles(filtered_refs, scenario_key)

            if tone_profiles:
                log("story_orchestrator", f"🎭 Loaded tone profiles for {len(tone_profiles)} characters")
                return tone_profiles
            else:
                log("story_orchestrator", "⚠️ Failed to load tone profiles")
                return {}

        except Exception as e:
            log("story_orchestrator", f"⚠️ Exception loading tone profiles: {e}")
            return {}

    def _format_tone_profiles(self, tone_profiles: Dict[str, Any]) -> str:
        """
        tone_profiles를 프롬프트용 문자열로 포맷팅

        Args:
            tone_profiles: { "char_id": { "tone": {...}, "relationships": {...} }, ... }

        Returns:
            포맷팅된 문자열
        """
        if not tone_profiles:
            return ""

        lines = ["\n\n### 등장인물 및 말투"]

        for char_id, profile in tone_profiles.items():
            lines.append(f"\n**{char_id}**")

            # tone 정보
            tone_data = profile.get("tone", {})
            if isinstance(tone_data, dict):
                mid_tone = tone_data.get("mid", {})
                style = mid_tone.get("style", "")
                emotion = mid_tone.get("emotion", "")
                if style:
                    lines.append(f"- 말투: {style}")
                if emotion:
                    lines.append(f"- 감정: {emotion}")
            elif tone_data:
                lines.append(f"- 말투: {tone_data}")

            # relationships 정보
            relationships = profile.get("relationships", {})
            if relationships:
                lines.append("- 관계:")
                for target, info in relationships.items():
                    if isinstance(info, dict):
                        description = info.get("description", "")
                        rel_type = info.get("type", "")
                        if description:
                            lines.append(f"  * {target} ({rel_type}): {description}")

        return "\n".join(lines)

    def _extract_recent_history(self, state: Dict[str, Any], limit: int = 4) -> str:
        """최근 대화 히스토리를 문자열로 추출"""
        history_lines = []

        # message_history에서 추출
        message_history = state.get("message_history", [])
        if isinstance(message_history, list):
            for entry in message_history[-limit:]:
                if not isinstance(entry, dict):
                    continue
                speaker = entry.get("speaker", "unknown")
                text = entry.get("text", "")
                if text:
                    history_lines.append(f"{speaker}: {text}")

        # output dialogues에서 추출
        output_dialogues = (state.get("output") or {}).get("dialogues", [])
        if isinstance(output_dialogues, list):
            for dialogue in output_dialogues[-limit:]:
                if not isinstance(dialogue, dict):
                    continue
                speaker = dialogue.get("speaker", "unknown")
                text = dialogue.get("text", "")
                if text:
                    history_lines.append(f"{speaker}: {text}")

        return "\n".join(history_lines[-limit:]) if history_lines else ""

    def _create_fallback_response(
        self,
        context: str,
        speaker_pool: List[str],
    ) -> Dict[str, Any]:
        """LLM 실패 시 기본 응답 생성"""
        fallback_speaker = speaker_pool[0] if speaker_pool else "narr"

        return {
            "dialogues": [
                {
                    "speaker": "narr",
                    "text": context,
                },
                {
                    "speaker": fallback_speaker,
                    "text": "무슨 일이 일어날지 예측할 수 없다. 조심스럽게 나아가자.",
                },
            ],
            "state_update": {
                "story_summary": context,
            },
        }


# ============================================================
# 🚀 모듈 수준 인스턴스
# ============================================================
_DEFAULT_ORCHESTRATOR = None


def get_story_orchestrator() -> StoryOrchestrator:
    """Story Orchestrator 싱글톤 인스턴스 반환"""
    global _DEFAULT_ORCHESTRATOR
    if _DEFAULT_ORCHESTRATOR is None:
        _DEFAULT_ORCHESTRATOR = StoryOrchestrator()
    return _DEFAULT_ORCHESTRATOR


__all__ = ["StoryOrchestrator", "get_story_orchestrator"]
