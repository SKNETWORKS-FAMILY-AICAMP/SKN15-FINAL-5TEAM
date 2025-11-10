#!/usr/bin/env python3
"""
Method 4: Hybrid Multi-hop RAG

Graph RAG + Multi-hop 관계 탐색 + Embedding 검색 결합
- Entity 관계를 따라 2-hop까지 탐색
- Embedding으로 유사 상황 검색
- 고품질 예제 + 관련 엔티티 컨텍스트 제공

장점:
  ✅ 파인튜닝 불필요 (즉시 사용 가능)
  ✅ 엔티티 관계를 활용한 맥락 이해
  ✅ 2-hop 관계로 더 풍부한 컨텍스트
  ✅ 기존 Graph RAG 시스템과 통합 용이

사용 사례:
  - "렌고쿠와 탄지로의 관계는?" → 렌고쿠-탄지로 직접 관계 + 무한열차 공통 참여
  - "이노스케 설득법?" → 이노스케-탄지로 관계 + 과거 성공 사례 검색

사용법:
  # 1. Multi-hop 검색 인덱스 구축
  python scripts/method4_hybrid_multihop_rag.py --build-index

  # 2. 쿼리 테스트
  python scripts/method4_hybrid_multihop_rag.py --query "이노스케를 설득하려면?" --hops 2

  # 3. 프롬프트 강화 모드 (실시간)
  python scripts/method4_hybrid_multihop_rag.py --enhance-prompt --agent children
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor


class HybridMultihopRAG:
    """Hybrid Multi-hop RAG 검색 엔진"""

    def __init__(self, db_url: Optional[str] = None, statedb_url: Optional[str] = None):
        """
        Args:
            db_url: LogDB connection URL (training_logs)
            statedb_url: StateDB connection URL (entities, relationships)
        """
        self.db_url = db_url or os.getenv("LOGDB_URL", os.getenv("DATABASE_URL"))
        self.statedb_url = statedb_url or os.getenv("DATABASE_URL")

    def get_logdb_connection(self):
        """LogDB 연결 (training_logs)"""
        return psycopg2.connect(self.db_url)

    def get_statedb_connection(self):
        """StateDB 연결 (entities, relationships)"""
        return psycopg2.connect(self.statedb_url)

    def extract_entities_from_query(
        self,
        query_text: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        쿼리에서 관련 엔티티 추출

        Args:
            query_text: 쿼리 텍스트
            query_embedding: 쿼리 임베딩 (옵션)
            top_k: 검색할 엔티티 수

        Returns:
            관련 엔티티 리스트
        """
        conn = self.get_statedb_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 방법 1: 텍스트 매칭 (키워드)
        keywords = query_text.lower().split()
        text_matched = []

        cursor.execute("""
            SELECT
                entity_id,
                entity_type,
                entity_name,
                canonical_name,
                description,
                importance_score,
                mention_count
            FROM entities
            WHERE LOWER(entity_name) = ANY(%s)
               OR LOWER(canonical_name) = ANY(%s)
            ORDER BY importance_score DESC, mention_count DESC
            LIMIT %s
        """, (keywords, keywords, top_k))

        text_matched = cursor.fetchall()

        # 방법 2: Embedding 유사도 (query_embedding이 있을 때)
        embedding_matched = []
        if query_embedding:
            cursor.execute("""
                SELECT
                    entity_id,
                    entity_type,
                    entity_name,
                    canonical_name,
                    description,
                    importance_score,
                    mention_count,
                    1 - (embedding <=> %s::vector) as similarity
                FROM entities
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, top_k))

            embedding_matched = cursor.fetchall()

        cursor.close()
        conn.close()

        # 결합 (중복 제거)
        seen_ids = set()
        entities = []

        for entity in text_matched + embedding_matched:
            if entity["entity_id"] not in seen_ids:
                seen_ids.add(entity["entity_id"])
                entities.append(dict(entity))

        return entities[:top_k]

    def find_multihop_relationships(
        self,
        entity_ids: List[int],
        max_hops: int = 2,
        min_strength: float = 0.3
    ) -> Dict[str, Any]:
        """
        Multi-hop 관계 탐색

        Args:
            entity_ids: 시작 엔티티 ID 리스트
            max_hops: 최대 hop 수 (1 or 2)
            min_strength: 최소 관계 강도

        Returns:
            {
                "1hop": [(entity1, relation, entity2)],
                "2hop": [(entity1, bridge, entity2)],
                "related_entities": [entity_dict]
            }
        """
        conn = self.get_statedb_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 1-hop: 직접 연결
        cursor.execute("""
            SELECT
                r.source_entity_id,
                r.target_entity_id,
                r.relationship_type,
                r.strength,
                r.confidence,
                e1.entity_name as source_name,
                e2.entity_name as target_name
            FROM entity_relationships r
            JOIN entities e1 ON r.source_entity_id = e1.entity_id
            JOIN entities e2 ON r.target_entity_id = e2.entity_id
            WHERE (r.source_entity_id = ANY(%s) OR r.target_entity_id = ANY(%s))
              AND r.strength >= %s
            ORDER BY r.strength DESC, r.confidence DESC
        """, (entity_ids, entity_ids, min_strength))

        one_hop = cursor.fetchall()

        # 관련 엔티티 ID 수집
        related_ids = set()
        for rel in one_hop:
            related_ids.add(rel["source_entity_id"])
            related_ids.add(rel["target_entity_id"])

        # 2-hop: 간접 연결 (bridge entity)
        two_hop = []
        if max_hops >= 2:
            cursor.execute("""
                SELECT
                    r1.source_entity_id as start_id,
                    r1.target_entity_id as bridge_id,
                    r2.target_entity_id as end_id,
                    e1.entity_name as start_name,
                    e_bridge.entity_name as bridge_name,
                    e2.entity_name as end_name,
                    r1.relationship_type as relation1,
                    r2.relationship_type as relation2,
                    (r1.strength * r2.strength) as combined_strength
                FROM entity_relationships r1
                JOIN entity_relationships r2
                    ON r1.target_entity_id = r2.source_entity_id
                JOIN entities e1 ON r1.source_entity_id = e1.entity_id
                JOIN entities e_bridge ON r1.target_entity_id = e_bridge.entity_id
                JOIN entities e2 ON r2.target_entity_id = e2.entity_id
                WHERE r1.source_entity_id = ANY(%s)
                  AND r2.target_entity_id NOT IN (SELECT unnest(%s::int[]))
                  AND r1.strength >= %s
                  AND r2.strength >= %s
                ORDER BY combined_strength DESC
                LIMIT 20
            """, (entity_ids, entity_ids, min_strength, min_strength))

            two_hop = cursor.fetchall()

            for rel in two_hop:
                related_ids.add(rel["bridge_id"])
                related_ids.add(rel["end_id"])

        # 관련 엔티티 상세 정보
        cursor.execute("""
            SELECT
                entity_id,
                entity_type,
                entity_name,
                canonical_name,
                description,
                importance_score
            FROM entities
            WHERE entity_id = ANY(%s)
        """, (list(related_ids),))

        related_entities = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "1hop": [dict(r) for r in one_hop],
            "2hop": [dict(r) for r in two_hop],
            "related_entities": [dict(e) for e in related_entities]
        }

    def search_similar_training_logs(
        self,
        query_embedding: List[float],
        entity_ids: List[int],
        agent_name: str,
        min_score: float = 0.7,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        유사한 고품질 학습 로그 검색

        Args:
            query_embedding: 쿼리 임베딩
            entity_ids: 관련 엔티티 ID
            agent_name: 에이전트 이름
            min_score: 최소 feedback_score
            top_k: 검색할 로그 수

        Returns:
            유사한 로그 리스트
        """
        conn = self.get_logdb_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Hybrid 검색: Embedding + Entity overlap
        cursor.execute("""
            SELECT
                id,
                user_input,
                context,
                model_output,
                feedback_score,
                outcome_reason,
                mentioned_entity_ids,
                -- Vector similarity
                1 - (embedding <=> %s::vector) as vector_similarity,
                -- Entity overlap (Jaccard)
                CASE
                    WHEN mentioned_entity_ids IS NULL OR cardinality(mentioned_entity_ids) = 0
                    THEN 0
                    ELSE
                        cardinality(mentioned_entity_ids & %s::int[])::float /
                        cardinality(mentioned_entity_ids | %s::int[])::float
                END as entity_overlap,
                -- Combined score (70% vector + 30% entity)
                (0.7 * (1 - (embedding <=> %s::vector)) +
                 0.3 * CASE
                    WHEN mentioned_entity_ids IS NULL OR cardinality(mentioned_entity_ids) = 0
                    THEN 0
                    ELSE
                        cardinality(mentioned_entity_ids & %s::int[])::float /
                        cardinality(mentioned_entity_ids | %s::int[])::float
                END) as combined_score
            FROM training_logs
            WHERE agent_name = %s
              AND feedback_score >= %s
              AND embedding IS NOT NULL
              AND outcome = 'success'
            ORDER BY combined_score DESC
            LIMIT %s
        """, (
            query_embedding,
            entity_ids, entity_ids,
            query_embedding,
            entity_ids, entity_ids,
            agent_name, min_score, top_k
        ))

        logs = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(log) for log in logs]

    def generate_enhanced_prompt(
        self,
        query: str,
        agent_name: str,
        query_embedding: Optional[List[float]] = None,
        max_hops: int = 2,
        include_examples: int = 3
    ) -> str:
        """
        Multi-hop RAG로 프롬프트 강화

        Args:
            query: 사용자 쿼리
            agent_name: 에이전트 이름
            query_embedding: 쿼리 임베딩
            max_hops: 최대 hop 수
            include_examples: 포함할 예제 수

        Returns:
            강화된 프롬프트
        """
        prompt_parts = []

        # 1. 관련 엔티티 추출
        entities = self.extract_entities_from_query(query, query_embedding, top_k=3)

        if entities:
            prompt_parts.append("\n## 🔍 관련 엔티티\n")
            for ent in entities[:3]:
                prompt_parts.append(
                    f"- **{ent['entity_name']}** ({ent['entity_type']}): "
                    f"{ent.get('description', 'N/A')[:100]}"
                )

        # 2. Multi-hop 관계 탐색
        if entities:
            entity_ids = [e["entity_id"] for e in entities]
            relationships = self.find_multihop_relationships(entity_ids, max_hops=max_hops)

            # 1-hop 관계
            if relationships["1hop"]:
                prompt_parts.append("\n## 🔗 직접 관계 (1-hop)\n")
                for rel in relationships["1hop"][:5]:
                    prompt_parts.append(
                        f"- {rel['source_name']} --[{rel['relationship_type']}]--> "
                        f"{rel['target_name']} (강도: {rel['strength']:.2f})"
                    )

            # 2-hop 관계
            if max_hops >= 2 and relationships["2hop"]:
                prompt_parts.append("\n## 🌐 간접 관계 (2-hop)\n")
                for rel in relationships["2hop"][:3]:
                    prompt_parts.append(
                        f"- {rel['start_name']} → {rel['bridge_name']} → {rel['end_name']} "
                        f"(강도: {rel['combined_strength']:.2f})"
                    )

        # 3. 유사한 고품질 예제 검색
        if query_embedding and entities:
            entity_ids = [e["entity_id"] for e in entities]
            similar_logs = self.search_similar_training_logs(
                query_embedding,
                entity_ids,
                agent_name,
                top_k=include_examples
            )

            if similar_logs:
                prompt_parts.append(f"\n## ⭐ 유사한 고품질 예제 ({len(similar_logs)}개)\n")
                for i, log in enumerate(similar_logs, 1):
                    prompt_parts.append(
                        f"\n### 예제 {i} "
                        f"(점수: {log['feedback_score']:.2f}, "
                        f"유사도: {log['vector_similarity']:.2f}, "
                        f"엔티티 겹침: {log['entity_overlap']:.2f})"
                    )
                    prompt_parts.append(f"**입력**: {log['user_input'][:100]}...")

                    # Agent별 출력 포맷
                    if agent_name == "children":
                        responses = log["model_output"].get("agent_responses", [])
                        prompt_parts.append(f"**대사 수**: {len(responses)}")
                        for j, resp in enumerate(responses[:2], 1):
                            prompt_parts.append(
                                f"  {j}. {resp.get('character')}: "
                                f"\"{resp.get('text', '')[:50]}...\""
                            )

        return "\n".join(prompt_parts)

    def build_index_stats(self) -> Dict[str, Any]:
        """Multi-hop RAG 인덱스 통계"""
        statedb_conn = self.get_statedb_connection()
        logdb_conn = self.get_logdb_connection()

        state_cursor = statedb_conn.cursor(cursor_factory=RealDictCursor)
        log_cursor = logdb_conn.cursor(cursor_factory=RealDictCursor)

        # Entity 통계
        state_cursor.execute("""
            SELECT
                COUNT(*) as total_entities,
                COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embedding,
                AVG(importance_score) as avg_importance,
                SUM(mention_count) as total_mentions
            FROM entities
        """)
        entity_stats = state_cursor.fetchone()

        # Relationship 통계
        state_cursor.execute("""
            SELECT
                COUNT(*) as total_relationships,
                AVG(strength) as avg_strength,
                AVG(confidence) as avg_confidence
            FROM entity_relationships
        """)
        rel_stats = state_cursor.fetchone()

        # Training logs 통계
        log_cursor.execute("""
            SELECT
                COUNT(*) as total_logs,
                COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embedding,
                COUNT(CASE WHEN mentioned_entity_ids IS NOT NULL THEN 1 END) as with_entities,
                AVG(feedback_score) as avg_score
            FROM training_logs
            WHERE outcome = 'success'
        """)
        log_stats = log_cursor.fetchone()

        state_cursor.close()
        log_cursor.close()
        statedb_conn.close()
        logdb_conn.close()

        return {
            "entities": dict(entity_stats),
            "relationships": dict(rel_stats),
            "training_logs": dict(log_stats)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Hybrid Multi-hop RAG (Method 4)"
    )

    parser.add_argument(
        "--build-index",
        action="store_true",
        help="인덱스 통계 확인"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="검색 쿼리"
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="children",
        choices=["router", "parent", "children"],
        help="에이전트 이름 (기본: children)"
    )
    parser.add_argument(
        "--hops",
        type=int,
        default=2,
        choices=[1, 2],
        help="최대 hop 수 (기본: 2)"
    )
    parser.add_argument(
        "--enhance-prompt",
        action="store_true",
        help="프롬프트 강화 모드"
    )

    args = parser.parse_args()

    rag = HybridMultihopRAG()

    if args.build_index:
        print("\n" + "="*70)
        print("📊 Hybrid Multi-hop RAG 인덱스 통계")
        print("="*70)

        stats = rag.build_index_stats()

        print("\n### Entities (statedb)")
        print(f"  총 엔티티: {stats['entities']['total_entities']}")
        print(f"  Embedding 보유: {stats['entities']['with_embedding']}")
        print(f"  평균 중요도: {stats['entities']['avg_importance']:.3f}")
        print(f"  총 언급 수: {stats['entities']['total_mentions']}")

        print("\n### Relationships (statedb)")
        print(f"  총 관계: {stats['relationships']['total_relationships']}")
        print(f"  평균 강도: {stats['relationships']['avg_strength']:.3f}")
        print(f"  평균 확신도: {stats['relationships']['avg_confidence']:.3f}")

        print("\n### Training Logs (logdb)")
        print(f"  성공 로그: {stats['training_logs']['total_logs']}")
        print(f"  Embedding 보유: {stats['training_logs']['with_embedding']}")
        print(f"  Entity 연결: {stats['training_logs']['with_entities']}")
        print(f"  평균 점수: {stats['training_logs']['avg_score']:.3f}")

        print("\n✅ Multi-hop RAG 준비 완료!")

    elif args.query or args.enhance_prompt:
        query = args.query or "이노스케를 설득하려면?"

        print("\n" + "="*70)
        print(f"🔍 Multi-hop RAG 검색: '{query}'")
        print("="*70)

        # 실제 사용 시에는 EmbeddingClient 사용
        print("\n⚠️  Demo 모드: 실제로는 query embedding 생성 필요")

        # 임시: 첫 번째 training log의 embedding 사용
        logdb_conn = rag.get_logdb_connection()
        cursor = logdb_conn.cursor()
        cursor.execute("""
            SELECT embedding FROM training_logs
            WHERE embedding IS NOT NULL
            LIMIT 1
        """)
        row = cursor.fetchone()
        query_embedding = row[0] if row else None
        cursor.close()
        logdb_conn.close()

        if not query_embedding:
            print("❌ Embedding 데이터가 없습니다.")
            return

        # 프롬프트 강화
        enhanced = rag.generate_enhanced_prompt(
            query=query,
            agent_name=args.agent,
            query_embedding=query_embedding,
            max_hops=args.hops,
            include_examples=3
        )

        print(enhanced)

        print("\n" + "="*70)
        print("💡 이 컨텍스트를 LLM 프롬프트에 추가!")
        print("="*70)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
