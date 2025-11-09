#!/usr/bin/env python3
"""
Entity Relationships 분석 스크립트

현재 entity_relationships가 2개밖에 없는 문제를 분석하고,
어떤 관계를 추출할 수 있는지 확인합니다.

사용법:
    python scripts/analyze_entity_relationships.py
"""

import os
import sys
from typing import Dict, List, Any

import psycopg2
from psycopg2.extras import RealDictCursor


class EntityRelationshipAnalyzer:
    """Entity 관계 분석기"""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")

    def get_connection(self):
        """DB 연결"""
        return psycopg2.connect(self.db_url)

    def analyze_current_relationships(self) -> List[Dict[str, Any]]:
        """현재 존재하는 relationships 분석"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                r.relationship_id,
                e1.entity_name as source,
                e1.entity_type as source_type,
                r.relationship_type,
                e2.entity_name as target,
                e2.entity_type as target_type,
                r.strength,
                r.confidence,
                r.evidence_count,
                r.provenance,
                r.created_at
            FROM entity_relationships r
            JOIN entities e1 ON r.source_entity_id = e1.entity_id
            JOIN entities e2 ON r.target_entity_id = e2.entity_id
            ORDER BY r.created_at DESC
        """)

        relationships = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(r) for r in relationships]

    def find_co_occurrence_patterns(
        self,
        min_occurrences: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Co-occurrence 패턴 찾기

        같은 session_id + turn_number에 함께 언급된 엔티티 쌍
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                e1.entity_id as entity1_id,
                e1.entity_name as entity1,
                e1.entity_type as type1,
                e2.entity_id as entity2_id,
                e2.entity_name as entity2,
                e2.entity_type as type2,
                COUNT(*) as co_occurrence_count,
                COUNT(DISTINCT m1.session_id) as session_count,
                ARRAY_AGG(DISTINCT m1.session_id) as sessions
            FROM entity_mentions m1
            JOIN entity_mentions m2
                ON m1.session_id = m2.session_id
                AND m1.turn_number = m2.turn_number
                AND m1.entity_id < m2.entity_id  -- 중복 방지
            JOIN entities e1 ON m1.entity_id = e1.entity_id
            JOIN entities e2 ON m2.entity_id = e2.entity_id
            GROUP BY e1.entity_id, e1.entity_name, e1.entity_type,
                     e2.entity_id, e2.entity_name, e2.entity_type
            HAVING COUNT(*) >= %s
            ORDER BY co_occurrence_count DESC, session_count DESC
            LIMIT 100
        """, (min_occurrences,))

        patterns = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(p) for p in patterns]

    def find_affinity_relationships(
        self,
        min_affinity: float = 50.0
    ) -> List[Dict[str, Any]]:
        """
        Affinity 기반 관계 찾기

        affinity_records에서 캐릭터-유저 관계 추출
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 1. 캐릭터별 최대 affinity
        cursor.execute("""
            SELECT
                a.character_name,
                MAX(a.affinity_score) as max_affinity,
                AVG(a.affinity_score) as avg_affinity,
                COUNT(*) as interaction_count,
                COUNT(DISTINCT a.session_id) as session_count,
                COUNT(DISTINCT a.user_id) as user_count
            FROM affinity_records a
            GROUP BY a.character_name
            HAVING MAX(a.affinity_score) >= %s
            ORDER BY max_affinity DESC, interaction_count DESC
        """, (min_affinity,))

        affinities = cursor.fetchall()

        # 2. 캐릭터가 entities에 있는지 확인
        result = []
        for aff in affinities:
            cursor.execute("""
                SELECT entity_id, entity_name
                FROM entities
                WHERE entity_type = 'character'
                  AND (LOWER(entity_name) = LOWER(%s)
                       OR LOWER(canonical_name) = LOWER(%s))
                LIMIT 1
            """, (aff['character_name'], aff['character_name']))

            entity = cursor.fetchone()
            if entity:
                result.append({
                    **dict(aff),
                    'entity_id': entity['entity_id'],
                    'entity_name': entity['entity_name']
                })

        cursor.close()
        conn.close()

        return result

    def analyze_training_log_context(self) -> Dict[str, Any]:
        """
        Training logs의 context 필드 분석

        model_output에서 관계 추출 가능한 필드 확인
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 1. characters 필드가 있는 로그
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM public.training_logs
            WHERE model_output ? 'characters'
        """)
        chars_count = cursor.fetchone()['count']

        # 2. participants 필드가 있는 로그
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM public.training_logs
            WHERE context ? 'participants'
        """)
        participants_count = cursor.fetchone()['count']

        # 3. affinity 필드가 있는 로그
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM public.training_logs
            WHERE context ? 'affinity'
        """)
        affinity_count = cursor.fetchone()['count']

        # 4. 샘플 데이터 조회
        cursor.execute("""
            SELECT
                id,
                session_id,
                turn_count,
                context->>'participants' as participants,
                context->>'affinity' as affinity,
                model_output->>'characters' as characters
            FROM public.training_logs
            WHERE context ? 'participants'
               OR context ? 'affinity'
               OR model_output ? 'characters'
            LIMIT 5
        """)
        samples = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            'has_characters': chars_count,
            'has_participants': participants_count,
            'has_affinity': affinity_count,
            'samples': [dict(s) for s in samples]
        }

    def estimate_extractable_relationships(self) -> Dict[str, int]:
        """추출 가능한 관계 수 추정"""
        co_occurrence = len(self.find_co_occurrence_patterns(min_occurrences=2))
        affinity = len(self.find_affinity_relationships(min_affinity=50))

        # Character-Skill 관계 (캐릭터가 스킬과 함께 언급)
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(DISTINCT (e1.entity_id, e2.entity_id))
            FROM entity_mentions m1
            JOIN entity_mentions m2
                ON m1.session_id = m2.session_id
                AND m1.turn_number = m2.turn_number
            JOIN entities e1 ON m1.entity_id = e1.entity_id
            JOIN entities e2 ON m2.entity_id = e2.entity_id
            WHERE e1.entity_type = 'character'
              AND e2.entity_type = 'skill'
        """)
        char_skill = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return {
            'co_mentioned': co_occurrence,
            'has_affinity': affinity,
            'character_skill': char_skill,
            'estimated_total': co_occurrence + affinity + char_skill
        }

    def generate_report(self):
        """분석 리포트 생성"""
        print("\n" + "="*70)
        print("📊 Entity Relationships 분석 리포트")
        print("="*70)

        # 1. 현재 relationships
        print("\n### 1. 현재 Relationships")
        print("-" * 70)
        current = self.analyze_current_relationships()
        print(f"총 {len(current)}개의 relationships 존재\n")

        if current:
            for r in current:
                print(f"- {r['source']} ({r['source_type']}) "
                      f"--[{r['relationship_type']}, strength={r['strength']:.2f}]--> "
                      f"{r['target']} ({r['target_type']})")
                print(f"  Evidence: {r['evidence_count']}회, "
                      f"Confidence: {r['confidence']:.2f}, "
                      f"Source: {r['provenance']}")
                print()
        else:
            print("⚠️  현재 relationships가 하나도 없습니다!\n")

        # 2. Co-occurrence 패턴
        print("\n### 2. Co-occurrence 패턴 (상위 20개)")
        print("-" * 70)
        co_patterns = self.find_co_occurrence_patterns(min_occurrences=2)
        print(f"총 {len(co_patterns)}개 패턴 발견 (2회 이상)\n")

        for i, pattern in enumerate(co_patterns[:20], 1):
            print(f"{i:2}. {pattern['entity1']} ({pattern['type1']}) "
                  f"<--> {pattern['entity2']} ({pattern['type2']})")
            print(f"    함께 언급: {pattern['co_occurrence_count']}회, "
                  f"세션: {pattern['session_count']}개")

        # 3. Affinity 관계
        print("\n### 3. Affinity 기반 관계")
        print("-" * 70)
        affinity = self.find_affinity_relationships(min_affinity=50)
        print(f"총 {len(affinity)}개 캐릭터 (affinity >= 50)\n")

        for aff in affinity[:15]:
            print(f"- {aff['entity_name']}: "
                  f"최대 {aff['max_affinity']:.0f}, "
                  f"평균 {aff['avg_affinity']:.0f}, "
                  f"상호작용 {aff['interaction_count']}회")

        # 4. Training log context 분석
        print("\n### 4. Training Log Context 분석")
        print("-" * 70)
        context_analysis = self.analyze_training_log_context()
        print(f"characters 필드: {context_analysis['has_characters']}개 로그")
        print(f"participants 필드: {context_analysis['has_participants']}개 로그")
        print(f"affinity 필드: {context_analysis['has_affinity']}개 로그")

        # 5. 추출 가능한 관계 추정
        print("\n### 5. 추출 가능한 관계 수 추정")
        print("-" * 70)
        estimates = self.estimate_extractable_relationships()
        print(f"Co-mentioned: ~{estimates['co_mentioned']}개")
        print(f"Has Affinity: ~{estimates['has_affinity']}개")
        print(f"Character-Skill: ~{estimates['character_skill']}개")
        print(f"\n🎯 **예상 총 생성 가능 관계: ~{estimates['estimated_total']}개**")

        # 6. 권장 사항
        print("\n### 6. 권장 사항")
        print("-" * 70)
        print("✅ 1. extract_relationships_batch.py 실행 → 기존 데이터 백필")
        print(f"   예상 생성: ~{estimates['estimated_total']}개 relationships")
        print("\n✅ 2. relationship_extractor.py 구현 → 자동화")
        print("   새로운 entity_mention 저장 시 자동 관계 생성")
        print("\n✅ 3. training_logger.py 통합 → 실시간 관계 추출")
        print("   TrainingLogger가 엔티티 저장 후 자동으로 관계 생성")

        print("\n" + "="*70)
        print("💡 다음 명령어:")
        print("   python scripts/extract_relationships_batch.py --method all")
        print("="*70 + "\n")


def main():
    """메인 함수"""
    analyzer = EntityRelationshipAnalyzer()
    analyzer.generate_report()


if __name__ == "__main__":
    main()
