from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from src.core import scene_dialogue_tools as dialogue_tools
from src.utils.llm_client import get_llm_client
from src.utils.logger import log
from src.utils.config_loader import get_config_loader
from src.tools.training_logger import log_agent
from src.database.session_manager import HybridSessionManager

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
# 🎭 ChildrenAgent — parent가 넘겨준 children_ctx로 실제 대사를 생성
# ============================================================

class ChildrenAgent:

    # ============================================================
    # 🛠️ 초기화
    # ============================================================
    def __init__(self):
        """LLM 클라이언트 초기화"""
        self._llm = get_llm_client()
        self._session_manager: Optional[HybridSessionManager] = None

        # Initialize session manager for error logging
        try:
            from src.database.db_manager import DatabaseManager
            db = DatabaseManager()
            self._session_manager = HybridSessionManager(db_manager=db)
        except Exception as e:
            log("children", "session_manager_init_failed", error=str(e))

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

        # 🎯 Brief response mode 체크 (Pre-transition user response)
        brief_mode = state.get("brief_response_mode", False)
        if brief_mode:
            log("children", "🎯 Brief response mode: generating short response to user input")
            return self._generate_brief_user_response(ctx, state)

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
        stage_context = ctx.get("stage_context")        # 장면 설정 (새 장면 전환 시)
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
        # 단, llm_beats=true인 경우는 LLM이 beats를 실시간 생성
        llm_beats_enabled = ctx.get("llm_beats", False)

        if not beats and not llm_beats_enabled:
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
        if llm_beats_enabled:
            log("children", f"🎭 LLM Beats mode enabled for stage={stage_tag}")

            # beats 자동 생성 조건:
            # 1. 유저 입력이 있을 때
            # 2. 장면 첫 진입 시 (stage_turn == 0)
            if not beats:
                latest_user_input = ctx.get("latest_user_input", "").strip()
                user_input = state.get("user_input", "").strip()
                stage_turn = int(state.get("stage_turn", 0) or 0)

                # 유저 입력이 있거나, 장면 첫 진입인 경우 beats 생성
                should_generate = (latest_user_input or user_input) or (stage_turn == 0)

                if should_generate:
                    # context를 기반으로 beats 생성 프롬프트를 만듦
                    beats = self._generate_beats_from_context(state, ctx)
                    if stage_turn == 0:
                        log("children", f"✨ Generated {len(beats)} beats via LLM (first entry)")
                    else:
                        log("children", f"✨ Generated {len(beats)} beats via LLM (user input)")
                else:
                    # 유저 입력도 없고 첫 진입도 아니면 beats 생성하지 않음
                    log("children", "⚠️ LLM Beats mode: No user input and not first entry, skipping auto-generation")
                    # beats를 비워서 fallback 메시지 사용
        else:
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

        # 🌍 세계관 정보 로드
        world_id = scenario_ref.get("world_id") if isinstance(scenario_ref, dict) else None
        world_context = None
        if world_id:
            try:
                world_context = WorldLoader.get_world_context(world_id)
                if world_context:
                    log("children", f"🌍 Loaded world context: {world_id}")
            except Exception as e:
                log("children", f"⚠️ Failed to load world {world_id}: {e}")

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
            stage_context=stage_context if isinstance(stage_context, str) else None,
            world_context=world_context if isinstance(world_context, str) else None,
        )


        # -----------------------------
        # 4️⃣ LLM 호출 시도
        # -----------------------------
        try:
            # Phase 2 개선: yaml 기반 설정 + 개선된 기본값
            system_prompt = _CHILDREN_DIALOGUE_PROMPT
            primary_temperature = self._llm.get_agent_setting("children", "temperature", 0.8)  # 0.65 → 0.8
            retry_temperature = self._llm.get_agent_setting("children", "retry_temperature", 1.0)  # 기본값 1.0
            max_tokens = self._llm.get_agent_setting("children", "max_tokens", 2000)

            # Phase 2 개선: Temperature 상향 (0.65 → 0.8)
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

            # 🛑 플레이어 speaker 제거 (후처리)
            response_text = json.dumps(response, ensure_ascii=False)
            response_text = self._remove_player_speakers(state, response_text)
            response = json.loads(response_text)

            dialogue_payload = None
            if isinstance(response, dict):
                dialogue_payload = response.get("dialogues")

            # 1차 응답 검증
            if not isinstance(dialogue_payload, list) or not dialogue_payload:
                log("children", "⚠️ LLM response invalid or empty → retrying once")
                # Phase 2 개선: Retry Temperature 상향 (0.9 → 1.0)
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

                # 🛑 플레이어 speaker 제거 (후처리)
                retry_text = json.dumps(retry_resp, ensure_ascii=False)
                retry_text = self._remove_player_speakers(state, retry_text)
                retry_resp = json.loads(retry_text)

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
        """
        대화 항목을 정규화하고 플레이어 speaker를 필터링
        """
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

                # 🛑 플레이어 speaker 필터링 (normalize 단계에서도 체크)
                # JSON 필터를 통과했더라도 beats/fallback에서 올 수 있음
                final_speaker = speaker or "narr"
                if self._is_player_speaker(final_speaker):
                    log("children", f"❌ Filtering player speaker in normalize: '{final_speaker}' → 'narr'")
                    final_speaker = "narr"

                normalized.append(
                    {
                        "speaker": final_speaker,
                        "text": text or json.dumps(entry, ensure_ascii=False),
                        "fx": entry.get("fx"),
                    }
                )
            else:
                normalized.append({"speaker": "narr", "text": str(entry)})
        return normalized

    def _generate_beats_from_context(
        self,
        state: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        llm_beats=true일 때 context를 기반으로 LLM이 beats를 실시간 생성
        """
        stage_tag = ctx.get("stage_tag", "unknown")
        speaker_pool = ctx.get("speaker_pool", [])
        latest_user_input = ctx.get("latest_user_input", "")
        recent_dialogues = ctx.get("recent_dialogues", [])

        # 시나리오 context 추출
        scenario_ref = state.get("scenario") or state.get("scenario_data") or {}

        # 디버깅: scenario_ref 타입 확인
        if not isinstance(scenario_ref, dict):
            log("children", f"⚠️ scenario_ref is not dict: type={type(scenario_ref)}")
            scenario_ref = {}

        stage_context = ""

        # 현재 스테이지의 context 찾기
        stages = scenario_ref.get("stages", [])
        if isinstance(stages, list):
            for stage in stages:
                if isinstance(stage, dict) and stage.get("tag") == stage_tag:
                    stage_context = stage.get("context", "")
                    break

        if not stage_context:
            stage_context = f"현재 {stage_tag} 장면이 진행 중입니다."

        # 🔄 이전 스테이지 요약 가져오기 (맥락 연결용)
        previous_stage_summary = state.get("story_summary", "")
        if not previous_stage_summary:
            previous_stage_summary = "(이전 장면 없음)"

        # LLM 프롬프트 구성
        system_prompt = _LLM_BEATS_SYSTEM

        recent_history_str = "\n".join(recent_dialogues[-4:]) if recent_dialogues else "(없음)"

        user_prompt = _LLM_BEATS_USER.format(
            stage_context=stage_context,
            recent_history=recent_history_str,
            latest_user_input=latest_user_input if latest_user_input else "(없음)",
            speaker_pool=", ".join(speaker_pool),
            previous_stage_summary=previous_stage_summary,
        )

        try:
            response = self._llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=1000,
            )

            # 🔧 Double-encoded JSON 처리
            # LLM이 JSON 문자열로 반환하는 경우 (이중 인코딩) 파싱
            if isinstance(response, str):
                try:
                    import json
                    response = json.loads(response)
                    log("children", "🔧 Parsed double-encoded JSON response")
                except json.JSONDecodeError:
                    log("children", "⚠️ Response is string but not valid JSON")
                    return self._create_fallback_beats(stage_context, speaker_pool)

            # 📋 Case 1: 직접 list 반환 (예: [{"goal": "..."}, ...])
            if isinstance(response, list) and response:
                # ✅ 각 beat 검증
                validated_beats = self._validate_beats(response, stage_context, speaker_pool)
                if validated_beats:
                    log("children", f"✅ Generated {len(validated_beats)} beats via LLM")
                    return validated_beats
                else:
                    log("children", "⚠️ All beats failed validation")
                    return self._create_fallback_beats(stage_context, speaker_pool)

            # 📋 Case 2: dict 반환
            elif isinstance(response, dict):
                # Case 2-1: {"beats": [...]} 형태
                beats = response.get("beats")

                # beats가 문자열인 경우 (이중 인코딩)
                if isinstance(beats, str):
                    try:
                        import json
                        beats = json.loads(beats)
                        log("children", "🔧 Parsed double-encoded beats field")
                    except json.JSONDecodeError:
                        log("children", "⚠️ beats field is string but not valid JSON")
                        return self._create_fallback_beats(stage_context, speaker_pool)

                # beats가 list인 경우
                if isinstance(beats, list):
                    validated_beats = self._validate_beats(beats, stage_context, speaker_pool)
                    if validated_beats:
                        log("children", f"✅ Generated {len(validated_beats)} beats via LLM")
                        return validated_beats

                # Case 2-2: 단일 beat dict (예: {"goal": "...", "speaker_hint": [...]})
                if "goal" in response:
                    log("children", "🔧 Single beat dict detected, converting to list")
                    validated_beats = self._validate_beats([response], stage_context, speaker_pool)
                    if validated_beats:
                        log("children", f"✅ Generated {len(validated_beats)} beats via LLM (single dict)")
                        return validated_beats

            log("children", "⚠️ LLM beats generation returned invalid format")
            return self._create_fallback_beats(stage_context, speaker_pool)

        except Exception as exc:
            log("children", f"❌ LLM beats generation failed: {exc}")
            import traceback
            log("children", f"Traceback: {traceback.format_exc()}")
            return self._create_fallback_beats(stage_context, speaker_pool)

    def _validate_beats(
        self,
        beats: List[Any],
        stage_context: str,
        speaker_pool: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Beats 리스트 검증 및 정리

        Args:
            beats: 검증할 beats 리스트
            stage_context: 현재 스테이지 컨텍스트 (fallback용)
            speaker_pool: 사용 가능한 speaker 리스트 (fallback용)

        Returns:
            검증된 beats 리스트 (빈 리스트면 모두 실패)
        """
        validated = []

        for i, beat in enumerate(beats):
            # beat가 dict가 아니면 스킵
            if not isinstance(beat, dict):
                log("children", f"⚠️ Beat[{i}] is not dict: {type(beat)}")
                continue

            # "goal" 키가 없으면 스킵
            if "goal" not in beat:
                log("children", f"⚠️ Beat[{i}] missing 'goal' key: {beat}")
                continue

            # goal이 빈 문자열이면 스킵
            goal = beat.get("goal", "").strip()
            if not goal:
                log("children", f"⚠️ Beat[{i}] has empty 'goal'")
                continue

            # speaker_hint가 없으면 기본값 설정
            if "speaker_hint" not in beat:
                beat["speaker_hint"] = ["narr"]
                log("children", f"🔧 Beat[{i}] missing 'speaker_hint', defaulting to ['narr']")

            # speaker_hint가 리스트가 아니면 변환
            if not isinstance(beat["speaker_hint"], list):
                beat["speaker_hint"] = [str(beat["speaker_hint"])]
                log("children", f"🔧 Beat[{i}] speaker_hint not list, converting")

            validated.append(beat)

        return validated

    def _create_fallback_beats(self, context: str, speaker_pool: list) -> List[Dict[str, Any]]:
        """LLM beats 생성 실패 시 기본 beats 반환"""
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
    # 🎯 Brief User Response (Pre-Transition)
    # ============================================================
    def _generate_brief_user_response(
        self,
        ctx: Dict[str, Any],
        state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        유저 입력에 대한 짧은 응답 생성 (1~2줄)

        Stage 전환 직전에 유저 발화를 무시하지 않기 위한 서브플로우

        Returns:
            짧은 응답 대사 리스트 (최대 2개)
        """
        user_input = state.get("user_input", "").strip()
        if not user_input:
            log("children", "⚠️ Brief mode but no user input")
            return []

        speaker_pool = ctx.get("speaker_pool", [])
        character_refs = ctx.get("character_refs", {})

        # speaker_pool에서 가장 적절한 응답자 선택
        responder = self._select_responder_for_user_input(user_input, speaker_pool, character_refs)

        log("children", f"🎯 Selected responder: {responder} for user input: '{user_input[:30]}...'")

        # Tone profile 로드
        scenario_ref = state.get("scenario") or state.get("scenario_data") or {}
        metadata = scenario_ref.get("metadata") if isinstance(scenario_ref, dict) else {}
        tone_meta = metadata.get("tone") or {}
        scenario_key = tone_meta.get("scenario_key")

        tone_profiles = {}
        if responder and responder in character_refs:
            from src.core.scene_dialogue_tools import load_tone_profiles
            tone_profiles = load_tone_profiles({responder: character_refs[responder]}, scenario_key)

        tone_profile = tone_profiles.get(responder, {}) if tone_profiles else {}
        tone_data = tone_profile.get("tone", {})

        # Tone 정보 추출
        if isinstance(tone_data, dict):
            mid_tone = tone_data.get("mid", {})
            tone_style = mid_tone.get("style", "자연스러운 말투")
        else:
            tone_style = str(tone_data) if tone_data else "자연스러운 말투"

        # 간단한 응답 프롬프트
        system_prompt = f"""당신은 '{responder}' 캐릭터입니다.
말투: {tone_style}

유저의 발화에 1~2문장으로 짧고 자연스럽게 반응하세요.
JSON 형식으로 응답하세요."""

        user_prompt = f"""유저: "{user_input}"

위 유저 발화에 {responder} 캐릭터로서 짧게 반응하세요.

출력 형식:
{{"speaker": "{responder}", "text": "응답 내용"}}"""

        try:
            response = self._llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=150,
            )

            # 응답 검증
            if isinstance(response, dict) and "speaker" in response and "text" in response:
                log("children", f"✅ Generated brief response from {response.get('speaker')}")
                return [response]
            else:
                log("children", f"⚠️ Invalid brief response format: {response}")
                return []

        except Exception as e:
            log("children", f"❌ Brief response generation failed: {e}")
            return []

    def _select_responder_for_user_input(
        self,
        user_input: str,
        speaker_pool: List[str],
        character_refs: Dict[str, str],
    ) -> str:
        """
        유저 입력에 가장 적절한 응답자 선택

        간단한 휴리스틱:
        1. 유저가 특정 캐릭터 이름 언급하면 그 캐릭터
        2. 없으면 speaker_pool 첫 번째 (narr 제외)
        """
        # 캐릭터 이름 매핑 (일반적인 호칭)
        name_mapping = {
            "렌고쿠": "rengoku",
            "탄지로": "tanjiro",
            "젠이츠": "zenitsu",
            "이노스케": "inosuke",
            "네즈코": "nezuko",
            "아카자": "akaza",
        }

        # 유저가 캐릭터 이름 언급했는지 체크
        for name, char_id in name_mapping.items():
            if name in user_input and char_id in speaker_pool:
                return char_id

        # speaker_pool에서 narr 제외한 첫 번째 캐릭터
        for speaker in speaker_pool:
            if speaker != "narr":
                return speaker

        # narr밖에 없으면 narr 반환
        return speaker_pool[0] if speaker_pool else "narr"

# ============================================================
# 🚀 모듈 수준 헬퍼
# ============================================================
DEFAULT_AGENT = ChildrenAgent()

def run_children_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    start_time = time.perf_counter()

    try:
        result = DEFAULT_AGENT.run(state)

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

        # 📊 Performance Metric 저장: Children Agent 실행 시간
        try:
            from src.database.session_manager import HybridSessionManager
            from src.database.db_manager import DatabaseManager

            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            session_id = state.get("session_id")

            if session_id:
                db = DatabaseManager()
                session_manager = HybridSessionManager(db_manager=db)
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
        # Phase 4: 로그 수집 (에러)
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
