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

from src.core import scene_dialogue_tools as dialogue_tools
from src.utils.llm_client import get_llm_client
from src.utils.logger import log


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
        - state.children_ctx를 직접 사용 (parent_agent가 업데이트하는 값)
        - state.agent_inputs.children은 stale할 수 있으므로 사용하지 않음
        """
        # 🔧 수정: agent_inputs.children은 오래된 값일 수 있으므로 무시
        # parent_agent가 업데이트한 state.children_ctx만 사용
        ctx = state.get("children_ctx")

        if ctx:
            log("children", "✅ Using ctx from state.children_ctx")
        else:
            log("children", "⚠️ No children_ctx found in state")

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
        stage_type = ctx.get("stage_type")              # 스테이지 타입
        prefetch_entries = ctx.get("prefetch_dialogues") or []
        prefetch_dialogues = self._render_dialogues(state, [dict(entry) for entry in prefetch_entries if isinstance(entry, dict)]) if prefetch_entries else []

        def merge_with_prefetch(dialogues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            if not prefetch_dialogues:
                return dialogues
            # 사본을 만들어 원본 훼손 방지
            merged = []
            for item in prefetch_dialogues:
                merged.append(dict(item))
            for item in dialogues:
                merged.append(item)
            return merged

        # ⚠️ beats가 비어있으면 에러 반환 (LLM hallucination 방지)
        if not beats:
            fallback = (ctx.get("fallback") or {}).get("dialogues") or []
            if fallback:
                log("children", "⚙️ Using provided fallback dialogues (no beats)")
                return merge_with_prefetch(self._render_dialogues(state, fallback))

            log("children", "⚠️ No beats provided - cannot generate dialogue")
            return merge_with_prefetch([{
                "speaker": "system",
                "text": "시나리오를 불러오는 중 문제가 발생했습니다. 다시 시도해주세요."
            }])

        # 🔧 OFF_TOPIC이나 system_notice는 LLM 우회하고 fallback 직접 사용
        if stage_type == "system_notice" or stage_tag == "OFF_TOPIC":
            log("children", f"⚙️ Bypassing LLM for {stage_type or stage_tag} - using fallback directly")

            # fallback에 dialogues가 있으면 우선 사용
            fallback = ctx.get("fallback", {})
            if isinstance(fallback, dict):
                fallback_dialogues = fallback.get("dialogues", [])
                if fallback_dialogues:
                    log("children", f"✅ Using {len(fallback_dialogues)} fallback dialogues")
                    return merge_with_prefetch(self._render_dialogues(state, fallback_dialogues))

            # fallback이 없으면 beats 그대로 사용
            log("children", f"✅ Using {len(beats)} beats as-is")
            normalized = self._normalize_dialogues(beats)
            return merge_with_prefetch(self._render_dialogues(state, normalized))

        # 🔍 디버깅: 받은 beats 확인
        log("children", f"📋 Received {len(beats)} beats for stage={stage_tag}")
        for i, beat in enumerate(beats[:3]):  # 첫 3개만
            if isinstance(beat, dict):
                goal = beat.get("goal", "")[:60]
                log("children", f"  Beat[{i}]: {goal}...")

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
        speaker_pool = ctx.get("speaker_pool", [])

        # 🔧 speaker_pool에 있는 캐릭터만 tone_profile 로드
        filtered_character_refs = {}
        for char in speaker_pool:
            if char in character_refs:
                filtered_character_refs[char] = character_refs[char]

        tone_profiles = dialogue_tools.load_tone_profiles(filtered_character_refs, scenario_key)

        # -----------------------------
        # 3️⃣ LLM 프롬프트 생성
        # -----------------------------
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
            system_prompt = (
                "당신은 Demon Slayer 시나리오의 대사 생성기입니다.\n"
                "주어진 [상황 요약] beats를 정확히 따라 대사를 생성하세요.\n"
                "절대로 beats에 없는 장소, 상황, 캐릭터를 추가하지 마세요.\n"
                "goal 텍스트를 복사하지 말고 자연스러운 대사나 내레이션으로 재해석하세요.대사는 2~3줄로 풍부하게 표현하세요\n"
                "narr가 아닌 화자는 설명체 대신 캐릭터의 말만 하세요 (\"~라고 말한다\" 같은 서술 금지).\n"
                "narr만 장면 묘사와 효과음을 담당합니다."
            )
            if not system_prompt.strip():
                log("children", "⚠️ system_prompt missing - using default guardrail")
                system_prompt = "You generate in-character dialogue for a scripted scene."

            response = self._llm.call_json(
                system_prompt=system_prompt,
                user_prompt=llm_prompt,
                temperature=0.65,
                max_tokens=2000,
            )
            log("children", f"LLM raw response: {json.dumps(response, ensure_ascii=False)[:500]}")

            dialogue_payload = None
            if isinstance(response, dict):
                dialogue_payload = response.get("dialogues")

            # 1차 응답 검증
            if not isinstance(dialogue_payload, list) or not dialogue_payload:
                log("children", "⚠️ LLM response invalid or empty → retrying once")
                retry_resp = self._llm.call_json(
                    system_prompt=system_prompt,
                    user_prompt=llm_prompt,
                    temperature=0.9,
                    max_tokens=2000,
                )
                log("children", f"LLM retry response: {json.dumps(retry_resp, ensure_ascii=False)[:500]}")

                if isinstance(retry_resp, dict):
                    dialogue_payload = retry_resp.get("dialogues")

            if isinstance(dialogue_payload, list) and dialogue_payload:
                dialogues = self._normalize_dialogues(dialogue_payload)
                if dialogues:
                    log("children", f"✅ Generated {len(dialogues)} tone-aware dialogues.")
                    return merge_with_prefetch(self._render_dialogues(state, dialogues))

            log("children", f"⚠️ LLM invalid response → {type(response)} {response}")
        except Exception as exc:
            log("children", f"❌ LLM call failed: {exc}")

        # -----------------------------
        # 5️⃣ Fallback: beats 그대로 사용
        # -----------------------------
        log("children", "⚙️ Using beats fallback (no LLM response).")

        ctx.setdefault("fallback_count", 0)
        ctx["fallback_count"] += 1
        if ctx["fallback_count"] > 3:
            log("children", "❌ Too many fallback calls → forcing stage advance")
            state["stage_turn"] = int(state.get("stage_turn", 0) or 0) + 1
            state.setdefault("temp_data", {})["force_story_resume"] = True

        # beats가 비어있으면 에러 메시지 반환
        if not beats:
            log("children", "⚠️ No beats available for fallback")
            return merge_with_prefetch([{
                "speaker": "system",
                "text": "시나리오를 불러오는 중 문제가 발생했습니다. 다시 시도해주세요."
            }])

        fallback_dialogues = self._normalize_dialogues(beats)
        fallback = (ctx.get("fallback") or {}).get("dialogues") or []
        if fallback:
            log("children", "⚙️ Using provided fallback dialogues for this stage")
            fallback_dialogues = self._normalize_dialogues(fallback)
        return merge_with_prefetch(self._render_dialogues(state, fallback_dialogues))

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

    def _normalize_text(self, text: Optional[str]) -> str:
        return (text or "").strip().lower()

    def _normalize_dialogues(self, entries: List[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for entry in entries:
            if isinstance(entry, dict):
                text = (
                    entry.get("text")
                    or entry.get("line")
                    or entry.get("goal")
                    or entry.get("description")
                )
                speaker = entry.get("speaker")
                if not speaker:
                    hints = entry.get("speaker_hint")
                    if isinstance(hints, list) and hints:
                        speaker = hints[0]

                # 🔥 goal에서 따옴표 안의 대사 추출 (더 자연스러운 대사를 위해)
                if not entry.get("text") and text:
                    text = self._extract_dialogue_from_goal(text, speaker or "narr")

                normalized.append(
                    {
                        "speaker": (speaker or "narr"),
                        "text": text or json.dumps(entry, ensure_ascii=False),
                        "fx": entry.get("fx"),
                    }
                )
            else:
                normalized.append({"speaker": "narr", "text": str(entry)})
        return normalized

    def _extract_dialogue_from_goal(self, goal: str, speaker: str) -> str:
        """
        goal 텍스트에서 따옴표 안의 대사를 추출하여 자연스럽게 만듦
        예: "탄지로가 말한다. '이노스케! 지금은 싸움이 아니야!'"
            → "이노스케! 지금은 싸움이 아니야! 우리가 지금 해야 할 일은 렌고쿠 님을 돕는 거야!"
        """
        import re

        # 따옴표 안의 대사 찾기 (', ", 「」 모두 지원)
        quotes_pattern = r"['\"\「]([^'\"」]+)['\"\」]"
        matches = re.findall(quotes_pattern, goal)

        if matches:
            # 대사를 찾았으면 그것을 반환 (여러 개면 합침)
            dialogue = " ".join(matches)

            # narr(내레이션)인 경우 goal 전체 사용 (상황 묘사)
            if speaker == "narr":
                # 【 】 안의 상황 태그 제거
                cleaned = re.sub(r"【[^】]+】\s*", "", goal)
                return cleaned.strip()

            return dialogue.strip()

        # 대사를 못 찾았으면 goal 그대로 반환
        return goal

# ----------------------------------------------------------------------
# Module-level default instance (편의 함수)
# ----------------------------------------------------------------------
DEFAULT_AGENT = ChildrenAgent()

def run_children_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """외부에서 호출하는 엔트리 포인트 (ex. LangGraph 노드에서 사용)"""
    return DEFAULT_AGENT.run(state)


__all__ = ["ChildrenAgent", "run_children_agent"]
