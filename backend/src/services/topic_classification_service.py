"""
============================================================
🧭 Topic Classification Service — 토픽 분류 비즈니스 로직
============================================================
RouterAgent의 topic classification 로직을 서비스로 분리합니다.
사용자 입력이 시나리오 관련(on_topic)인지 무관(off_topic)인지 판별합니다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from src.core.prompt_builder import RouterPromptBuilder
from src.utils.embedding_matcher import EmbeddingClient, EmbeddingMatcher, get_embedding_client
from src.utils.llm_client import LLMClient, get_llm_client
from src.utils.logger import log
from src.utils.config_loader import get_config_loader
from src.database.session_manager import HybridSessionManager

_PROMPTS = get_config_loader().get_prompts()
_ROUTER_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("router") or {})
_ROUTER_TOPIC_PROMPT = (_ROUTER_PROMPTS.get("topic_classifier") or "").strip()

if not _ROUTER_TOPIC_PROMPT:
    raise ValueError("RouterAgent topic_classifier prompt missing in configs/prompts.yaml")


@dataclass
class TopicClassification:
    """Topic classification 결과"""
    is_off_topic: bool
    confidence: float
    category: Optional[str] = None
    reason: Optional[str] = None


class TopicClassificationService:
    """
    Topic Classification 서비스

    RouterAgent의 topic classification 로직을 서비스로 분리했습니다.
    임베딩 매칭 → LLM 판별 순으로 분류합니다.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        embedding_client: Optional[EmbeddingClient] = None,
        session_manager: Optional[HybridSessionManager] = None,
    ):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
            embedding_client: 임베딩 클라이언트 (None이면 자동 생성)
            session_manager: 세션 매니저 (에러 로깅용)
        """
        self._llm_client = llm_client or get_llm_client()
        self._embedding_client = embedding_client or get_embedding_client()
        self._session_manager = session_manager

        # Topic matcher 초기화 (임베딩 기반 분류)
        self._topic_matcher = EmbeddingMatcher(
            {
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

        # Initialize session manager if not provided
        if not self._session_manager:
            try:
                from src.database.db_manager import DatabaseManager
                from src.database.cache_manager import CacheManager
                db = DatabaseManager()
                cache_manager = CacheManager()
                self._session_manager = HybridSessionManager(db_manager=db, cache_manager=cache_manager)
            except Exception as e:
                log("topic_classification", "session_manager_init_failed", error=str(e))

    def classify(
        self,
        user_input: str,
        state: Dict[str, Any],
        embedding: Optional[Sequence[float]] = None,
    ) -> TopicClassification:
        """
        사용자 입력을 on_topic / off_topic으로 분류합니다.

        Args:
            user_input: 사용자 입력 텍스트
            state: 전체 state 객체 (시나리오 정보 등)
            embedding: 미리 계산된 임베딩 벡터 (선택)

        Returns:
            TopicClassification 결과
        """
        normalized = (user_input or "").strip()

        # 빈 입력은 off_topic
        if not normalized:
            return TopicClassification(
                is_off_topic=True,
                confidence=1.0,
                category="empty",
                reason="empty_input",
            )

        # 1차: 임베딩 매칭
        embedding_result = self._classify_with_embedding(normalized, embedding=embedding)
        if embedding_result:
            return embedding_result

        # 2차: LLM 판별
        return self._classify_with_llm(state, normalized)

    def _classify_with_embedding(
        self,
        text: str,
        *,
        embedding: Optional[Sequence[float]] = None,
    ) -> Optional[TopicClassification]:
        """임베딩을 통한 분류"""
        if not text:
            return None

        match = self._topic_matcher.match(text, embedding=embedding)
        if not match.label:
            return None

        confidence = max(0.0, min(1.0, match.score or 0.0))
        is_off_topic = match.label == "off_topic"
        reason = f"{match.label}_match"
        log(
            "topic_classification",
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

    def _classify_with_llm(self, state: Dict[str, Any], text: str) -> TopicClassification:
        """LLM을 통한 분류"""
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

        # 🎨 RouterPromptBuilder 사용
        user_prompt = RouterPromptBuilder.build_topic_classification(
            user_input=text,
            scenario_id=scenario_id,
            current_stage=current_stage,
            recent_history=recent_history,
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
            log("topic_classification", "LLM topic classification failed", error=str(exc))

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
                    log("topic_classification", "error_log_save_failed", error=str(e))

            return TopicClassification(
                is_off_topic=True,
                confidence=0.6,
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
            "topic_classification",
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

    def _summarize_recent_history(self, state: Dict[str, Any], limit: int = 4) -> str:
        """최근 대화 압축"""
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


__all__ = ["TopicClassificationService", "TopicClassification"]
