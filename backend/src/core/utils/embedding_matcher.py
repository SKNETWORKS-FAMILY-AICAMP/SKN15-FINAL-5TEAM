from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - defensive
    OpenAI = None  # type: ignore


logger = logging.getLogger("embedding_client")


class EmbeddingClient:
    """
    OpenAI 기반 임베딩 클라이언트.
    - OpenAI Embedding API 호출
    - 실패 시 해시 기반 임베딩으로 폴백
    """

    _TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")

    def __init__(self, *, model: Optional[str] = None, hash_dim: int = 256) -> None:
        self.model = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self._hash_dim = hash_dim
        self._cache: Dict[str, List[float]] = {}
        self._fallback_cache: Dict[str, List[float]] = {}
        self._use_fallback = False

        api_key = os.getenv("OPENAI_API_KEY")
        self._client: Optional[OpenAI] = None
        if api_key and OpenAI is not None:
            try:
                self._client = OpenAI(api_key=api_key)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to initialise OpenAI client, using hashed embeddings. (%s)", exc)
                self._client = None
                self._use_fallback = True
        elif api_key and OpenAI is None:
            logger.warning("openai 패키지를 찾을 수 없습니다. hashed embedding으로 대체합니다.")
            self._use_fallback = True
        else:
            logger.warning("OPENAI_API_KEY not set. Falling back to hashed embeddings.")
            self._use_fallback = True

    # ------------------------------------------------------------------
    def embed(self, text: str) -> List[float]:
        key = (text or "").strip()
        if not key:
            return []

        cache_key = key.lower()
        if not self._use_fallback and cache_key in self._cache:
            return self._cache[cache_key]
        if self._use_fallback and cache_key in self._fallback_cache:
            return self._fallback_cache[cache_key]

        if not self._use_fallback and self._client:
            try:
                response = self._client.embeddings.create(model=self.model, input=key)
                vector = response.data[0].embedding
                self._cache[cache_key] = vector
                return vector
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Embedding API failed (%s). Falling back to hashed embeddings.", exc)
                self._use_fallback = True
                # fall through to hashed embedding

        vector = self._hash_embedding(key)
        self._fallback_cache[cache_key] = vector
        return vector

    def cosine_similarity(self, a: Sequence[float], b: Sequence[float]) -> float:
        if not a or not b:
            return 0.0
        if len(a) != len(b):
            # if dimensions differ (e.g., real vs fallback), align by padding/truncation
            length = min(len(a), len(b))
            a = a[:length]
            b = b[:length]
        dot = sum(x * y for x, y in zip(a, b))
        if dot == 0.0:
            return 0.0
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ------------------------------------------------------------------
    def _hash_embedding(self, text: str) -> List[float]:
        features = self._extract_features(text)
        vector = [0.0] * self._hash_dim
        for feature, weight in features.items():
            index = self._hash_index(feature)
            vector[index] += weight
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def _extract_features(self, text: str) -> Counter[str]:
        tokens = self._TOKEN_RE.findall(text.lower())
        lowered = "".join(tokens)
        bigrams = [lowered[i : i + 2] for i in range(max(len(lowered) - 1, 0))]
        return Counter(tokens + bigrams)

    def _hash_index(self, feature: str) -> int:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16).digest()
        return int.from_bytes(digest, "big") % self._hash_dim


_EMBEDDING_CLIENT: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    global _EMBEDDING_CLIENT
    if _EMBEDDING_CLIENT is None:
        _EMBEDDING_CLIENT = EmbeddingClient()
    return _EMBEDDING_CLIENT


@dataclass
class MatchResult:
    label: Optional[str]
    score: float


class EmbeddingMatcher:
    """
    사전 정의된 용어 집합과의 코사인 유사도를 이용해 분류를 수행하는 헬퍼.
    - 각 라벨은 하나 이상의 대표 키워드로 구성
    - 입력 문장을 OpenAI 임베딩으로 변환 후 가장 높은 유사도 라벨을 반환
    """

    def __init__(
        self,
        label_terms: Dict[str, Iterable[str]],
        *,
        threshold: float = 0.85,
        embedding_client: Optional[EmbeddingClient] = None,
    ) -> None:
        self.threshold = threshold
        self._client = embedding_client or get_embedding_client()
        self._label_embeddings: Dict[str, List[Sequence[float]]] = {}
        self._prepare_embeddings(label_terms)

    def _prepare_embeddings(self, label_terms: Dict[str, Iterable[str]]) -> None:
        for label, terms in label_terms.items():
            vectors: List[Sequence[float]] = []
            for term in terms:
                normalized = (term or "").strip()
                if not normalized:
                    continue
                vector = self._client.embed(normalized)
                if vector:
                    vectors.append(vector)
            if vectors:
                self._label_embeddings[label] = vectors

    def match(self, text: str, *, embedding: Optional[Sequence[float]] = None) -> MatchResult:
        if not text or not text.strip():
            return MatchResult(label=None, score=0.0)

        vector = embedding or self._client.embed(text)
        if not vector:
            return MatchResult(label=None, score=0.0)

        best_label: Optional[str] = None
        best_score = 0.0

        for label, vectors in self._label_embeddings.items():
            for ref in vectors:
                score = self._client.cosine_similarity(vector, ref)
                if score > best_score:
                    best_score = score
                    best_label = label

        if best_score < self.threshold:
            return MatchResult(label=None, score=best_score)
        return MatchResult(label=best_label, score=best_score)

    def best_match(self, text: str, *, embedding: Optional[Sequence[float]] = None) -> MatchResult:
        """
        threshold를 무시하고 가장 높은 점수의 label을 반환
        fallback 모드에서 사용
        """
        if not text or not text.strip():
            return MatchResult(label=None, score=0.0)

        vector = embedding or self._client.embed(text)
        if not vector:
            return MatchResult(label=None, score=0.0)

        best_label: Optional[str] = None
        best_score = 0.0

        for label, vectors in self._label_embeddings.items():
            for ref in vectors:
                score = self._client.cosine_similarity(vector, ref)
                if score > best_score:
                    best_score = score
                    best_label = label

        # threshold 체크 없이 best를 반환
        return MatchResult(label=best_label, score=best_score)

    def is_match(self, text: str, *, embedding: Optional[Sequence[float]] = None) -> bool:
        result = self.match(text, embedding=embedding)
        return result.label is not None


__all__ = ["EmbeddingMatcher", "MatchResult", "EmbeddingClient", "get_embedding_client"]
