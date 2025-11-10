#!/usr/bin/env python3
"""
Method 1: Graph RAG Few-shot Learning

가장 빠르고 효과적인 방법 (파인튜닝 불필요)
- training_logs의 embedding으로 유사 상황 검색
- 고품질 예제(feedback_score >= 0.8)를 프롬프트에 동적 추가
- Entity 기반 컨텍스트 매칭으로 정확도 향상

장점:
  ✅ 파인튜닝 없이 즉시 사용 가능
  ✅ 실시간 업데이트 (새 고품질 로그가 추가되면 자동 반영)
  ✅ 비용 효율적 (추론 시 토큰만 증가, 학습 비용 없음)
  ✅ Entity-aware 검색으로 맥락 일치도 높음

사용법:
  python scripts/method1_graph_rag_fewshot.py --build-index
  python scripts/method1_graph_rag_fewshot.py --test "이노스케 찾아줘"
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor


class GraphRAGFewShotRetriever:
    """Graph RAG 기반 Few-shot 예제 검색기"""

    def __init__(
        self,
        db_url: Optional[str] = None,
        min_score: float = 0.8,
        top_k: int = 3
    ):
        """
        Args:
            db_url: LogDB connection URL
            min_score: 최소 feedback_score (기본 0.8)
            top_k: 검색할 예제 수 (기본 3)
        """
        self.db_url = db_url or os.getenv("LOGDB_URL", os.getenv("DATABASE_URL"))
        self.min_score = min_score
        self.top_k = top_k

    def get_connection(self):
        """DB 연결"""
        return psycopg2.connect(self.db_url)

    def retrieve_similar_examples(
        self,
        query_embedding: List[float],
        agent_name: str,
        entity_ids: Optional[List[int]] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        유사 예제 검색 (Vector + Entity 기반)

        Args:
            query_embedding: 현재 입력의 embedding
            agent_name: 에이전트 이름
            entity_ids: 현재 언급된 entity ID 리스트
            limit: 검색할 예제 수

        Returns:
            고품질 예제 리스트
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Vector 유사도 기반 검색
        if entity_ids:
            # Entity overlap 고려 (Jaccard similarity)
            cursor.execute("""
                SELECT
                    id,
                    agent_name,
                    user_input,
                    context,
                    model_output,
                    feedback_score,
                    outcome_reason,
                    mentioned_entity_ids,
                    -- Vector similarity
                    1 - (embedding <=> %s::vector) as similarity,
                    -- Entity overlap (Jaccard)
                    CASE
                        WHEN mentioned_entity_ids IS NULL OR cardinality(mentioned_entity_ids) = 0
                        THEN 0
                        ELSE
                            cardinality(mentioned_entity_ids & %s::int[])::float /
                            cardinality(mentioned_entity_ids | %s::int[])::float
                    END as entity_overlap
                FROM training_logs
                WHERE agent_name = %s
                  AND feedback_score >= %s
                  AND embedding IS NOT NULL
                  AND outcome = 'success'
                ORDER BY
                    (0.7 * (1 - (embedding <=> %s::vector)) +
                     0.3 * CASE
                        WHEN mentioned_entity_ids IS NULL OR cardinality(mentioned_entity_ids) = 0
                        THEN 0
                        ELSE
                            cardinality(mentioned_entity_ids & %s::int[])::float /
                            cardinality(mentioned_entity_ids | %s::int[])::float
                    END) DESC
                LIMIT %s
            """, (
                query_embedding,
                entity_ids, entity_ids,
                agent_name, self.min_score,
                query_embedding,
                entity_ids, entity_ids,
                limit
            ))
        else:
            # Vector 유사도만 사용
            cursor.execute("""
                SELECT
                    id,
                    agent_name,
                    user_input,
                    context,
                    model_output,
                    feedback_score,
                    outcome_reason,
                    mentioned_entity_ids,
                    1 - (embedding <=> %s::vector) as similarity
                FROM training_logs
                WHERE agent_name = %s
                  AND feedback_score >= %s
                  AND embedding IS NOT NULL
                  AND outcome = 'success'
                ORDER BY similarity DESC
                LIMIT %s
            """, (query_embedding, agent_name, self.min_score, limit))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        examples = []
        for row in rows:
            examples.append({
                "id": row["id"],
                "user_input": row["user_input"],
                "context": row["context"],
                "model_output": row["model_output"],
                "feedback_score": row["feedback_score"],
                "similarity": row["similarity"],
                "entity_overlap": row.get("entity_overlap", 0.0),
                "mentioned_entities": row.get("mentioned_entity_ids", [])
            })

        return examples

    def format_examples_for_prompt(
        self,
        examples: List[Dict[str, Any]],
        agent_name: str
    ) -> str:
        """
        Few-shot 예제를 프롬프트 형식으로 변환

        Args:
            examples: 검색된 예제 리스트
            agent_name: 에이전트 이름

        Returns:
            프롬프트에 추가할 텍스트
        """
        if not examples:
            return ""

        prompt_parts = ["\n## 🌟 고품질 예제 (참고용)\n"]
        prompt_parts.append("다음은 유사한 상황에서 잘 작동한 예제입니다:\n")

        for i, ex in enumerate(examples, 1):
            score = ex["feedback_score"]
            similarity = ex.get("similarity", 0)

            prompt_parts.append(f"\n### 예제 {i} (품질: {score:.2f}, 유사도: {similarity:.2f})")

            # Agent별 포맷
            if agent_name == "router":
                user_input = ex["user_input"]
                classification = ex["model_output"].get("classification", "")
                next_node = ex["model_output"].get("next_node", "")
                confidence = ex["model_output"].get("confidence", 0)

                prompt_parts.append(f"**입력**: \"{user_input}\"")
                prompt_parts.append(f"**분류**: {classification} (confidence: {confidence})")
                prompt_parts.append(f"**라우팅**: {next_node}")

            elif agent_name == "children":
                user_input = ex["user_input"]
                agent_responses = ex["model_output"].get("agent_responses", [])

                prompt_parts.append(f"**입력**: \"{user_input}\"")
                prompt_parts.append(f"**생성 대사** ({len(agent_responses)}개):")
                for j, resp in enumerate(agent_responses[:2], 1):  # 최대 2개만
                    char = resp.get("character", "")
                    text = resp.get("text", "")
                    prompt_parts.append(f"  {j}. {char}: \"{text[:50]}...\"")

            elif agent_name == "parent":
                beats = ex.get("context", {}).get("children_ctx", {}).get("beats", [])
                prompt_parts.append(f"**Beats 수**: {len(beats)}")

        return "\n".join(prompt_parts)

    def build_fewshot_index_stats(self) -> Dict[str, Any]:
        """Few-shot 예제 인덱스 통계"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Agent별 고품질 예제 수
        cursor.execute("""
            SELECT
                agent_name,
                COUNT(*) as total_examples,
                AVG(feedback_score) as avg_score,
                MIN(feedback_score) as min_score,
                MAX(feedback_score) as max_score,
                COUNT(DISTINCT mentioned_entity_ids) as unique_entity_sets
            FROM training_logs
            WHERE feedback_score >= %s
              AND embedding IS NOT NULL
              AND outcome = 'success'
            GROUP BY agent_name
            ORDER BY total_examples DESC
        """, (self.min_score,))

        agent_stats = cursor.fetchall()

        # 전체 통계
        cursor.execute("""
            SELECT
                COUNT(*) as total_high_quality,
                AVG(feedback_score) as avg_score,
                COUNT(CASE WHEN mentioned_entity_ids IS NOT NULL AND cardinality(mentioned_entity_ids) > 0 THEN 1 END) as with_entities
            FROM training_logs
            WHERE feedback_score >= %s
              AND embedding IS NOT NULL
              AND outcome = 'success'
        """, (self.min_score,))

        total_stats = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "total_high_quality_examples": total_stats["total_high_quality"],
            "avg_score": round(total_stats["avg_score"], 3),
            "with_entities": total_stats["with_entities"],
            "agent_breakdown": [dict(row) for row in agent_stats]
        }


def main():
    parser = argparse.ArgumentParser(
        description="Graph RAG Few-shot Learning (Method 1)"
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="인덱스 통계 확인"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="테스트 쿼리 (예: '이노스케 찾아줘')"
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="router",
        choices=["router", "parent", "children"],
        help="에이전트 이름"
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.8,
        help="최소 feedback_score (기본 0.8)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="검색할 예제 수 (기본 3)"
    )

    args = parser.parse_args()

    retriever = GraphRAGFewShotRetriever(
        min_score=args.min_score,
        top_k=args.top_k
    )

    if args.build_index:
        print("\n" + "="*70)
        print("📊 Graph RAG Few-shot 인덱스 통계")
        print("="*70)

        stats = retriever.build_fewshot_index_stats()

        print(f"\n총 고품질 예제 수: {stats['total_high_quality_examples']}개")
        print(f"평균 점수: {stats['avg_score']}")
        print(f"Entity 포함: {stats['with_entities']}개")

        print("\n에이전트별 통계:")
        print("-" * 70)
        print(f"{'Agent':<15} {'Examples':<12} {'Avg Score':<12} {'Entity Sets':<15}")
        print("-" * 70)

        for agent in stats["agent_breakdown"]:
            print(f"{agent['agent_name']:<15} "
                  f"{agent['total_examples']:<12} "
                  f"{agent['avg_score']:<12.3f} "
                  f"{agent.get('unique_entity_sets', 0):<15}")

        print("\n✅ 인덱스가 준비되었습니다!")
        print("💡 사용법: python scripts/method1_graph_rag_fewshot.py --test '테스트 쿼리'")

    elif args.test:
        print("\n" + "="*70)
        print(f"🔍 Few-shot 예제 검색: '{args.test}'")
        print("="*70)

        # 임시: embedding 생성 (실제로는 EmbeddingClient 사용)
        # 여기서는 간단히 임의의 embedding을 사용
        print("\n⚠️  실제 사용 시 EmbeddingClient를 사용해서 query embedding 생성 필요")
        print("현재는 데모 모드로 임의 검색 실행\n")

        # 임시로 첫 번째 고품질 예제의 embedding을 사용
        conn = retriever.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT embedding FROM training_logs
            WHERE agent_name = %s
              AND feedback_score >= %s
              AND embedding IS NOT NULL
            LIMIT 1
        """, (args.agent, args.min_score))

        row = cursor.fetchone()
        if not row:
            print("❌ 고품질 예제가 없습니다. 먼저 데이터를 수집하세요.")
            cursor.close()
            conn.close()
            return

        query_embedding = row[0]
        cursor.close()
        conn.close()

        # 유사 예제 검색
        examples = retriever.retrieve_similar_examples(
            query_embedding=query_embedding,
            agent_name=args.agent,
            entity_ids=None,  # 실제로는 extract_entities로 추출
            limit=args.top_k
        )

        if not examples:
            print("❌ 유사 예제를 찾을 수 없습니다.")
            return

        print(f"\n✅ {len(examples)}개 예제 검색 완료\n")

        # 프롬프트 형식으로 변환
        prompt_text = retriever.format_examples_for_prompt(examples, args.agent)
        print(prompt_text)

        print("\n" + "="*70)
        print("💡 이 텍스트를 LLM 프롬프트에 추가하면 정확도 향상!")
        print("="*70)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
