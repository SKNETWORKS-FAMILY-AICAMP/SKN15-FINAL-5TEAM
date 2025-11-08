"""
============================================================
🎯 Intent Detection Service — 의도 판별 비즈니스 로직
============================================================
RouterAgent의 intent detection 로직을 서비스로 분리합니다.
ROUTE_CHOICE 등 자유 의사결정 스테이지에서 사용할 intent 값을 추론합니다.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.utils.intent_handler import detect_intent_with_llm
from src.utils.intent_detector import detect_intents
from src.utils.logger import log


class IntentDetectionService:
    """
    Intent Detection 서비스

    RouterAgent의 _detect_route_intent() 로직을 서비스로 분리했습니다.
    LLM 기반 의도 판별 → 시나리오 예시 매칭 → 패턴 기반 감정 스코어 순으로 시도합니다.
    """

    def detect_intent(
        self,
        state: Dict[str, Any],
        user_input: str,
    ) -> Optional[Dict[str, Any]]:
        """
        ROUTE_CHOICE 등 자유 의사결정 스테이지에서 사용할 intent 값을 추론합니다.

        Args:
            state: 전체 state 객체
            user_input: 사용자 입력 텍스트

        Returns:
            {"intent": "...", "stage": "...", "source": "..."} 형식의 intent 정보
            또는 None (판별 실패)
        """
        scenario = state.get("scenario") or state.get("scenario_data") or {}
        if not isinstance(scenario, dict):
            return None

        metadata = scenario.get("metadata") or {}
        router_meta = metadata.get("router") or {}
        if not isinstance(router_meta, dict):
            return None

        normalized_input = (user_input or "").strip()
        if not normalized_input:
            return None

        intent_stage = router_meta.get("intent_stage")
        allies_key = router_meta.get("allies_intent")
        reckless_key = router_meta.get("reckless_intent")
        intent_examples = router_meta.get("intent_examples") or {}

        resolved_stage = str(intent_stage or "").upper()
        if not resolved_stage:
            resolved_stage = str(state.get("current_stage") or "").upper()
        resolved_stage = resolved_stage or None

        # 1️⃣ LLM 기반 의도 판별
        llm_intent = detect_intent_with_llm(state, normalized_input, stage_tag=resolved_stage)
        if llm_intent:
            log("intent_detection", "✅ LLM intent detected", intent=llm_intent, detected_stage=resolved_stage)
            return {"intent": str(llm_intent), "stage": resolved_stage, "source": "llm"}

        # 2️⃣ 시나리오 예시 매칭
        example_match = self._match_examples(normalized_input, intent_examples)
        if example_match:
            log("intent_detection", "✅ Example match", intent=example_match, detected_stage=resolved_stage)
            return {"intent": example_match, "stage": resolved_stage, "source": "examples"}

        # 3️⃣ Intent options 매칭
        intents_meta = metadata.get("intents") or {}
        normalized_meta = {str(k).upper(): v for k, v in intents_meta.items()}
        stage_meta = normalized_meta.get((resolved_stage or "").upper(), {})
        options_map = stage_meta.get("options") if isinstance(stage_meta, dict) else {}
        if isinstance(options_map, dict) and options_map:
            option_match = self._match_examples(normalized_input, {key: [key] for key in options_map.keys()})
            if option_match:
                log("intent_detection", "✅ Option match", intent=option_match, detected_stage=resolved_stage)
                return {"intent": option_match, "stage": resolved_stage, "source": "options"}

        # 4️⃣ 패턴 기반 감정 스코어 (Heuristic)
        heuristics = detect_intents(state, normalized_input)
        player_flags = heuristics.get("player", {}) if isinstance(heuristics, dict) else {}

        # Reckless intent (전투적, 목표 지향적)
        if player_flags.get("combat_coop") or player_flags.get("core_goal_achievement"):
            if reckless_key:
                log("intent_detection", "✅ Heuristic: reckless", intent=reckless_key, detected_stage=resolved_stage)
                return {"intent": str(reckless_key), "stage": resolved_stage, "source": "intent_detector"}

        # Allies intent (긍정적, 협력적)
        if any(player_flags.get(flag) for flag in ("positive_core", "general_interaction", "optimal_interaction")):
            if allies_key:
                log("intent_detection", "✅ Heuristic: allies", intent=allies_key, detected_stage=resolved_stage)
                return {"intent": str(allies_key), "stage": resolved_stage, "source": "intent_detector"}

        # 판별 실패
        log("intent_detection", "⚠️ No intent detected", input=normalized_input[:50])
        return None

    def _match_examples(self, user_input: str, example_map: Dict[str, Any]) -> Optional[str]:
        """예시 문장 매칭"""
        lower_text = user_input.lower()
        for intent_key, samples in (example_map or {}).items():
            sample_list = samples if isinstance(samples, list) else [samples]
            for sample in sample_list:
                sample_str = str(sample or "").strip().lower()
                if sample_str and sample_str in lower_text:
                    return str(intent_key)
        return None


__all__ = ["IntentDetectionService"]
