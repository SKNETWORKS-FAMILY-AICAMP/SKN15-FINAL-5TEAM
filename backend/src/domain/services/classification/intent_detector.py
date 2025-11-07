'''각 캐릭터별 친밀도 위한 파일 -> 각 캐릭터별 가치관과 상황이 다르므로
1. 패턴 스코어 + 캐릭터 weights/sensitivities → 총합
2. 간단 컨텍스트 boost(INTRO/INTERVENE/COMBAT 상황에서 combat_coop 보정)
3. 애매할 때만 LLM 보강(use_llm=True & 호출 성공 시)'''
# ============================================================
# ============================================================
from __future__ import annotations

import os
from typing import Dict, Any, List
from logging import getLogger

from src.domain.services.orchestration.characters_repo import (
    list_characters,
    build_character_rulebook,
    affinity_applicable,
    character_names_aliases,
)

logger = getLogger(__name__)


def _pattern_score(user_text: str, patterns: Dict[str, List[str]]) -> Dict[str, float]:
    s = (user_text or "").lower()
    scores: Dict[str, float] = {}
    for intent_key, kws in (patterns or {}).items():
        sc = 0.0
        for kw in kws or []:
            kwl = (kw or "").lower()
            if kwl and kwl in s:
                sc += 1.0
        if sc:
            scores[intent_key] = sc
    return scores


def _apply_weights(scores: Dict[str, float], weights: Dict[str, float]) -> Dict[str, float]:
    if not weights:
        return scores
    return {k: v * float(weights.get(k, 1.0)) for k, v in scores.items()}


def _apply_sensitivities(scores: Dict[str, float], sens: Dict[str, float]) -> Dict[str, float]:
    if not sens:
        return scores
    return {k: v * float(sens.get(k, 1.0)) for k, v in scores.items()}


def _context_boost(state: dict) -> Dict[str, float]:
    stage = ((state.get("current_stage") or "").upper())
    boost: Dict[str, float] = {}
    if any(x in stage for x in ("INTERVENE", "BATTLE", "COMBAT", "INTRO")):
        boost["combat_coop"] = 1.0
        boost["positive_core"] = 0.2
    return boost


def _merge_scores(*maps: Dict[str, float]) -> Dict[str, float]:
    agg: Dict[str, float] = {}
    for m in maps:
        for k, v in (m or {}).items():
            agg[k] = agg.get(k, 0.0) + float(v)
    return agg


def _maybe_llm_boost(state: dict, user_text: str, totals: Dict[str, float]) -> Dict[str, float]:
    use_llm = os.getenv("INTENT_LLM", "0") == "1"
    if not use_llm:
        return totals
    try:
        if not totals or max(totals.values()) < 1.0:
            from src.infrastructure.shared.dependency_container import get_llm_provider

            llm = get_llm_provider()
            system = (
                "You label user intent for a Demon Slayer game.\n"
                "Return JSON with scores (0-1) for keys: combat_coop, praise_encourage, positive_core, general_interaction, optimal_interaction, core_goal_achievement, selfish_cowardly.\n"
            )
            userp = f"Text: {user_text}\nReturn: {{\"combat_coop\":0-1,...}}"
            resp = llm.call_json(system_prompt=system, user_prompt=userp, temperature=0.1)
            for k, v in (resp or {}).items():
                try:
                    totals[k] = max(totals.get(k, 0.0), float(v or 0.0))
                except Exception:
                    continue
    except Exception as e:
        logger.debug("[INTENT-LLM] skipped: %s", e)
    return totals


def detect_intents(state: dict, user_text: str) -> Dict[str, Any]:
    totals: Dict[str, float] = {}
    evidence: List[str] = []

    for cid in list_characters():
        if not affinity_applicable(cid):
            continue
        rule = build_character_rulebook(cid)
        base = _pattern_score(user_text, rule.get("patterns", {}))
        w = _apply_weights(base, rule.get("weights", {}))
        s = _apply_sensitivities(w, rule.get("sensitivities", {}))
        totals = _merge_scores(totals, s)
        if base:
            evidence.append(f"pattern:{cid}:{sorted(base.keys())}")

    cb = _context_boost(state)
    totals = _merge_scores(totals, cb)
    if cb:
        evidence.append(f"context:{cb}")

    totals = _maybe_llm_boost(state, user_text, totals)

    player_flags: Dict[str, bool] = {k: (v >= 1.0) for k, v in totals.items() if v >= 1.0}

    speaker_pool = ((state.get("children_ctx") or {}).get("speaker_pool") or (state.get("scene") or {}).get("speaker_pool") or [])
    speaker_pool = [c for c in speaker_pool if c not in ("system", "narr", "akaza")]

    text = (user_text or "").lower()
    explicit: List[str] = []
    if text:
        alias_map = character_names_aliases()
        particles = ["이", "가", "은", "는", "을", "를", "에게", "한테", "야", "아", "도"]
        for cid, aliases in alias_map:
            for a in aliases:
                a_l = a.lower()
                if not a_l:
                    continue
                #  
                if a_l in text:
                    #    
                    matched = True
                    if matched and speaker_pool and cid not in speaker_pool:
                        #      
                        matched = False
                    if matched and cid not in explicit:
                        explicit.append(cid)
                        break

    collective = False
    for tok in ["다들", "모두", "전원", "함께들", "우리", "팀"]:
        if tok in text:
            collective = True
            break

    targets: List[str]
    if explicit:
        targets = explicit[:1]
        evidence.append(f"target:explicit:{targets}")
    elif collective or not explicit:
        targets = list(speaker_pool)
        evidence.append(f"target:collective:{targets}")
    else:
        targets = speaker_pool[:1] if speaker_pool else []

    intent_tags: Dict[str, Any] = {
        "player": player_flags,
        "targets": targets,
        "confidence": 0.7 if player_flags else 0.0,
        "evidence": evidence,
    }

    logger.debug("[INTENT] %s", intent_tags)
    return intent_tags
