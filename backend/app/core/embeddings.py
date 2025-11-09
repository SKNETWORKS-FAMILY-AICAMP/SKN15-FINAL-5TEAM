"""
Embeddings Service - 임베딩 생성 및 유사도 계산
텍스트를 벡터로 변환하여 의미적 유사도 기반 검색 지원
"""
import numpy as np
from typing import List, Dict, Any, Optional, Iterable, Sequence
from dataclasses import dataclass
from openai import OpenAI
import os
from functools import lru_cache

from app.core.logging import get_parent_logger

logger = get_parent_logger("Embeddings")


@dataclass
class MatchResult:
    """매칭 결과"""
    label: Optional[str]
    score: float


class EmbeddingsService:
    """
    임베딩 생성 및 유사도 계산 서비스

    OpenAI text-embedding-3-small 모델 사용
    - 저렴하고 빠름
    - 1536 차원 벡터
    - 다국어 지원
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        """
        EmbeddingsService 초기화

        Args:
            model: OpenAI 임베딩 모델명
        """
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        logger.info("__init__", f"EmbeddingsService initialized with model: {model}")

    def embed(self, text: str) -> List[float]:
        """
        텍스트를 임베딩 벡터로 변환

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (1536차원)
        """
        try:
            # OpenAI API 호출
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip()
            )

            embedding = response.data[0].embedding

            logger.debug("embed", f"Embedded text (len={len(text)})", dim=len(embedding))
            return embedding

        except Exception as e:
            logger.error("embed", f"Embedding failed: {e}", text_len=len(text))
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        여러 텍스트를 한 번에 임베딩 (배치 처리)

        Args:
            texts: 임베딩할 텍스트 리스트

        Returns:
            임베딩 벡터 리스트
        """
        try:
            # OpenAI API 배치 호출
            response = self.client.embeddings.create(
                model=self.model,
                input=[text.strip() for text in texts]
            )

            embeddings = [item.embedding for item in response.data]

            logger.info("embed_batch", f"Embedded {len(texts)} texts", total=len(texts))
            return embeddings

        except Exception as e:
            logger.error("embed_batch", f"Batch embedding failed: {e}", count=len(texts))
            raise

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        코사인 유사도 계산

        Args:
            vec1: 벡터 1
            vec2: 벡터 2

        Returns:
            유사도 (-1.0 ~ 1.0, 높을수록 유사)
        """
        # NumPy 배열로 변환
        a = np.array(vec1)
        b = np.array(vec2)

        # 코사인 유사도 = dot(a, b) / (norm(a) * norm(b))
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        similarity = dot_product / (norm_a * norm_b)
        return float(similarity)

    def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: Dict[str, List[float]],
        top_k: int = 1
    ) -> List[tuple[str, float]]:
        """
        쿼리 임베딩과 가장 유사한 후보들 찾기

        Args:
            query_embedding: 쿼리 임베딩 벡터
            candidate_embeddings: 후보 이름 → 임베딩 벡터 dict
            top_k: 상위 k개 반환

        Returns:
            (후보명, 유사도) 튜플 리스트 (유사도 내림차순)
        """
        similarities = []

        for name, embedding in candidate_embeddings.items():
            similarity = self.cosine_similarity(query_embedding, embedding)
            similarities.append((name, similarity))

        # 유사도 내림차순 정렬
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """
        서비스 통계 정보

        Returns:
            통계 dict
        """
        return {
            "model": self.model,
            "dimension": 1536,
            "service": "EmbeddingsService"
        }


# 전역 싱글톤 인스턴스
_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    """
    EmbeddingsService 싱글톤 인스턴스 가져오기

    Returns:
        EmbeddingsService 인스턴스
    """
    global _embeddings_service

    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()

    return _embeddings_service


# Convenience alias
def get_embeddings() -> EmbeddingsService:
    """Alias for get_embeddings_service()"""
    return get_embeddings_service()


class EmbeddingMatcher:
    """
    사전 정의된 라벨과의 유사도 매칭

    사전 정의된 용어 집합과의 코사인 유사도를 이용해 분류를 수행하는 헬퍼
    - 각 라벨은 하나 이상의 대표 키워드로 구성
    - 입력 문장을 임베딩으로 변환 후 가장 높은 유사도 라벨 반환

    Example:
        label_terms = {
            "greeting": ["안녕", "안녕하세요", "반가워요"],
            "farewell": ["잘가", "안녕히가세요", "나중에 봐요"]
        }
        matcher = EmbeddingMatcher(label_terms, threshold=0.8)
        result = matcher.match("안녕하세요!")
        print(result.label)  # "greeting"
        print(result.score)  # 0.95
    """

    def __init__(
        self,
        label_terms: Dict[str, Iterable[str]],
        *,
        threshold: float = 0.85,
        embeddings_service: Optional[EmbeddingsService] = None,
    ) -> None:
        """
        Args:
            label_terms: 라벨 → 대표 키워드 리스트 dict
            threshold: 매칭 임계값 (0.0-1.0)
            embeddings_service: EmbeddingsService 인스턴스 (None이면 자동 생성)
        """
        self.threshold = threshold
        self._service = embeddings_service or get_embeddings_service()
        self._label_embeddings: Dict[str, List[Sequence[float]]] = {}

        self._prepare_embeddings(label_terms)

        logger.info("__init__", "EmbeddingMatcher initialized",
                   labels=len(self._label_embeddings),
                   threshold=threshold)

    def _prepare_embeddings(self, label_terms: Dict[str, Iterable[str]]) -> None:
        """라벨별 키워드 임베딩 사전 계산"""
        for label, terms in label_terms.items():
            vectors: List[Sequence[float]] = []
            for term in terms:
                normalized = (term or "").strip()
                if not normalized:
                    continue

                try:
                    vector = self._service.embed(normalized)
                    if vector:
                        vectors.append(vector)
                except Exception as e:
                    logger.warning("_prepare_embeddings", f"Failed to embed term '{term}': {e}")
                    continue

            if vectors:
                self._label_embeddings[label] = vectors

        logger.debug("_prepare_embeddings", f"Prepared embeddings for {len(self._label_embeddings)} labels")

    def match(self, text: str, *, embedding: Optional[Sequence[float]] = None) -> MatchResult:
        """
        텍스트를 가장 유사한 라벨과 매칭 (threshold 적용)

        Args:
            text: 입력 텍스트
            embedding: 사전 계산된 임베딩 (None이면 자동 계산)

        Returns:
            MatchResult (label, score)
        """
        if not text or not text.strip():
            return MatchResult(label=None, score=0.0)

        # 임베딩 계산
        try:
            vector = embedding or self._service.embed(text)
            if not vector:
                return MatchResult(label=None, score=0.0)
        except Exception as e:
            logger.error("match", f"Embedding failed: {e}")
            return MatchResult(label=None, score=0.0)

        # 모든 라벨과 비교
        best_label: Optional[str] = None
        best_score = 0.0

        for label, vectors in self._label_embeddings.items():
            for ref in vectors:
                try:
                    score = self._service.cosine_similarity(vector, ref)
                    if score > best_score:
                        best_score = score
                        best_label = label
                except Exception as e:
                    logger.warning("match", f"Similarity calculation failed for label '{label}': {e}")
                    continue

        # Threshold 체크
        if best_score < self.threshold:
            return MatchResult(label=None, score=best_score)

        return MatchResult(label=best_label, score=best_score)

    def best_match(self, text: str, *, embedding: Optional[Sequence[float]] = None) -> MatchResult:
        """
        threshold를 무시하고 가장 높은 점수의 label 반환 (fallback 모드)

        Args:
            text: 입력 텍스트
            embedding: 사전 계산된 임베딩

        Returns:
            MatchResult (label, score)
        """
        if not text or not text.strip():
            return MatchResult(label=None, score=0.0)

        # 임베딩 계산
        try:
            vector = embedding or self._service.embed(text)
            if not vector:
                return MatchResult(label=None, score=0.0)
        except Exception as e:
            logger.error("best_match", f"Embedding failed: {e}")
            return MatchResult(label=None, score=0.0)

        # 모든 라벨과 비교
        best_label: Optional[str] = None
        best_score = 0.0

        for label, vectors in self._label_embeddings.items():
            for ref in vectors:
                try:
                    score = self._service.cosine_similarity(vector, ref)
                    if score > best_score:
                        best_score = score
                        best_label = label
                except Exception as e:
                    logger.warning("best_match", f"Similarity calculation failed for label '{label}': {e}")
                    continue

        # threshold 체크 없이 best 반환
        return MatchResult(label=best_label, score=best_score)

    def is_match(self, text: str, *, embedding: Optional[Sequence[float]] = None) -> bool:
        """
        텍스트가 어떤 라벨과 매칭되는지 여부만 반환

        Args:
            text: 입력 텍스트
            embedding: 사전 계산된 임베딩

        Returns:
            매칭 성공 여부
        """
        result = self.match(text, embedding=embedding)
        return result.label is not None
