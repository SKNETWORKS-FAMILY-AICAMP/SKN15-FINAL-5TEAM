'''ParentAgent
 └── children_ctx 전달
       ├─ stage_tag
       ├─ beats
       └─ character_refs (tone 파일 경로)
          ↓
ChildrenAgent
 ├─ SceneDialogueTools.load_tone_profiles()
 ├─ SceneDialogueTools.compose_llm_prompt()
 ├─ LLM 호출 → tone 반영된 대사 JSON 생성
 └─ 실패 시 beats fallback'''

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.utils.llm_client import get_llm_client     # OpenAI 또는 커스텀 LLM 클라이언트
from src.core import scene_dialogue_tools as dialogue_tools  # 새로 만든 tone/profile 유틸
from .utils.logger import log                        # 로깅 유틸


class ChildrenAgent:
    """
    ChildrenAgent - LLM을 사용해 실제 대사(dialogue)를 생성하는 핵심 클래스.

    🎯 주요 역할:
    - ParentAgent가 넘긴 children_ctx를 받아서
      → tone_profiles (캐릭터 말투)
      → beats (상황 가이드)
      → stage_tag (현재 스테이지명)
      정보를 종합한 뒤 LLM에 프롬프트를 보냄.
    - LLM이 생성한 대사를 JSON으로 받아서 반환.
    - LLM 실패 시 beats를 그대로 출력하여 fallback 작동.
    """

    def __init__(self):
        """LLM 클라이언트 초기화"""
        self._llm = get_llm_client()

    # ----------------------------------------------------------------------
    # Public Entry
    # ----------------------------------------------------------------------
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        ChildrenAgent의 메인 엔트리 포인트.
        ParentAgent → children_ctx를 넘겨주면,
        여기서 실제 대사 리스트(agent_responses)를 생성한다.
        """
        ctx = self._extract_context(state)

        # 컨텍스트가 없으면 빈 응답 처리
        if not ctx:
            log("children", "Missing children_ctx; emitting empty response")
            state["agent_responses"] = []
            state["has_more_dialogues"] = False
            state["next_node"] = "dialogue_agent"
            return state

        # ✅ 대사 생성 (LLM or fallback)
        dialogues = self._build_dialogues(ctx, state)

        # 생성된 대사 결과를 state에 저장
        state["agent_responses"] = dialogues
        state["has_more_dialogues"] = False
        state["next_node"] = "dialogue_agent"

        return state

    # ----------------------------------------------------------------------
    # Internal Helpers
    # ----------------------------------------------------------------------
    def _extract_context(self, state: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        children_ctx를 추출하는 함수.
        - state.agent_inputs.children → 우선
        - state.children_ctx → fallback
        """
        agent_inputs = state.get("agent_inputs") or {}
        ctx = agent_inputs.get("children") or state.get("children_ctx")
        return ctx if isinstance(ctx, dict) else None

    def _render_text(self, state: Dict[str, Any], text: str) -> str:
        """텍스트 내의 플레이어 이름, 변수 등을 실제 값으로 치환"""
        user_name = (
            state.get("user_name")
            or (state.get("temp_data") or {}).get("user_name")
            or "츠구코"  # 디폴트 이름 (없을 경우)
        )

        replacements = {
            "{user}": user_name,
            "{user_name}": user_name,
            "{{user}}": user_name,
        }

        result = text
        for token, value in replacements.items():
            result = result.replace(token, value)
        return result

    # ----------------------------------------------------------------------
    # Core Dialogue Builder
    # ----------------------------------------------------------------------
    def _build_dialogues(self, ctx: Dict[str, Any], state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        핵심 로직:
        1️⃣ ParentAgent가 전달한 children_ctx에서
            - character_refs
            - beats
            - stage_tag
        를 추출.
        2️⃣ SceneDialogueTools를 통해 tone_profiles 로드 및 llm_prompt 생성.
        3️⃣ LLM 호출하여 tone-aware 대사 생성.
        4️⃣ 실패 시 beats 그대로 fallback.
        """

        # -----------------------------
        # 1️⃣ 컨텍스트 추출
        # -----------------------------
        character_refs = ctx.get("character_refs", {})  # 캐릭터 JSON 경로들
        beats = ctx.get("beats") or []                  # 시나리오 내 상황 묘사 텍스트
        stage_tag = ctx.get("stage_tag")                # 현재 스테이지명

        # ✅ (추가) 시나리오 키 감지
        scenario_id = state.get("scenario_id") or ctx.get("scenario_id")
        scenario_key = None
        if scenario_id:
            if "cutscene5" in str(scenario_id).lower():
                scenario_key = "mugen_train"
            elif "cutscene6" in str(scenario_id).lower():
                scenario_key = "final_battle"
            # 나중에 다른 스토리 확장 시 elif로 추가

        # -----------------------------
        # 2️⃣ 캐릭터 톤 + 관계 로드
        # -----------------------------
        tone_profiles = dialogue_tools.load_tone_profiles(character_refs, scenario_key)

        # -----------------------------
        # 3️⃣ LLM 프롬프트 생성
        # -----------------------------
        speaker_pool = ctx.get("speaker_pool", [])
        llm_prompt = dialogue_tools.compose_llm_prompt(
            stage_tag=stage_tag,
            beats=beats,
            tone_profiles=tone_profiles,
            speaker_pool=speaker_pool
        )


        # -----------------------------
        # 4️⃣ LLM 호출 시도
        # -----------------------------
        try:
            response = self._llm.call_json(
                system_prompt="당신은 Demon Slayer 시나리오의 대사 생성기입니다.",
                user_prompt=llm_prompt,
                temperature=0.65,
                max_tokens=700,
            )

            # 응답이 정상적일 경우
            if isinstance(response, dict) and "dialogues" in response:
                dialogues = response["dialogues"]
                if isinstance(dialogues, list):
                    if not self._contains_narration(dialogues):
                        narration = self._extract_intro_narration(beats)
                        if narration:
                            log("codex_fix", "Prepending intro narration to LLM output")
                            dialogues = narration + dialogues
                    log("children", f"✅ Generated {len(dialogues)} tone-aware dialogues.")
                    return self._render_dialogues(state, dialogues)

            # 예상 포맷이 아닐 경우
            log("children", f"⚠️ Unexpected LLM response: {type(response)}")
        except Exception as exc:
            # LLM 호출 실패 (네트워크 / 포맷 오류 등)
            log("children", f"❌ LLM call failed: {exc}")

        # -----------------------------
        # 5️⃣ Fallback: beats 그대로 사용
        # -----------------------------
        log("children", "⚙️ Using beats fallback (no LLM response).")
        fallback_dialogues = [
            {
                "speaker": b.get("speaker", "narr"),
                "text": b.get("text") or b.get("line") or str(b)
            }
            for b in beats
        ]
        return self._render_dialogues(state, fallback_dialogues)

    def _render_dialogues(self, state: Dict[str, Any], entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rendered: List[Dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            text = entry.get("text")
            if isinstance(text, str):
                entry["text"] = self._render_text(state, text)
            rendered.append(entry)
        return rendered

    def _contains_narration(self, dialogues: List[Dict[str, Any]]) -> bool:
        for entry in dialogues:
            if isinstance(entry, dict) and str(entry.get("speaker", "")).lower() == "narr":
                return True
        return False

    def _extract_intro_narration(self, beats: List[Any]) -> List[Dict[str, Any]]:
        for beat in beats:
            if not isinstance(beat, dict):
                continue
            text = beat.get("text") or beat.get("line") or beat.get("goal")
            if not text:
                continue
            speaker = beat.get("speaker")
            hints = beat.get("speaker_hint") or []
            fx = beat.get("fx")
            if (speaker and speaker.lower() == "narr") or any(
                isinstance(h, str) and h.lower() == "narr" for h in hints
            ):
                dialogue = {"speaker": "narr", "text": text}
                if fx:
                    dialogue["fx"] = fx
                return [dialogue]
        return []

# ----------------------------------------------------------------------
# Module-level default instance (편의 함수)
# ----------------------------------------------------------------------
DEFAULT_AGENT = ChildrenAgent()

def run_children_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """외부에서 호출하는 엔트리 포인트 (ex. LangGraph 노드에서 사용)"""
    return DEFAULT_AGENT.run(state)


__all__ = ["ChildrenAgent", "run_children_agent"]
