# Router Agent (Context-aware variant)
"""
Router Agent - 사용자 입력을 분류하고 다음 처리 방향을 결정
- on_topic/off_topic 구분 (LLM 기반 + 규칙 기반)
- Fallback 정책 적용 (장면별 허용 횟수)
- Loop 제어 적용 (반복 입력 자동 전환)
- 다음 노드 결정 (parent_agent or children_agent)

본 모듈은 기존 router_agent에 `message_history` 컨텍스트를 포함해
LLM 분류 정확도를 높인 버전입니다.
"""

from typing import List, Dict, Any
import time
import re

from src.core.graph_state import AgentState
from src.utils.llm_client import get_llm_client
from src.tools.fallback_tools import check_fallback_policy, apply_fallback_result
from src.tools.loop_tools import check_loop_detection, apply_loop_result
from src.utils.characters_repo import list_characters


def _ensure_speaker_pool(state: AgentState) -> None:
    scene = state.setdefault("scene", {})
    cc = state.get("children_ctx") or {}
    if cc.get("speaker_pool"):
        scene["speaker_pool"] = cc.get("speaker_pool")
        return
    pool = scene.get("speaker_pool") or []
    if pool:
        return
    # Build a conservative pool from known characters
    base = ["tanjiro", "rengoku", "zenitsu", "inosuke", "akaza", "system", "narr"]
    present = set(list_characters())
    candidates = [c for c in base if c in present or c in ("akaza", "system", "narr")]
    scene["speaker_pool"] = candidates


def _normalize_korean(text: str) -> str:
    """
    한글 형태소 정규화 (간이 버전)
    조사와 어미를 제거하여 어간만 추출

    예시:
    - "돕죠" → "돕"
    - "도와줘" → "도와"
    - "찾자" → "찾"
    - "함께하자" → "함께하"
    """
    # 일반적인 조사/어미 패턴 제거
    patterns = [
        r'(을|를|이|가|은|는|와|과|의|에|에서|으로|로|부터|까지|한테|께|님|씨)$',  # 조사
        r'(죠|요|야|아|어|네|지|ㅂ니다|습니다)$',  # 종결어미
        r'(자|까|줘|주|게|라)$',  # 명령/제안형 어미
    ]
    normalized = text
    for pattern in patterns:
        normalized = re.sub(pattern, '', normalized)
    return normalized


def _detect_intent_cutscene5(state: Dict[str, Any], user_input: str) -> str:
    """cutscene5_llm_driven 시나리오 전용 의도 판별 (형태소 정규화 적용)"""
    current_stage = (state.get("current_stage") or "").upper()
    user_text = user_input.lower()

    # 형태소 정규화된 텍스트 (조사/어미 제거)
    normalized_text = _normalize_korean(user_text)

    if current_stage == "ROUTE_CHOICE":
        # 동료 찾기 키워드 (어간 중심)
        allies_keywords = ["동료", "찾", "모아", "모으", "젠이츠", "이노스케", "데려", "규합", "도움", "부르", "모집", "둘"]
        # 함께 싸우기 키워드 (어간 중심)
        reckless_keywords = ["함께", "같이", "렌고쿠", "싸우", "돌진", "막", "지키", "지원", "붙", "돕", "도와"]

        # 원문과 정규화된 텍스트 모두에서 검색 : choose_allies_path -> RECRUIT 
        if any(kw in user_text or kw in normalized_text for kw in allies_keywords):
            state["user_intent"] = "choose_allies_path"
            print(f"[ROUTER] 🎯 Detected intent: choose_allies_path (input: '{user_input}')")
            return "choose_allies_path"
        # 함께 싸우기 키워드 (reckless)
        if any(kw in user_text or kw in normalized_text for kw in reckless_keywords):
            state["user_intent"] = "choose_reckless_path"
            print(f"[ROUTER] 🎯 Detected intent: choose_reckless_path (input: '{user_input}')")
            return "choose_reckless_path"

        print(f"[ROUTER] ⚠️ No intent matched for ROUTE_CHOICE (input: '{user_input}', normalized: '{normalized_text}')")
        state.pop("user_intent", None)
        state.pop("router_label", None)
        return None

    if current_stage == "INTERVENE":
        # 형태소 정규화 적용
        attack_keywords = ["검기", "궤도", "비틀", "원거리", "견제", "공격"]
        noise_keywords = ["돌", "소리", "주의", "시선", "던"]
        ignore_keywords = ["무시", "개입", "피", "도망"]

        if any(kw in user_text or kw in normalized_text for kw in attack_keywords):
            print(f"[ROUTER] 🎯 Detected intent: intervene_attack (input: '{user_input}')")
            return "intervene_attack"
        if any(kw in user_text or kw in normalized_text for kw in noise_keywords):
            print(f"[ROUTER] 🎯 Detected intent: intervene_noise (input: '{user_input}')")
            return "intervene_noise"
        if any(kw in user_text or kw in normalized_text for kw in ignore_keywords):
            print(f"[ROUTER] 🎯 Detected intent: intervene_ignore (input: '{user_input}')")
            return "intervene_ignore"
        return "intervene_ignore"

    if current_stage == "RECRUIT":
        # 형태소 정규화 적용
        zenitsu_keywords = ["젠이츠", "네즈코", "위험", "깨우"]
        inosuke_keywords = ["이노스케", "대장", "앞장", "강한", "강", "왕"]

        if any(kw in user_text or kw in normalized_text for kw in zenitsu_keywords):
            print(f"[ROUTER] 🎯 Detected intent: wake_zenitsu (input: '{user_input}')")
            return "wake_zenitsu"
        if any(kw in user_text or kw in normalized_text for kw in inosuke_keywords):
            print(f"[ROUTER] 🎯 Detected intent: provoke_inosuke (input: '{user_input}')")
            return "provoke_inosuke"
        # 🔥 매칭 실패 시 None 리턴 (기본값 제거)
        print(f"[ROUTER] ⚠️ No intent matched for RECRUIT (input: '{user_input}')")
        return None

    return None


def _format_message_history(state: AgentState, limit: int = 6, max_chars: int = 800) -> str:
    """최근 message_history를 문자열 컨텍스트로 정리"""
    history: List[Dict[str, Any]] = state.get("message_history") or []
    if not history:
        return ""

    trimmed = history[-limit:]
    lines: List[str] = []
    for item in trimmed:
        speaker = (item.get("speaker") or "unknown").strip()
        text = (
            item.get("text")
            or item.get("content")
            or ""
        ).strip()
        if text:
            lines.append(f"{speaker}: {text}")

    context_text = "\n".join(lines).strip()
    if not context_text:
        return ""

    if len(context_text) > max_chars:
        context_text = context_text[-max_chars:]
    return context_text


def run_router_agent(state: AgentState, user_input: str) -> AgentState:
    """
    Router Agent 실행 함수
    - 사용자 의도 판별 (cutscene5_llm_driven 전용)
    - LLM 기반 + 규칙 기반 분류 (message_history 컨텍스트 포함)
    """
    start_time = time.perf_counter()
    # print(f"[ROUTER+] DEBUG label={state.get('router_label')}, keys={list(state.keys())}")
    print(f"[ROUTER+] DEBUG routing_result={state.get('routing_result')}, temp_data={state.get('temp_data')}")
    
    def _finish(result_state: AgentState, stage: str) -> AgentState:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        ui = result_state.get("user_intent")
        ctx_tag = ((result_state.get("temp_data") or {}).get("children_ctx") or {}).get("stage_tag")
        print(f"[ROUTER+] Elapsed {elapsed_ms:.2f} ms ({stage}) | user_intent={ui} ctx_tag={ctx_tag}")
        return result_state

    print(f"[ROUTER+] Processing input: {user_input[:30]}...")

    # Hard safety: ensure a minimal speaker_pool before intent detection
    scene = state.setdefault("scene", {})
    if not (state.get("children_ctx") or {}).get("speaker_pool") and not scene.get("speaker_pool"):
        scene["speaker_pool"] = ["tanjiro", "rengoku", "akaza", "system", "narr"]

    # Ensure a reasonable speaker_pool before intent detection
    try:
        scene = state.setdefault("scene", {})
        cc = state.get("children_ctx") or {}
        if not (cc.get("speaker_pool") or scene.get("speaker_pool")):
            # Scenario-aware conservative defaults
            scenario_id = (state.get("scenario_id") or "").strip().lower()
            current_stage = (state.get("current_stage") or "").strip().upper()
            present = set(list_characters())
            default_pool = []
            if scenario_id == "cutscene5_llm_driven" and current_stage in ("INTRO", "INTERVENE", "ROUTE_CHOICE"):
                # Place known actors for this scene
                for c in ["tanjiro", "rengoku", "akaza", "system", "narr"]:
                    if c in present or c in ("akaza", "system", "narr"):
                        default_pool.append(c)
            else:
                for c in ["tanjiro", "rengoku", "zenitsu", "inosuke", "akaza", "system", "narr"]:
                    if c in present or c in ("akaza", "system", "narr"):
                        default_pool.append(c)
            scene["speaker_pool"] = default_pool
    except Exception:
        pass

    # 0단계: 데이터 주도 의도 태깅(하이브리드 패턴/컨텍스트/선택적 LLM) - 친밀도
    try:
        from src.agents.intent_detector import detect_intents
        state["intent_tags"] = detect_intents(state, user_input)
        print(f"[ROUTER+] intent_tags: {state['intent_tags']}")
        
    except Exception as e:
        print(f"[ROUTER+] intent detection skipped: {e}")

    # 1단계: 시나리오별 의도 판별 (cutscene5_llm_driven)
    current_stage = state.get("current_stage", "")
    scenario_id = state.get("scenario_id", "")

    print(f"[ROUTER+] 🔍 scenario_id='{scenario_id}', current_stage='{current_stage}'")

    if scenario_id == "cutscene5_llm_driven":
        print(f"[ROUTER+] 🎯 Calling _detect_intent_cutscene5() for stage '{current_stage}'")
        detected_intent = _detect_intent_cutscene5(state, user_input)
        print(f"[ROUTER+] 📌 _detect_intent_cutscene5() returned: {detected_intent}")

        if detected_intent:
            state["user_intent"] = detected_intent
            state["router_label"] = detected_intent
            # ❗ Persist intent so parent_after_dialogue can consume it reliably
            temp = state.get("temp_data") or {}
            temp["intent"] = detected_intent
            temp["sticky_intent"] = detected_intent
            state["temp_data"] = temp
            rr = state.get("routing_result") or {}
            rr["intent"] = detected_intent
            state["routing_result"] = rr
            print(f"[ROUTER+] ✅ Intent: '{detected_intent}' at '{current_stage}'")
            state["next_node"] = "parent_agent"
            return _finish(state, "scenario_intent")

    # 2단계: 규칙 기반 빠른 분류
    off_topic_keywords = ["날씨", "밥", "음식"]
    user_input_lower = user_input.lower().strip()
    is_off_topic_keyword = any(kw in user_input_lower for kw in off_topic_keywords) and len(user_input) < 10

    # off_topic일 경우
    if is_off_topic_keyword:
        classification = "off_topic"
        confidence = 0.95
        detected_intent = "casual_chat"
        print("[ROUTER+] Quick classification: off_topic (규칙 기반)")
    else:
        # 3단계: LLM 기반 정교한 분류 (컨텍스트 포함)
        try:
            # LLM 호출 객체를 전역으로 1개만 만들어서 재사용
            llm_client = get_llm_client()
            context_text = _format_message_history(state)

            system_prompt = """You are a router agent for a Demon Slayer (Kimetsu no Yaiba) story game.

Your task: Classify if user input is related to the game or not.

**on_topic (게임 관련):**
- Mentions game characters: 탄지로, 이노스케, 젠이츠, 렌고쿠, 아카자, 네즈코, etc.
- Game actions: 설득하다, 싸우다, 선택하다, 도와주다, 함께하다, 가자, etc.
- Story progression: 계속, 다음, 확인, 진행, 어떻게 해야, etc.
- Questions about game/story: "탄지로는 어떻게 생각해?", "이노스케를 어떻게 설득해?"
- Responses to character dialogue: 괜찮아, 고마워, 알았어, 네, 아니, 그래, 좋아, 싫어, etc.
- Any response that could be a reply to a character in the story.

**off_topic (게임 무관):**
- Weather: 날씨, 비, 눈, 더워, 추워
- Food/daily life: 밥, 점심, 저녁, 배고파
- Greetings only: 안녕, hello, 하이 (단독 인사, 스토리와 무관)
- Random chat: 오늘 뭐했어?, 심심해, 너는 누구야 (메타 질문), etc.

**IMPORTANT:**
- If unclear, classify as 'on_topic' (게임 진행 우선)
- Short responses like "괜찮아", "네", "좋아" are usually on_topic (캐릭터에게 대답)

Return JSON: {"classification": "on_topic or off_topic", "confidence": 0.0-1.0}"""

            if context_text:
                user_prompt = (
                    f"Recent conversation:\n{context_text}\n\n"
                    f"Current user input: \"{user_input}\"\n"
                    "Classify this input."
                )
            else:
                user_prompt = f"User input: \"{user_input}\"\nClassify this input."

            response = llm_client.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1
            )

            classification = response.get("classification", "on_topic")
            confidence = response.get("confidence", 0.7)
            detected_intent = "casual_chat" if classification == "off_topic" else "game_action"
            state["router_label"] = classification
            print(f"[ROUTER+] LLM classification: {classification} (conf: {confidence})")
            
        except Exception as exc:
            print(f"[ROUTER+] LLM 분류 실패 ({exc}), 규칙 기반 폴백")
            classification = "on_topic"
            confidence = 0.6
            detected_intent = "game_action"
            print("[ROUTER+] Fallback classification: on_topic")

    # 분류 결과 저장
    is_off_topic = classification == "off_topic"
    is_valid_input = classification == "on_topic"

    routing_result = state.get("routing_result") or {}
    routing_result.update(
        {
            "classification": classification,
            "confidence": confidence,
            "detected_intent": detected_intent,
        }
    )
    state["routing_result"] = routing_result

    # 3단계: Fallback 정책 적용 (off_topic인 경우)
    fallback_result = check_fallback_policy(state, is_off_topic)
    state = apply_fallback_result(state, fallback_result)

    if fallback_result.get("message"):
        print(f"[ROUTER+] Fallback message: {fallback_result['message']}")
        state.setdefault("agent_responses", [])
        state["agent_responses"].append({
            "speaker": "system",
            # content -> text 로 변경 (agent_responses에 들어가는 키가 대부분 text)
            "text": fallback_result["message"],
            "emotion": "neutral"
        })

    # 4단계: Loop 제어 적용
    # loop_result : should_auto_advance, loop_count, message,reset 반환
    loop_result = check_loop_detection(state, user_input, is_valid_input)
    
    state = apply_loop_result(state, loop_result)

    if loop_result.get("message"):
        print(f"[ROUTER+] Loop message: {loop_result['message']}")
        state.setdefault("agent_responses", [])
        state["agent_responses"].append({
            "speaker": "system",
            "text": loop_result["message"],
            "emotion": "neutral"
        })

    # 5단계: 다음 노드 결정
    if loop_result.get("should_auto_advance"):
        state["next_node"] = "parent_agent"
        print("[ROUTER+] Loop exceeded → auto advance to parent_agent")
        
    elif fallback_result.get("should_block"):
        # ❌ 기존: state["next_node"] = "blocked"  (그래프에 노드가 없어 크래시)
        # ✅ 차단 시에도 parent_agent로 진행하되, 시스템 경고 대사 추가
        state["next_node"] = "parent_agent"
        print("[ROUTER+] Fallback blocked → continue via parent_agent with system notice")

        state.setdefault("agent_responses", []).append({
            "speaker": "system",
            "content": fallback_result.get("message", "지금은 진행에 집중해야 합니다."),
            "emotion": "neutral",
        })

        td = state.setdefault("temp_data", {})
        td["fallback_blocked"] = True
    else:
        next_node = "parent_agent" if classification == "on_topic" else "children_agent"
        state["next_node"] = next_node
        print(f"[ROUTER+] Result: {classification} → {next_node}")

    if "meta" in state and isinstance(state["meta"], dict):
        state["meta"]["processed_by"] = "router+"

    return _finish(state, "completed")
