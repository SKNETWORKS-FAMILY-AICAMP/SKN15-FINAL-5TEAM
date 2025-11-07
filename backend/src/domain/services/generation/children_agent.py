# ============================================================
# 👧 자식 에이전트 — 캐릭터별 대사 생성 로직
# ============================================================
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from src.domain.models.conversation import Dialogue
from src.domain.models.story import Beat

from src.domain.services.orchestration import tone_profile_loader as dialogue_tools
from src.core.utils.llm_client import LLMClient
from src.core.config.config_loader import get_config_loader
import logging
from src.core.utils.tools.training_logger import log_agent
from src.core.interfaces.managers.session_manager import ISessionManager
from src.core.utils.logger import log

_PROMPTS = get_config_loader().get_prompts()
_CHILDREN_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("children") or {})
_CHILDREN_DIALOGUE_PROMPT = (_CHILDREN_PROMPTS.get("dialogue_generation") or "").strip()
_LLM_BEATS_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("llm_beats") or {})
_LLM_BEATS_SYSTEM = (_LLM_BEATS_PROMPTS.get("system") or "").strip()
_LLM_BEATS_USER = (_LLM_BEATS_PROMPTS.get("user") or "").strip()

if not _CHILDREN_DIALOGUE_PROMPT:
    raise ValueError("ChildrenAgent dialogue_generation prompt missing in configs/prompts.yaml (llm_prompts.children.dialogue_generation).")
if not _LLM_BEATS_SYSTEM or not _LLM_BEATS_USER:
    raise ValueError("LLM beats prompts missing in configs/prompts.yaml (llm_prompts.llm_beats.system/user).")

# ============================================================
# ============================================================

class ChildrenAgent:

    # ============================================================
    # 🛠️ 초기화
    # ============================================================
    def __init__(self, session_manager: Optional[ISessionManager] = None):
        """
        ChildrenAgent 초기화

        Args:
            session_manager: 세션 관리자 (DI)
        """
        self._llm = LLMClient()
        self._session_manager = session_manager

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

        dialogues = self._build_dialogues(ctx, state)

        # 생성된 대사 결과를 상태에 저장
        state["agent_responses"] = [d.to_dict() for d in dialogues] # Convert back to dict for state
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
    def _build_dialogues(self, ctx: Dict[str, Any], state: Dict[str, Any]) -> List[Dialogue]:

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
        prefetch_dialogues = self._render_dialogues(state, [Dialogue(speaker=entry.get("speaker"), content=entry.get("text"), emotion=entry.get("emotion")) for entry in prefetch_entries if isinstance(entry, dict)]) if prefetch_entries else []

        def merge_with_prefetch(dialogues: List[Dialogue]) -> List[Dialogue]:
            if not prefetch_dialogues:
                return dialogues
            # 사본을 만들어 원본 훼손 방지
            merged = []
            for item in prefetch_dialogues:
                merged.append(item) # item is already a Dialogue object
            for item in dialogues:
                merged.append(item)
            return merged

        llm_beats_enabled = ctx.get("llm_beats", False)

        if not beats and not llm_beats_enabled:
            fallback = (ctx.get("fallback") or {}).get("dialogues") or []
            if fallback:
                log("children", "⚙️ Using provided fallback dialogues (no beats)")
                return merge_with_prefetch(self._render_dialogues(state, [Dialogue(speaker=d.get("speaker"), content=d.get("text"), emotion=d.get("emotion")) for d in fallback]))

            log("children", "⚠️ No beats provided - cannot generate dialogue")
            return merge_with_prefetch([Dialogue(speaker="system", content="시나리오를 불러오는 중 문제가 발생했습니다. 다시 시도해주세요.")])

        if stage_type == "system_notice" or stage_tag == "OFF_TOPIC":
            log("children", f"⚙️ Bypassing LLM for {stage_type or stage_tag} - using fallback directly")

            # 폴백에 대사가 있으면 우선 사용
            fallback = ctx.get("fallback", {})
            if isinstance(fallback, dict):
                fallback_dialogues = fallback.get("dialogues", [])
                if fallback_dialogues:
                    log("children", f"✅ Using {len(fallback_dialogues)} fallback dialogues")
                    return merge_with_prefetch(self._render_dialogues(state, [Dialogue(speaker=d.get("speaker"), content=d.get("text"), emotion=d.get("emotion")) for d in fallback_dialogues]))

            log("children", f"✅ Using {len(beats)} beats as-is")
            normalized = self._normalize_dialogues(beats)
            return merge_with_prefetch(self._render_dialogues(state, normalized))

        if llm_beats_enabled:
            log("children", f"🎭 LLM Beats mode enabled for stage={stage_tag}")

            # 유저 입력이 있을 때만 LLM이 즉흥적으로 비트를 생성
            # 유저 입력이 없으면 캐릭터가 자율 대화를 이어가는 문제를 방지
            if not beats:
                latest_user_input = ctx.get("latest_user_input", "").strip()
                user_input = state.get("user_input", "").strip()

                if latest_user_input or user_input:
                    beats = self._generate_beats_from_context(state, ctx)
                    log("children", f"✨ Generated {len(beats)} beats via LLM based on user input")
                else:
                    log("children", "⚠️ LLM Beats mode: No user input detected, skipping auto-generation")
                    # 비트를 비워 폴백 메시지를 사용
        else:
            log("children", f"📋 Received {len(beats)} beats for stage={stage_tag}")
            for i, beat in enumerate(beats[:3]):  # 첫 3개만
                if isinstance(beat, Beat):
                    goal = beat.goal[:60] if beat.goal else ""
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
            conversation_summary=state.get("conversation_summary"),  # 🧠 장기기억
        )


        # -----------------------------
        # 4️⃣ LLM 호출 시도
        # -----------------------------
        try:
            system_prompt = _CHILDREN_DIALOGUE_PROMPT
            primary_temperature = self._llm.get_agent_setting("children", "temperature", 0.8)  # 0.65 → 0.8
            retry_temperature = self._llm.get_agent_setting("children", "retry_temperature", 1.0)  # 기본값 1.0
            max_tokens = self._llm.get_agent_setting("children", "max_tokens", 2000)

            # - 더 창의적이고 다양한 대사 생성
            # - 캐릭터별 개성이 더 잘 드러남
            # - 예측 가능한 패턴 감소
            response = self._llm.call_json(
                system_prompt=system_prompt,
                user_prompt=llm_prompt,
                temperature=primary_temperature,
                max_tokens=max_tokens,
                agent="children",
            )
            log("children", f"LLM raw response: {json.dumps(response, ensure_ascii=False)[:500]}")

            # ✅ LLM 응답 키 표준화 적용
            response = self._normalize_llm_output(response)

            # 표준화된 응답에서 dialogues 추출
            dialogue_payload = response.get("dialogues", [])

            # 1차 응답 검증
            if not isinstance(dialogue_payload, list) or not dialogue_payload:
                log("children", "⚠️ LLM response invalid or empty → retrying once")
                # - 첫 시도 실패 시 완전히 다른 접근 시도
                # - 동일한 실패 패턴 반복 방지
                # - 최대 다양성으로 성공 가능성 향상
                retry_resp = self._llm.call_json(
                    system_prompt=system_prompt,
                    user_prompt=llm_prompt,
                    temperature=retry_temperature,
                    max_tokens=max_tokens,
                    agent="children",
                )
                log("children", f"LLM retry response: {json.dumps(retry_resp, ensure_ascii=False)[:500]}")

                # ✅ LLM 응답 키 표준화 적용 (retry)
                retry_resp = self._normalize_llm_output(retry_resp)
                dialogue_payload = retry_resp.get("dialogues", [])

            if isinstance(dialogue_payload, list) and dialogue_payload:
                dialogues = self._normalize_dialogues(dialogue_payload)
                if dialogues:
                    log("children", f"✅ Generated {len(dialogues)} tone-aware dialogues.")
                    return merge_with_prefetch(self._render_dialogues(state, dialogues))

            log("children", f"⚠️ LLM invalid response → {type(response)} {response}")
        except Exception as exc:
            log("children", f"❌ LLM call failed: {exc}")

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
                                "stage_tag": ctx.get("stage_tag"),
                                "stage_type": ctx.get("stage_type"),
                                "speaker_pool": ctx.get("speaker_pool")
                            }
                        )
                except Exception as e:
                    log("children", "error_log_save_failed", error=str(e))

        # -----------------------------
        # -----------------------------
        log("children", "⚙️ Using beats fallback (no LLM response).")

        ctx.setdefault("fallback_count", 0)
        ctx["fallback_count"] += 1
        if ctx["fallback_count"] > 3:
            log("children", "❌ Too many fallback calls → forcing stage advance")
            state["stage_turn"] = int(state.get("stage_turn", 0) or 0) + 1
            state.setdefault("temp_data", {})["force_story_resume"] = True

        # 가 비어있으면 에러 메시지 반환
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

    def _render_dialogues(self, state: Dict[str, Any], entries: List[Dialogue]) -> List[Dialogue]:
        rendered: List[Dialogue] = []
        for entry in entries:
            if isinstance(entry.content, str):
                entry.content = self._render_text(state, entry.content)
            rendered.append(entry)
        return rendered

    def _extract_intro_narration(self, beats: List[Beat]) -> List[Dialogue]:
        for beat in beats:
            if not isinstance(beat, Beat):
                continue
            text = beat.text or beat.line or beat.goal
            if not text:
                continue
            speaker = beat.speaker
            hints = beat.speaker_hint or []
            fx = beat.fx
            if (speaker and speaker.lower() == "narr") or any(
                isinstance(h, str) and h.lower() == "narr" for h in hints
            ):
                dialogue = Dialogue(speaker="narr", content=text, fx=fx)
                return [dialogue]
        return []

    def _normalize_llm_output(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ LLM 응답 키 표준화 추가됨

        LLM이 반환하는 다양한 응답 구조를 표준 형식으로 변환:
        - {"dialogue": [...]} → {"dialogues": [...]}
        - {"scene": {"characters": {...}}} → {"dialogues": [...]}
        - {"character": "..."} → {"speaker": "..."}
        - {"line": "..."} → {"text": "..."}

        Args:
            llm_response: LLM 원본 응답 (dict)

        Returns:
            표준화된 응답 {"dialogues": [{"speaker": "...", "text": "..."}, ...]}
        """
        if not isinstance(llm_response, dict):
            return llm_response

        dialogues_list = []

        # 1️⃣ 표준 구조: {"dialogues": [...]}
        if "dialogues" in llm_response:
            dialogues_list = llm_response.get("dialogues", [])

        # 2️⃣ 단수 형태: {"dialogue": [...]}
        elif "dialogue" in llm_response:
            dialogue_data = llm_response.get("dialogue", [])
            if isinstance(dialogue_data, list):
                dialogues_list = dialogue_data
            elif isinstance(dialogue_data, dict):
                dialogues_list = [dialogue_data]

        # 3️⃣ Scene 구조: {"scene": {"characters": {"rengoku": {"dialogue": [...]}, ...}}}
        elif "scene" in llm_response:
            scene = llm_response.get("scene", {})
            if isinstance(scene, dict):
                # scene.characters 구조
                characters = scene.get("characters", {})
                if isinstance(characters, dict):
                    for speaker, char_data in characters.items():
                        if isinstance(char_data, dict) and "dialogue" in char_data:
                            char_dialogues = char_data.get("dialogue", [])
                            # dialogue가 리스트인 경우
                            if isinstance(char_dialogues, list):
                                for text in char_dialogues:
                                    if text:
                                        dialogues_list.append({
                                            "speaker": speaker,
                                            "text": text
                                        })
                            # dialogue가 문자열인 경우
                            elif isinstance(char_dialogues, str) and char_dialogues:
                                dialogues_list.append({
                                    "speaker": speaker,
                                    "text": char_dialogues
                                })

                # scene에 직접 dialogue 있는 경우
                if not dialogues_list and "dialogue" in scene:
                    scene_dialogue = scene.get("dialogue", [])
                    if isinstance(scene_dialogue, list):
                        dialogues_list = scene_dialogue

        # 4️⃣ Characters 구조: {"characters": {"rengoku": {"dialogue": [...]}, ...}}
        elif "characters" in llm_response:
            characters = llm_response.get("characters", {})
            if isinstance(characters, dict):
                for speaker, char_data in characters.items():
                    if isinstance(char_data, dict) and "dialogue" in char_data:
                        char_dialogues = char_data.get("dialogue", [])
                        if isinstance(char_dialogues, list):
                            for text in char_dialogues:
                                if text:
                                    dialogues_list.append({
                                        "speaker": speaker,
                                        "text": text
                                    })
                        elif isinstance(char_dialogues, str) and char_dialogues:
                            dialogues_list.append({
                                "speaker": speaker,
                                "text": char_dialogues
                            })

        # 필드명 표준화: character → speaker, line → text
        normalized_dialogues = []
        for item in dialogues_list:
            if not isinstance(item, dict):
                continue

            normalized_item = {
                "speaker": item.get("speaker") or item.get("character") or "narr",
                "text": item.get("text") or item.get("line") or ""
            }

            # 추가 필드 보존 (emotion, fx 등)
            if "emotion" in item:
                normalized_item["emotion"] = item["emotion"]
            if "fx" in item:
                normalized_item["fx"] = item["fx"]

            if normalized_item["text"]:
                normalized_dialogues.append(normalized_item)

        if normalized_dialogues:
            log("children", f"✅ Normalized LLM output ({len(normalized_dialogues)} items)")
            return {"dialogues": normalized_dialogues}

        # 변환 실패 시 원본 반환
        return llm_response

    def _normalize_text(self, text: Optional[str]) -> str:
        return (text or "").strip().lower()

    def _normalize_dialogues(self, entries: List[Any]) -> List[Dialogue]:
        normalized: List[Dialogue] = []
        for entry in entries:
            if isinstance(entry, dict):
                text = (
                    entry.get("text")
                    or entry.get("line")
                    or entry.get("goal")
                    or entry.get("description")
                )
                speaker = entry.get("speaker") or entry.get("character")
                if not speaker:
                    hints = entry.get("speaker_hint")
                    if isinstance(hints, list) and hints:
                        speaker = hints[0]

                # 🔥 에서 따옴표 안의 대사 추출 (더 자연스러운 대사를 위해)
                if not entry.get("text") and text:
                    text = self._extract_dialogue_from_goal(text, speaker or "narr")

                normalized.append(
                    Dialogue(
                        speaker=(speaker or "narr"),
                        content=text or json.dumps(entry, ensure_ascii=False),
                        emotion=entry.get("emotion"),
                        fx=entry.get("fx"),
                    )
                )
            else:
                normalized.append(Dialogue(speaker="narr", content=str(entry)))
        return normalized

    def _generate_beats_from_context(
        self,
        state: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> List[Beat]:
        """
        llm_beats=true일 때 context를 기반으로 LLM이 beats를 실시간 생성
        """
        stage_tag = ctx.get("stage_tag", "unknown")
        speaker_pool = ctx.get("speaker_pool", [])
        latest_user_input = ctx.get("latest_user_input", "")
        recent_dialogues = ctx.get("recent_dialogues", [])

        scenario_ref = state.get("scenario") or state.get("scenario_data") or {}
        stage_context = ""

        stages = scenario_ref.get("stages", [])
        for stage in stages:
            # 스테이지가 딕셔너리인지 확인 (문자열일 수도 있음)
            if isinstance(stage, dict) and stage.get("tag") == stage_tag:
                stage_context = stage.get("context", "")
                break

        if not stage_context:
            stage_context = f"현재 {stage_tag} 장면이 진행 중입니다."

        # 이전 스테이지 요약 추출
        previous_summary = state.get("state_update", {}).get("scene_summary", "")
        if not previous_summary:
            previous_summary = "(이전 장면 정보 없음)"

        # LLM 프롬프트 구성
        system_prompt = _LLM_BEATS_SYSTEM

        recent_history_str = "\n".join(recent_dialogues[-4:]) if recent_dialogues else "(없음)"

        user_prompt = _LLM_BEATS_USER.format(
            previous_stage_summary=previous_summary,
            stage_context=stage_context,
            recent_history=recent_history_str,
            latest_user_input=latest_user_input if latest_user_input else "(없음)",
            speaker_pool=", ".join(speaker_pool),
        )

        try:
            response = self._llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=1000,
            )

            if isinstance(response, list) and response:
                log("children", f"✅ Generated {len(response)} beats via LLM")
                return [Beat(**b) for b in response]
            elif isinstance(response, dict) and response.get("beats"):
                beats = response["beats"]
                if isinstance(beats, list):
                    return [Beat(**b) for b in beats]

            log("children", "⚠️ LLM beats generation returned invalid format")
            return self._create_fallback_beats(stage_context, speaker_pool)

        except Exception as exc:
            log("children", f"❌ LLM beats generation failed: {exc}")

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
                    log("children", "error_log_save_failed", error=str(e))

            return self._create_fallback_beats(stage_context, speaker_pool)

    def _create_fallback_beats(self, context: str, speaker_pool: list) -> List[Beat]:
        """LLM beats 생성 실패 시 기본 beats 반환"""
        fallback_speaker = speaker_pool[0] if speaker_pool else "narr"

        return [
            Beat(
                goal=context,
                speaker_hint=["narr"],
            ),
            Beat(
                goal="상황을 파악하고 다음 행동을 결정한다.",
                speaker_hint=[fallback_speaker],
            ),
        ]

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

            if speaker == "narr":
                # 【 】 안의 상황 태그 제거
                cleaned = re.sub(r"【[^】]+】\s*", "", goal)
                return cleaned.strip()

            return dialogue.strip()

        return goal

# ============================================================
# 🚀 모듈 수준 헬퍼
# ============================================================
DEFAULT_AGENT = ChildrenAgent()

def run_children_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    # 단계 4: 로그 수집 시작
    start_time = time.perf_counter()

    try:
        result = DEFAULT_AGENT.run(state)

        # 단계 4: 로그 수집 (성공)
        model_output = {
            "agent_responses": result.get("agent_responses", []),
            "has_more_dialogues": result.get("has_more_dialogues", False),
            "next_node": result.get("next_node"),
        }

        log_agent(
            agent_name="children",
            state=state,
            model_output=model_output,
            start_time=start_time,
            llm_model="gpt-4o-mini",  # Children Agent uses gpt-4o-mini (설정 기준)
        )

        try:
            from src.infrastructure.shared.dependency_container import get_session_manager

            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            session_id = state.get("session_id")

            if session_id:
                session_manager = get_session_manager()
                session_manager.save_performance_metric(
                    metric_name="children_agent_execution_time",
                    metric_value=execution_time_ms,
                    session_id=session_id,
                    metadata={
                        "dialogue_count": len(result.get("agent_responses", [])),
                        "has_more": result.get("has_more_dialogues", False),
                        "next_node": result.get("next_node")
                    }
                )
        except Exception as e:
            log("children", "performance_metric_save_failed", error=str(e))

        return result
    except Exception as e:
        # 단계 4: 로그 수집 (에러)
        log_agent(
            agent_name="children",
            state=state,
            model_output={"error": str(e)},
            start_time=start_time,
            is_error=True,
            error_message=str(e),
        )
        raise


__all__ = ["ChildrenAgent", "run_children_agent"]
