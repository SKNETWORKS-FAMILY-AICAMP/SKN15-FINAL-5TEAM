"""
Router Agent - 토픽 분류
사용자 입력의 의도와 토픽을 분류하여 적절한 응답 전략 선택
"""
import re
from typing import Dict, Any, Optional, List
from app.core.logging import get_parent_logger
from app.core.embeddings import get_embeddings_service

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

    Phase 7: 임베딩 기반 분류 + 키워드 fallback
    """

    # 토픽별 예시 문장 (임베딩용)
    TOPIC_EXAMPLES = {
        "greeting": [
            "안녕하세요",
            "처음 뵙겠습니다",
            "반갑습니다",
            "하이",
            "헬로"
        ],
        "farewell": [
            "안녕히 계세요",
            "나중에 봐요",
            "다음에 또 만나요",
            "그만 이야기할게요",
            "잘 가요"
        ],
        "question": [
            "이게 뭐예요?",
            "어디로 가야 하나요?",
            "왜 그런 거죠?",
            "어떻게 하면 되나요?",
            "누가 한 거예요?"
        ],
        "emotion_positive": [
            "정말 좋아요!",
            "최고예요!",
            "감사합니다!",
            "너무 행복해요",
            "기분이 좋네요"
        ],
        "emotion_negative": [
            "화가 나요",
            "슬퍼요",
            "짜증이 나네요",
            "우울해요",
            "너무 힘들어요"
        ],
        "agreement": [
            "네, 알겠습니다",
            "그래요, 맞아요",
            "오케이",
            "좋아요",
            "응"
        ],
        "disagreement": [
            "아니요",
            "싫어요",
            "안 할래요",
            "거절할게요",
            "반대합니다"
        ],
        "personal": [
            "저는요",
            "제 이야기를 해볼게요",
            "나는 말이야",
            "우리 가족은",
            "내 생각에는"
        ],
        "scenario_specific": [
            "도깨비가 어디 있나요?",
            "임무를 완수했어요",
            "이 퀘스트 어떻게 해요?",
            "미션 진행 상황은?",
            "목표는 뭔가요?"
        ],
        "general": [
            "그냥 이야기하고 싶어요",
            "요즘 어때요?",
            "재미있네요",
            "계속 해봐요",
            "그렇군요"
        ]
    }

    # 토픽별 키워드 (fallback용)
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

    def __init__(self, use_embeddings: bool = True):
        """
        RouterAgent 초기화

        Args:
            use_embeddings: 임베딩 기반 분류 사용 여부
        """
        self.use_embeddings = use_embeddings
        self.embeddings_service = None
        self.topic_embeddings: Dict[str, List[float]] = {}

        if use_embeddings:
            try:
                self.embeddings_service = get_embeddings_service()
                self._precompute_topic_embeddings()
                logger.info("__init__", "RouterAgent initialized with embeddings")
            except Exception as e:
                logger.warning("__init__", f"Failed to initialize embeddings: {e}. Falling back to keywords.")
                self.use_embeddings = False
        else:
            logger.info("__init__", "RouterAgent initialized (keyword-only)")

    def _precompute_topic_embeddings(self):
        """토픽별 예시 문장들의 평균 임베딩을 미리 계산"""
        if not self.embeddings_service:
            return

        logger.info("_precompute_topic_embeddings", "Precomputing topic embeddings...")

        for topic, examples in self.TOPIC_EXAMPLES.items():
            try:
                # 배치로 임베딩 생성
                embeddings = self.embeddings_service.embed_batch(examples)

                # 평균 임베딩 계산 (centroid)
                import numpy as np
                avg_embedding = np.mean(embeddings, axis=0).tolist()

                self.topic_embeddings[topic] = avg_embedding

                logger.debug(
                    "_precompute_topic_embeddings",
                    f"Topic '{topic}' embedded",
                    examples_count=len(examples)
                )

            except Exception as e:
                logger.error("_precompute_topic_embeddings", f"Failed to embed topic '{topic}': {e}")

        logger.info("_precompute_topic_embeddings", f"✅ Precomputed {len(self.topic_embeddings)} topic embeddings")

    def classify(self, user_input: str, state: Dict[str, Any]) -> RouteResult:
        """
        사용자 입력 분류

        Phase 7: 임베딩 기반 → 키워드 fallback

        Args:
            user_input: 사용자 입력
            state: 세션 상태

        Returns:
            RouteResult
        """
        user_input_lower = user_input.lower().strip()

        # 1. 임베딩 기반 분류 시도
        if self.use_embeddings and self.embeddings_service and self.topic_embeddings:
            try:
                embedding_result = self._classify_by_embedding(user_input, state)
                if embedding_result.confidence >= 0.6:  # 신뢰도 충분
                    logger.info(
                        "classify",
                        f"✅ Topic classified (embedding): {embedding_result.topic}",
                        confidence=round(embedding_result.confidence, 2),
                        method="embedding"
                    )
                    return embedding_result
            except Exception as e:
                logger.warning("classify", f"Embedding classification failed: {e}. Falling back to keywords.")

        # 2. 키워드 fallback
        return self._classify_by_keywords(user_input_lower, state)

    def _classify_by_embedding(self, user_input: str, state: Dict[str, Any]) -> RouteResult:
        """
        임베딩 기반 분류

        Args:
            user_input: 사용자 입력
            state: 세션 상태

        Returns:
            RouteResult
        """
        # 사용자 입력 임베딩
        input_embedding = self.embeddings_service.embed(user_input)

        # 각 토픽과의 유사도 계산
        similarities = self.embeddings_service.find_most_similar(
            query_embedding=input_embedding,
            candidate_embeddings=self.topic_embeddings,
            top_k=3  # 상위 3개
        )

        # 컨텍스트 기반 조정
        context_modifiers = self._get_context_modifiers(state)

        adjusted_similarities = []
        for topic, similarity in similarities:
            # 컨텍스트 보정 적용
            modifier = context_modifiers.get(topic, 1.0)
            adjusted_score = similarity * modifier
            adjusted_similarities.append((topic, adjusted_score))

        # 재정렬
        adjusted_similarities.sort(key=lambda x: x[1], reverse=True)

        best_topic, best_score = adjusted_similarities[0]

        # 특수 규칙 적용
        best_topic = self._apply_special_rules(best_topic, user_input.lower(), state)

        return RouteResult(
            topic=best_topic,
            confidence=float(best_score),
            keywords=[],  # 임베딩 기반이므로 키워드 없음
            metadata={
                "method": "embedding",
                "top3": adjusted_similarities[:3],
                "input_length": len(user_input)
            }
        )

    def _classify_by_keywords(self, user_input: str, state: Dict[str, Any]) -> RouteResult:
        """
        키워드 기반 분류 (fallback)

        Args:
            user_input: 사용자 입력 (소문자)
            state: 세션 상태

        Returns:
            RouteResult
        """
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
                if keyword in user_input:  # user_input is already lowercase
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
            best_topic, user_input, state  # user_input is already lowercase
        )

        logger.info(
            "classify",
            f"✅ Topic classified (keywords): {best_topic}",
            confidence=round(confidence, 2),
            keywords=matched_keywords.get(best_topic, []),
            method="keywords"
        )

        return RouteResult(
            topic=best_topic,
            confidence=confidence,
            keywords=matched_keywords.get(best_topic, []),
            metadata={
                "method": "keywords",
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
