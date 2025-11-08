from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Sequence

from src.services import (
    TopicClassificationService,
    TopicClassification,
    IntentDetectionService,
    RouterResponseService,
)
from src.utils.embedding_matcher import get_embedding_client
from src.utils.logger import log
from src.tools.training_logger import log_agent
from src.database.session_manager import HybridSessionManager

# ============================================================
# 🎯 RouterAgent — 사용자의 발화가 시나리오 관련(on_topic)인지 아닌지(off_topic) 분류
# TopicClassificationService와 IntentDetectionService를 활용합니다.
# (1차 : 임베딩 매칭 / 2차 : LLM 판별)
# ============================================================


class RouterAgent:
    """
    RouterAgent - Topic 분류 및 Intent 탐지 노드

    TopicClassificationService를 통해 on/off topic을 분류하고,
    IntentDetectionService를 통해 사용자 의도를 탐지합니다.
    비즈니스 로직은 서비스에 위임하고, 노드 역할만 수행합니다.
    """

    # ============================================================
    # 🛠️ 초기화
    # ============================================================
    def __init__(self) -> None:
        self._embedding_client = get_embedding_client()
        self._session_manager: Optional[HybridSessionManager] = None

        # Initialize session manager for error logging
        try:
            from src.database.db_manager import DatabaseManager
            from src.database.cache_manager import CacheManager
            db = DatabaseManager()
            cache_manager = CacheManager()
            self._session_manager = HybridSessionManager(db_manager=db, cache_manager=cache_manager)
        except Exception as e:
            log("router", "session_manager_init_failed", error=str(e))

        # 🆕 서비스 레이어 초기화
        self._topic_service = TopicClassificationService(
            embedding_client=self._embedding_client,
            session_manager=self._session_manager,
        )
        self._intent_service = IntentDetectionService()
        self._response_service = RouterResponseService()

    # ============================================================
    # 🚦 분류 엔트리 포인트
    # ============================================================
    def run(self, state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """
        RouterAgent의 메인 엔트리 포인트.
        TopicClassificationService를 통해 on/off topic을 분류하고,
        IntentDetectionService를 통해 사용자 의도를 탐지합니다.
        """
        # Phase 4: 로그 수집 시작
        start_time = time.perf_counter()

        normalized = (user_input or "").strip()
        state["user_input"] = normalized

        # 빈 입력 처리
        if not normalized:
            empty_topic = TopicClassification(
                is_off_topic=True,
                confidence=1.0,
                category="empty",
                reason="empty_input",
            )
            result = self._response_service.build_off_topic_response(state, normalized, empty_topic)
            self._log_execution(state, result, start_time)
            return result

        # 임베딩 생성 (캐싱)
        embedding = self._get_user_embedding(state, normalized)

        # 🚀 Phase 2 최적화: topic classification + intent detection 병렬 실행
        with ThreadPoolExecutor(max_workers=2) as executor:
            topic_future = executor.submit(
                self._topic_service.classify,
                normalized,
                state,
                embedding
            )
            intent_future = executor.submit(
                self._intent_service.detect_intent,
                state,
                normalized
            )

            topic = topic_future.result()
            # topic이 on_topic일 때만 intent 결과 사용
            detected_intent = intent_future.result() if not topic.is_off_topic else None

        if topic.is_off_topic:
            result = self._response_service.build_off_topic_response(state, normalized, topic)
        else:
            result = self._response_service.build_on_topic_response(state, normalized, topic, detected_intent=detected_intent)

        # Phase 4: 로그 수집
        self._log_execution(state, result, start_time)
        return result

    # ============================================================
    # 🧾 상태 히스토리/캐시
    # ============================================================
    def _get_user_embedding(self, state: Dict[str, Any], text: str) -> Optional[Sequence[float]]:
        """임베딩 시 캐시 이용"""
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
