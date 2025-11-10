"""
[Core] 텍스트 임베딩 서비스 모듈

이 모듈은 텍스트를 고차원 벡터(Embedding)로 변환하고, 벡터 간의 유사도를
계산하는 기능을 제공합니다. 주로 의미 기반 검색이나 콘텐츠 추천 등에 활용됩니다.
OpenAI의 임베딩 모델을 사용하여 구현되었습니다.
"""
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI
import os
from functools import lru_cache

from app.core.logging import get_parent_logger
from app.core.config import get_settings

# 모듈 전역 로거 및 설정 객체
logger = get_parent_logger("Embeddings")
settings = get_settings()


# ============================================================
# 임베딩 서비스 클래스
# ============================================================
class EmbeddingsService:
    """
    텍스트 임베딩 생성 및 관련 계산을 수행하는 서비스 클래스입니다.

    주요 기능:
    - 단일/배치 텍스트를 임베딩 벡터로 변환합니다.
    - 두 벡터 간의 코사인 유사도를 계산합니다.
    - 주어진 쿼리 벡터와 가장 유사한 후보 벡터를 찾습니다.

    사용 모델:
    - OpenAI `text-embedding-3-small`: 비용 효율적이고 빠른 성능을 제공하며,
      1536 차원의 벡터를 생성하고 다국어를 지원합니다.
    """

    def __init__(self, model: Optional[str] = None):
        """
        EmbeddingsService를 초기화합니다.

        Args:
            model (Optional[str]): 사용할 OpenAI 임베딩 모델명.
                                   None이면 설정 파일의 기본값을 사용합니다.
        """
        self.model = model or settings.OPENAI_EMBEDDING_MODEL
        # NOTE: API 키를 설정(settings) 객체에서 일관되게 가져오는 것이 좋습니다.
        #       os.getenv()를 직접 사용하는 것보다 중앙 관리 방식이 유지보수에 유리합니다.
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("__init__", f"EmbeddingsService initialized with model: {self.model}")

    def embed(self, text: str) -> List[float]:
        """
        하나의 텍스트를 임베딩 벡터로 변환합니다.

        Args:
            text (str): 임베딩으로 변환할 텍스트.

        Returns:
            List[float]: 텍스트에 해당하는 1536차원의 임베딩 벡터.

        Raises:
            Exception: OpenAI API 호출 실패 시 예외가 발생합니다.
        """
        try:
            # 텍스트 양 끝의 공백을 제거하여 불필요한 토큰 사용을 방지합니다.
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
        여러 개의 텍스트를 한 번의 API 호출로 임베딩 처리합니다. (배치 처리)
        단일 텍스트를 여러 번 호출하는 것보다 효율적입니다.

        Args:
            texts (List[str]): 임베딩으로 변환할 텍스트 목록.

        Returns:
            List[List[float]]: 각 텍스트에 해당하는 임베딩 벡터의 목록.
        """
        try:
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
        두 벡터 간의 코사인 유사도를 계산합니다.

        코사인 유사도는 두 벡터가 이루는 각도의 코사인 값으로, -1에서 1 사이의 값을 가집니다.
        1에 가까울수록 두 벡터의 방향이 유사함을 의미합니다.

        Args:
            vec1 (List[float]): 첫 번째 벡터.
            vec2 (List[float]): 두 번째 벡터.

        Returns:
            float: 두 벡터 간의 코사인 유사도 값.
        """
        # 계산을 위해 리스트를 NumPy 배열로 변환합니다.
        a = np.array(vec1)
        b = np.array(vec2)

        # 코사인 유사도 공식: dot(a, b) / (norm(a) * norm(b))
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        # 0으로 나누는 것을 방지
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
        주어진 쿼리 임베딩과 가장 유사한 후보들을 상위 k개 찾습니다.

        Args:
            query_embedding (List[float]): 기준이 되는 쿼리 임베딩 벡터.
            candidate_embeddings (Dict[str, List[float]]): 비교 대상이 될 후보 임베딩들의 딕셔너리 (key: 후보 이름, value: 임베딩 벡터).
            top_k (int): 반환할 상위 유사도 후보의 수.

        Returns:
            List[tuple[str, float]]: (후보 이름, 유사도) 튜플의 리스트. 유사도 순으로 내림차순 정렬됩니다.
        """
        similarities = []
        for name, embedding in candidate_embeddings.items():
            similarity = self.cosine_similarity(query_embedding, embedding)
            similarities.append((name, similarity))

        # 유사도를 기준으로 내림차순 정렬
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """
        현재 임베딩 서비스의 통계 정보를 반환합니다.

        Returns:
            Dict[str, Any]: 서비스 관련 통계 정보 (모델명, 차원 등).
        """
        return {
            "model": self.model,
            "dimension": 1536,  # text-embedding-3-small 모델의 벡터 차원
            "service": "EmbeddingsService"
        }


# ============================================================
# 싱글톤 인스턴스 관리
# ============================================================
# 애플리케이션 전역에서 단 하나의 EmbeddingsService 인스턴스만 사용하도록 관리합니다.
_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    """
    EmbeddingsService의 싱글톤 인스턴스를 반환합니다.

    NOTE: 이 싱글톤 구현은 스레드 환경에서 안전하지 않습니다(Not Thread-Safe).
          만약 여러 스레드가 동시에 이 함수를 호출하면, `_embeddings_service`가
          None인지 확인하는 부분에서 Race Condition이 발생하여 여러 개의 인스턴스가
          생성될 수 있습니다.
          더 안전한 방법은 애플리케이션 시작 시점에 인스턴스를 생성하여
          FastAPI의 app.state에 보관하는 것입니다.

    Returns:
        EmbeddingsService: 전역 싱글톤 인스턴스.
    """
    global _embeddings_service

    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()

    return _embeddings_service
