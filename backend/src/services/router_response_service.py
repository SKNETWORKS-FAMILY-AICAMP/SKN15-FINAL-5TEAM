"""
============================================================
🎯 Router Response Service — 라우팅 결과 응답 생성
============================================================
RouterAgent의 on/off topic 처리 로직을 서비스로 분리합니다.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.services import TopicClassification
from src.utils.fallback_llm import generate_off_topic_response
from src.utils.logger import log


class RouterResponseService:
    """
    Router 응답 생성 서비스

    책임:
    - Off-topic 응답 생성 및 children_ctx 구성
    - On-topic 라우팅 결과 구성
    - State 업데이트 로직
    """

    # ============================================================
    # Off-topic 처리
    # ============================================================
    def build_off_topic_response(
        self,
        state: Dict[str, Any],
        user_input: str,
        topic: TopicClassification,
    ) -> Dict[str, Any]:
        """
        Off-topic 응답 생성

        Args:
            state: 전체 state 객체
            user_input: 사용자 입력
            topic: TopicClassification 결과

        Returns:
            업데이트된 state
        """
        count = int(state.get("off_topic_count", 0)) + 1
        state["off_topic_count"] = count

        confidence = round(max(0.0, min(1.0, topic.confidence or 0.0)), 4)
        reason = topic.reason or topic.category or "off_topic"

        routing_result = {
            "intent": "off_topic",
            "classification": "off_topic",
            "confidence": confidence,
            "reason": reason,
        }
        state["routing_result"] = routing_result
        state["user_intent"] = "off_topic"
        state["classification"] = "off_topic"

        # Fallback 응답 생성
        fallback = generate_off_topic_response(state, user_input) or {}
        fallback_text = fallback.get("text") or "지금은 임무에 집중해야 해요. 이야기는 나중에 이어가요."
        fallback_speaker = fallback.get("speaker") or "system"

        # Character refs 구성
        character_refs = self._build_character_refs(state, fallback_speaker)

        # Temp data 설정
        temp = state.setdefault("temp_data", {})
        temp["skip_parent_after_dialogue"] = True
        temp.pop("force_story_resume", None)

        # 3회 이상 off-topic 시 강제 복귀
        if count >= 3:
            state["off_topic_count"] = 0
            fallback_text = "⚠️ 집중하세요. 시나리오로 복귀합니다."
            fallback_speaker = "system"
            temp["skip_parent_after_dialogue"] = False
            temp["force_story_resume"] = True
            routing_result["intent"] = "on_topic"
            routing_result["classification"] = "on_topic"
            routing_result["reason"] = "force_resume"
            routing_result["confidence"] = 1.0
            state["user_intent"] = "on_topic"
            state["classification"] = "on_topic"

        # Children context 구성
        children_ctx = {
            "stage_tag": "OFF_TOPIC",
            "stage_type": "system_notice",
            "speaker_pool": [fallback_speaker],
            "beats": [
                {
                    "speaker": fallback_speaker,
                    "text": fallback_text,
                }
            ],
            "character_refs": character_refs,
            "scenario_id": state.get("scenario_id"),
            "fallback": {
                "dialogues": [
                    {
                        "speaker": fallback_speaker,
                        "text": fallback_text,
                    }
                ]
            },
        }
        state["children_ctx"] = children_ctx
        state["next_node"] = "children_agent"

        log(
            "router",
            "off_topic_detected",
            count=count,
            reason=routing_result["reason"],
            confidence=confidence,
        )
        return state

    # ============================================================
    # On-topic 처리
    # ============================================================
    def build_on_topic_response(
        self,
        state: Dict[str, Any],
        user_input: str,
        topic: TopicClassification,
        detected_intent: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        On-topic 응답 생성

        Args:
            state: 전체 state 객체
            user_input: 사용자 입력
            topic: TopicClassification 결과
            detected_intent: 사전 감지된 intent (병렬 실행 결과)

        Returns:
            업데이트된 state
        """
        state["off_topic_count"] = 0
        state["classification"] = "on_topic"

        confidence = round(max(0.0, min(1.0, topic.confidence or 0.0)), 4)
        routing_result = {
            "intent": "on_topic",
            "classification": "on_topic",
            "confidence": confidence,
        }
        if topic.reason:
            routing_result["reason"] = topic.reason
        elif topic.category:
            routing_result["reason"] = topic.category

        state["routing_result"] = routing_result
        state.pop("children_ctx", None)

        # Temp data 초기화
        temp = state.setdefault("temp_data", {})
        temp.pop("skip_parent_after_dialogue", None)
        temp.pop("force_story_resume", None)
        temp.pop("intent", None)
        temp.pop("sticky_intent", None)
        temp.pop("intent_stage", None)

        # Intent 처리
        if detected_intent and isinstance(detected_intent, dict):
            intent_key = str(detected_intent.get("intent") or "").strip()
            if intent_key:
                routing_result["intent"] = intent_key
                routing_result["classification"] = intent_key
                source = detected_intent.get("source")
                routing_result["source"] = source or routing_result.get("source")
                if source:
                    routing_result["reason"] = source
                state["user_intent"] = intent_key
                temp["intent"] = intent_key
                temp["sticky_intent"] = intent_key
                stage_marker = detected_intent.get("stage")
                if stage_marker:
                    temp["intent_stage"] = stage_marker
                log("router", "intent_resolved", intent=intent_key, source=routing_result.get("source"), stage_tag=stage_marker)
            else:
                state["user_intent"] = "on_topic"
        else:
            state["user_intent"] = "on_topic"

        state["next_node"] = "parent_agent"
        log("router", "on_topic_detected", confidence=confidence, reason=routing_result.get("reason"))
        return state

    # ============================================================
    # Helper methods
    # ============================================================
    def _build_character_refs(self, state: Dict[str, Any], speaker: str) -> Dict[str, Any]:
        """
        Character refs 구성

        Args:
            state: 전체 state
            speaker: 스피커 이름

        Returns:
            character_refs dict
        """
        character_refs: Dict[str, Any] = {}
        scenario = state.get("scenario") or state.get("scenario_data")
        if isinstance(scenario, dict):
            scenario_refs = scenario.get("character_refs") or {}
            if isinstance(scenario_refs, dict):
                ref = scenario_refs.get(speaker)
                if ref:
                    character_refs[speaker] = ref
        return character_refs


__all__ = ["RouterResponseService"]
