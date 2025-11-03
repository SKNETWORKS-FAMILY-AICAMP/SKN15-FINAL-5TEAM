from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from src.utils.embedding_matcher import EmbeddingClient, EmbeddingMatcher, get_embedding_client
from src.tools.fallback_tools import handle_off_topic, reset_fallback_count
from src.utils.llm_client import LLMClient, get_llm_client
from src.utils.logger import log
from src.utils.intent_handler import detect_intent_with_llm
from src.utils.intent_detector import detect_intents
from src.utils.config_loader import get_config_loader
from src.tools.training_logger import log_agent
from src.database.session_manager import HybridSessionManager

_PROMPTS = get_config_loader().get_prompts()
_ROUTER_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("router") or {})
_ROUTER_TOPIC_PROMPT = (_ROUTER_PROMPTS.get("topic_classifier") or "").strip()
_ROUTER_TOPIC_USER_TEMPLATE = (_ROUTER_PROMPTS.get("topic_classifier_user") or "").strip()
if not _ROUTER_TOPIC_PROMPT:
    raise ValueError("RouterAgent topic_classifier prompt missing in configs/prompts.yaml (llm_prompts.router.topic_classifier).")
if not _ROUTER_TOPIC_USER_TEMPLATE:
    raise ValueError("RouterAgent topic_classifier_user prompt missing in configs/prompts.yaml (llm_prompts.router.topic_classifier_user).")

# ============================================================
# 🎯 RouterAgent — 사용자의 발화가 시나리오 관련(on_topic)인지 아닌지(off_topic) 분류
# (필요한 utils : llm_clien, fallback_llm, embedding_matcher, logger)
# (1차 : 임베딩 매칭 / 2차 : LLM 판별)
# ============================================================

@dataclass
class TopicClassification:
    is_off_topic: bool
    confidence: float
    category: Optional[str] = None
    reason: Optional[str] = None


class RouterAgent:
    # ============================================================
    # 🛠️ 초기화
    # ============================================================
    # 여기도 일단은 임시로 키워드를 넣어서 on / off 토픽을 코사인 유사도로 매치
    def __init__(self) -> None:
        self._llm_client: LLMClient = get_llm_client()
        self._embedding_client: EmbeddingClient = get_embedding_client()
        self._session_manager: Optional[HybridSessionManager] = None
        self._topic_matcher = EmbeddingMatcher(
            {
                # 임시 키워드 분류
                "off_topic": [
                    "학교 숙제 끝났어",
                    "게임 얘기하자",
                    "유튜브 추천해줘",
                    "뉴스 알려줘",
                    "mbti가 뭐야?"
                ],
            },
            threshold=0.6,
            embedding_client=self._embedding_client,
        )

        # Initialize session manager for error logging
        try:
            from src.database.db_manager import DatabaseManager
            db = DatabaseManager()
            self._session_manager = HybridSessionManager(db_manager=db)
        except Exception as e:
            log("router", "session_manager_init_failed", error=str(e))

    # ============================================================
    # 🚦 분류 엔트리 포인트
    # ============================================================
    # 전체 실행 함수, 임베딩 -> LLM 순으로 분류, 입력이 없는 경우 off 토픽
    def run(self, state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        # Phase 4: 로그 수집 시작
        start_time = time.perf_counter()

        normalized = (user_input or "").strip()
        state["user_input"] = normalized

        if not normalized:
            empty_topic = TopicClassification(
                is_off_topic=True,
                confidence=1.0,
                category="empty",
                reason="empty_input",
            )
            result = self._handle_off_topic(state, normalized, empty_topic)
            # Phase 4: 로그 수집
            self._log_execution(state, result, start_time)
            return result

        embedding = self._get_user_embedding(state, normalized)
        embedding_topic = self._classify_with_embedding(normalized, embedding=embedding)
        if embedding_topic:
            result = (
                self._handle_off_topic(state, normalized, embedding_topic)
                if embedding_topic.is_off_topic
                else self._handle_on_topic(state, normalized, embedding_topic)
            )
            # Phase 4: 로그 수집
            self._log_execution(state, result, start_time)
            return result

        # 🚀 Phase 2 최적화: topic classification + intent detection 병렬 실행
        with ThreadPoolExecutor(max_workers=2) as executor:
            topic_future = executor.submit(self._classify_with_llm, state, normalized)
            intent_future = executor.submit(self._detect_route_intent, state, normalized)

            topic = topic_future.result()
            # topic이 on_topic일 때만 intent 결과 사용
            detected_intent = intent_future.result() if not topic.is_off_topic else None

        if topic.is_off_topic:
            result = self._handle_off_topic(state, normalized, topic)
        else:
            result = self._handle_on_topic(state, normalized, topic, precomputed_intent=detected_intent)

        # Phase 4: 로그 수집
        self._log_execution(state, result, start_time)
        return result

    # ============================================================
    # 🔍 분류 헬퍼
    # ============================================================
    # 임베딩을 통한 분류
    def _classify_with_embedding(
        self,
        text: str,
        *,
        embedding: Optional[Sequence[float]] = None,
    ) -> Optional[TopicClassification]:
        if not text:
            return None

        match = self._topic_matcher.match(text, embedding=embedding)
        if not match.label:
            return None

        confidence = max(0.0, min(1.0, match.score or 0.0))
        is_off_topic = match.label == "off_topic"
        reason = f"{match.label}_match"
        log(
            "router",
            "embedding_classification",
            label=match.label,
            score=f"{confidence:.4f}",
            is_off_topic=is_off_topic,
        )

        return TopicClassification(
            is_off_topic=is_off_topic,
            confidence=confidence,
            category="embedding",
            reason=reason,
        )

    # ============================================================
    # 🧠 LLM 보조 판정
    # ============================================================
    # LLM을 통한 분류
    def _classify_with_llm(self, state: Dict[str, Any], text: str) -> TopicClassification:
        if not text:
            return TopicClassification(
                is_off_topic=True,
                confidence=1.0,
                category="empty",
                reason="empty_input",
            )

        scenario_id = state.get("scenario_id") or "unknown"
        current_stage = state.get("current_stage") or "unknown"
        recent_history = self._summarize_recent_history(state, limit=4)

        user_prompt = _ROUTER_TOPIC_USER_TEMPLATE.format(
            text=text,
            scenario_id=scenario_id,
            current_stage=current_stage,
            recent_history=recent_history or "(최근 대화 없음)"
        )

        try:
            temperature = self._llm_client.get_agent_setting("router", "temperature", 0.0)
            max_tokens = self._llm_client.get_agent_setting("router", "max_tokens", 200)
            response = self._llm_client.call_json(
                system_prompt=_ROUTER_TOPIC_PROMPT,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                agent="router",
            )
        except Exception as exc:
            log("router", "LLM topic classification failed", error=str(exc))

            # 🚨 LLM 호출 실패 에러 로깅
            if self._session_manager:
                try:
                    session_id = state.get("session_id")
                    if session_id:
                        self._session_manager.save_error_log(
                            error_type="router_llm_call_failed",
                            error_message=str(exc),
                            session_id=session_id,
                            metadata={
                                "agent": "router",
                                "scenario_id": scenario_id,
                                "current_stage": current_stage,
                                "user_input": text[:100] if text else None
                            }
                        )
                except Exception as e:
                    log("router", "error_log_save_failed", error=str(e))

            return TopicClassification(
                is_off_topic=True,
                confidence=0.5,
                category="llm_fallback",
                reason="llm_error",
            )

        raw_classification = str(response.get("classification") or "").strip().lower()
        is_off_topic = raw_classification != "on_topic"

        confidence_raw = response.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        reason = response.get("explanation") or response.get("reason")
        if isinstance(reason, str):
            reason = reason.strip()
        else:
            reason = None

        classification = "off_topic" if is_off_topic else "on_topic"
        log(
            "router",
            "llm_classification",
            classification=classification,
            confidence=f"{confidence:.4f}",
            reason=reason or "n/a",
        )

        return TopicClassification(
            is_off_topic=is_off_topic,
            confidence=confidence,
            category="llm",
            reason=reason,
        )

    def _detect_route_intent(
        self,
        state: Dict[str, Any],
        user_input: str,
    ) -> Optional[Dict[str, Any]]:
        """
        ROUTE_CHOICE 등 자유 의사결정 스테이지에서 사용할 intent 값을 추론한다.
        LLM 기반 의도 판별 → 시나리오 예시 매칭 → 패턴 기반 감정 스코어 순으로 시도한다.
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

        llm_intent = detect_intent_with_llm(state, normalized_input, stage_tag=resolved_stage)
        if llm_intent:
            return {"intent": str(llm_intent), "stage": resolved_stage, "source": "llm"}

        def _match_examples(example_map: Dict[str, Any]) -> Optional[str]:
            lower_text = normalized_input.lower()
            for intent_key, samples in (example_map or {}).items():
                sample_list = samples if isinstance(samples, list) else [samples]
                for sample in sample_list:
                    sample_str = str(sample or "").strip().lower()
                    if sample_str and sample_str in lower_text:
                        return str(intent_key)
            return None

        example_match = _match_examples(intent_examples if isinstance(intent_examples, dict) else {})
        if example_match:
            return {"intent": example_match, "stage": resolved_stage, "source": "examples"}

        intents_meta = metadata.get("intents") or {}
        normalized_meta = {str(k).upper(): v for k, v in intents_meta.items()}
        stage_meta = normalized_meta.get((resolved_stage or "").upper(), {})
        options_map = stage_meta.get("options") if isinstance(stage_meta, dict) else {}
        if isinstance(options_map, dict) and options_map:
            option_match = _match_examples({key: [key] for key in options_map.keys()})
            if option_match:
                return {"intent": option_match, "stage": resolved_stage, "source": "options"}

        heuristics = detect_intents(state, normalized_input)
        player_flags = heuristics.get("player", {}) if isinstance(heuristics, dict) else {}
        if player_flags.get("combat_coop") or player_flags.get("core_goal_achievement"):
            if reckless_key:
                return {"intent": str(reckless_key), "stage": resolved_stage, "source": "intent_detector"}
        if any(player_flags.get(flag) for flag in ("positive_core", "general_interaction", "optimal_interaction")):
            if allies_key:
                return {"intent": str(allies_key), "stage": resolved_stage, "source": "intent_detector"}

        return None

    # ============================================================
    # 🧱 분기 처리
    # ============================================================
    # off 토픽일 경우의 처리
    def _handle_off_topic(
        self,
        state: Dict[str, Any],
        user_input: str,
        topic: TopicClassification,
    ) -> Dict[str, Any]:
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

        fallback_result = handle_off_topic(state, user_input, use_llm=True)
        print(f'fallback_result 확인 : {fallback_result}')

        # dialogue 우선, 없으면 message 사용
        dialogue = fallback_result.get("dialogue")
        if dialogue:
            fallback_text = dialogue.get("text", "지금은 임무에 집중해야 해요. 이야기는 나중에 이어가요.")
            fallback_speaker = dialogue.get("speaker", "system")
        else:
            fallback_text = fallback_result.get("message", "지금은 임무에 집중해야 해요. 이야기는 나중에 이어가요.")
            fallback_speaker = fallback_result.get("speaker", "system")

        scenario = state.get("scenario") or state.get("scenario_data")
        character_refs: Dict[str, Any] = {}
        if isinstance(scenario, dict):
            scenario_refs = scenario.get("character_refs") or {}
            if isinstance(scenario_refs, dict):
                ref = scenario_refs.get(fallback_speaker)
                if ref:
                    character_refs[fallback_speaker] = ref

        temp = state.setdefault("temp_data", {})
        temp["skip_parent_after_dialogue"] = True
        temp.pop("force_story_resume", None)

        # 🧹 Off-topic 응답 전 기존 output 클리어 (이전 대사는 이미 전송됨)
        if "output" in state:
            state["output"] = {}
        log("router", "🧹 Cleared previous output for off-topic response")

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


    # on topic일 경우의 처리
    def _handle_on_topic(
        self,
        state: Dict[str, Any],
        user_input: str,
        topic: TopicClassification,
        *,
        precomputed_intent: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        state["off_topic_count"] = 0
        state["classification"] = "on_topic"

        # ✅ Fallback 카운트도 초기화 (on-topic 복귀 시)
        reset_fallback_count(state)

        normalized_input = (user_input or "").strip()
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

        temp = state.setdefault("temp_data", {})
        temp.pop("skip_parent_after_dialogue", None)
        temp.pop("force_story_resume", None)
        temp.pop("intent", None)
        temp.pop("sticky_intent", None)
        temp.pop("intent_stage", None)

        # 🚀 Phase 2 최적화: precomputed_intent 우선 사용 (병렬 실행 결과)
        detected_intent = precomputed_intent if precomputed_intent is not None else self._detect_route_intent(state, normalized_input)
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
    # 🧾 상태 히스토리/캐시
    # ============================================================
    # 최근 대화 압축
    def _summarize_recent_history(self, state: Dict[str, Any], limit: int = 4) -> str:
        entries: list[str] = []

        message_history = state.get("message_history") or []
        if isinstance(message_history, list):
            for record in message_history[-limit:]:
                if not isinstance(record, dict):
                    continue
                speaker = record.get("speaker") or record.get("role") or "unknown"
                text = record.get("text") or record.get("content") or ""
                if text:
                    entries.append(f"{speaker}: {text}")

        user_inputs = state.get("user_inputs") or []
        if isinstance(user_inputs, list):
            for utterance in user_inputs[-limit:]:
                if isinstance(utterance, str) and utterance.strip():
                    entries.append(f"user: {utterance.strip()}")

        trimmed = entries[-limit:]
        return "\n".join(trimmed)


    # 임베딩 시 캐시 이용
    def _get_user_embedding(self, state: Dict[str, Any], text: str) -> Optional[Sequence[float]]:
        cache = state.setdefault("_embedding_cache", {})
        cached_text = cache.get("text")
        cached_vector = cache.get("vector")
        if cached_text == text and cached_vector:
            return cached_vector
        vector = self._embedding_client.embed(text) if text else []
        cache["text"] = text
        cache["vector"] = vector
        return vector

    # ============================================================
    # Phase 4: 로그 수집
    # ============================================================
    def _log_execution(self, state: Dict[str, Any], result: Dict[str, Any], start_time: float):
        """Router Agent 실행 로그를 LogDB에 저장"""
        try:
            # Model output 추출
            model_output = {
                "next_node": result.get("next_node"),
                "classification": result.get("classification", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "category": result.get("category"),
                "reason": result.get("reason"),
            }

            # 로그 저장 (비동기 처리는 추후 개선 가능)
            log_agent(
                agent_name="router",
                state=state,
                model_output=model_output,
                start_time=start_time,
                llm_model="gpt-4o-mini",  # Router가 사용하는 LLM 모델
            )

            # 📊 Performance Metric 저장: Router Agent 실행 시간
            if self._session_manager:
                try:
                    execution_time_ms = (time.perf_counter() - start_time) * 1000.0
                    session_id = state.get("session_id")
                    if session_id:
                        self._session_manager.save_performance_metric(
                            metric_name="router_agent_execution_time",
                            metric_value=execution_time_ms,
                            session_id=session_id,
                            metadata={
                                "classification": result.get("classification"),
                                "next_node": result.get("next_node")
                            }
                        )
                except Exception as e:
                    log("router", "performance_metric_save_failed", error=str(e))

        except Exception as e:
            # 로깅 실패는 무시 (메인 로직에 영향 없도록)
            log("router", "training_log_failed", error=str(e))

DEFAULT_AGENT = RouterAgent()


def run_router_agent(state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
    return DEFAULT_AGENT.run(state, user_input)


__all__ = ["RouterAgent", "run_router_agent"]
