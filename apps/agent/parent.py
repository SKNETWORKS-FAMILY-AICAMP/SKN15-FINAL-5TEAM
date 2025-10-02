"""
High-level flow (Router → Guardrail → Parent → Children)

1) Router/Guardrail → ContextEnvelope 생성

2) Parent.step(state, envelope)
   a. build_prompt(state, envelope)로 Children에 줄 “문제지(JSON)” 구성
   b. Children 호출 → ParentLLMResult(JSON) 수신
   c. 검증(Validation)
   d. 분기 결정(Branch resolve)
   e. 상태 병합(State merge)
   f. 반환

3) scenes.json(또는 등가 데이터) 구조 요약

4) apply_patch 핵심

Contract
- Children은 분기를 스스로 결정하지 않음(대사/연기만).
- Parent만이 최종 분기·검증·병합을 담당.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TypedDict, Dict, Any, Optional, List
import json, datetime, os
from pydantic import BaseModel, Field, ConfigDict

# ============================================
# 0) GameState 타입
#    - "한 턴 직전/직후"의 게임 진행 스냅샷
#    - ParentAgent.step()의 입력/출력으로 사용
# ============================================
class GameState(TypedDict, total=False):
    # 1) IDs (세션/시나리오/유저 식별)
    user_id: Optional[str]
    session_id: str
    scenario_id: str

    # 2) 진행 상태
    scene: Dict[str, Any]             # {"current_scene": "scene_id"}
    route: Optional[str]

    # 3) 카운터/자원
    turn: int
    total_turns_used: int
    character_turns_used: Dict[str, int]

    # 4) 상태
    allies: Dict[str, bool]
    affinity: Dict[str, int]
    flags: List[str]

    # 5) 결과
    ending: str
    end_reason: str

    # 6) 상호작용 컨텍스트
    user_choice: Optional[str]
    last_user_msg: str

    # 7) 히스토리/메타
    scene_history: List[str]
    updated_at: str


# ============================================
# Router/Guardrail가 Parent로 넘겨주는 Envelope
# ============================================

class ContextEnvelope(TypedDict, total=False):
    session_id: str                  # 세션 식별자
    turn: int                        # 현재 턴
    language: str                    # "ko"/"en" 등
    user_msg_raw: str                # 유저 원문 (또는 이미 정제된 문장)
    recent_messages: List[Dict[str, str]]  # 최근 4~5턴 로그
    rolling_summary: str             # 압축 요약

    # 선택(있으면 사용, 없으면 생략)
    router_choice_hint: Dict[str, Any]     # {"value":"gather_allies","confidence":0.82}
    router_intent: Dict[str, Any]          # {"label":"continue_story","confidence":0.86}
    guardrail: Dict[str, Any]              # {"allowed": True, "sanitized_user_msg": "...", "reason":"OK"}

# ============================================
# speaker_rules 해석기: 허용 화자 동적 계산
# ============================================
def _resolve_allowed_speakers(scene_def: dict, state: Dict[str, Any]) -> List[str]:
    base = scene_def.get("allowed_speakers", []) or []
    rules = scene_def.get("speaker_rules", []) or []
    flags = set(state.get("flags", []))

    for rule in rules:
        req = set(rule.get("require_flags", []))
        forbid = set(rule.get("forbid_flags", []))
        if not req.issubset(flags):
            continue
        if forbid & flags:
            continue
        if "override" in rule:
            # override가 있으면 그걸 최종 허용 화자로 사용
            return list(dict.fromkeys(rule["override"]))
    return list(dict.fromkeys(base))


# ============================================
# JSON 로더 (scenes.json 등)
# ============================================
def load_json(source: str | dict) -> dict:
    if isinstance(source, dict):
        return source
    if not isinstance(source, str):
        raise TypeError("load_json: source must be dict or str(path)")
    if not os.path.exists(source):
        raise FileNotFoundError(f"JSON file not found: {source}")
    with open(source, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================
# Repo들 (정적 데이터 접근)
# ============================================
class ScenesRepo:
    def __init__(self, data: dict):
        self._d = data

    def get_scene(self, scene_id: str) -> dict:
        return self._d.get(scene_id, {})

    def has_choice_id(self, scene_id: str, choice_id: str) -> bool:
        scene = self.get_scene(scene_id)
        return any(c.get("id") == choice_id for c in scene.get("choices", []))


class CharactersRepo:
    def __init__(self, data: dict):
        self._d = data

    def get(self, char_id: str) -> dict:
        return self._d.get(char_id, {})

    def all_ids(self) -> List[str]:
        return list(self._d.keys())


class ImagesRepo:
    def __init__(self, data: dict):
        self._d = data

    def has(self, rid: str) -> bool:
        return rid in self._d

    def get(self, rid: str) -> dict:
        return self._d.get(rid, {})


# ============================================
# LLM 결과 스키마(엄격 검증)
# ============================================
class Line(BaseModel):
    speaker: str
    text: str
    model_config = ConfigDict(extra="forbid")


class Choice(BaseModel):
    id: str
    text: str
    value: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


class ParentLLMResult(BaseModel):
    narration: str
    lines: List[Line] = Field(default_factory=list)
    choices: List[Choice] = Field(default_factory=list)
    state_patch: Dict[str, Any]
    image_resource_id: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


# ============================================
# 보조: 친밀도 → 톤 키 선택
# ============================================
def select_tone_level(affinity_val: int) -> str:
    if affinity_val >= 801: return "high"
    if affinity_val >= 401: return "medium"
    return "low"


# ============================================
# 자유 발화 백업 매핑: user_msg → choice.value
# ============================================
def parse_user_choice_alias(user_msg: str, scene_def: dict) -> Optional[str]:
    msg = user_msg.strip().lower()
    for ch in scene_def.get("choices", []):
        aliases = [ch.get("value",""), ch.get("text","")] + ch.get("aliases", [])
        aliases = [a.lower() for a in aliases if a]
        if any(a and a in msg for a in aliases):
            return ch.get("value")
    return None


# ============================================
# ParentAgent
# ============================================
@dataclass
class ParentAgent:
    scenes: ScenesRepo
    llm: Any  # Callable[[str], str] 형태여야 함
    characters: Optional[CharactersRepo] = None
    images: Optional[ImagesRepo] = None

    # Router의 힌트를 Parent가 받아들이는 최소 확신도
    INTENT_CONF_THRESHOLD: float = 0.75

    @staticmethod
    def _sanitize_user_msg(envelope: ContextEnvelope) -> str:
        return (envelope.get("guardrail") or {}).get("sanitized_user_msg") \
               or envelope.get("user_msg_raw","")

    def build_prompt(self, state: Dict[str, Any], envelope: ContextEnvelope) -> str:
        """
        Children LLM에게 넘길 '문제지' 생성:
        - 어떤 화자만 말할 수 있는지, 이번 씬의 비트(beats)와 선택지 스펙은 무엇인지
        - Parent가 분기를 결정하므로, Children은 분기 결정을 하지 말라는 규칙 포함
        """
        current_scene = (state.get("scene") or {}).get("current_scene", "scene5_fork")
        scene_def = self.scenes.get_scene(current_scene) # ✅ Repo 사용

        tone_hint = None
        if self.characters:
            tanjiro = self.characters.get("tanjiro")
            tone_map = tanjiro.get("tone", {}) if tanjiro else {}
            aff = state.get("affinity", {}).get("tanjiro", 500)
            tone_hint = tone_map.get(select_tone_level(aff))

        prompt = {
            "system": {
                "allowed_speakers": scene_def.get("allowed_speakers", []),
                "beats": scene_def.get("beats", {}),
                "choice_spec": scene_def.get("choices", []),
                "tone_hint": tone_hint,
                "output_schema": {
                    "narration": "str",
                    "lines": [{"speaker":"str","text":"str"}],
                    "choices": [{"id":"str","text":"str","value?":"str"}],
                    "state_patch": "object (subset of GameState)",
                    "image_resource_id?": "str"
                },
                "rules": [
                    "No meta talk about internal state (turns/affinity/etc).",
                    "Follow allowed_speakers and choice_spec.",
                    "Do not decide a branch; the parent decides based on router hints."
                ]
            },
            "state_view": {
                "current_scene": current_scene,
                "affinity": state.get("affinity", {}),
                "allies": state.get("allies", {}),
            },
            # Children이 참고는 하되, 스스로 분기하지 않게 규칙으로 제어
            "router_hint": envelope.get("router_choice_hint", {}),
            "recent_messages": envelope.get("recent_messages", []),
            "rolling_summary": envelope.get("rolling_summary", ""),
            "user_msg": self._sanitize_user_msg(envelope),
        }
        return json.dumps(prompt, ensure_ascii=False)

    def step(self, state: Dict[str, Any], envelope: ContextEnvelope) -> Dict[str, Any]:
        """
        한 턴 처리:
        1) Children 호출 → 2) 결과 스키마·화자·선택 검증
        3) Router 힌트(+자연어 alias 백업)로 분기 결정 → 4) state_patch 병합 → 5) 렌더 페이로드 반환
        """
        user_msg = self._sanitize_user_msg(envelope)

        # 1) Children 호출
        prompt = self.build_prompt(state, envelope)
        raw = self.llm(prompt)  # 반드시 JSON 문자열 반환
        parsed = ParentLLMResult(**json.loads(raw))

        # 2) 검증
        current_scene = (state.get("scene") or {}).get("current_scene", "scene5_fork")
        scene_def = self.scenes.get_scene(current_scene)

        allowed = set(_resolve_allowed_speakers(scene_def, state))
        if allowed:
            for ln in parsed.lines:
                if ln.speaker not in allowed:
                    raise ValueError(f"speaker not allowed in this scene: {ln.speaker}")

        valid_choice_ids = {c["id"] for c in scene_def.get("choices", [])}
        if valid_choice_ids:
            for ch in parsed.choices:
                if ch.id not in valid_choice_ids:
                    raise ValueError(f"invalid choice id: {ch.id}")

        if parsed.image_resource_id and self.images and not self.images.has(parsed.image_resource_id):
            raise ValueError(f"image not found: {parsed.image_resource_id}")

        # 3) 최종 선택값 결정: Router 힌트 우선 → alias 백업
        allowed_values = {c.get("value") for c in scene_def.get("choices", []) if c.get("value")}
        choice_value: Optional[str] = None

        rh = (envelope.get("router_choice_hint") or {})
        if rh.get("value") in allowed_values and float(rh.get("confidence", 0)) >= self.INTENT_CONF_THRESHOLD:
            choice_value = rh["value"]
        if not choice_value:
            choice_value = parse_user_choice_alias(user_msg, scene_def)

        # 4) split_rules로 분기 계산
        patch_from_choice: Dict[str, Any] = {}
        if choice_value:
            sr = eval_split_rules(scene_def, state, choice_value)
            if sr:
                patch_from_choice = {
                    "user_choice": choice_value,
                    "scene": {"current_scene": sr["goto"]},
                }
                if sr.get("set"):
                    patch_from_choice.update(sr["set"])  # 필요시 추가 패치(set)

        # 5) 상태 병합 (Children patch → choice patch 순서로 override)
        base = {**state, "last_user_msg": user_msg}
        merged_patch: Dict[str, Any] = {}
        merged_patch.update(parsed.state_patch or {})
        merged_patch.update(patch_from_choice)

        new_state = apply_patch(base, merged_patch)

        return {
            "render": {
                "narration": parsed.narration,
                "lines": [l.model_dump() for l in parsed.lines],
                "choices": [c.model_dump() for c in parsed.choices],
                "image": parsed.image_resource_id,
            },
            "state": new_state,
        }


# ============================================
# apply_patch 및 규칙들
# ============================================
MISSION_TURNS_LIMIT = 8
CHAR_TURNS_LIMIT = 3

# 플래그 상수
FLAG_RECRUIT_INOSUKE = "recruited_inosuke"
FLAG_RECRUIT_ZENITSU = "recruited_zenitsu"
FLAG_ORDER_FIRST_INOSUKE = "order_first_inosuke"
FLAG_ORDER_INOSUKE_THEN_ZENITSU = "order_inosuke_then_zenitsu"
FLAG_HIDDEN_ELIGIBLE = "hidden_ending_eligible"

def _iso_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))

def _hidden_eligible(s: Dict[str, Any], flags: set[str]) -> bool:
    # 히든 조건: 이노스케→젠이츠 순서 + 각 3회 이하 + 총 8턴 이하
    if FLAG_ORDER_INOSUKE_THEN_ZENITSU not in flags:
        return False
    ct = s.get("character_turns_used", {}) or {}
    ino = int(ct.get("inosuke", 0))
    zen = int(ct.get("zenitsu", 0))
    total = int(s.get("total_turns_used", 0))
    return (ino <= CHAR_TURNS_LIMIT) and (zen <= CHAR_TURNS_LIMIT) and (total <= MISSION_TURNS_LIMIT)

def apply_patch(state: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    룰 엔진(병합 정책): 숫자 증감 {$inc}, 얕은 병합, flags/allies 파생 규칙 동기화
    """
    s: Dict[str, Any] = {**state}

    def _inc_key(key: str, dv: int, lo: Optional[int] = None, hi: Optional[int] = None):
        cur = int(s.get(key, 0)) + int(dv)
        if lo is not None: cur = max(lo, cur)
        if hi is not None: cur = min(hi, cur)
        s[key] = cur

    # turn / total_turns_used
    if "turn" in patch:
        v = patch["turn"]
        if isinstance(v, dict) and "$inc" in v:
            _inc_key("turn", int(v["$inc"]), lo=0)
        else:
            s["turn"] = max(0, int(v))

    if "total_turns_used" in patch:
        v = patch["total_turns_used"]
        if isinstance(v, dict) and "$inc" in v:
            _inc_key("total_turns_used", int(v["$inc"]), lo=0)
        else:
            s["total_turns_used"] = max(0, int(v))

    # character_turns_used
    if "character_turns_used" in patch:
        base = dict(s.get("character_turns_used", {}))
        for ch, v in patch["character_turns_used"].items():
            if isinstance(v, dict) and "$inc" in v:
                base[ch] = max(0, int(base.get(ch, 0)) + int(v["$inc"]))
            else:
                base[ch] = max(0, int(v))
        s["character_turns_used"] = base

    # scene (얕은 병합)
    if "scene" in patch:
        base = dict(s.get("scene", {}))
        pv = patch["scene"]
        if not isinstance(pv, dict):
            raise ValueError("scene patch must be an object")
        base.update(pv)
        s["scene"] = base

    # affinity (0~1000 clamp)
    if "affinity" in patch:
        base = dict(s.get("affinity", {}))
        for k, v in patch["affinity"].items():
            if isinstance(v, dict) and "$inc" in v:
                base[k] = _clamp(int(base.get(k, 0)) + int(v["$inc"]), 0, 1000)
            else:
                base[k] = _clamp(int(v), 0, 1000)
        s["affinity"] = base

    # allies (bool 덮어쓰기)
    allies_changed = False
    if "allies" in patch:
        base = dict(s.get("allies", {}))
        for k, v in patch["allies"].items():
            base[k] = bool(v)
        s["allies"] = base
        allies_changed = True

    # flags (add/remove/교체)
    flags_changed = False
    if "flags" in patch:
        base = list(s.get("flags", []))
        op = patch["flags"]
        if isinstance(op, dict):
            add = op.get("$add", [])
            rem = op.get("$remove", [])
            if add:
                for f in add:
                    if f not in base: base.append(f)
            if rem:
                base = [f for f in base if f not in rem]
        elif isinstance(op, list):
            base = list(dict.fromkeys(op))
        else:
            raise ValueError("flags patch must be list or object with $add/$remove")
        s["flags"] = base
        flags_changed = True

    # 잡다 필드
    if "route" in patch: s["route"] = patch["route"]
    if "ending" in patch: s["ending"] = patch["ending"]

    if "end_reason" in patch:
        if not s.get("end_reason"):
            s["end_reason"] = patch["end_reason"]

    if "user_choice" in patch: s["user_choice"] = patch["user_choice"]

    if "dialogue_rules" in patch:
        base = dict(s.get("dialogue_rules", {}))
        pv = patch["dialogue_rules"]
        if not isinstance(pv, dict):
            raise ValueError("dialogue_rules patch must be an object")
        base.update(pv)
        s["dialogue_rules"] = base

    # scene_history
    if "scene_history" in patch:
        base = list(s.get("scene_history", []))
        op = patch["scene_history"]
        if isinstance(op, dict) and "$push" in op:
            base.append(op["$push"])
        elif isinstance(op, list):
            base.extend(op)
        else:
            raise ValueError("scene_history patch must be list or {'$push': item}")
        s["scene_history"] = base

    # last_user_msg / updated_at
    if "last_user_msg" in patch:
        s["last_user_msg"] = str(patch["last_user_msg"])
    s["updated_at"] = _iso_now()

    # ---- 파생 규칙: allies/flags → 순서/히든 자격 ----
    flags = set(s.get("flags", []))
    if allies_changed or flags_changed:
        allies = s.get("allies", {})
        if allies.get("inosuke"): flags.add(FLAG_RECRUIT_INOSUKE)
        if allies.get("zenitsu"): flags.add(FLAG_RECRUIT_ZENITSU)

    if (FLAG_RECRUIT_INOSUKE in flags) and (FLAG_RECRUIT_ZENITSU not in flags) \
       and (FLAG_ORDER_FIRST_INOSUKE not in flags):
        flags.add(FLAG_ORDER_FIRST_INOSUKE)

    if (FLAG_ORDER_FIRST_INOSUKE in flags) and \
       (FLAG_RECRUIT_INOSUKE in flags) and (FLAG_RECRUIT_ZENITSU in flags):
        flags.add(FLAG_ORDER_INOSUKE_THEN_ZENITSU)

    if _hidden_eligible(s, flags):
        flags.add(FLAG_HIDDEN_ELIGIBLE)

    s["flags"] = sorted(flags)
    return s


# ============================================
# 씬 상수 & 샘플 데이터 (테스트용)
# ============================================
SCN_CUTSCENE_5     = "scene5_cutscene"
SCN_FORK           = "scene5_fork"
SCN_MISSION_GATHER = "scene5_mission_gather"
SCN_END_ORIGINAL   = "scene5_end_original"
SCN_END_HIDDEN     = "scene5_end_hidden"

scenes_data_flow = {
    SCN_CUTSCENE_5: {
        "summary": "컷신 5: 상현 등장",
        "allowed_speakers": ["tanjiro"],
        "choices": [
            {"id": "go_fork", "text": "운명의 갈림길로", "value": "to_fork"}
        ],
        "split_rules": [
            {"when": "to_fork", "goto": SCN_FORK}
        ],
        "beats": {"intro": "상현의 기척이 점점 가까워진다."}
    },
    SCN_FORK: {
        "summary": "운명의 갈림길",
        "allowed_speakers": ["tanjiro"],
        "choices": [
            {"id": "c", "text": "무모한 희생(돌진)", "value": "rush",
             "aliases": ["돌진", "직행", "rush", "무모하게 가자"]},
            {"id": "d", "text": "동료 규합 임무로 간다", "value": "gather_allies",
             "aliases": ["동료 규합","동료 모으자","모으자","ally","gather"]}
        ],
        "split_rules": [
            {"when": "rush", "goto": SCN_END_ORIGINAL},
            {"when": "gather_allies", "goto": SCN_MISSION_GATHER}
        ],
        "beats": {"intro": "탄지로: 넌 어떻게 할래?"}
    },
    SCN_MISSION_GATHER: {
        "summary": "동료 규합: 이노스케, 젠이츠를 데려오기",
        "allowed_speakers": ["tanjiro"],
        "choices": [
            {"id": "recruit_inosuke", "text": "이노스케 설득 시도", "value": "try_inosuke",
             "aliases": ["이노스케", "이노스케 설득"]},
            {"id": "recruit_zenitsu", "text": "젠이츠 설득 시도", "value": "try_zenitsu",
             "aliases": ["젠이츠", "젠이츠 설득"]},
            {"id": "finish_mission", "text": "임무 종료/판정으로 이동", "value": "finish",
             "aliases": ["끝", "판정", "finish", "종료"]}
        ],
        "split_rules": [
            # finish에서만 엔딩 판정(함수 evaluate_mission_end로 전환 권장)
            {"when": "finish", "goto": SCN_MISSION_GATHER}
        ],
        "beats": {"intro": "시간은 많지 않다. 설득을 시도하자."}
    },
    SCN_END_ORIGINAL: {
        "summary": "기존 원작 엔딩",
        "allowed_speakers": ["tanjiro"],
        "choices": [],
        "beats": {"intro": "운명은 바뀌지 않았다."}
    },
    SCN_END_HIDDEN: {
        "summary": "히든 엔딩: 기적의 공조",
        "allowed_speakers": ["tanjiro"],
        "choices": [],
        "beats": {"intro": "새로운 미래가 열렸다."}
    },
}


# ============================================
# 분기 규칙 평가 (간단판)
# ============================================
def eval_split_rules(scene_def: dict, state: dict, choice_value: str) -> Optional[dict]:
    rules = scene_def.get("split_rules", [])
    flags = set(state.get("flags", []))
    for r in rules:
        if r.get("when") != choice_value:
            continue
        req = set(r.get("require_flags", []))
        forb = set(r.get("forbid_flags", []))
        if not req.issubset(flags):
            continue
        if forb & flags:
            continue
        return {"goto": r.get("goto"), "set": r.get("set", {})}
    return None


# ============================================
# 엔딩 판정 (finish 트리거 이후)
# ============================================
def evaluate_mission_end(state: Dict[str, Any]) -> Dict[str, Any]:
    cur = (state.get("scene") or {}).get("current_scene")
    if cur != SCN_MISSION_GATHER:
        return state

    flags = set(state.get("flags", []))
    if _hidden_eligible(state, flags):
        patch = {
            "route": "hidden_branch",
            "ending": "hidden:miracle_coordination",
            "end_reason": "mission_success",
            "scene": {"current_scene": SCN_END_HIDDEN},
            "scene_history": {"$push": cur},
        }
    else:
        patch = {
            "route": "original_branch",
            "ending": "original",
            "end_reason": "mission_failed_or_timeout",
            "scene": {"current_scene": SCN_END_ORIGINAL},
            "scene_history": {"$push": cur},
        }
    return apply_patch(state, patch)


# ============================================
# 간단 로컬 테스트
# ============================================
if __name__ == "__main__":
    # 샘플 초기 상태: 갈림길에서 시작
    st: GameState = {
        "scene": {"current_scene": SCN_FORK},
        "turn": 0, "total_turns_used": 0,
        "character_turns_used": {},
        "allies": {"inosuke": False, "zenitsu": False},
        "affinity": {"tanjiro": 500}, "flags": [],
        "ending": "", "end_reason": "", "user_choice": None,
        "last_user_msg": "", "scene_history": [], "updated_at": _iso_now(),
        "user_id": "u1", "session_id": "s1", "scenario_id": "sc1",
    }

    # 히든 조건 충족 케이스(간단 검증): 이노스케→젠이츠, 각 1회씩, 총 2턴
    st = apply_patch(st, {"character_turns_used": {"inosuke": {"$inc": 1}},
                          "total_turns_used": {"$inc": 1},
                          "allies": {"inosuke": True}})
    st = apply_patch(st, {"character_turns_used": {"zenitsu": {"$inc": 1}},
                          "total_turns_used": {"$inc": 1},
                          "allies": {"zenitsu": True}})
    assert "order_inosuke_then_zenitsu" in st["flags"]
    assert "hidden_ending_eligible" in st["flags"]
    print("✅ patch engine OK:", st["flags"])

    # 엔딩 판정 호출 전, 미션 씬으로 이동
    st = apply_patch(st, {"scene": {"current_scene": SCN_MISSION_GATHER}})
    st_end = evaluate_mission_end(st)
    print("→ ending scene:", st_end["scene"]["current_scene"], "ending:", st_end["ending"])

    # 역순(젠이츠→이노스케): 히든 불가
    st2: GameState = {
        "scene": {"current_scene": SCN_FORK},
        "turn": 0, "total_turns_used": 0,
        "character_turns_used": {}, "allies": {"inosuke": False, "zenitsu": False},
        "affinity": {"tanjiro": 500}, "flags": [],
        "ending": "", "end_reason": "", "user_choice": None,
        "last_user_msg": "", "scene_history": [], "updated_at": _iso_now(),
        "user_id": "u1", "session_id": "s2", "scenario_id": "sc1",
    }
    st2 = apply_patch(st2, {"character_turns_used": {"zenitsu": {"$inc": 1}},
                            "total_turns_used": {"$inc": 1},
                            "allies": {"zenitsu": True}})
    st2 = apply_patch(st2, {"character_turns_used": {"inosuke": {"$inc": 1}},
                            "total_turns_used": {"$inc": 1},
                            "allies": {"inosuke": True}})
    assert "order_inosuke_then_zenitsu" not in st2["flags"]
    assert "hidden_ending_eligible" not in st2["flags"]
    print("✅ patch engine OK:", st2["flags"])

    st2 = apply_patch(st2, {"scene": {"current_scene": SCN_MISSION_GATHER}})
    st2_end = evaluate_mission_end(st2)
    print("→ ending scene:", st2_end["scene"]["current_scene"], "ending:", st2_end["ending"])

    # 이노스케만 4턴: 한도 초과로 히든 불가
    st3: GameState = {
        "scene": {"current_scene": SCN_FORK},
        "turn": 0, "total_turns_used": 0,
        "character_turns_used": {}, "allies": {"inosuke": False, "zenitsu": False},
        "affinity": {"tanjiro": 500}, "flags": [],
        "ending": "", "end_reason": "", "user_choice": None,
        "last_user_msg": "", "scene_history": [], "updated_at": _iso_now(),
        "user_id": "u1", "session_id": "s3", "scenario_id": "sc1",
    }
    for _ in range(4):
        st3 = apply_patch(st3, {"character_turns_used": {"inosuke": {"$inc": 1}},
                                "total_turns_used": {"$inc": 1}})
    st3 = apply_patch(st3, {"allies": {"inosuke": True}})
    st3 = apply_patch(st3, {"character_turns_used": {"zenitsu": {"$inc": 1}},
                            "total_turns_used": {"$inc": 1},
                            "allies": {"zenitsu": True}})
    assert "order_inosuke_then_zenitsu" in st3["flags"]
    assert "hidden_ending_eligible" not in st3["flags"]
    print("✅ patch engine OK:", st3["flags"])

    st3 = apply_patch(st3, {"scene": {"current_scene": SCN_MISSION_GATHER}})
    st3_end = evaluate_mission_end(st3)
    print("→ ending scene:", st3_end["scene"]["current_scene"], "ending:", st3_end["ending"])
