from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.core import scene_dialogue_tools as dialogue_tools
from src.utils.llm_client import get_llm_client
from src.utils.logger import log

# ============================================================
# 🎭 ChildrenAgent — parent가 넘겨준 children_ctx로 실제 대사를 생성
# ============================================================

class ChildrenAgent:

    # ============================================================
    # 🛠️ 초기화
    # ============================================================
    def __init__(self):
        """LLM 클라이언트 초기화"""
        self._llm = get_llm_client()

    # ============================================================
    # 🚦 실행 엔트리 포인트
    # ============================================================
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

    # ============================================================
    # 🔧 내부 헬퍼
    # ============================================================
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

    # ============================================================
    # 💬 대사 생성
    # ============================================================
    def _build_dialogues(self, ctx: Dict[str, Any], state: Dict[str, Any]) -> List[Dict[str, Any]]:

        # -----------------------------
        # 1️⃣ 컨텍스트 추출
        # -----------------------------
        character_refs = ctx.get("character_refs", {})  # 캐릭터 JSON 경로들
        beats = ctx.get("beats") or []                  # 시나리오 내 상황 묘사 텍스트
        stage_tag = ctx.get("stage_tag")                # 현재 스테이지명
        stage_type = ctx.get("stage_type")              # 스테이지 타입
        stage_objective = ctx.get("stage_objective")
        intent_options = ctx.get("intent_options")
        latest_user_input = ctx.get("latest_user_input")
        recent_dialogues = ctx.get("recent_dialogues")
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
        scenario_ref = state.get("scenario") or state.get("scenario_data") or {}
        metadata = scenario_ref.get("metadata") if isinstance(scenario_ref, dict) else {}
        tone_meta = metadata.get("tone") or {}
        scenario_key = tone_meta.get("scenario_key")

        # -----------------------------
        # 2️⃣ 캐릭터 톤 + 관계 로드
        # -----------------------------
        speaker_pool = ctx.get("speaker_pool", [])
        context_summary = ctx.get("context_summary")

        # 🔧 speaker_pool에 있는 캐릭터만 tone_profile 로드
        filtered_character_refs = {}
        for char in speaker_pool:
            if char in character_refs:
                filtered_character_refs[char] = character_refs[char]

        tone_profiles = dialogue_tools.load_tone_profiles(filtered_character_refs, scenario_key)

        # -----------------------------
        # 3️⃣ LLM 프롬프트 생성
        # -----------------------------
        stage_turn = int(state.get("stage_turn", 0) or 0)
        llm_prompt = dialogue_tools.compose_llm_prompt(
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
        )


        # -----------------------------
        # 4️⃣ LLM 호출 시도
        # -----------------------------
        try:
            system_prompt = (
                "당신은 귀멸의 칼날 시나리오의 대사 작가이자 편집자입니다.\n"
                "주어진 [상황 요약] beats는 장면의 목표일 뿐이므로, 그 문장을 반복하거나 따옴표 안의 문장을 그대로 쓰면 안 됩니다.\n"
                "각 beat의 의미를 해석해 캐릭터가 실제로 말하거나 느낄 법한 자연스러운 대사를 2~3문장으로 새롭게 작성하세요.\n"
                "goal에 나온 단어, 문장, 말투, 따옴표, 감탄사를 그대로 복사하거나 부분 발췌하지 말고, 동의어·비유·감정을 활용해 재구성하세요.\n"
                "[이전 턴 요약]에 있는 사용자 입력과 직전 대사에 반드시 반응하고, 같은 말을 반복하지 말며 이야기와 감정을 앞으로 전개하세요.\n"
                "사용자가 한 질문이나 요청이 있다면 직접적으로 답하거나 행동으로 보여주세요.\n"
                "narr는 장면 묘사와 감각을 서술하되 다른 인물의 대사를 대신하지 않습니다.\n"
                "캐릭터 화자는 설명체 대신 말투와 감정을 살린 직접 화법으로 대사만 말합니다 (\"~라고 말한다\" 등 금지).\n"
                "가능하다면 마지막 발화(또는 내레이션)에서 플레이어가 다음 행동을 취하도록 자연스럽게 촉구하거나, 현재 스테이지 목표/선택지를 상기시키세요.\n"
                "출력은 반드시 JSON 객체 하나로 응답하고, 구조는 {\"dialogues\": [...]} 형식을 지키세요.\n"
                "캐릭터의 말투·관계는 tone_profile과 상황을 준수하고, narr는 beats에 나온 감각/효과음을 활용해 생생하게 묘사하세요."
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

# ============================================================
# 🚀 모듈 수준 헬퍼
# ============================================================
DEFAULT_AGENT = ChildrenAgent()

def run_children_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    return DEFAULT_AGENT.run(state)


__all__ = ["ChildrenAgent", "run_children_agent"]
