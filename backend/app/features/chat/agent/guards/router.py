"""
Router Agent - 토픽 분류
사용자 입력의 의도와 토픽을 분류하여 적절한 응답 전략 선택
"""
import re
from typing import Dict, Any, Optional, List
from app.core.logging import get_parent_logger

logger = get_parent_logger("RouterAgent")


class RouteResult:
    """라우팅 결과"""
    def __init__(
        self,
        topic: str,
        confidence: float = 1.0,
        keywords: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.topic = topic
        self.confidence = confidence
        self.keywords = keywords or []
        self.metadata = metadata or {}


class RouterAgent:
    """
    토픽 분류 Agent

    책임:
    - 사용자 입력의 의도 파악
    - 토픽 카테고리 분류
    - 적절한 응답 전략 선택

    Phase 3: 키워드 기반 간소화 버전
    TODO: 향후 임베딩 기반 분류 추가
    """

    # 토픽별 키워드 (간소화 버전)
    TOPIC_KEYWORDS = {
        "greeting": {
            "keywords": ["안녕", "하이", "hello", "hi", "헬로", "처음", "반가"],
            "priority": 10
        },
        "farewell": {
            "keywords": ["안녕", "잘가", "bye", "나중", "다음에", "그만"],
            "priority": 10
        },
        "question": {
            "keywords": ["뭐", "무엇", "어디", "언제", "왜", "어떻게", "누구", "?", "?"],
            "priority": 8
        },
        "emotion_positive": {
            "keywords": ["좋아", "최고", "멋져", "감사", "고마워", "행복", "기뻐", "ㅎㅎ", "ㅋㅋ"],
            "priority": 7
        },
        "emotion_negative": {
            "keywords": ["싫어", "화나", "짜증", "슬퍼", "우울", "힘들", "지쳐"],
            "priority": 7
        },
        "agreement": {
            "keywords": ["응", "그래", "맞아", "오케이", "okay", "ok", "알겠어", "좋아"],
            "priority": 6
        },
        "disagreement": {
            "keywords": ["아니", "no", "싫어", "안돼", "거절", "반대"],
            "priority": 6
        },
        "personal": {
            "keywords": ["나는", "내가", "저는", "제가", "우리", "나"],
            "priority": 5
        },
        "scenario_specific": {
            "keywords": ["귀신", "도깨비", "미션", "퀘스트", "목표", "임무"],
            "priority": 9
        },
        "general": {
            "keywords": [],  # 기본값
            "priority": 1
        }
    }

    def __init__(self):
        """RouterAgent 초기화"""
        logger.info("__init__", "RouterAgent initialized")

    def classify(self, user_input: str, state: Dict[str, Any]) -> RouteResult:
        """
        사용자 입력 분류

        Args:
            user_input: 사용자 입력
            state: 세션 상태

        Returns:
            RouteResult
        """
        user_input_lower = user_input.lower().strip()

        # 1. 컨텍스트 기반 우선순위 조정
        context_modifiers = self._get_context_modifiers(state)

        # 2. 키워드 매칭
        topic_scores: Dict[str, float] = {}
        matched_keywords: Dict[str, List[str]] = {}

        for topic, config in self.TOPIC_KEYWORDS.items():
            keywords = config["keywords"]
            priority = config["priority"]

            matched = []
            score = 0.0

            for keyword in keywords:
                if keyword in user_input_lower:
                    matched.append(keyword)
                    score += priority

            # 컨텍스트 보정
            if topic in context_modifiers:
                score *= context_modifiers[topic]

            if matched or topic == "general":
                topic_scores[topic] = score
                matched_keywords[topic] = matched

        # 3. 최고 점수 토픽 선택
        best_topic = max(topic_scores, key=topic_scores.get)
        confidence = self._calculate_confidence(topic_scores, best_topic)

        # 4. 특수 케이스 처리
        best_topic = self._apply_special_rules(
            best_topic, user_input_lower, state
        )

        logger.info(
            "classify",
            f"✅ Topic classified: {best_topic}",
            confidence=round(confidence, 2),
            keywords=matched_keywords.get(best_topic, [])
        )

        return RouteResult(
            topic=best_topic,
            confidence=confidence,
            keywords=matched_keywords.get(best_topic, []),
            metadata={
                "all_scores": topic_scores,
                "input_length": len(user_input)
            }
        )

    def _get_context_modifiers(self, state: Dict[str, Any]) -> Dict[str, float]:
        """
        컨텍스트 기반 우선순위 조정

        Args:
            state: 세션 상태

        Returns:
            토픽별 가중치 dict
        """
        modifiers = {}

        # 첫 턴에는 greeting 우선
        turn_count = state.get("turn_count", 0)
        if turn_count == 0:
            modifiers["greeting"] = 2.0

        # 10턴 이상이면 farewell 우선도 증가
        if turn_count >= 10:
            modifiers["farewell"] = 1.5

        # 현재 스테이지에 따른 조정
        current_stage = state.get("current_stage", "")
        if current_stage == "intro":
            modifiers["greeting"] = 1.5
            modifiers["personal"] = 1.3

        # 최근 대화에서 질문이 많았다면 question 우선도 감소
        conversation_history = state.get("conversation_history", [])
        recent_questions = sum(
            1 for msg in conversation_history[-5:]
            if isinstance(msg, dict) and ("?" in msg.get("text", "") or "?" in msg.get("text", ""))
        )
        if recent_questions >= 3:
            modifiers["question"] = 0.8

        return modifiers

    def _calculate_confidence(
        self,
        topic_scores: Dict[str, float],
        best_topic: str
    ) -> float:
        """
        분류 신뢰도 계산

        Args:
            topic_scores: 토픽별 점수
            best_topic: 선택된 토픽

        Returns:
            0.0 ~ 1.0 신뢰도
        """
        best_score = topic_scores.get(best_topic, 0)

        if best_score == 0:
            return 0.5  # general 기본값

        # 2위와의 차이가 클수록 신뢰도 높음
        sorted_scores = sorted(topic_scores.values(), reverse=True)
        if len(sorted_scores) < 2:
            return 1.0

        second_score = sorted_scores[1]
        gap = best_score - second_score

        # 점수 차이를 0~1 범위로 정규화
        confidence = min(1.0, 0.5 + (gap / (best_score + 1e-6)) * 0.5)
        return confidence

    def _apply_special_rules(
        self,
        topic: str,
        user_input: str,
        state: Dict[str, Any]
    ) -> str:
        """
        특수 규칙 적용

        Args:
            topic: 현재 선택된 토픽
            user_input: 사용자 입력
            state: 세션 상태

        Returns:
            최종 토픽
        """
        # 규칙 1: "안녕"은 컨텍스트로 greeting vs farewell 구분
        if "안녕" in user_input:
            turn_count = state.get("turn_count", 0)
            if turn_count == 0:
                return "greeting"
            elif turn_count >= 5 and any(word in user_input for word in ["잘", "나중", "다음"]):
                return "farewell"

        # 규칙 2: 물음표 있으면 question 우선
        if "?" in user_input or "?" in user_input:
            if topic not in ["greeting", "farewell"]:
                return "question"

        # 규칙 3: 짧은 입력 (3자 이하)은 agreement/disagreement 우선
        if len(user_input.strip()) <= 3:
            if topic in ["agreement", "disagreement"]:
                return topic

        return topic

    def get_response_strategy(self, route_result: RouteResult) -> Dict[str, Any]:
        """
        토픽에 따른 응답 전략 반환

        Args:
            route_result: 라우팅 결과

        Returns:
            전략 dict
        """
        strategies = {
            "greeting": {
                "emotion": "friendly",
                "style": "warm",
                "max_turns": 2,
                "should_ask_name": True
            },
            "farewell": {
                "emotion": "friendly",
                "style": "warm",
                "max_turns": 1,
                "should_end_session": True
            },
            "question": {
                "emotion": "helpful",
                "style": "informative",
                "max_turns": 3,
                "should_provide_detail": True
            },
            "emotion_positive": {
                "emotion": "happy",
                "style": "enthusiastic",
                "max_turns": 2,
                "should_encourage": True
            },
            "emotion_negative": {
                "emotion": "empathetic",
                "style": "supportive",
                "max_turns": 3,
                "should_comfort": True
            },
            "scenario_specific": {
                "emotion": "focused",
                "style": "narrative",
                "max_turns": 5,
                "should_advance_plot": True
            },
            "general": {
                "emotion": "neutral",
                "style": "conversational",
                "max_turns": 2,
                "should_maintain_context": True
            }
        }

        strategy = strategies.get(route_result.topic, strategies["general"])

        logger.info(
            "get_response_strategy",
            f"Strategy selected for {route_result.topic}",
            emotion=strategy["emotion"],
            style=strategy["style"]
        )

        return strategy
