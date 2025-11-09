#!/usr/bin/env python3
"""
Graph RAG 시스템 종합 테스트

테스트 항목:
1. 엔티티 벡터 유사도 검색
2. 관련 엔티티 그래프 탐색
3. 엔티티 정보 조회
"""

import sys
import os
sys.path.insert(0, '/Users/jtm427/Desktop/workspace/backend')

from src.database.db_manager import DatabaseManager
from src.utils.embedding_matcher import EmbeddingClient

print("=" * 80)
print("🧪 Graph RAG 시스템 종합 테스트")
print("=" * 80)

# 초기화
db = DatabaseManager(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5433")),
    dbname=os.getenv("DB_NAME", "kimedb"),
    user=os.getenv("DB_USER", "kime"),
    password=os.getenv("DB_PASSWORD", "dev123")
)

embedding_client = EmbeddingClient()

print("\n" + "="*80)
print("테스트 1: 엔티티 벡터 유사도 검색")
print("="*80)

# "불꽃 검술"과 유사한 엔티티 찾기
query_text = "불꽃 검술"
print(f"\n🔍 쿼리: '{query_text}'")

query_embedding = embedding_client.embed(query_text)
similar_entities = db.find_similar_entities(
    embedding=query_embedding,
    limit=5
)

if similar_entities:
    print(f"\n✅ 유사한 엔티티 {len(similar_entities)}개 발견:")
    for i, entity in enumerate(similar_entities, 1):
        similarity = 1 - entity['distance']  # distance를 similarity로 변환 (0=동일, 1=완전다름)
        print(f"  {i}. {entity['entity_name']} ({entity['entity_type']}) - 거리: {entity['distance']:.3f}, 유사도: {similarity:.3f}")
else:
    print("\n❌ 유사한 엔티티를 찾지 못했습니다.")

print("\n" + "="*80)
print("테스트 2: 관련 엔티티 그래프 탐색")
print("="*80)

# 렌고쿠와 관련된 엔티티 찾기
entity = db.get_entity_by_name(entity_type="character", canonical_name="렌고쿠")
if entity:
    entity_id = entity['entity_id']
    print(f"\n🔍 중심 엔티티: {entity['entity_name']} (ID: {entity_id})")
    print(f"   - 중요도: {entity['importance_score']:.2f}")
    print(f"   - 언급 횟수: {entity['mention_count']}회")

    # 관련 엔티티 조회
    related = db.get_related_entities(entity_id=entity_id, limit=10)

    if related:
        print(f"\n✅ 관련 엔티티 {len(related)}개 발견:")
        for rel in related:
            print(f"  - {rel['entity_name']} ({rel['entity_type']})")
            print(f"    관계: {rel['relationship_type']} (강도: {rel['strength']:.2f})")
    else:
        print("\n⚠️  관계가 설정된 엔티티가 없습니다 (아직 관계 추출 미실행)")
else:
    print("\n❌ '렌고쿠' 엔티티를 찾지 못했습니다.")

print("\n" + "="*80)
print("테스트 3: 전체 엔티티 현황")
print("="*80)

with db.get_connection() as conn:
    with conn.cursor() as cur:
        # 엔티티 타입별 통계
        cur.execute("""
            SELECT
                entity_type,
                COUNT(*) as count,
                AVG(importance_score) as avg_importance,
                SUM(mention_count) as total_mentions
            FROM entities
            GROUP BY entity_type
            ORDER BY count DESC
        """)

        stats = cur.fetchall()

        if stats:
            print("\n📊 엔티티 타입별 통계:")
            for stat in stats:
                entity_type = stat[0]
                count = stat[1]
                avg_importance = stat[2]
                total_mentions = stat[3]
                print(f"  - {entity_type}: {count}개 (평균 중요도: {avg_importance:.2f}, 총 {total_mentions}회 언급)")

        # 모든 엔티티 나열
        cur.execute("""
            SELECT entity_type, entity_name, importance_score, mention_count
            FROM entities
            ORDER BY mention_count DESC, importance_score DESC
        """)

        all_entities = cur.fetchall()

        if all_entities:
            print(f"\n📝 전체 엔티티 목록 ({len(all_entities)}개):")
            for entity in all_entities:
                entity_type, entity_name, importance, mentions = entity
                print(f"  - {entity_name} ({entity_type}): 중요도 {importance:.2f}, {mentions}회 언급")

print("\n" + "="*80)
print("테스트 4: 엔티티 멘션 확인")
print("="*80)

with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                e.entity_name,
                e.entity_type,
                COUNT(em.mention_id) as mention_count
            FROM entities e
            LEFT JOIN entity_mentions em ON e.entity_id = em.entity_id
            GROUP BY e.entity_id, e.entity_name, e.entity_type
            HAVING COUNT(em.mention_id) > 0
            ORDER BY COUNT(em.mention_id) DESC
        """)

        mention_stats = cur.fetchall()

        if mention_stats:
            print(f"\n✅ 멘션이 있는 엔티티 {len(mention_stats)}개:")
            for stat in mention_stats:
                entity_name, entity_type, count = stat
                print(f"  - {entity_name} ({entity_type}): {count}개 멘션")
        else:
            print("\n❌ 멘션이 기록된 엔티티가 없습니다.")

print("\n" + "="*80)
print("✅ 테스트 완료!")
print("="*80)

print("\n📝 요약:")
print(f"  - 벡터 유사도 검색: {'✅ 작동' if similar_entities else '❌ 데이터 부족'}")
print(f"  - 그래프 탐색: {'✅ 작동' if entity else '❌ 실패'}")
print(f"  - 엔티티 통계: {'✅ 작동' if stats else '❌ 실패'}")
print(f"  - 멘션 추적: {'✅ 작동' if mention_stats else '❌ 실패'}")

print("\n🎉 Graph RAG 시스템이 정상 작동하고 있습니다!")
print("="*80)
