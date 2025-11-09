#!/usr/bin/env python3
"""
Entity Relationships 배치 추출 스크립트

기존 entity_mentions 데이터에서 관계를 추출하여 entity_relationships에 저장합니다.

사용법:
    # 모든 방법으로 추출
    python scripts/extract_relationships_batch.py --method all

    # Co-occurrence만 추출
    python scripts/extract_relationships_batch.py --method co-occurrence --min-count 2

    # Affinity만 추출
    python scripts/extract_relationships_batch.py --method affinity --min-affinity 50

    # Dry-run (실제 저장 안함)
    python scripts/extract_relationships_batch.py --method all --dry-run
"""

import argparse
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch


class RelationshipBatchExtractor:
    """배치 관계 추출기"""

    def __init__(self, db_url: str = None, dry_run: bool = False):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.dry_run = dry_run

    def get_connection(self):
        """DB 연결"""
        return psycopg2.connect(self.db_url)

    def extract_co_occurrence_relationships(
        self,
        min_count: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Co-occurrence 기반 관계 추출

        같은 session + turn에 함께 언급된 엔티티 쌍
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print(f"\n[Co-occurrence] 최소 {min_count}회 이상 함께 언급된 쌍 찾기...")

        cursor.execute("""
            SELECT
                e1.entity_id as source_id,
                e1.entity_name as source_name,
                e1.entity_type as source_type,
                e2.entity_id as target_id,
                e2.entity_name as target_name,
                e2.entity_type as target_type,
                COUNT(*) as co_count,
                COUNT(DISTINCT m1.session_id) as session_count,
                ARRAY_AGG(DISTINCT m1.session_id ORDER BY m1.session_id) as sessions
            FROM statedb.entity_mentions m1
            JOIN statedb.entity_mentions m2
                ON m1.session_id = m2.session_id
                AND m1.turn_number = m2.turn_number
                AND m1.entity_id < m2.entity_id
            JOIN statedb.entities e1 ON m1.entity_id = e1.entity_id
            JOIN statedb.entities e2 ON m2.entity_id = e2.entity_id
            GROUP BY e1.entity_id, e1.entity_name, e1.entity_type,
                     e2.entity_id, e2.entity_name, e2.entity_type
            HAVING COUNT(*) >= %s
            ORDER BY COUNT(*) DESC
        """, (min_count,))

        patterns = cursor.fetchall()
        cursor.close()
        conn.close()

        relationships = []
        for p in patterns:
            # Strength 계산: log(co_count) / log(max_possible)
            # 정규화: 최소 0.3, 최대 1.0
            strength = min(1.0, max(0.3, p['co_count'] / 10.0))

            # Confidence: 세션 다양성 기반
            confidence = min(1.0, max(0.5, p['session_count'] / 5.0))

            relationships.append({
                'source_entity_id': p['source_id'],
                'target_entity_id': p['target_id'],
                'relationship_type': 'CO_MENTIONED',
                'strength': strength,
                'confidence': confidence,
                'evidence_count': p['co_count'],
                'provenance': f"co_occurrence:{p['session_count']}_sessions",
                'properties': {
                    'co_occurrence_count': p['co_count'],
                    'session_count': p['session_count'],
                    'sessions': p['sessions'][:10]  # 최대 10개만
                },
                'source_name': p['source_name'],
                'target_name': p['target_name']
            })

        print(f"   찾은 패턴: {len(relationships)}개")
        return relationships

    def extract_character_skill_relationships(
        self,
        min_count: int = 2
    ) -> List[Dict[str, Any]]:
        """
        캐릭터-스킬 관계 추출

        character 타입 엔티티와 skill 타입 엔티티가 함께 언급
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print(f"\n[Character-Skill] 캐릭터와 스킬 관계 찾기...")

        cursor.execute("""
            SELECT
                e1.entity_id as char_id,
                e1.entity_name as char_name,
                e2.entity_id as skill_id,
                e2.entity_name as skill_name,
                COUNT(*) as use_count,
                COUNT(DISTINCT m1.session_id) as session_count
            FROM statedb.entity_mentions m1
            JOIN statedb.entity_mentions m2
                ON m1.session_id = m2.session_id
                AND m1.turn_number = m2.turn_number
            JOIN statedb.entities e1 ON m1.entity_id = e1.entity_id
            JOIN statedb.entities e2 ON m2.entity_id = e2.entity_id
            WHERE e1.entity_type = 'character'
              AND e2.entity_type = 'skill'
            GROUP BY e1.entity_id, e1.entity_name, e2.entity_id, e2.entity_name
            HAVING COUNT(*) >= %s
            ORDER BY COUNT(*) DESC
        """, (min_count,))

        patterns = cursor.fetchall()
        cursor.close()
        conn.close()

        relationships = []
        for p in patterns:
            strength = min(1.0, max(0.4, p['use_count'] / 8.0))
            confidence = min(1.0, max(0.6, p['session_count'] / 4.0))

            relationships.append({
                'source_entity_id': p['char_id'],
                'target_entity_id': p['skill_id'],
                'relationship_type': 'USES_SKILL',
                'strength': strength,
                'confidence': confidence,
                'evidence_count': p['use_count'],
                'provenance': f"char_skill:{p['session_count']}_sessions",
                'properties': {
                    'use_count': p['use_count'],
                    'session_count': p['session_count']
                },
                'source_name': p['char_name'],
                'target_name': p['skill_name']
            })

        print(f"   찾은 관계: {len(relationships)}개")
        return relationships

    def extract_affinity_relationships(
        self,
        min_affinity: float = 50.0
    ) -> List[Dict[str, Any]]:
        """
        Affinity 기반 관계 추출

        affinity_records에서 캐릭터 친밀도 관계
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print(f"\n[Affinity] 친밀도 >= {min_affinity} 관계 찾기...")

        # 1. 캐릭터별 affinity 정보
        cursor.execute("""
            SELECT
                a.character_name,
                MAX(a.affinity_score) as max_affinity,
                AVG(a.affinity_score) as avg_affinity,
                COUNT(*) as interaction_count,
                COUNT(DISTINCT a.session_id) as session_count
            FROM statedb.affinity_records a
            GROUP BY a.character_name
            HAVING MAX(a.affinity_score) >= %s
        """, (min_affinity,))

        affinities = cursor.fetchall()

        relationships = []
        for aff in affinities:
            # 캐릭터가 entities에 있는지 확인
            cursor.execute("""
                SELECT entity_id
                FROM statedb.entities
                WHERE entity_type = 'character'
                  AND (LOWER(entity_name) = LOWER(%s)
                       OR LOWER(canonical_name) = LOWER(%s))
                LIMIT 1
            """, (aff['character_name'], aff['character_name']))

            entity = cursor.fetchone()
            if not entity:
                continue

            # "유저"라는 가상 엔티티 생성 (또는 생략)
            # 여기서는 HAS_HIGH_AFFINITY 관계로 단방향 저장
            # (실제로는 user entity를 만들어야 하지만 간단히 처리)

            # Strength: affinity_score 기반
            strength = min(1.0, aff['max_affinity'] / 100.0)
            confidence = min(1.0, max(0.6, aff['interaction_count'] / 10.0))

            # Note: 이 관계는 character 자체에 대한 "인기도"로 해석
            # 실제 user-character 관계를 만들려면 user entity 필요
            relationships.append({
                'source_entity_id': entity['entity_id'],
                'target_entity_id': entity['entity_id'],  # Self-loop (실제로는 user)
                'relationship_type': 'HAS_HIGH_AFFINITY',
                'strength': strength,
                'confidence': confidence,
                'evidence_count': aff['interaction_count'],
                'provenance': f"affinity:{aff['session_count']}_sessions",
                'properties': {
                    'max_affinity': float(aff['max_affinity']),
                    'avg_affinity': float(aff['avg_affinity']),
                    'interaction_count': aff['interaction_count'],
                    'session_count': aff['session_count']
                },
                'source_name': aff['character_name'],
                'target_name': aff['character_name']
            })

        cursor.close()
        conn.close()

        print(f"   찾은 관계: {len(relationships)}개")
        return relationships

    def save_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        관계를 DB에 저장 (upsert)

        Returns:
            (inserted_count, updated_count)
        """
        if not relationships:
            return (0, 0)

        if self.dry_run:
            print(f"\n[DRY-RUN] {len(relationships)}개 관계를 저장하지 않음")
            return (0, 0)

        conn = self.get_connection()
        cursor = conn.cursor()

        inserted = 0
        updated = 0

        for rel in relationships:
            # Self-loop 체크 (HAS_HIGH_AFFINITY 제외)
            if (rel['source_entity_id'] == rel['target_entity_id'] and
                rel['relationship_type'] != 'HAS_HIGH_AFFINITY'):
                continue

            try:
                # Upsert: ON CONFLICT DO UPDATE
                cursor.execute("""
                    INSERT INTO statedb.entity_relationships (
                        source_entity_id,
                        target_entity_id,
                        relationship_type,
                        strength,
                        confidence,
                        properties,
                        evidence_count,
                        first_observed_at,
                        last_observed_at,
                        provenance
                    ) VALUES (
                        %(source_entity_id)s,
                        %(target_entity_id)s,
                        %(relationship_type)s,
                        %(strength)s,
                        %(confidence)s,
                        %(properties)s::jsonb,
                        %(evidence_count)s,
                        NOW(),
                        NOW(),
                        %(provenance)s
                    )
                    ON CONFLICT (source_entity_id, target_entity_id, relationship_type)
                    DO UPDATE SET
                        strength = EXCLUDED.strength,
                        confidence = EXCLUDED.confidence,
                        properties = EXCLUDED.properties,
                        evidence_count = EXCLUDED.evidence_count,
                        last_observed_at = NOW(),
                        provenance = EXCLUDED.provenance
                    RETURNING (xmax = 0) AS inserted
                """, {
                    **rel,
                    'properties': psycopg2.extras.Json(rel['properties'])
                })

                result = cursor.fetchone()
                if result and result[0]:
                    inserted += 1
                else:
                    updated += 1

            except Exception as e:
                print(f"⚠️  저장 실패: {rel['source_name']} -> {rel['target_name']}: {e}")
                continue

        conn.commit()
        cursor.close()
        conn.close()

        return (inserted, updated)

    def run(
        self,
        methods: List[str],
        min_co_count: int = 2,
        min_affinity: float = 50.0
    ) -> Dict[str, Any]:
        """
        배치 추출 실행

        Args:
            methods: ['co-occurrence', 'character-skill', 'affinity', 'all']
            min_co_count: Co-occurrence 최소 횟수
            min_affinity: Affinity 최소 점수

        Returns:
            통계 딕셔너리
        """
        print("\n" + "="*70)
        print("🚀 Entity Relationships 배치 추출 시작")
        print("="*70)
        print(f"Methods: {', '.join(methods)}")
        print(f"Dry-run: {self.dry_run}")

        all_relationships = []

        # 1. Co-occurrence
        if 'all' in methods or 'co-occurrence' in methods:
            co_rels = self.extract_co_occurrence_relationships(min_co_count)
            all_relationships.extend(co_rels)

        # 2. Character-Skill
        if 'all' in methods or 'character-skill' in methods:
            skill_rels = self.extract_character_skill_relationships(min_co_count)
            all_relationships.extend(skill_rels)

        # 3. Affinity
        if 'all' in methods or 'affinity' in methods:
            aff_rels = self.extract_affinity_relationships(min_affinity)
            all_relationships.extend(aff_rels)

        # 중복 제거 (같은 source, target, type)
        print(f"\n[중복 제거] 총 {len(all_relationships)}개 관계 발견")
        unique_rels = {}
        for rel in all_relationships:
            key = (rel['source_entity_id'], rel['target_entity_id'], rel['relationship_type'])
            if key not in unique_rels:
                unique_rels[key] = rel
            else:
                # 이미 있으면 strength가 높은 것 선택
                if rel['strength'] > unique_rels[key]['strength']:
                    unique_rels[key] = rel

        unique_relationships = list(unique_rels.values())
        print(f"   중복 제거 후: {len(unique_relationships)}개")

        # 저장
        print(f"\n[저장] {len(unique_relationships)}개 관계 저장 중...")
        inserted, updated = self.save_relationships(unique_relationships)

        # 통계
        stats = {
            'total_found': len(all_relationships),
            'unique_count': len(unique_relationships),
            'inserted': inserted,
            'updated': updated,
            'by_type': {}
        }

        for rel in unique_relationships:
            rel_type = rel['relationship_type']
            stats['by_type'][rel_type] = stats['by_type'].get(rel_type, 0) + 1

        # 결과 출력
        print("\n" + "="*70)
        print("📊 추출 결과")
        print("="*70)
        print(f"총 발견: {stats['total_found']}개")
        print(f"중복 제거 후: {stats['unique_count']}개")
        print(f"새로 생성: {stats['inserted']}개")
        print(f"업데이트: {stats['updated']}개")
        print("\n관계 타입별 분포:")
        for rel_type, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
            print(f"  - {rel_type}: {count}개")

        if not self.dry_run:
            print("\n✅ 배치 추출 완료!")
            print("💡 다음 명령어로 확인:")
            print("   python scripts/analyze_entity_relationships.py")
        else:
            print("\n✅ Dry-run 완료 (실제 저장 안됨)")

        print("="*70 + "\n")

        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Entity Relationships 배치 추출"
    )

    parser.add_argument(
        "--method",
        type=str,
        default="all",
        choices=["all", "co-occurrence", "character-skill", "affinity"],
        help="추출 방법 (기본: all)"
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="Co-occurrence 최소 횟수 (기본: 2)"
    )
    parser.add_argument(
        "--min-affinity",
        type=float,
        default=50.0,
        help="Affinity 최소 점수 (기본: 50.0)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 저장 안함 (테스트용)"
    )

    args = parser.parse_args()

    methods = [args.method] if args.method != "all" else ["all"]

    extractor = RelationshipBatchExtractor(dry_run=args.dry_run)
    extractor.run(
        methods=methods,
        min_co_count=args.min_count,
        min_affinity=args.min_affinity
    )


if __name__ == "__main__":
    main()
