# children_agent.py
# - parent가 주입한 children_ctx를 표준화(stage_tag/stage_type/speaker_pool/beats)해서 사용
# - scenario에서 복원 가능(list/dict stages + beats_i18n 지원)
# - user 화자 허용 + 최소 1줄 보장
# - 플레이스홀더 치환({user.name}, {{user}}, {player}, {rengoku} 등)
# - LLM 실패 시 폴백

from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging, os, glob, json, random, hashlib, time
import re

logger = logging.getLogger("CHILDREN_LLM")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[CHILDREN_LLM] %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

DEFAULT_CHAR_DIR = os.path.join("data", "character_data")
_CHAR_DB: Optional[Dict[str, Any]] = None

# ---------- 안전 접근 ----------
def _state_get(state: Any, key: str, default=None):
    try:
        if isinstance(state, dict):
            return state.get(key, default)
        v = getattr(state, key, default)
        return v if v is not None else default
    except Exception:
        return default

def _nested_get(d: Any, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

# ---------- 시나리오/스테이지 ----------
def _get_scenario(state: Any) -> Optional[Dict[str, Any]]:
    for cand in (
        _state_get(state, "scenario"),
        _state_get(state, "scenario_data"),
        _nested_get(state, "game", "scenario"),
        _nested_get(state, "game", "scenario_data"),
    ):
        if isinstance(cand, dict):
            return cand
        if isinstance(cand, str) and os.path.exists(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return None

def _find_stage(scenario: Dict[str, Any], stage_tag: str) -> Optional[Dict[str, Any]]:
    stages = scenario.get("stages")
    cands: List[Dict[str, Any]] = []
    if isinstance(stages, list):
        cands = [s for s in stages if isinstance(s, dict)]
    elif isinstance(stages, dict):
        cands = [v for v in stages.values() if isinstance(v, dict)]
    tag_norm = (stage_tag or "").strip().lower()
    for st in cands:
        for key in ("tag", "id", "name", "slug"):
            v = st.get(key)
            if isinstance(v, str) and v.strip().lower() == tag_norm:
                return st
    return None

def _resolve_beats(stage: Dict[str, Any], scenario: Dict[str, Any], locale: str = "ko") -> List[str]:
    # 우선 beats
    beats = stage.get("beats")
    if not beats:
        # beats_i18n (스테이지 내부)
        bi18n = stage.get("beats_i18n") or {}
        if isinstance(bi18n, dict):
            beats = bi18n.get(locale) or bi18n.get("default") or []
    if isinstance(beats, list):
        out = []
        for b in beats:
            if isinstance(b, dict) and "text" in b:
                out.append(str(b["text"]))
            else:
                out.append(str(b))
        return out
    return []

def _speaker_pool_for_stage(stage: Dict[str, Any]) -> List[str]:
    for key in ("speaker_pool", "speakers", "characters", "actors"):
        val = stage.get(key)
        if isinstance(val, list) and val:
            return val
    return []

def _get_current_stage(state) -> str:
    return (_state_get(state, "current_stage", "") or "").strip()

# ---------- 캐릭터 DB ----------
def _load_character_db(char_dir: Optional[str]) -> Dict[str, Any]:
    global _CHAR_DB
    if _CHAR_DB is not None:
        return _CHAR_DB
    char_dir = char_dir or DEFAULT_CHAR_DIR
    db: Dict[str, Any] = {}
    for p in glob.glob(os.path.join(char_dir, "*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "characters" in data and isinstance(data["characters"], dict):
                data = data["characters"]
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        db[str(k).strip().lower()] = v
        except Exception:
            continue
    _CHAR_DB = db
    return db

# ---------- 텍스트/화자 정리 ----------
_SPEAKER_ALIASES = {
    "탄지로": "tanjiro", "tanjiro": "tanjiro",
    "렌고쿠": "rengoku", "rengoku": "rengoku", "렌고쿠 쿄쥬로": "rengoku",
    "아카자": "akaza", "akaza": "akaza",
    "이노스케": "inosuke", "inosuke": "inosuke",
    "젠이츠": "zenitsu", "zenitsu": "zenitsu",
    "사용자": "user", "유저": "user", "플레이어": "user", "user": "user",
}
def _normalize_speaker(speaker: str) -> str:
    s = (speaker or "").strip().lower()
    return _SPEAKER_ALIASES.get(s, s)

def _normalize_text(text: str) -> str:
    if not text: return text
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = re.sub(r"([.,!?;:])([^\s.,!?;:])", r"\1 \2", text)
    text = re.sub(r"([가-힣])([A-Za-z])", r"\1 \2", text)
    return text

def _apply_placeholders(text: str, state: dict) -> str:
    player = (state.get("player") or {}).get("name") \
             or (state.get("user_profile") or {}).get("name") \
             or state.get("user_name") or "당신"
    # 모든 플레이스홀더 변형을 {user_name}으로 통일
    text = (text or "").replace("{user.name}", player)
    text = text.replace("{{user.name}}", player)
    text = text.replace("{{user}}", player)
    text = text.replace("{user}", player)
    text = text.replace("{player}", player)
    text = text.replace("{user_name}", player)
    return text

def _placeholder_variants(key: str) -> List[str]:
    return [f"{{{key}}}", f"<{key}>", f"[{key}]", f"[[{key}]]", f"{{{{{key}}}}}"]

def _display_name_of(key: str, db: Dict[str, Any]) -> str:
    prof = db.get(key, {})
    return prof.get("display_name") or prof.get("name") or key

def _replace_placeholders(text: str, db: Dict[str, Any], state: dict) -> str:
    if not text: return text
    out = text
    # 캐릭터 이름 치환
    for k in list(db.keys()) + ["user"]:
        for p in _placeholder_variants(k):
            out = out.replace(p, _display_name_of(k, db))
    # 사용자 이름 치환
    out = _apply_placeholders(out, state)
    return _normalize_text(out)

# ---------- 폴백 합성 ----------
def _tone_bucket(score: Optional[int]) -> str:
    if score is None: return "neutral"
    if score < 201: return "distrust"
    if score < 401: return "wary"
    if score < 601: return "neutral"
    if score < 801: return "friendly"
    return "intimate"

def _seeded_choice(seq: List[str], seed_key: str, turn_index: int) -> str:
    if not seq: return ""
    seed = int(hashlib.md5(f"{seed_key}:{turn_index}".encode()).hexdigest(), 16) % (2**32)
    rnd = random.Random(seed)
    return rnd.choice(seq)

def _render_fallback_line(speaker: str, hint: str, profile: Dict[str, Any], turn_index: int, state: dict, db: dict) -> str:
    ticks = []
    style = profile.get("style") or {}
    tone = _tone_bucket((_state_get(state, "affinity", {}) or {}).get(speaker))
    bucket = (style.get(tone) or style.get("neutral")) if isinstance(style, dict) else {}
    ticks = bucket.get("ticks") or profile.get("ticks") or []
    tick = _seeded_choice(ticks, speaker, turn_index) if isinstance(ticks, list) else ""
    base = f"{tick} {hint}".strip()
    return _replace_placeholders(base, db, state)

# ---------- 컨텍스트 표준화 ----------
def _normalize_children_ctx(raw_ctx: Dict[str, Any], state: dict) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_ctx, dict):
        return None
    stage_tag = raw_ctx.get("stage_tag") or raw_ctx.get("tag") or _get_current_stage(state)
    stage_type = raw_ctx.get("stage_type") or raw_ctx.get("type") or "scene"
    speaker_pool = raw_ctx.get("speaker_pool") or raw_ctx.get("speakers") or raw_ctx.get("characters") or []
    beats = raw_ctx.get("beats")
    if not beats:
        bi18n = raw_ctx.get("beats_i18n") or {}
        if isinstance(bi18n, dict):
            loc = _state_get(state, "locale", "ko") or "ko"
            beats = bi18n.get(loc) or bi18n.get("default") or []
    if not stage_tag:
        return None
    return {
        "stage_tag": stage_tag,
        "stage_type": stage_type,
        "speaker_pool": speaker_pool,
        "beats": beats or [],
        "turn_index": int(_state_get(state, "turn_index", 0) or 0),
        "stage_turn_index": int(_state_get(state, "stage_turn", 0) or 0),
        "vars": {},
    }

def _pickup_ctx(state: Any) -> Optional[Dict[str, Any]]:
    # 1) agent_inputs.children 우선
    ai = _state_get(state, "agent_inputs", {}) or {}
    if isinstance(ai, dict) and isinstance(ai.get("children"), dict):
        norm = _normalize_children_ctx(ai["children"], state)
        if norm: return norm
    # 2) children_ctx 여러 위치 탐색
    for raw in (
        _state_get(state, "children_ctx"),
        _nested_get(state, "temp_data", "children_ctx"),
        _nested_get(state, "game", "children_ctx"),
    ):
        norm = _normalize_children_ctx(raw, state) if isinstance(raw, dict) else None
        if norm: return norm
    # 3) 시나리오에서 복원
    scenario = _get_scenario(state)
    stag = _get_current_stage(state)
    if scenario and stag:
        st = _find_stage(scenario, stag)
        if st:
            beats = _resolve_beats(st, scenario, _state_get(state, "locale", "ko") or "ko")
            speakers = _speaker_pool_for_stage(st)
            return {
                "stage_tag": st.get("tag") or stag,
                "stage_type": st.get("type") or "scene",
                "speaker_pool": speakers,
                "beats": beats,
                "turn_index": int(_state_get(state, "turn_index", 0) or 0),
                "stage_turn_index": int(_state_get(state, "stage_turn", 0) or 0),
                "vars": {},
            }
    return None

# ---------- 대사 생성 ----------
def _generate_dialogues(ctx: Dict[str, Any], state: dict, db: dict) -> tuple[List[Dict[str, str]], bool]:
    """
    Generate dialogues in batches of 3.
    Returns: (dialogues, has_more)
    """
    from src.utils.llm_client import get_llm_client

    speakers = ctx.get("speaker_pool") or []
    # 🚫 system, user 차단 — ✅ _env는 허용 (FX용)
    # USER는 실제 사용자 입력이므로 절대 생성하지 않음
    blocked = {"system", "시스템", "user", "사용자", "유저", "플레이어"}
    speakers = [s for s in speakers if isinstance(s, str) and s.strip() and _normalize_speaker(s) not in blocked]
    if not speakers:
        return [], False

    beats = ctx.get("beats") or []
    stage_tag = ctx.get("stage_tag", "unknown")
    stage_type = ctx.get("stage_type", "scene")

    # 배치 처리 로직: 몇 번째 배치인지, 총 몇 개 생성해야 하는지 추적
    batch_index = int(_state_get(state, "dialogue_batch_index", 0) or 0)
    dialogues_generated_so_far = int(_state_get(state, "dialogues_generated_count", 0) or 0)

    # 상황 요약 (beats가 dict면 goal 또는 text 추출)
    situation_goals = []
    if beats:
        for b in beats:
            if isinstance(b, dict):
                # goal 필드 우선 (상황 설명)
                goal = b.get("goal") or b.get("text", "")
                if goal:
                    situation_goals.append(goal)
            else:
                situation_goals.append(str(b))
    situation = "\n".join(situation_goals) if situation_goals else "상황을 자유롭게 연출하세요"

    # 캐릭터 설명
    char_desc = []
    for sp in speakers:
        prof = _load_character_db(None).get(sp, {})
        nm = prof.get("name") or sp
        per = prof.get("personality", "")
        char_desc.append(f"- {nm}: {per}")
    character_list = "\n".join(char_desc)

    # 최근 히스토리
    hist = _state_get(state, "message_history", []) or []
    rh = hist[-3:] if len(hist) > 3 else hist
    history_text = ""
    if rh:
        lines = []
        for m in rh:
            if isinstance(m, dict) and m.get("speaker") and m.get("text"):
                lines.append(f"{m['speaker']}: {m['text'][:50]}...")
        if lines:
            history_text = "\n이전 대화:\n" + "\n".join(lines)

    # 프롬프트
    user_input = _state_get(state, "last_user_msg") or _state_get(state, "user_input") or ""
    turn_idx = int(_state_get(state, "turn_index", 0) or 0)

    # 사용자 이름 가져오기
    user_name = state.get("user_name") or (state.get("player") or {}).get("name") or "당신"

    # 현재 턴에 해당하는 beat 정보 추출 (데이터 기반 우선 발화자 유도)
    beats = ctx.get("beats", [])
    stage_turn = ctx.get("stage_turn_index", 0)

    proactive_guide = ""
    if isinstance(beats, list) and 0 <= stage_turn < len(beats):
        current_beat = beats[stage_turn]
        if isinstance(current_beat, dict):
            speaker_hint = current_beat.get("speaker_hint", [])
            beat_goal = current_beat.get("goal", "")

            # speaker_hint가 있으면 해당 캐릭터가 먼저 발화하도록 유도
            if speaker_hint and beat_goal:
                speakers_str = ", ".join(speaker_hint)
                proactive_guide = f"""
=== 🎬 이번 턴 우선 발화 (데이터 기반) ===
**{speakers_str}**가 먼저 다음 상황을 전달해야 합니다:
"{beat_goal}"

→ 첫 1-2개 대사를 위 캐릭터들이 상황에 맞게 시작하세요.
→ 그 후 다른 캐릭터들이 자연스럽게 반응하며 대화를 이어갑니다.
"""

    # 스테이지별 목표 대화 개수 설정
    stage_upper = stage_tag.upper()

    # 스테이지별 총 필요 대화 개수
    total_dialogues_needed = {
        "INTRO": 12,  # 4 + 4 + 4 = 3배치
        "ROUTE_CHOICE": 8,
        "INTERVENE": 8,
        "RETURN_TO_FRONT": 8,  # 10 → 8 (4 + 4)
        "RECKLESS_SACRIFICE": 8,
    }.get(stage_upper, 8)  # 기본값도 8로 증가

    # 배치 크기: 4개 (일관성 있게)
    batch_size = 4  # 모든 배치에서 4개씩 생성

    # 남은 대화 개수 계산
    remaining_dialogues = total_dialogues_needed - dialogues_generated_so_far
    current_batch_size = min(batch_size, remaining_dialogues)

    # 더 생성할 대화가 있는지 확인
    # 🔥 free_intent 스테이지는 항상 첫 배치 후 사용자 입력 대기
    if stage_type == "free_intent":
        has_more = False  # 사용자 입력을 기다려야 하므로 auto-continue 차단
    else:
        has_more = (dialogues_generated_so_far + current_batch_size) < total_dialogues_needed

    # 배치별 상황 설명 (beats에서 현재 배치에 해당하는 부분만 선택)
    if beats and batch_index < len(beats):
        # 현재 배치에 해당하는 beat 선택
        current_beats = beats[batch_index:batch_index+1] if batch_index < len(beats) else []
    else:
        current_beats = beats

    # narr 발화 제어: INTRO의 경우 첫 배치(batch_index=0)에서만 narr 허용
    allow_narr_first = (batch_index == 0 and dialogues_generated_so_far == 0)
    # akaza 발화 제어: INTRO의 경우 마지막 배치에서만 akaza 허용
    allow_akaza_last = not has_more  # 마지막 배치일 때만

    if stage_upper == "INTRO":
        dialogue_rule = f"""**풍부한 연출**: 인트로 씬 - 현재 배치에서 **정확히 {current_batch_size}개**의 대화를 생성
   - 배치 진행: {dialogues_generated_so_far + 1}~{dialogues_generated_so_far + current_batch_size}번째 대화 (전체 {total_dialogues_needed}개 중)
   - narr는 {"맨 처음 1회만 허용" if allow_narr_first else "이번 배치에서 사용 금지 (이미 출력됨)"}
   - akaza는 {"마지막 배치이므로 1회 등장 가능" if allow_akaza_last else "이번 배치에서 사용 금지 (마지막 배치에만 등장)"}
   - tanjiro와 rengoku가 **교대로** 대화를 이끌어가며 상황을 설명
   - **대화 교차**: 같은 캐릭터가 연속으로 2회 이상 말하지 않기 (예: [tanjiro]→[rengoku]→[tanjiro])
   - **대화 마무리**: 마지막 대사는 반드시 NPC 캐릭터가 하며, {"사용자에게 질문하거나 다음 행동을 유도" if not has_more else "자연스럽게 상황 전개"}"""

    elif stage_upper == "ROUTE_CHOICE":
        dialogue_rule = f"""**선택 장면 연출**: 갈림길 선택 씬 - 현재 배치에서 **정확히 {current_batch_size}개**의 대화를 생성
   - 배치 진행: {dialogues_generated_so_far + 1}~{dialogues_generated_so_far + current_batch_size}번째 대화 (전체 {total_dialogues_needed}개 중)
   - narr는 {"맨 처음 1회만 허용" if allow_narr_first else "이번 배치에서 사용 금지 (이미 출력됨)"}
   - tanjiro가 주도하되 **rengoku의 반응을 교차**하며 위기 상황과 선택지를 설명
   - **대화 교차**: 같은 캐릭터가 연속으로 2회 이상 말하지 않기 (예: [narr]→[tanjiro]→[rengoku]→[tanjiro])
   - **대화 마무리**: 마지막 대사는 반드시 tanjiro가 하며, {"사용자에게 선택을 요청" if not has_more else "자연스럽게 상황 전개"}"""

    elif stage_upper == "INTERVENE":
        dialogue_rule = f"""**전투 개입 연출**: 급박한 전투 씬 - 현재 배치에서 **정확히 {current_batch_size}개**의 대화를 생성
   - 배치 진행: {dialogues_generated_so_far + 1}~{dialogues_generated_so_far + current_batch_size}번째 대화 (전체 {total_dialogues_needed}개 중)
   - narr는 {"맨 처음 1회만 허용" if allow_narr_first else "이번 배치에서 사용 금지 (이미 출력됨)"}
   - tanjiro, rengoku, akaza가 **번갈아가며** 격렬한 전투 상황 전개
   - **대화 교차**: 같은 캐릭터가 연속으로 2회 이상 말하지 않기 (예: [narr]→[tanjiro]→[rengoku]→[akaza])
   - **대화 마무리**: 마지막 대사는 반드시 tanjiro가 하며, {"사용자에게 개입 방법을 제안" if not has_more else "자연스럽게 전투 전개"}"""

    elif stage_upper == "RETURN_TO_FRONT":
        dialogue_rule = f"""**귀환 장면 연출**: 동료들과 함께 전장으로 돌아가는 씬 - 현재 배치에서 **정확히 {current_batch_size}개**의 대화를 생성
   - 배치 진행: {dialogues_generated_so_far + 1}~{dialogues_generated_so_far + current_batch_size}번째 대화 (전체 {total_dialogues_needed}개 중)
   - narr는 {"맨 처음 1회만 허용" if allow_narr_first else "이번 배치에서 사용 금지 (이미 출력됨)"}
   - 모든 동료(tanjiro, zenitsu, inosuke)가 **골고루 교차**하며 등장
   - 렌고쿠와 합류하는 감동적 장면 연출
   - **대화 교차**: 같은 캐릭터가 연속으로 2회 이상 말하지 않기 (예: [narr]→[tanjiro]→[zenitsu]→[inosuke]→[rengoku])
   - **대화 마무리**: 마지막 대사는 NPC 캐릭터가 하며, {"사용자에게 다음 행동을 유도" if not has_more else "자연스럽게 귀환 전개"}"""

    elif stage_upper == "RECKLESS_SACRIFICE":
        dialogue_rule = f"""**희생 장면 연출**: 무모한 선택의 결과를 보여주는 씬 - 현재 배치에서 **정확히 {current_batch_size}개**의 대화를 생성
   - 배치 진행: {dialogues_generated_so_far + 1}~{dialogues_generated_so_far + current_batch_size}번째 대화 (전체 {total_dialogues_needed}개 중)
   - narr는 {"맨 처음 1회만 허용" if allow_narr_first else "이번 배치에서 사용 금지 (이미 출력됨)"}
   - tanjiro, rengoku, akaza가 **교대로** 반응하며 치명적 부상 과정 묘사
   - 희생 분위기와 후회감 강조
   - **대화 교차**: 같은 캐릭터가 연속으로 2회 이상 말하지 않기 (예: [narr]→[tanjiro]→[rengoku]→[akaza])
   - **대화 마무리**: 마지막 대사는 NPC 캐릭터(narr 또는 tanjiro)가 하며, {"절망적 상황을 묘사" if not has_more else "자연스럽게 희생 장면 전개"}"""

    else:
        dialogue_rule = f"""**자유로운 연출**: 현재 배치에서 **정확히 {current_batch_size}개**의 대화를 생성
   - 배치 진행: {dialogues_generated_so_far + 1}~{dialogues_generated_so_far + current_batch_size}번째 대화 (전체 {total_dialogues_needed}개 중)
   - **대화 교차**: 같은 캐릭터가 연속으로 2회 이상 말하지 않기
   - **대화 마무리**: 마지막 대사는 NPC 캐릭터가 하며, {"사용자가 응답할 수 있도록 유도" if not has_more else "자연스럽게 상황 전개"}"""

    system_prompt = f"""당신은 귀멸의 칼날 스토리 게임의 **연출가이자 배우**입니다.
주어진 상황 설명을 바탕으로 캐릭터들의 대사, 발화 순서, 대화 흐름을 자유롭게 연출하세요.

=== 현재 상황 ===
{situation}

스테이지: {stage_tag} (타입: {stage_type})
턴: {turn_idx}
{history_text}
{proactive_guide}

=== 등장 캐릭터 ===
{character_list}

플레이어 이름: {user_name}

=== 사용자 입력 ===
"{user_input}"

=== 연출 규칙 ===
1. {dialogue_rule}
2. **대화 교차 원칙** (매우 중요!):
   - 같은 speaker가 연속으로 2회 이상 대사를 하지 않도록 주의
   - 캐릭터 간 자연스럽게 대화를 주고받아야 함
   - ✅ 좋은 예: [tanjiro] → [rengoku] → [tanjiro] → [narr] → [rengoku]
   - ❌ 나쁜 예: [tanjiro] → [tanjiro] → [tanjiro] → [rengoku] → [rengoku]
3. **대화 마무리 원칙** (필수!):
   - 마지막 대사는 **반드시 NPC 캐릭터**(narr, tanjiro, rengoku 등)가 해야 함
   - 마지막 대사는 사용자가 응답할 수 있도록 질문, 제안, 또는 행동 유도로 끝내기
   - ✅ 좋은 예: [tanjiro]: "태민, 어떻게 할까요? 결정해주세요!"
   - ❌ 나쁜 예: [narr]: "그렇게 긴박한 상황이 계속되었다." (응답 유도 없음)
4. **캐릭터 연기**: 각 캐릭터의 성격과 말투를 살려 2~3문장으로 연기
   - 아카자: 조롱적이고 냉혹하며 강자를 인정. "흥, 인간 주제에 재미있군."
   - 렌고쿠: 단호하고 격려적이며 책임감 강함. "음! 훌륭하다!"
   - 탄지로: 염려하고 관찰력 있으며 정서적 유도. "조심하세요!"
5. **사용자 반영**: 사용자 입력에 맞춰 캐릭터들이 자연스럽게 반응
6. **긴장감 유지**: 보스전이므로 긴박하고 생동감 있게
7. **플레이어 호칭**: "{user_name}"으로 직접 호칭
8. **speaker 키**: tanjiro, rengoku, akaza, zenitsu, inosuke 중 선택

⚠️ 중요:
- 절대 'user' speaker로 대사 생성 금지 (사용자가 직접 입력)
- 상황 설명을 그대로 복사 금지, 자연스러운 대사로 재창조
- 이전 대화와 중복 금지, 매번 새로운 전개
- **같은 캐릭터가 연속으로 말하지 않도록 반드시 확인**
- **마지막 대사는 반드시 NPC 캐릭터가 사용자에게 질문/제안으로 끝내기**
"""

    # 스테이지별 user_prompt 설정
    if stage_upper == "INTRO":
        narr_instruction = "- narr는 맨 처음 1회만" if allow_narr_first else "- narr는 사용 금지 (이미 출력됨)"
        akaza_instruction = "- akaza는 마지막 상황에서 1회 등장" if allow_akaza_last else "- akaza는 사용 금지 (마지막 배치에만 등장)"
        user_prompt = f'사용자 입력: "{user_input}"\n\n위 "현재 상황"의 각 단계를 **순서대로** 반영하여 **정확히 {current_batch_size}개**의 캐릭터 대사를 생성하세요.\n{narr_instruction}\n{akaza_instruction}\n- 나머지는 tanjiro, rengoku가 상황을 설명하며 대화\n- **같은 캐릭터가 연속으로 2회 이상 말하지 않기**\n- **마지막 대사는 NPC 캐릭터가 {"사용자에게 질문/제안으로 끝내기" if not has_more else "자연스럽게 상황 전개"}**\n\nJSON: {{"dialogues":[{{"speaker":"...","text":"..."}},{{"speaker":"...","text":"..."}},...]}}'

    elif stage_upper == "ROUTE_CHOICE":
        narr_instruction = "- narr는 맨 처음 1회만 (전투 직후 상황 묘사)" if allow_narr_first else "- narr는 사용 금지 (이미 출력됨)"
        user_prompt = f'사용자 입력: "{user_input}"\n\n위 "현재 상황"을 **순서대로** 반영하여 **정확히 {current_batch_size}개**의 캐릭터 대사를 생성하세요.\n{narr_instruction}\n- tanjiro가 주도하며 렌고쿠의 위기와 선택지를 설명\n- **같은 캐릭터가 연속으로 2회 이상 말하지 않기**\n- **마지막 대사는 tanjiro가 {"사용자에게 선택을 요청하며 끝내기" if not has_more else "자연스럽게 상황 전개"}**\n\nJSON: {{"dialogues":[{{"speaker":"...","text":"..."}},{{"speaker":"...","text":"..."}},...]}}'

    elif stage_upper == "INTERVENE":
        narr_instruction = "- narr는 맨 처음 1회만 (전장 접근 장면)" if allow_narr_first else "- narr는 사용 금지 (이미 출력됨)"
        user_prompt = f'사용자 입력: "{user_input}"\n\n위 "현재 상황"을 **순서대로** 반영하여 **정확히 {current_batch_size}개**의 캐릭터 대사를 생성하세요.\n{narr_instruction}\n- rengoku와 akaza의 격렬한 전투 묘사\n- tanjiro가 개입 방법을 제시하며 긴박함 강조\n- **같은 캐릭터가 연속으로 2회 이상 말하지 않기**\n- **마지막 대사는 tanjiro가 {"사용자에게 개입 방법을 제안하며 끝내기" if not has_more else "자연스럽게 전투 전개"}**\n\nJSON: {{"dialogues":[{{"speaker":"...","text":"..."}},{{"speaker":"...","text":"..."}},...]}}'

    elif stage_upper == "RETURN_TO_FRONT":
        narr_instruction = "- narr는 맨 처음 1회만 (전장 귀환 장면)" if allow_narr_first else "- narr는 사용 금지 (이미 출력됨)"
        user_prompt = f'사용자 입력: "{user_input}"\n\n위 "현재 상황"을 **순서대로** 반영하여 **정확히 {current_batch_size}개**의 캐릭터 대사를 생성하세요.\n{narr_instruction}\n- 모든 동료(tanjiro, zenitsu, inosuke)가 골고루 등장\n- 렌고쿠와 합류하는 감동적 장면 연출\n- **같은 캐릭터가 연속으로 2회 이상 말하지 않기**\n- **마지막 대사는 NPC 캐릭터가 {"사용자에게 다음 행동을 유도하며 끝내기" if not has_more else "자연스럽게 귀환 전개"}**\n\nJSON: {{"dialogues":[{{"speaker":"...","text":"..."}},{{"speaker":"...","text":"..."}},...]}}'

    elif stage_upper == "RECKLESS_SACRIFICE":
        narr_instruction = "- narr는 맨 처음 1회만 (무모한 돌입 장면)" if allow_narr_first else "- narr는 사용 금지 (이미 출력됨)"
        user_prompt = f'사용자 입력: "{user_input}"\n\n위 "현재 상황"을 **순서대로** 반영하여 **정확히 {current_batch_size}개**의 캐릭터 대사를 생성하세요.\n{narr_instruction}\n- 렌고쿠가 치명적 부상을 입는 과정 묘사\n- 희생 분위기와 후회감 강조\n- **같은 캐릭터가 연속으로 2회 이상 말하지 않기**\n- **마지막 대사는 NPC 캐릭터(narr 또는 tanjiro)가 {"절망적 상황을 묘사하며 끝내기" if not has_more else "자연스럽게 희생 장면 전개"}**\n\nJSON: {{"dialogues":[{{"speaker":"...","text":"..."}},{{"speaker":"...","text":"..."}},...]}}'

    else:
        user_prompt = f'사용자 입력: "{user_input}"\n위 상황을 반영하여 **정확히 {current_batch_size}개**의 캐릭터 대사를 생성하세요.\n- **같은 캐릭터가 연속으로 2회 이상 말하지 않기**\n- **마지막 대사는 NPC 캐릭터가 {"사용자에게 응답 유도하며 끝내기" if not has_more else "자연스럽게 상황 전개"}**\n\nJSON: {{"dialogues":[{{"speaker":"...","text":"..."}}]}}'

    try:
        llm = get_llm_client()
        res = llm.call_json(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.8)
        items = (res or {}).get("dialogues") or []
    except Exception as e:
        logger.warning(f"LLM error: {e}; fallback composing")
        items = []

    # 후처리 - LLM 생성 대사만 사용 (beats는 힌트로만 활용)
    out: List[Dict[str, str]] = []

    # narr가 이미 나왔는지 추적 (주요 스테이지에서 사용)
    narr_already_output = False

    # narr 필터링이 필요한 스테이지 목록
    narr_filter_stages = ["INTRO", "ROUTE_CHOICE", "INTERVENE", "RETURN_TO_FRONT", "RECKLESS_SACRIFICE"]

    for it in items:
        sp = _normalize_speaker(it.get("speaker", ""))
        tx = _normalize_text(it.get("text", ""))
        if not sp or not tx:
            continue

        # 주요 스테이지에서 narr 필터링 (첫 번째 배치에서만 허용)
        if stage_upper in narr_filter_stages:
            if sp == "narr":
                # 첫 배치가 아니거나, 첫 배치 내에서 이미 narr가 출력되었으면 스킵
                if not allow_narr_first or narr_already_output:
                    logger.info(f"[{stage_upper}] Skipping narr - batch_index={batch_index}, already_output={narr_already_output}")
                    continue
                narr_already_output = True

        # akaza 필터링 (마지막 배치에서만 허용)
        if stage_upper in narr_filter_stages:
            if sp == "akaza":
                if not allow_akaza_last:
                    logger.info(f"[{stage_upper}] Skipping akaza - not last batch (batch_index={batch_index})")
                    continue

        # 미등록 스피커는 speaker_pool로 보정 시도
        if sp not in speakers and sp not in _load_character_db(None):
            for cand in speakers:
                prof = _load_character_db(None).get(cand, {})
                if it.get("speaker") == prof.get("name"):
                    sp = cand
                    break
        out.append({"speaker": sp, "text": _replace_placeholders(tx, _load_character_db(None), state)})

    # # USER 최소 1줄 보장
    # pool_norm = [_normalize_speaker(s) for s in speakers]
    # if "user" in pool_norm and not any(x["speaker"] == "user" for x in out):
    #     uin = _state_get(state, "last_user_msg") or _state_get(state, "user_input") or ""
    #     uline = f"내 생각은 이래. {uin}" if uin else "나는 동료들을 먼저 모으겠어."
    #     out.insert(0, {"speaker": "user", "text": _replace_placeholders(_normalize_text(uline), _load_character_db(None), state)})

    # LLM이 아무 것도 못 만들면 폴백
    # if not out:
    #     beats = ctx.get("beats") or ["상황을 간단히 설명한다."]
    #     t = int(_state_get(state, "turn_index", 0) or 0)
    #     for sp in pool_norm[:3]:
    #         prof = _load_character_db(None).get(sp, {})
    #         out.append({"speaker": sp, "text": _render_fallback_line(sp, beats[0], prof, t, state, _load_character_db(None))})

    return out, has_more

# ---------- 엔트리 ----------
class ChildrenAgent:
    def run(self, state: Any) -> Any:
        start_time = time.perf_counter()

        def _finish(result_state: Any, label: str) -> Any:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Elapsed {elapsed_ms:.2f} ms ({label})")
            return result_state

        # 캐릭터 DB 미리 로드 + user를 가상 캐릭터로 주입(치환용)
        paths = _state_get(state, "paths", {}) or {}
        char_dir = (paths or {}).get("character_dir")
        db = _load_character_db(char_dir)
        user_name = (
            _state_get(state, "user_name")
            or _nested_get(state, "user_profile", "display_name")
            or _nested_get(state, "meta", "user_display_name")
        )
        if user_name:
            db["user"] = {"display_name": user_name, "name": user_name, "aliases": ["player", "주인공"]}

        # 컨텍스트 확보
        ctx = _pickup_ctx(state)
        if not ctx:
            logger.warning("No context and cannot reconstruct; skipping")
            return _finish(state, "no_context")

        # 대사 생성 (배치 모드)
        replies, has_more = _generate_dialogues(ctx, state, db)
        if not replies:
            logger.info("No dialogues generated.")
            return _finish(state, "no_dialogues")

        # 배치 진행 상태 업데이트
        batch_index = int(_state_get(state, "dialogue_batch_index", 0) or 0)
        dialogues_generated = int(_state_get(state, "dialogues_generated_count", 0) or 0)

        # 새로 생성된 대화 개수 누적
        new_count = dialogues_generated + len(replies)

        # 상태 업데이트
        if isinstance(state, dict):
            state["dialogue_batch_index"] = batch_index + 1
            state["dialogues_generated_count"] = new_count
            state["has_more_dialogues"] = has_more
        else:
            try:
                setattr(state, "dialogue_batch_index", batch_index + 1)
                setattr(state, "dialogues_generated_count", new_count)
                setattr(state, "has_more_dialogues", has_more)
            except Exception:
                pass

        # 상태 반영
        buf = _state_get(state, "agent_responses", []) or []
        buf.extend(replies)
        if isinstance(state, dict):
            state["agent_responses"] = buf
        else:
            try:
                setattr(state, "agent_responses", buf)
            except Exception:
                pass

        # 히스토리 축적(최대 20)
        hist = _state_get(state, "message_history", []) or []
        hist.extend(replies)
        if len(hist) > 20:
            hist = hist[-20:]
        if isinstance(state, dict):
            state["message_history"] = hist
        else:
            try:
                setattr(state, "message_history", hist)
            except Exception:
                pass

        speakers = [r["speaker"] for r in replies]
        logger.info(f"✅ Generated {len(replies)} dialogues (batch {batch_index + 1}, has_more: {has_more}): {speakers}")
        return _finish(state, "completed")

DEFAULT_AGENT = ChildrenAgent()

def run_children_agent(state: Any) -> Any:
    return DEFAULT_AGENT.run(state)
