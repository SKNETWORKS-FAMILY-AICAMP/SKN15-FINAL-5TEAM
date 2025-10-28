# ============================================================
# 🎭 StoryOrchestrator — Open Narrative용 LLM 기반 서사 생성
# ============================================================
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.utils.llm_client import get_llm_client
from src.utils.logger import log


class StoryOrchestrator:
    """
    Open Narrative 스테이지에서 유저 입력을 기반으로
    LLM이 즉흥적으로 사건/대사를 생성하고 state에 누적 저장하는 컴포넌트.
    """

    def __init__(self):
        self._llm = get_llm_client()

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

        # 최근 대화 히스토리 추출
        recent_history = self._extract_recent_history(state, limit=4)

        # LLM 프롬프트 구성
        system_prompt = self._build_system_prompt()
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

            return {
                "dialogues": dialogues,
                "state_update": state_update if isinstance(state_update, dict) else {},
            }

        except Exception as exc:
            log("story_orchestrator", f"❌ LLM call failed: {exc}")
            return self._create_fallback_response(context, speaker_pool)

    def _build_system_prompt(self) -> str:
        """Open Narrative용 시스템 프롬프트"""
        return """당신은 귀멸의 칼날 세계관의 서사 작가입니다.

당신의 역할:
1. 유저의 자유로운 입력을 받아 이야기를 즉흥적으로 전개합니다.
2. 등장인물들의 대사와 행동을 생생하게 묘사합니다.
3. 몰입감 있고 감정 중심의 서사를 만듭니다.
4. narr(내레이션)를 통해 장면과 감각을 묘사합니다.

규칙:
- 유저 입력에 반응하되, 이야기의 흐름을 자연스럽게 이어갑니다.
- 등장인물의 성격과 관계를 고려합니다.
- 대사는 2~4개 정도로 적절히 구성합니다.
- 내레이션(narr)으로 시작해 장면을 묘사하고, 캐릭터 대사로 이어갑니다.
- 유저에게 다음 행동을 자연스럽게 유도합니다.

출력 형식 (JSON):
{
  "dialogues": [
    {"speaker": "narr", "text": "장면 묘사..."},
    {"speaker": "tanjiro", "text": "대사..."}
  ],
  "state_update": {
    "story_summary": "지금까지 일어난 일의 요약",
    "important_event": "중요한 사건이나 변화"
  }
}"""

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

        prompt = f"""[현재 상황]
{context}

[지금까지의 이야기]
{story_summary if story_summary else "(이야기 시작)"}

[최근 대화]
{recent_history if recent_history else "(없음)"}

[유저 입력]
{user_input}

[현재 턴]
{turn_count + 1}턴째

[등장 가능한 인물]
{speakers_str}

---

위 정보를 바탕으로 다음을 수행하세요:

1. 유저의 입력({user_input})에 반응하는 자연스러운 대사와 장면을 생성하세요.
2. 이야기가 앞으로 전개되도록 사건을 진행하세요.
3. 캐릭터의 감정과 행동을 생생하게 묘사하세요.
4. narr(내레이션)로 시작해 분위기를 잡고, 등장인물의 대사로 이어가세요.
5. state_update에는 지금까지 일어난 일의 간단한 요약을 포함하세요.

JSON 형식으로 응답하세요:
{{
  "dialogues": [
    {{"speaker": "narr", "text": "..."}},
    {{"speaker": "character_name", "text": "..."}}
  ],
  "state_update": {{
    "story_summary": "지금까지 일어난 일 요약"
  }}
}}"""

        return prompt

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
