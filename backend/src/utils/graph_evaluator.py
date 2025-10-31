#!/usr/bin/env python3
"""
Graph Context Evaluator for Auto-labeling

그래프 컨텍스트를 활용한 자동 라벨링 품질 평가

평가 기준:
1. 엔티티 일관성 (40%): 언급된 엔티티가 맥락에 적합한가?
2. 관계 일관성 (30%): 엔티티 간 관계가 올바른가?
3. 시간적 일관성 (20%): 이전 대화와 시간적으로 일치하는가?
4. 커뮤니티 응집성 (10%): 같은 커뮤니티의 엔티티들인가?
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class GraphEvaluator:
    """
    그래프 컨텍스트 기반 로그 품질 평가기

    자동 라벨링 시스템에서 사용:
    - Rule-based: 30%
    - LLM-based: 30%
    - Graph-based: 40% (이 클래스)
    """

    def __init__(self, db_manager):
        """
        Args:
            db_manager: DatabaseManager 인스턴스
        """
        self.db = db_manager

    def evaluate_log_quality(
        self,
        log_id: int,
        entity_ids: List[int],
        session_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float, str]:
        """
        그래프 컨텍스트 기반 로그 품질 평가

        Args:
            log_id: training_logs ID
            entity_ids: 로그에서 추출된 엔티티 ID 리스트
            session_id: 세션 ID
            turn_number: 턴 번호
            context: 추가 컨텍스트 정보

        Returns:
            (outcome, score, reason)
            - outcome: 'success', 'partial', 'failure'
            - score: 0.0-1.0
            - reason: 평가 이유
        """
        if not entity_ids:
            return ("partial", 0.5, "No entities extracted")

        reasons = []

        # 1. 엔티티 일관성 평가 (40%)
        entity_score, entity_reason = self._evaluate_entity_consistency(
            entity_ids, context
        )
        reasons.append(f"Entity: {entity_reason}")

        # 2. 관계 일관성 평가 (30%)
        relationship_score, rel_reason = self._evaluate_relationship_consistency(
            entity_ids
        )
        reasons.append(f"Relation: {rel_reason}")

        # 3. 시간적 일관성 평가 (20%)
        temporal_score, temp_reason = self._evaluate_temporal_consistency(
            entity_ids, session_id, turn_number
        )
        reasons.append(f"Temporal: {temp_reason}")

        # 4. 커뮤니티 응집성 평가 (10%)
        community_score, comm_reason = self._evaluate_community_coherence(
            entity_ids
        )
        reasons.append(f"Community: {comm_reason}")

        # 가중치 합산
        total_score = (
            entity_score * 0.4 +
            relationship_score * 0.3 +
            temporal_score * 0.2 +
            community_score * 0.1
        )

        # 결과 결정
        if total_score >= 0.75:
            outcome = "success"
        elif total_score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        reason = "; ".join(reasons)

        return (outcome, total_score, reason)

    def _evaluate_entity_consistency(
        self,
        entity_ids: List[int],
        context: Optional[Dict[str, Any]]
    ) -> Tuple[float, str]:
        """
        엔티티 일관성 평가

        평가 항목:
        - 엔티티 타입 다양성 (character, location, skill 등)
        - 중요도 점수 (importance_score)
        - 출현 빈도 (mention_count)
        """
        if not entity_ids:
            return (0.5, "no entities")

        try:
            # 엔티티 정보 조회
            entities = []
            for entity_id in entity_ids:
                entity = self.db.get_connection().cursor()
                entity.execute("""
                    SELECT entity_type, importance_score, mention_count
                    FROM statedb.entities
                    WHERE entity_id = %s
                """, (entity_id,))
                row = entity.fetchone()
                if row:
                    entities.append({
                        "type": row[0],
                        "importance": row[1],
                        "mentions": row[2]
                    })
                entity.close()

            if not entities:
                return (0.5, "entities not found")

            # 1. 타입 다양성 평가 (0.3)
            type_counts = Counter([e["type"] for e in entities])
            type_diversity = min(1.0, len(type_counts) / 3.0)  # 3개 이상이면 만점

            # 2. 중요도 평가 (0.4)
            avg_importance = sum(e["importance"] for e in entities) / len(entities)

            # 3. 출현 빈도 평가 (0.3)
            # 높은 mention_count = 자주 등장하는 중요 엔티티
            avg_mentions = sum(e["mentions"] for e in entities) / len(entities)
            mention_score = min(1.0, avg_mentions / 10.0)  # 10회 이상이면 만점

            # 종합 점수
            score = (
                type_diversity * 0.3 +
                avg_importance * 0.4 +
                mention_score * 0.3
            )

            reason = f"types={len(type_counts)}, importance={avg_importance:.2f}, mentions={avg_mentions:.1f}"

            return (score, reason)

        except Exception as e:
            logger.error(f"Entity consistency evaluation failed: {e}")
            return (0.5, "evaluation error")

    def _evaluate_relationship_consistency(
        self,
        entity_ids: List[int]
    ) -> Tuple[float, str]:
        """
        관계 일관성 평가

        평가 항목:
        - 엔티티 간 관계 존재 여부
        - 관계 강도 (strength)
        - 관계 확신도 (confidence)
        """
        if len(entity_ids) < 2:
            return (0.7, "single entity")

        try:
            # 엔티티 쌍 간 관계 조회
            relationships = []
            conn = self.db.get_connection()
            cur = conn.cursor()

            for i, entity1_id in enumerate(entity_ids):
                for entity2_id in entity_ids[i + 1:]:
                    cur.execute("""
                        SELECT relationship_type, strength, confidence
                        FROM statedb.entity_relationships
                        WHERE (source_entity_id = %s AND target_entity_id = %s)
                           OR (source_entity_id = %s AND target_entity_id = %s)
                    """, (entity1_id, entity2_id, entity2_id, entity1_id))

                    rows = cur.fetchall()
                    for row in rows:
                        relationships.append({
                            "type": row[0],
                            "strength": row[1],
                            "confidence": row[2]
                        })

            cur.close()

            # 엔티티 쌍 수
            total_pairs = len(entity_ids) * (len(entity_ids) - 1) // 2

            if total_pairs == 0:
                return (0.7, "no pairs")

            # 1. 관계 존재 비율 (0.5)
            relationship_ratio = min(1.0, len(relationships) / total_pairs)

            # 2. 평균 강도 (0.3)
            avg_strength = (
                sum(r["strength"] for r in relationships) / len(relationships)
                if relationships else 0.5
            )

            # 3. 평균 확신도 (0.2)
            avg_confidence = (
                sum(r["confidence"] for r in relationships) / len(relationships)
                if relationships else 0.5
            )

            # 종합 점수
            score = (
                relationship_ratio * 0.5 +
                avg_strength * 0.3 +
                avg_confidence * 0.2
            )

            reason = f"rels={len(relationships)}/{total_pairs}, strength={avg_strength:.2f}"

            return (score, reason)

        except Exception as e:
            logger.error(f"Relationship consistency evaluation failed: {e}")
            return (0.5, "evaluation error")

    def _evaluate_temporal_consistency(
        self,
        entity_ids: List[int],
        session_id: Optional[str],
        turn_number: Optional[int]
    ) -> Tuple[float, str]:
        """
        시간적 일관성 평가

        평가 항목:
        - 최근 N턴 내 엔티티 재등장 여부
        - 엔티티 연속성 (같은 세션에서 계속 등장하는가)
        """
        if not session_id or turn_number is None:
            return (0.7, "no session context")

        try:
            # 최근 5턴 내 엔티티 조회
            conn = self.db.get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT DISTINCT entity_id
                FROM statedb.entity_mentions
                WHERE session_id = %s
                  AND turn_number >= %s
                  AND turn_number < %s
                  AND source_type = 'training_log'
            """, (session_id, max(0, turn_number - 5), turn_number))

            recent_entity_ids = {row[0] for row in cur.fetchall()}
            cur.close()

            if not recent_entity_ids:
                return (0.7, "no recent history")

            # 현재 엔티티와 최근 엔티티의 교집합
            overlap = set(entity_ids) & recent_entity_ids
            overlap_ratio = len(overlap) / len(entity_ids) if entity_ids else 0

            # 점수: 50% 이상 겹치면 높은 점수
            score = min(1.0, overlap_ratio * 2.0)

            reason = f"overlap={len(overlap)}/{len(entity_ids)}"

            return (score, reason)

        except Exception as e:
            logger.error(f"Temporal consistency evaluation failed: {e}")
            return (0.7, "evaluation error")

    def _evaluate_community_coherence(
        self,
        entity_ids: List[int]
    ) -> Tuple[float, str]:
        """
        커뮤니티 응집성 평가

        평가 항목:
        - 같은 community_id를 가진 엔티티 비율
        - (커뮤니티 감지는 향후 구현)
        """
        if len(entity_ids) < 2:
            return (0.8, "single entity")

        try:
            # 엔티티 커뮤니티 ID 조회
            conn = self.db.get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT entity_id, community_id
                FROM statedb.entities
                WHERE entity_id = ANY(%s)
            """, (entity_ids,))

            communities = {}
            for row in cur.fetchall():
                entity_id, community_id = row[0], row[1]
                if community_id is not None:
                    communities[entity_id] = community_id

            cur.close()

            if not communities:
                # 커뮤니티 미할당 시 중립 점수
                return (0.8, "no communities")

            # 가장 많은 커뮤니티
            community_counts = Counter(communities.values())
            most_common_count = community_counts.most_common(1)[0][1]

            # 동일 커뮤니티 비율
            coherence_ratio = most_common_count / len(entity_ids)

            # 점수: 80% 이상 같은 커뮤니티면 만점
            score = min(1.0, coherence_ratio / 0.8)

            reason = f"coherence={most_common_count}/{len(entity_ids)}"

            return (score, reason)

        except Exception as e:
            logger.error(f"Community coherence evaluation failed: {e}")
            return (0.8, "evaluation error")


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)

    from src.database.db_manager import DatabaseManager

    db = DatabaseManager(
        host="localhost",
        port=5433,
        dbname="kimedb",
        user="kime",
        password="dev123"
    )

    evaluator = GraphEvaluator(db)

    # 테스트용 엔티티 ID (실제 DB에 있는 ID 사용)
    test_entity_ids = [1, 2, 3, 4]  # 염의 호흡, 렌고쿠, 탄지로, 무한열차

    outcome, score, reason = evaluator.evaluate_log_quality(
        log_id=1,
        entity_ids=test_entity_ids,
        session_id="test_session",
        turn_number=5
    )

    print(f"\n평가 결과:")
    print(f"  Outcome: {outcome}")
    print(f"  Score: {score:.3f}")
    print(f"  Reason: {reason}")
