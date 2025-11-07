# ============================================================
# 💞 친밀도 모델 — 점수 구조와 헬퍼
# ============================================================
from __future__ import annotations

from typing import Dict, List

CUTSCENE_CAP: int = 20

_POS_RULES: Dict[str, int] = {  # 친밀도 상승 규칙
    "general_interaction": 2, # 일반 상호작
    "positive_core": 5, # 긍정적/핵심 상호작용
    "praise_encourage": 3, # 칭찬과 격려
    "optimal_interaction": 8, # 결정적/공략적 상호작용
    "combat_coop": 6, # 전투 협력
    "core_goal_achievement": 10, # 핵심 목표 달성
}

_NEG_RULES: Dict[str, int] = {
    "trust_destruction": -15, # 신뢰 관계 파괴
    "selfish_cowardly": -10, # 이기적/비겁한 행동
    "contempt_blame": -8, # 경멸 및 비난
    "ignore_indifference": -3, # 무시 및 무관심
    "uncooperative_dialogue": -2, # 비협조적/맥락 이탈 대화
}

_ALL_RULES: Dict[str, int] = {**_POS_RULES, **_NEG_RULES}


def _ensure_affinity_state(state: dict) -> Dict[str, int]:
    affinity = state.get("affinity") or state.get("affinity_scores") or {}
    #       
    state["affinity"] = affinity
    state["affinity_scores"] = affinity
    #    
    if "affinity_delta_this_cutscene" not in state or not isinstance(
        state.get("affinity_delta_this_cutscene"), dict
    ):
        state["affinity_delta_this_cutscene"] = {}
    return affinity


def reset_cutscene_cap(state: dict) -> None:
    state["affinity_delta_this_cutscene"] = {}


def apply_rules(state: dict, bundle: Dict[str, List[str]]) -> None:
    if not bundle:
        return

    affinity = _ensure_affinity_state(state)
    cap_acc = state["affinity_delta_this_cutscene"]

    applied_log: Dict[str, int] = {}
    cap_left_log: Dict[str, int] = {}

    for char_id, keys in bundle.items():
        # 아카자는 일단 친밀도 시스템에서 제외
        if str(char_id).strip().lower() == "akaza":
            continue
        if not keys:
            continue

        total = 0
        for k in keys:
            delta = _ALL_RULES.get(k)
            if delta is not None:
                total += delta

        if total == 0:
            continue

        old = affinity.get(char_id, 0)

        #       
        if total > 0:
            used = cap_acc.get(char_id, 0)
            left = max(0, CUTSCENE_CAP - used)
            apply_pos = min(total, left)
            if apply_pos > 0:
                new_val = max(0, min(1000, old + apply_pos))
                affinity[char_id] = new_val
                cap_acc[char_id] = used + apply_pos
                applied_log[char_id] = apply_pos
                cap_left_log[char_id] = max(0, CUTSCENE_CAP - cap_acc[char_id])
            else:
                cap_left_log[char_id] = 0
        else:
            new_val = max(0, min(1000, old + total))
            affinity[char_id] = new_val
            applied_log[char_id] = total
            used = cap_acc.get(char_id, 0)
            cap_left_log[char_id] = max(0, CUTSCENE_CAP - used)

    #       
    state["affinity"] = affinity
    state["affinity_scores"] = affinity

    #    
    if applied_log:
        try:
            from logging import getLogger

            logger = getLogger(__name__)
            logger.debug(
                "[AFFINITY] applied=%s cap_left=%s", applied_log, cap_left_log
            )
        except Exception:
            pass


def _intent_to_bundle(intent_tags: dict) -> Dict[str, List[str]]:
    p = (intent_tags or {}).get("player", {}) or {}
    targets = (intent_tags or {}).get("targets") or []
    if not targets:
        return {}
    keys = [k for k, v in p.items() if v is True]
    if not keys:
        return {}
    return {t: keys[:] for t in targets}
