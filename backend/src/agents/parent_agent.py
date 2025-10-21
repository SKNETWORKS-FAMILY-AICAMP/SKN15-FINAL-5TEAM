# parent_agent.py
# 목적:
# - 매 턴 children으로 넘길 컨텍스트(children_ctx)를 책임지고 채워준다.
# - scene 제약(min_turns/max_turns) 충족 시 안전하게 전이한다.
# - i18n 비트(beats_i18n) / stage.speaker_pool 존중.
# - 하드코딩 최소화.

from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging, os, json, time, re
from copy import deepcopy


# ---------- drop-in: stage helpers ----------
def _sync_stage_keys(state: dict):
    """current_stage <-> scene.current_scene 동기화"""
    scene = state.setdefault("scene", {})
    cur_flat = state.get("current_stage")
    cur_scene = scene.get("current_scene")
    if cur_scene and cur_scene != cur_flat:
        state["current_stage"] = cur_scene
    elif cur_flat and not cur_scene:
        scene["current_scene"] = cur_flat

def _goto(state: dict, next_stage: str):
    """스테이지 전환 공통 처리"""
    scene = state.setdefault("scene", {})
    prev_stage = state.get("current_stage") or scene.get("current_scene")
    state["current_stage"] = next_stage   # 양방향 동기화
    scene["current_scene"] = next_stage
    scene["stage_turn"] = 0               # 새 스테이지 시작은 0턴
    state["stage_turn"] = 0
    # 다음 루프에서 이전 스테이지를 표시하기 위한 플래그
    temp = state.get("temp_data") or {}
    if prev_stage and "display_stage" not in temp:
        temp["display_stage"] = prev_stage
    state["temp_data"] = temp
    # stage_history에 진입 스테이지 기록 (중복 방지)
    try:
        history = state.get("stage_history")
        if not isinstance(history, list):
            history = []
        if not history or history[-1] != next_stage:
            history.append(next_stage)
        state["stage_history"] = history
    except Exception:
        pass
    # Reset cutscene cap on stage change
    try:
        from kime_chat_agent_dev.src.utils.affinity import reset_cutscene_cap
        reset_cutscene_cap(state)
    except Exception:
        pass
    # 전역 컨텍스트/스피커 동기화: 스테이지 전환 시마다 보장
    try:
        scenario = state.get("scenario") or state.get("scenario_data")
        if scenario:
            ctx = _build_children_ctx(state, scenario, next_stage)
            agent_inputs = state.get("agent_inputs") or {}
            agent_inputs["children"] = ctx
            state["agent_inputs"] = agent_inputs
            state["children_ctx"] = ctx
            temp = state.get("temp_data") or {}
            temp["children_ctx"] = ctx
            state["temp_data"] = temp
            scene["speaker_pool"] = ctx.get("speaker_pool") or scene.get("speaker_pool")
    except Exception:
        pass

def _apply_state_defaults(state: Dict[str, Any], scenario: Dict[str, Any]) -> None:
    """시나리오에 정의된 state_defaults를 최초 진입 시 적용"""
    defaults = scenario.get("state_defaults") or {}
    if not isinstance(defaults, dict):
        return
    for key, value in defaults.items():
        if key in state:
            continue
        state[key] = deepcopy(value)

    params = scenario.get("params")
    if isinstance(params, dict) and "params" not in state:
        state["params"] = deepcopy(params)

def _get_intent(state: Dict[str, Any]) -> str:
    """router → parent 간 전달된 의도를 통일된 방식으로 조회"""
    return (
        (state.get("temp_data") or {}).get("sticky_intent")
        or state.get("user_intent")
        or (state.get("routing_result") or {}).get("intent")
        or ""
    ).strip().lower()

def _consume_intent(state: Dict[str, Any]) -> None:
    """소비된 의도를 정리해 다음 스테이지에 누수되지 않도록 한다."""
    temp = state.get("temp_data") or {}
    temp.pop("intent", None)
    temp.pop("sticky_intent", None)
    state["temp_data"] = temp
    state.pop("user_intent", None)
    state.pop("router_label", None)
    rr = state.get("routing_result")
    if isinstance(rr, dict) and "intent" in rr:
        rr.pop("intent", None)
        state["routing_result"] = rr

def _apply_operations(state: Dict[str, Any], updates: Optional[Dict[str, Any]]) -> None:
    """set/effects 블록을 공통 처리"""
    if not updates or not isinstance(updates, dict):
        return
    for key, instruction in updates.items():
        if isinstance(instruction, dict):
            # 연산자 기반 처리 ($inc, $dec, $push_unique 등)
            handled = False
            for op, val in instruction.items():
                if op == "$inc":
                    state[key] = state.get(key, 0) + int(val)
                    handled = True
                elif op == "$dec":
                    state[key] = state.get(key, 0) - int(val)
                    handled = True
                elif op == "$push_unique":
                    arr = state.get(key, [])
                    if not isinstance(arr, list):
                        arr = list(arr) if arr else []
                    if val not in arr:
                        arr.append(val)
                    state[key] = arr
                    handled = True
                elif op == "$set":
                    state[key] = deepcopy(val)
                    handled = True
                elif op == "$append":
                    arr = state.get(key, [])
                    if not isinstance(arr, list):
                        arr = list(arr) if arr else []
                    arr.append(val)
                    state[key] = arr
                    handled = True
            if handled:
                continue
        # 기본 대입 (dict도 허용)
        state[key] = deepcopy(instruction)

def _eval_condition(expr: Optional[str], state: Dict[str, Any]) -> bool:
    """시나리오 표현식 평가 (간단한 비교/논리)"""
    if not expr or not isinstance(expr, str):
        return False
    prepared = expr.replace("&&", " and ").replace("||", " or ")
    prepared = re.sub(r"\btrue\b", "True", prepared, flags=re.IGNORECASE)
    prepared = re.sub(r"\bfalse\b", "False", prepared, flags=re.IGNORECASE)

    def includes(container, item):
        if container is None:
            return False
        if isinstance(container, dict):
            return item in container
        try:
            return item in container
        except TypeError:
            return False

    def exists(value):
        return value is not None

    context: Dict[str, Any] = {}
    for key, val in state.items():
        if isinstance(key, str):
            context[key] = val
    context.setdefault("params", state.get("params") or {})
    safe_globals = {"__builtins__": None, "includes": includes, "exists": exists, "len": len}
    try:
        result = eval(prepared, safe_globals, context)
        return bool(result)
    except Exception:
        return False

def _apply_rules(state: Dict[str, Any], stage: Dict[str, Any]) -> bool:
    """stage.rules 배열을 평가하여 조건에 맞으면 적용"""
    if not isinstance(stage, dict):
        return False
    rules = stage.get("rules")
    if not isinstance(rules, list):
        return False

    stage_tag = stage.get("tag") or (state.get("current_stage") or "")
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        condition = rule.get("if")
        else_marker = rule.get("else")
        should_apply = False
        if condition:
            should_apply = _eval_condition(condition, state)
        elif else_marker is not None:
            should_apply = True
        if not should_apply:
            continue

        _apply_operations(state, rule.get("set"))
        _apply_operations(state, rule.get("effects"))
        goto = rule.get("goto")
        label = condition or else_marker or "rule"
        if goto:
            logger.info(f"[{stage_tag}] rule matched ({label}) → {goto}")
            _goto(state, goto)
        else:
            logger.info(f"[{stage_tag}] rule matched ({label}) (stay)")
        _consume_intent(state)
        return True
    return False

def _handle_free_intent_stage(state: Dict[str, Any], stage: Dict[str, Any]) -> bool:
    """free_intent 스테이지 on_action 처리 + min_turns 폴백"""
    actions = stage.get("on_action")
    if not isinstance(actions, list):
        return False
    stage_tag = stage.get("tag") or (state.get("current_stage") or "")

    # ✅ 1️⃣ AUTO_CONTINUE 입력 시 즉시 반환 (모든 free_intent 공통)
    user_input = (state.get("user_input") or "").strip().lower()
    if user_input == "__auto_continue__":
        logger.info(f"[{stage_tag}] Skipping auto-fallback: auto-continue input")
        return False

    # ✅ 2️⃣ 스테이지 막 진입했을 때는 폴백 금지
    scene = state.setdefault("scene", {})
    if int(scene.get("stage_turn", 0)) <= 1 and not user_input:
        logger.info(f"[{stage_tag}] Skipping auto-fallback: just entered stage or no input yet")
        return False
    
    temp = state.get("temp_data") or {}
    intent = _get_intent(state)
    intent_lower = intent.lower()
    stage_upper = stage_tag.upper()
    intent_match_key = intent_lower
    first_target_hint: Optional[str] = None

    if stage_upper == "ROUTE_CHOICE" and intent_lower:
        prefix = "choose_allies_"
        suffix = "_first"
        stored_target = (temp.get("mission_first_target") or state.get("mission_first_target") or "").strip().lower()
        if intent_lower.startswith(prefix) and intent_lower.endswith(suffix):
            candidate = intent_lower[len(prefix):-len(suffix)]
            if candidate:
                first_target_hint = candidate
                intent_match_key = "choose_allies_path"
        elif intent_lower == "choose_allies_path" and stored_target:
            first_target_hint = stored_target

    matched_rule = None
    if intent_match_key:
        for rule in actions:
            if not isinstance(rule, dict):
                continue
            action_key = (rule.get("action") or "").strip().lower()
            if action_key and action_key == intent_match_key:
                matched_rule = rule
                break
    if not matched_rule and intent_match_key:
        for rule in actions:
            if not isinstance(rule, dict):
                continue
            if rule.get("fallback"):
                matched_rule = rule
                break

    # # Intent 매칭이 안 되었을 때 min_turns 폴백 체크
    # if not matched_rule:
    #     # min_turns 체크: constraints.min_turns 도달 시 스마트 폴백
    #     constraints = stage.get("constraints") or {}
    #     min_turns = int(constraints.get("min_turns", 0))
    #     scene = state.setdefault("scene", {})
    #     stage_turn = int(scene.get("stage_turn", 0))

    #     if min_turns > 0 and stage_turn >= min_turns and actions:
    #         # 🔥 스마트 폴백: user_input에서 키워드 재검사
    #         user_input = (state.get("user_input") or "").lower()

    #         # ROUTE_CHOICE 전용 간이 키워드 감지
    #         if stage_tag.upper() == "ROUTE_CHOICE":
    #             allies_kw = ["동료", "찾", "모아", "젠이츠", "이노스케", "둘"]
    #             reckless_kw = ["함께", "렌고쿠", "싸우", "돌진", "돕", "도와", "지키"]

    #             # reckless 키워드 우선 체크 (INTERVENE 우선)
    #             if any(kw in user_input for kw in reckless_kw):
    #                 for rule in actions:
    #                     if (rule.get("action") or "").lower() == "choose_reckless_path":
    #                         matched_rule = rule
    #                         logger.info(
    #                             f"🔍 [{stage_tag}] Smart fallback: keyword matched → choose_reckless_path"
    #                         )
    #                         break
    #             elif any(kw in user_input for kw in allies_kw):
    #                 for rule in actions:
    #                     if (rule.get("action") or "").lower() == "choose_allies_path":
    #                         matched_rule = rule
    #                         logger.info(
    #                             f"🔍 [{stage_tag}] Smart fallback: keyword matched → choose_allies_path"
    #                         )
    #                         break

        #     # 키워드 매칭도 실패 시 첫 번째 action 사용
        #     if not matched_rule:
        #         matched_rule = actions[0]
        #         logger.info(
        #             f"⏰ [{stage_tag}] No intent/keyword matched but min_turns({min_turns}) reached "
        #             f"(stage_turn={stage_turn}), using first action as fallback"
        #         )
        # else:
        #     logger.info(
        #         f"⏳ [{stage_tag}] No intent matched, stage_turn={stage_turn}/{min_turns} "
        #         f"(waiting for user intent...)"
        #     )
        #     return False

    if not isinstance(matched_rule, dict):
        logger.info(f"[{stage_tag}] No valid rule matched (intent='{intent_lower}') → waiting for user input")
        return False

    normalized_action = (matched_rule.get("action") or intent_match_key or "").strip().lower()

    if stage_upper == "ROUTE_CHOICE" and normalized_action == "choose_allies_path":
        target_value = first_target_hint
        if not target_value:
            target_value = (temp.get("mission_first_target") or state.get("mission_first_target"))
        if not target_value:
            hints = {
                "inosuke": ["이노스케", "멧돼지", "inosuke"],
                "zenitsu": ["젠이츠", "zenitsu", "츠고쿠", "츠구코"],
            }
            for candidate, keys in hints.items():
                if any(kw in user_input for kw in keys):
                    target_value = candidate
                    break
        if isinstance(target_value, str) and target_value:
            target_value = target_value.strip().lower()
            state["mission_first_target"] = target_value
            temp = state.get("temp_data") or {}
            temp["mission_first_target"] = target_value
            state["temp_data"] = temp
            # Reset previously cached lane preference so new target takes effect
            state.pop("mission_first_lane_id", None)
            temp.pop("mission_first_lane_id", None)
            logger.info(f"[ROUTE_CHOICE] Allies mission selected, first target: {target_value}")
            logger.info(f"[RECRUIT INIT] mission_first_target = {target_value}")

    _apply_operations(state, matched_rule.get("set"))
    _apply_operations(state, matched_rule.get("effects"))
    goto = matched_rule.get("goto")
    label = (matched_rule.get("action") or ("fallback" if matched_rule.get("fallback") else intent_lower)) or "unknown"
    if goto:
        logger.info(f"✅ [{stage_tag}] on_action '{label}' → {goto}")
        _goto(state, goto)
    else:
        logger.info(f"[{stage_tag}] on_action '{label}' applied (stay)")
    _consume_intent(state)
    return True

def _handle_router_stage(state: Dict[str, Any], stage: Dict[str, Any]) -> bool:
    """router 스테이지 rules 처리"""
    return _apply_rules(state, stage)

def _handle_mission_stage(state: Dict[str, Any], stage: Dict[str, Any]) -> bool:
    """mission 스테이지 lanes/steps 처리 (간소화 버전)"""
    stage_tag = stage.get("tag") or (state.get("current_stage") or "")
    scene = state.setdefault("scene", {})
    temp = state.setdefault("temp_data", {})
    mission_store = temp.setdefault("_mission", {})
    stage_state = mission_store.setdefault(stage_tag, {})
    progress: Dict[str, int] = stage_state.setdefault("progress", {})

    # 턴마다 감소/증가 처리 (실제 유저 입력일 때만!)
    user_input = (state.get("user_input") or "").strip()
    is_user_turn = user_input and user_input != "__AUTO_CONTINUE__"

    ticking = stage.get("ticking") or {}
    each_turn = ticking.get("each_turn")

    # 🔥 each_turn은 실제 유저 턴에만 적용 (중복 방지)
    last_ticking_turn = stage_state.get("_last_ticking_turn", -1)
    current_turn = state.get("turn_count", 0)

    if isinstance(each_turn, dict) and is_user_turn and last_ticking_turn < current_turn:
        _apply_operations(state, each_turn)
        stage_state["_last_ticking_turn"] = current_turn
        logger.info(f"[MISSION:{stage_tag}] Ticking applied (turn {current_turn}): {each_turn}")

    intent = _get_intent(state)
    intent_lower = intent.lower()
    raw_lanes = stage.get("lanes") or []
    lanes = _order_lanes_by_preference(state, raw_lanes)
    max_inosuke_attempts = int(state.get("inosuke_max_attempts") or INOSUKE_MAX_ATTEMPTS)
    if max_inosuke_attempts < 1:
        max_inosuke_attempts = INOSUKE_MAX_ATTEMPTS
    state["inosuke_max_attempts"] = max_inosuke_attempts
    current_attempts = int(state.get("inosuke_attempts", 0) or 0)
    if current_attempts < 0:
        current_attempts = 0
    if current_attempts > max_inosuke_attempts:
        current_attempts = max_inosuke_attempts
    state["inosuke_attempts"] = current_attempts
    matched = False

    if intent_lower:
        # intent에 맞는 lane을 우선 처리하기 위해 정렬
        sorted_lanes = []
        for lane in lanes:
            lane_id = lane.get("id") or lane.get("tag") or ""
            steps = lane.get("steps") or []
            idx = progress.get(lane_id, 0)
            if idx >= len(steps):
                continue
            step = steps[idx]
            if not isinstance(step, dict):
                continue
            actions = step.get("on_action") or []
            # 이 lane에 intent와 매칭되는 action이 있는지 확인
            has_match = any((rule.get("action") or "").strip().lower() == intent_lower for rule in actions)
            if has_match:
                sorted_lanes.insert(0, lane)  # 매칭되는 lane을 앞에
            else:
                sorted_lanes.append(lane)

        # sorted_lanes로 순회
        for lane in sorted_lanes:
            lane_id = lane.get("id") or lane.get("tag") or ""
            if not lane_id:
                continue
            steps = lane.get("steps") or []
            idx = progress.get(lane_id, 0)
            if idx >= len(steps):
                continue
            step = steps[idx]
            if not isinstance(step, dict):
                continue
            actions = step.get("on_action") or []
            for rule in actions:
                action_key = (rule.get("action") or "").strip().lower()
                if action_key and action_key == intent_lower:
                    _apply_operations(state, rule.get("set"))
                    _apply_operations(state, rule.get("effects"))
                    if "inosuke" in lane_id:
                        attempts_val = int(state.get("inosuke_attempts", 0) or 0)
                        if attempts_val < 0:
                            attempts_val = 0
                        if attempts_val > max_inosuke_attempts:
                            attempts_val = max_inosuke_attempts
                        state["inosuke_attempts"] = attempts_val
                    goto = rule.get("goto")
                    logger.info(
                        f"✅ [MISSION:{stage_tag}] lane '{lane_id}' action '{action_key}' → {goto or 'stay'}"
                    )
                    if goto:
                        _goto(state, goto)
                    if lane_id:
                        scene["current_lane"] = lane_id
                        steps_total = len(steps)
                        next_index = idx + 1
                        if next_index < steps_total:
                            stage_state["_pending_lane_ctx"] = {
                                "lane_id": lane_id,
                                "step_index": next_index,
                                "from_intent": intent_lower,
                            }
                        else:
                            stage_state.pop("_pending_lane_ctx", None)
                    progress[lane_id] = idx + 1
                    matched = True
                    break
            if matched:
                break

    if not matched and intent_lower:
        for lane in lanes:
            lane_id = lane.get("id") or lane.get("tag") or ""
            steps = lane.get("steps") or []
            idx = progress.get(lane_id, 0)
            if idx >= len(steps):
                continue
            step = steps[idx]
            if not isinstance(step, dict):
                continue
            fallback_rule = None
            for rule in step.get("on_action") or []:
                if rule.get("fallback"):
                    fallback_rule = rule
                    break
            if fallback_rule:
                _apply_operations(state, fallback_rule.get("set"))
                _apply_operations(state, fallback_rule.get("effects"))
                if "inosuke" in lane_id:
                    attempts_val = int(state.get("inosuke_attempts", 0) or 0)
                    if attempts_val < 0:
                        attempts_val = 0
                    if attempts_val > max_inosuke_attempts:
                        attempts_val = max_inosuke_attempts
                    state["inosuke_attempts"] = attempts_val
                goto = fallback_rule.get("goto")
                logger.info(
                    f"[MISSION:{stage_tag}] lane '{lane_id}' fallback applied → {goto or 'stay'}"
                )
                if goto:
                    _goto(state, goto)
                if lane_id:
                    scene["current_lane"] = lane_id
                    steps_total = len(steps)
                    next_index = idx + 1
                    if next_index < steps_total:
                        stage_state["_pending_lane_ctx"] = {
                            "lane_id": lane_id,
                            "step_index": next_index,
                            "from_intent": intent_lower or "fallback",
                        }
                    else:
                        stage_state.pop("_pending_lane_ctx", None)
                matched = True
                break

    # Inosuke 설득 실패 한계 체크
    attempts_after = int(state.get("inosuke_attempts", 0) or 0)
    if max_inosuke_attempts > 0 and attempts_after >= max_inosuke_attempts and not state.get("inosuke_willing"):
        for lane in lanes:
            lane_id = lane.get("id") or lane.get("tag") or ""
            if not lane_id or "inosuke" not in lane_id.lower():
                continue
            steps = lane.get("steps") or []
            progress[lane_id] = len(steps)
            stage_state.pop("_pending_lane_ctx", None)
            state["inosuke_engaged"] = False
            failure_msg = "이노스케 설득에 실패했습니다. 다음 단계로 이동합니다."
            state.setdefault("agent_responses", []).append({
                "speaker": "system",
                "text": failure_msg,
                "emotion": "neutral"
            })
            logger.info(f"[MISSION:{stage_tag}] Inosuke persuasion failed after {attempts_after} attempts → skipping lane")
            break

    # 진행 상황 저장
    stage_state["progress"] = progress
    mission_store[stage_tag] = stage_state
    temp["_mission"] = mission_store

    # 완료 판정
    all_done = True
    for lane in lanes:
        lane_id = lane.get("id") or lane.get("tag") or ""
        steps = lane.get("steps") or []
        if progress.get(lane_id, 0) < len(steps):
            all_done = False
            break
    if all_done and lanes:
        nxt = stage.get("next") or stage.get("goto")
        if nxt:
            logger.info(f"[MISSION:{stage_tag}] lanes completed → {nxt}")
            _goto(state, nxt)
            matched = True

    # fail_if + on_timeout 처리
    fail_if = ticking.get("fail_if")
    fail_expr = ""
    if isinstance(fail_if, dict):
        fail_expr = fail_if.get("expr") or ""
    elif isinstance(fail_if, str):
        fail_expr = fail_if
    if fail_expr and _eval_condition(fail_expr, state):
        timeout_rule = stage.get("on_timeout") or {}
        _apply_operations(state, timeout_rule.get("set"))
        goto = timeout_rule.get("goto")
        logger.info(f"[MISSION:{stage_tag}] fail_if triggered → {goto or 'stay'}")
        if goto:
            _goto(state, goto)
        matched = True

    if (state.get("current_stage") or "").strip().upper() == stage_tag.upper():
        scenario = state.get("scenario") or state.get("scenario_data")
        if scenario:
            _apply_ctx(state, scenario, stage_tag)

    if matched:
        _consume_intent(state)
    return matched

def _apply_intent_transition(state: dict, intent: str) -> dict:
    """의도를 소비해서 스테이지를 전환한다."""
    scene = state.setdefault("scene", {})
    current = (scene.get("current_scene") or state.get("current_stage") or "").upper()
    if not intent:
        # 의도가 없으면 아무 것도 하지 않음
        return state

    # 현재 스테이지 타입 파악 (children_ctx 우선, 없으면 시나리오 참조)
    stage_type = ""
    try:
        ctx = ((state.get("temp_data") or {}).get("children_ctx") or {})
        if (ctx.get("stage_tag") or "").upper() == current:
            stage_type = (ctx.get("stage_type") or "").lower()
    except Exception:
        pass
    if not stage_type:
        scenario = state.get("scenario") or state.get("scenario_data")
        if scenario:
            try:
                stage_def = _find_stage(scenario, current)
                if isinstance(stage_def, dict):
                    stage_type = (stage_def.get("type") or "").lower()
            except Exception:
                pass

    # INTRO의 강한 의도는 min_turns 무시하고 즉시 전환
    hard_intro = {
        "CHOOSE_RECKLESS_PATH": "ROUTE_CHOICE",
        "CHOOSE_ALLIES_PATH": "ROUTE_CHOICE",
    }
    if current == "INTRO":
        upper_intent = intent.upper()
        if upper_intent in hard_intro:
            _goto(state, hard_intro[upper_intent])
            print(f"[PARENT] Stage → {state['scene']['current_scene']} (intent={intent}) [FORCE from INTRO]")
            return state

    if stage_type == "free_intent":
        return state

    # 의도 → 다음 스테이지 매핑
    next_map = {
        "INTERVENE_ATTACK":     "RECRUIT",
        "INTERVENE_NOISE":      "RECRUIT",
        "INTERVENE_IGNORE":     "RECRUIT",
    }

    # 일반 규칙: min_turns 충족 시 전환
    min_turns = scene.get("min_turns", 1)
    scene["stage_turn"] = scene.get("stage_turn", 0) + 1

    if scene["stage_turn"] >= min_turns and intent.upper() in next_map:
        _goto(state, next_map[intent.upper()])
        print(f"[PARENT] Stage → {state['scene']['current_scene']} (intent={intent})")
    else:
        print(f"[PARENT] Stay at {current} (turn={scene['stage_turn']}/{min_turns}, intent={intent})")
    return state


logger = logging.getLogger("PARENT")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[PARENT] %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# --- helpers ---
def _apply_ctx(state: Dict[str, Any], scenario: Dict[str, Any], stage_tag: str) -> Dict[str, Any]:
    """Rebuild and apply children context for a stage (single source of truth).
    Updates agent_inputs.children, children_ctx, temp_data.children_ctx, scene.speaker_pool.
    Returns the built ctx.
    """
    ctx = _build_children_ctx(state, scenario, stage_tag)
    agent_inputs = state.get("agent_inputs") or {}
    agent_inputs["children"] = ctx
    state["agent_inputs"] = agent_inputs
    state["children_ctx"] = ctx
    temp = state.get("temp_data") or {}
    temp["children_ctx"] = ctx
    state["temp_data"] = temp
    scene = state.setdefault("scene", {})
    scene["speaker_pool"] = ctx.get("speaker_pool") or scene.get("speaker_pool")
    try:
        logger.info(f"[CTX] stage={stage_tag} tag={ctx.get('stage_tag')} type={ctx.get('stage_type')} speakers={ctx.get('speaker_pool')}")
    except Exception:
        pass
    return ctx

def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _is_scenario_dict(obj: Any) -> bool:
    """시나리오가 유효한지 확인: stages가 list 또는 dict 형태여야 함"""
    return isinstance(obj, dict) and isinstance(obj.get("stages"), (list, dict))

def _find_stage(scenario: Dict[str, Any], stage_tag: str) -> Optional[Dict[str, Any]]:
    """
    scenario['stages'] 가 다음 모든 형태를 안전하게 처리:
    - list[dict] (정상)
    - dict[str, dict] (키가 stage ID인 맵) ← cutscene5_simple.json 형태
    """
    stages = scenario.get("stages", [])

    # dict 형태 지원 (cutscene5_simple.json)
    if isinstance(stages, dict):
        # 직접 키로 찾기
        if stage_tag in stages:
            stage_data = stages[stage_tag]
            if isinstance(stage_data, dict):
                # tag 필드가 없으면 추가
                if "tag" not in stage_data:
                    stage_data["tag"] = stage_tag
                return stage_data
        # 키 목록을 list로 변환하여 순회
        candidates = list(stages.values())
    else:
        candidates = stages if isinstance(stages, list) else []

    if not candidates:
        return None

    tag_norm = _norm(stage_tag).lower()

    # 1차: 정확 매칭
    for st in candidates:
        if not isinstance(st, dict):
            continue
        for key in ("tag", "id", "name", "slug"):
            if key in st and _norm(st[key]).lower() == tag_norm:
                return st

    # 2차: 대소문자 구분 없이
    for st in candidates:
        if not isinstance(st, dict):
            continue
        if _norm(st.get("tag", "")).upper() == _norm(stage_tag).upper():
            return st

    return None

def _lane_identifier(lane: Dict[str, Any]) -> str:
    if not isinstance(lane, dict):
        return ""
    identifier = lane.get("id") or lane.get("tag") or lane.get("name")
    return (identifier or "").strip()

def _lane_matches_preference(lane: Dict[str, Any], hint: str) -> bool:
    if not hint or not isinstance(lane, dict):
        return False
    pref = hint.strip().lower()
    if not pref:
        return False

    lane_id = _lane_identifier(lane).lower()
    if lane_id == pref or pref in lane_id:
        return True

    for key in ("title", "label"):
        value = lane.get(key)
        if isinstance(value, str) and pref in value.strip().lower():
            return True

    for speaker in lane.get("speaker_pool") or []:
        if pref in str(speaker).strip().lower():
            return True

    steps = lane.get("steps") or []
    for step in steps:
        if not isinstance(step, dict):
            continue
        for speaker in step.get("speaker_pool") or []:
            if pref in str(speaker).strip().lower():
                return True
        for action in step.get("llm_actions") or []:
            if pref in (action or "").strip().lower():
                return True
        for rule in step.get("on_action") or []:
            action_key = (rule.get("action") or "").strip().lower()
            if pref in action_key:
                return True
    return False

def _order_lanes_by_preference(state: Dict[str, Any], lanes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(lanes, list):
        return []

    enumerated = [(idx, lane) for idx, lane in enumerate(lanes) if isinstance(lane, dict)]
    if not enumerated:
        return []

    temp = state.get("temp_data") or {}
    lane_priority_hints: List[str] = []

    lane_priority = state.get("mission_lane_priority")
    if isinstance(lane_priority, list):
        lane_priority_hints.extend(
            [str(item).strip().lower() for item in lane_priority if isinstance(item, str) and item.strip()]
        )

    first_lane_hint = state.get("mission_first_lane_id") or temp.get("mission_first_lane_id")
    first_target_hint = state.get("mission_first_target") or temp.get("mission_first_target")

    for hint in (first_lane_hint, first_target_hint):
        if isinstance(hint, str) and hint.strip():
            normalized = hint.strip().lower()
            if normalized not in lane_priority_hints:
                lane_priority_hints.insert(0, normalized)

    def _lane_priority(pair):
        idx, lane = pair
        for priority_index, hint in enumerate(lane_priority_hints):
            if _lane_matches_preference(lane, hint):
                return (priority_index, idx)
        return (len(lane_priority_hints), idx)

    ordered_pairs = sorted(enumerated, key=_lane_priority)

    if lane_priority_hints:
        preferred_hint = lane_priority_hints[0]
        for _, lane in ordered_pairs:
            if _lane_matches_preference(lane, preferred_hint):
                lane_id = _lane_identifier(lane)
                if lane_id:
                    temp = state.setdefault("temp_data", {})
                    temp["mission_first_lane_id"] = lane_id
                    state["mission_first_lane_id"] = lane_id
                break

    return [lane for _, lane in ordered_pairs]

def _resolve_beats(stage: Dict[str, Any], scenario: Dict[str, Any], locale: str) -> List[str]:
    """
    스테이지에서 beats 텍스트를 추출합니다.
    cutscene5_llm_driven.json의 beats_i18n 키 기반 참조를 지원합니다.
    """
    # 1) beats_i18n 키로 i18n[locale][key] 참조
    beats_key = stage.get("beats_i18n") or stage.get("beats_key")
    i18n = scenario.get("i18n") or {}

    if beats_key and isinstance(i18n.get(locale), dict):
        arr = i18n[locale].get(beats_key)
        if isinstance(arr, list) and arr:
            return arr

    # 2) i18n.beats[<key>][locale] 형태 지원 (레거시)
    beats_map = i18n.get("beats") or i18n.get("i18n_beats") or {}
    if beats_key and isinstance(beats_map.get(beats_key), dict):
        loc_map = beats_map[beats_key]
        for loc in (locale, "ko", "en"):
            arr = loc_map.get(loc)
            if isinstance(arr, list) and arr:
                return arr

    # 3) 직접 beats 필드
    beats = stage.get("beats")
    if isinstance(beats, list):
        return beats

    return []

def _speaker_pool_for_stage(stage: Dict[str, Any]) -> List[str]:
    """
    스테이지의 speaker_pool을 추출합니다.
    cutscene5_llm_driven.json의 speaker_pool 필드를 사용합니다.
    """
    for key in ("speaker_pool", "characters", "actors"):
        val = stage.get(key)
        if isinstance(val, list) and val:
            return val
    return []

def _extract_scenario_from_state(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # 주 소스: play.py가 scenario_data에 넣음
    for cand in [
        state.get("scenario"),
        state.get("scenario_data"),
        (state.get("game") or {}).get("scenario"),
        (state.get("game") or {}).get("scenario_data"),
    ]:
        if _is_scenario_dict(cand):
            return cand
    return None

def _build_children_ctx(state: Dict[str, Any], scenario: Dict[str, Any], stage_tag: str) -> Dict[str, Any]:
    """
    Children Agent에게 넘길 컨텍스트를 생성합니다.
    cutscene5_llm_driven.json의 구조에 맞춰 beats_i18n과 speaker_pool을 추출합니다.
    """
    stage = _find_stage(scenario, stage_tag)
    if not stage:
        logger.warning(f"Stage '{stage_tag}' not found.")
        return {}

    locale = state.get("locale", "ko")
    stage_turn = state.get("stage_turn", 0)
    scene = state.setdefault("scene", {})

    speakers = _speaker_pool_for_stage(stage)
    mission_ctx: Dict[str, Any] = {}
    beats_all = []

    # mission 타입에서는 active_lane에 따라 beats 결정
    if (stage.get("type") or "").lower() == "mission":
        temp = state.get("temp_data") or {}
        mission_store = (temp.get("_mission") or {}).get(stage.get("tag") or stage_tag, {})
        progress = mission_store.get("progress") or {}
        pending_ctx = mission_store.get("_pending_lane_ctx") if isinstance(mission_store, dict) else None
        active_lane = None
        active_step = None
        active_idx = 0
        raw_lanes = stage.get("lanes") or []
        lanes = _order_lanes_by_preference(state, raw_lanes)
        mission_intro = False

        # progress가 모두 0인지 확인 (첫 진입 여부)
        all_zero = all(progress.get(lane.get("id") or lane.get("tag"), 0) == 0 for lane in lanes if lane.get("id") or lane.get("tag"))

        if isinstance(pending_ctx, dict):
            pending_id = str(pending_ctx.get("lane_id") or "").strip().lower()
            pending_idx = int(pending_ctx.get("step_index") or 0)
            for lane in lanes:
                lane_id_val = _lane_identifier(lane).lower()
                if pending_id and (lane_id_val == pending_id or pending_id in lane_id_val):
                    active_lane = lane
                    steps = lane.get("steps") or []
                    if steps:
                        pending_idx = max(0, min(len(steps) - 1, pending_idx))
                        active_step = steps[pending_idx] if isinstance(steps[pending_idx], dict) else None
                        active_idx = pending_idx
                    break
            mission_store.pop("_pending_lane_ctx", None)
            if active_step and isinstance(active_step, dict):
                scene_key = active_step.get("scene_i18n")
                if scene_key:
                    beats_all = _resolve_beats({"beats_i18n": scene_key}, scenario, locale)
                else:
                    beats_all = _resolve_beats(active_lane or stage, scenario, locale)
            else:
                beats_all = _resolve_beats(active_lane or stage, scenario, locale)
        elif all_zero:
            # 첫 진입: intro_i18n 사용
            intro_key = stage.get("intro_i18n")
            if intro_key:
                beats_all = _resolve_beats({"beats_i18n": intro_key}, scenario, locale)
            else:
                beats_all = _resolve_beats(stage, scenario, locale)
            mission_intro = True
        else:
            # 진행 중: active_lane의 scene_i18n 사용
            # intent 기반으로 lane 우선순위 결정
            intent = _get_intent(state)
            intent_lower = intent.lower()

            sorted_lanes = []
            for lane in lanes:
                lane_id = lane.get("id") or lane.get("tag")
                if not lane_id:
                    continue
                steps = lane.get("steps") or []
                idx = int(progress.get(lane_id, 0))
                if idx >= len(steps):
                    continue
                step = steps[idx]
                if not isinstance(step, dict):
                    continue

                # intent와 매칭되는 action이 있는지 확인
                has_match = False
                if intent_lower:
                    actions = step.get("on_action") or []
                    has_match = any((rule.get("action") or "").strip().lower() == intent_lower for rule in actions)

                if has_match:
                    sorted_lanes.insert(0, (lane, step, idx))  # 매칭되는 lane을 앞에
                else:
                    sorted_lanes.append((lane, step, idx))

            # 첫 번째 유효한 lane을 active로 설정
            if sorted_lanes:
                active_lane, active_step, active_idx = sorted_lanes[0]

            if active_lane:
                # step 레벨의 scene_i18n이 있으면 우선 사용
                scene_key = None
                if active_step and isinstance(active_step, dict):
                    scene_key = active_step.get("scene_i18n")

                # step에 없으면 lane 레벨 scene_i18n 사용
                if not scene_key:
                    scene_key = active_lane.get("scene_i18n")

                if scene_key:
                    beats_all = _resolve_beats({"beats_i18n": scene_key}, scenario, locale)
                else:
                    beats_all = _resolve_beats(stage, scenario, locale)
            else:
                # 모든 lane 완료: stage 기본 beats
                beats_all = _resolve_beats(stage, scenario, locale)
            mission_intro = False

        current_lane_id = _lane_identifier(active_lane) if active_lane else ""
        if current_lane_id:
            scene["current_lane"] = current_lane_id

        if active_lane and active_step:
            step_pool = active_step.get("speaker_pool") or active_lane.get("speaker_pool")
            if isinstance(step_pool, list) and step_pool:
                lane_id = (_lane_identifier(active_lane) or "").lower()
                if lane_id and speakers:
                    # Preserve existing speaker ordering but promote the active lane's key actor(s)
                    def _promote(pool: List[str], key: str) -> List[str]:
                        key_norm = key.strip().lower()
                        prioritized = []
                        others = []
                        for sp in pool:
                            if isinstance(sp, str) and sp.strip().lower() == key_norm:
                                prioritized.append(sp)
                            else:
                                others.append(sp)
                        return prioritized + others if prioritized else pool

                    primary_hint = ""
                    if "inosuke" in lane_id:
                        primary_hint = "inosuke"
                    elif "zenitsu" in lane_id:
                        primary_hint = "zenitsu"
                    if primary_hint:
                        step_pool = _promote(step_pool, primary_hint)
                        speakers = _promote(speakers, primary_hint)
                speakers = step_pool
            elif not speakers:
                speakers = active_lane.get("speaker_pool") or speakers
            mission_ctx = {
                "lane_id": active_lane.get("id") or active_lane.get("tag"),
                "step_index": active_idx,
                "steps_total": len(active_lane.get("steps") or []),
                "remaining": max(0, len(active_lane.get("steps") or []) - active_idx),
            }
            mission_ctx["intro"] = mission_intro
            if lane_id:
                if "inosuke" in lane_id:
                    mission_ctx["attempts"] = state.get("inosuke_attempts", 0)
        elif lanes:
            # 모든 lane 완료한 경우 stage 전체 speaker_pool 사용
            speakers = speakers or stage.get("speaker_pool") or []
            if mission_intro:
                mission_ctx = {"intro": True}
        elif mission_intro:
            mission_ctx = {"intro": True}
    else:
        # mission이 아닌 타입: 기존 로직
        beats_all = _resolve_beats(stage, scenario, locale)

    # beats를 그대로 전달 (dict 형태 유지)
    # children_agent에서 speaker 정보가 있으면 활용
    # INTRO: 10개 beats를 모두 전달하여 풍부한 대화 유도 (children_agent에서 INTRO 전용 프롬프트 처리)
    beats_slice = beats_all

    payload = {
        "stage_tag": stage.get("tag") or stage_tag,
        "stage_type": stage.get("type"),
        "speaker_pool": speakers,
        "beats": beats_slice,
        "turn_index": state.get("turn_count", 0),
        "stage_turn_index": stage_turn,
        "vars": {
            "affinity": state.get("affinity_scores", {}) or state.get("affinity", {}),
            "time_left": state.get("time_left"),
        },
    }
    if mission_ctx:
        payload["mission"] = mission_ctx

    beats_count = len(beats_slice) if isinstance(beats_slice, list) else 0
    logger.info(f"Prepared children_ctx for stage '{stage_tag}': speaker_pool={speakers}, {beats_count} beats (type={stage.get('type')})")
    return payload

class ParentAgent:
    def step(self, state: Dict[str, Any], user_msg: Optional[str] = None) -> Dict[str, Any]:
        """
        1) 의도 소비/전환을 '가장 먼저' 수행
        2) 스테이지 초기화/보정
        3) children 컨텍스트 구성
        4) scene 타입이면 min_turns 로 자동 전환 + stage_turn 관리
        """
        start_time = time.perf_counter()

        def _finish(result_state: Dict[str, Any], label: str) -> Dict[str, Any]:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Elapsed {elapsed_ms:.2f} ms ({label})")
            return result_state
        # ---------- 0) 스테이지 키 동기화 ----------
        scene = state.setdefault("scene", {})
        # 이전 루프에서 표시용으로 남겨둔 스테이지 정보 초기화
        try:
            temp = state.get("temp_data") or {}
            if "display_stage" in temp:
                temp.pop("display_stage", None)
                state["temp_data"] = temp
        except Exception:
            pass
        # 역행 방지: intro_done 이후 INTRO로 되돌아오면 보정
        try:
            if (state.get("temp_data", {}).get("intro_done") and
                (state.get("current_stage") or "").upper() == "INTRO"):
                logger.info("[STAGE GUARD] intro_done set but current_stage=INTRO → correcting to ROUTE_CHOICE")
                state["current_stage"] = "ROUTE_CHOICE"
                scene["current_scene"] = "ROUTE_CHOICE"
        except Exception:
            pass

        before_cur = state.get("current_stage")
        before_scene = scene.get("current_scene")
        if scene.get("current_scene") and scene["current_scene"] != state.get("current_stage"):
            state["current_stage"] = scene["current_scene"]
        elif state.get("current_stage") and not scene.get("current_scene"):
            scene["current_scene"] = state["current_stage"]
        if before_cur != state.get("current_stage") or before_scene != scene.get("current_scene"):
            logger.info(f"[STAGE SYNC] cur:{before_cur} scene:{before_scene} → cur:{state.get('current_stage')} scene:{scene.get('current_scene')}")

        # ---------- 1) 의도 읽기 & 전환 (가장 먼저!) ----------
        # 여러 소스에서 의도 읽기 (router/intent_handler/backup 모두 커버)
        intent = (
            state.get("intent")
            or state.get("user_intent")
            or state.get("temp_data", {}).get("intent")
        )
        # 전환 시도 (INTRO 강의도는 즉시 전환 포함)
        state = _apply_intent_transition(state, intent)

        # ---------- 2) 시나리오 회수 ----------
        scenario = state.get("scenario") or state.get("scenario_data")
        if not _is_scenario_dict(scenario):
            scenario = _extract_scenario_from_state(state)
            if scenario:
                logger.info("Scenario reconstructed from state.")
                state["scenario_data"] = scenario
        if not _is_scenario_dict(scenario):
            logger.warning("No scenario available; cannot proceed this tick.")
            return _finish(state, "no_scenario")

        if not state.get("_scenario_defaults_applied"):
            _apply_state_defaults(state, scenario)
            state["_scenario_defaults_applied"] = True

        # 첫 실행 시 로깅
        if state.get("turn_count", 0) == 0:
            logger.info(
                f"Loaded scenario: {scenario.get('title', 'Unknown')} "
                f"(ID: {scenario.get('scenario_id', 'unknown')})"
            )

        # ---------- 3) 스테이지 보정(초기값: INTRO 또는 entry) ----------
        cur = state.get("current_stage")
        if not cur:
            if isinstance(scenario.get("stages"), list) and len(scenario["stages"]) > 0:
                first_stage = scenario["stages"][0]
                cur = first_stage.get("tag") or first_stage.get("id") or "INTRO"
            else:
                cur = scenario.get("entry") or "INTRO"
            state["current_stage"] = cur
            scene["current_scene"] = cur  # 동기화
            logger.info(f"Initial stage set to: {cur}")
        else:
            # 최신 전환 결과로 scene 키도 동기화
            scene["current_scene"] = cur

        history = state.get("stage_history")
        if not isinstance(history, list):
            history = []
        if cur and (not history or history[-1] != cur):
            history.append(cur)
        state["stage_history"] = history

        # ---------- 4) children 컨텍스트 구성 ----------
        _apply_ctx(state, scenario, cur)

        # ---------- 4.5) stage_turn 증가 (모든 스테이지 타입 공통) ----------
        scene = state.setdefault("scene", {})
        stage_turn = int(scene.get("stage_turn", 0)) + 1
        scene["stage_turn"] = stage_turn
        state["stage_turn"] = stage_turn  # 하위 호환성

        # ---------- 5) 스테이지별 전이 로직 (scene → min_turns 기반) ----------
        stage = _find_stage(scenario, cur)
        if not stage:
            logger.warning(f"Current stage '{cur}' not found in scenario")
            return _finish(state, "stage_missing")

        stage_type = (stage.get("type") or "").lower()
        constraints = stage.get("constraints") or {}
        min_turns = int(constraints.get("min_turns", 1))

        if stage_type == "ending":
            ending_tag = stage.get("tag") or cur
            if not state.get("final_ending"):
                state["final_ending"] = ending_tag
            temp = state.setdefault("temp_data", {})
            temp["session_end"] = True
            state["temp_data"] = temp
            state["has_more_dialogues"] = False
            logger.info(f"[PARENT] Ending stage '{ending_tag}' reached → session_end flag set")
            return _finish(state, "ending_reached")

        logger.info(
            f"[PARENT] Stage '{cur}' (type={stage_type}): stage_turn={stage_turn}, "
            f"min_turns={min_turns}, turn_count={state.get('turn_count', 0)}"
        )

        if stage_type == "scene":
            # scene 타입: min_turns 충족 시 자동 전환

            # ⬇️ INTRO 같은 하드 전환은 이미 1)에서 처리됨.
            # 여기서는 '컷신 유지' 로직만 담당
            if stage_turn >= min_turns and (cur or "").upper() != "INTRO":
                nxt = stage.get("next") or stage.get("goto")
                if not nxt:
                    next_map = stage.get("next_by_outcome")
                    if isinstance(next_map, dict):
                        outcome_key = stage.get("variant_by") or stage.get("result_key") or "_outcome"
                        outcome_val = state.get(outcome_key)
                        nxt = (
                            next_map.get(outcome_val)
                            or next_map.get(str(outcome_val))
                            or next_map.get("default")
                        )
                if nxt:
                    logger.info(
                        f"✅ Scene '{cur}': min_turns({min_turns}) met "
                        f"(stage_turn={stage_turn}), advancing to '{nxt}'"
                    )
                    _goto(state, nxt)
                    # stage_turn은 _goto에서 이미 리셋됨 (중복 제거)
            else:
                # 아직 컷신 유지
                logger.info(f"⏳ Scene '{cur}': turn {stage_turn}/{min_turns} (waiting...)")

        return _finish(state, "completed")


def run_parent_agent(state: dict, user_msg: Optional[str] = None) -> dict:
    """
    workflow.py가 기대하는 함수형 인터페이스.
    """
    agent = ParentAgent()
    new_state = agent.step(state, user_msg)
    return new_state

def parent_after_dialogue(state: dict) -> dict:
    """
    대화 출력 이후 후처리 훅
    - free_intent 스테이지에서 사용자 선택 처리
    - 상태 변수 업데이트 (battle_danger, mentor_margin, time_left)
    - 친밀도 업데이트 (중복 방지)
    """
    current_stage = state.get("current_stage", "")
    # 디버그: after_dialogue 시점의 인텐트/컨텍스트 스냅샷
    try:
        rr = state.get("routing_result") or {}
        dbg_intent = state.get("user_intent") or state.get("router_label") or rr.get("intent")
        ctx_tag = ((state.get("temp_data") or {}).get("children_ctx") or {}).get("stage_tag")
        spk = ((state.get("scene") or {}).get("speaker_pool"))
        logger.info(f"[AFTER] stage={current_stage} intent={dbg_intent} ctx_tag={ctx_tag} speakers={spk}")
    except Exception:
        pass

    # 🔥 턴 증가: **실제 사용자 입력**일 때만 turn_count 증가
    # __AUTO_CONTINUE__는 자동 재생이므로 유저 턴으로 카운트하지 않음
    user_input = (state.get("user_input") or "").strip()
    if user_input and user_input != "__AUTO_CONTINUE__":
        scene = state.setdefault("scene", {})
        old_turn_count = int(scene.get("turn_count", 0))
        scene["turn_count"] = old_turn_count + 1
        logger.info(f"[TURN] 🎮 User turn count incremented: {old_turn_count} → {scene['turn_count']}")

    # 의도 복구+고정: 중간 단계에서 유실되어도 sticky로 보존
    rr = state.get("routing_result") or {}
    sticky = (state.get("user_intent") or rr.get("intent") or "").strip().lower()
    if sticky:
        temp = state.get("temp_data") or {}
        temp["sticky_intent"] = sticky
        state["temp_data"] = temp
        state["user_intent"] = sticky

    scenario = state.get("scenario") or state.get("scenario_data") or {}
    for _ in range(12):
        current_stage = state.get("current_stage", "")
        stage = _find_stage(scenario, current_stage) or {}
        stage_type = (stage.get("type") or "").lower()
        changed = False

        if current_stage.upper() == "INTRO":
            # INTRO는 자동 재생 cutscene이므로 dialogue_batch_index로 진행 추적
            # (turn_count는 실제 유저 입력만 세므로 INTRO에서는 항상 0)
            batch_index = int(state.get("dialogue_batch_index", 0))
            min_batches = int(stage.get("constraints", {}).get("min_turns", 3))  # min_turns를 min_batches로 해석

            # 필요한 배치 수를 만족하면 전환
            if batch_index >= min_batches:
                next_stage = stage.get("next") or stage.get("goto") or "ROUTE_CHOICE"
                temp = state.get("temp_data") or {}
                temp["intro_done"] = True
                state["temp_data"] = temp
                if next_stage:
                    _goto(state, next_stage)
                _consume_intent(state)
                logger.info(f"[STAGE] 🎬 INTRO → {next_stage} (after {batch_index} batches, min: {min_batches})")
                changed = True
            else:
                # 아직 INTRO 유지
                logger.info(f"⏳ INTRO: batch {batch_index}/{min_batches} (auto-playing...)")
                changed = False
        elif stage_type == "free_intent":
            changed = _handle_free_intent_stage(state, stage)
        elif stage_type == "router":
            changed = _handle_router_stage(state, stage)
        elif stage_type == "mission":
            changed = _handle_mission_stage(state, stage)

        if not changed:
            changed = _apply_rules(state, stage)

        if not changed:
            break

        scenario = state.get("scenario") or state.get("scenario_data") or scenario
    else:
        logger.warning("[STAGE] Auto-transition loop exceeded safety limit")

    # 4. 친밀도 업데이트 (children_ctx 이후 즉시 적용, 그 다음 중복 방지 체크)
    affinity = state.get("affinity_scores", {}) or state.get("affinity", {})
    if not affinity:
        affinity = {"tanjiro": 0, "rengoku": 0, "inosuke": 0, "zenitsu": 0, "akaza": 0}

    # Intent-based affinity application (concise + robust)
    try:
        from kime_chat_agent_dev.src.utils.affinity import apply_rules, _intent_to_bundle
        intent_tags = state.get("intent_tags") or {}
        bundle = _intent_to_bundle(intent_tags)
        if not bundle:
            p = (intent_tags.get("player") or {})
            if any(v is True for v in p.values()):
                pool = ((state.get("children_ctx") or {}).get("speaker_pool") or (state.get("scene") or {}).get("speaker_pool") or [])
                pool = [c for c in pool if c not in ("system", "narr", "akaza")]
                if pool:
                    keys = [k for k, v in p.items() if v is True]
                    bundle = {c: keys[:] for c in pool}
        if bundle:
            apply_rules(state, bundle)
            try:
                print(f"[PARENT][AFF] bundle={bundle}")
            except Exception:
                pass
    except Exception:
        pass
    finally:
        state["affinity_scores"] = state.get("affinity", affinity)
        state["affinity"] = state.get("affinity", affinity)

    # 중복 방지 플래그 체크 (적용 후에 표기)
    turn_id = state.get("turn_count", 0)
    last_affinity_turn = state.get("_last_affinity_turn", -1)
    if turn_id == last_affinity_turn:
        return state
    state["_last_affinity_turn"] = turn_id

    return state
INOSUKE_MAX_ATTEMPTS = 3
