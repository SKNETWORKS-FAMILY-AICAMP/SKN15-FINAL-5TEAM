"""
Embeddings Service - 임베딩 생성 및 유사도 계산
텍스트를 벡터로 변환하여 의미적 유사도 기반 검색 지원
"""
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI
import os
from functools import lru_cache

from app.core.logging import get_parent_logger

logger = get_parent_logger("Embeddings")


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
