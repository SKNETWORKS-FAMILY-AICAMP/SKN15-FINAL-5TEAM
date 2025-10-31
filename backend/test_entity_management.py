#!/usr/bin/env python3
"""
Test Entity Management Methods

Verifies:
1. Entity saving and retrieval
2. Entity mentions (linking to training logs)
3. Entity relationships
4. Vector similarity search
"""

import sys
sys.path.insert(0, '/Users/jtm427/Desktop/workspace/backend')

from src.database.db_manager import DatabaseManager
from src.utils.entity_extractor import EntityExtractor
from src.utils.embedding_matcher import EmbeddingClient
import json

print("=" * 80)
print("🧪 Entity Management Test")
print("=" * 80)

# Initialize
db = DatabaseManager(
    host="localhost",
    port=5433,
    dbname="kimedb",
    user="kime",
    password="dev123"
)

extractor = EntityExtractor()
embedding_client = EmbeddingClient()

# ============================================================================
# Test 1: Extract and Save Entities
# ============================================================================
print("\n📋 Test 1: Extract and Save Entities")
print("-" * 80)

test_text = """
렌고쿠가 무한열차에서 탄지로와 만났다.
그는 염의 호흡을 사용하여 귀신과 싸웠다.
"""

# Extract entities
entities = extractor.extract_entities(test_text)
print(f"추출된 엔티티: {len(entities)}개")

# Generate embeddings and save entities
entity_ids = {}
for entity in entities:
    # Generate embedding
    embedding_text = f"{entity.entity_type}: {entity.entity_name}"
    if entity.description:
        embedding_text += f" - {entity.description}"

    embedding = embedding_client.embed(embedding_text)

    # Save entity
    entity_id = db.save_entity(
        entity_type=entity.entity_type,
        entity_name=entity.entity_name,
        canonical_name=entity.canonical_name,
        description=entity.description,
        properties=entity.properties,
        embedding=embedding,
        importance_score=0.8
    )

    if entity_id:
        entity_ids[entity.canonical_name] = entity_id
        print(f"✅ 저장됨: [{entity.entity_type}] {entity.entity_name} (ID: {entity_id})")
    else:
        print(f"❌ 저장 실패: {entity.entity_name}")

# ============================================================================
# Test 2: Retrieve Entities
# ============================================================================
print("\n📋 Test 2: Retrieve Entities")
print("-" * 80)

for canonical_name, expected_id in entity_ids.items():
    # Get entity type from entities list
    entity_type = next((e.entity_type for e in entities if e.canonical_name == canonical_name), None)

    if entity_type:
        retrieved = db.get_entity_by_name(entity_type, canonical_name)

        if retrieved and retrieved['entity_id'] == expected_id:
            print(f"✅ {canonical_name}: ID={retrieved['entity_id']}, "
                  f"mention_count={retrieved['mention_count']}")
        else:
            print(f"❌ {canonical_name}: 조회 실패")

# ============================================================================
# Test 3: Save Entity Relationships
# ============================================================================
print("\n📋 Test 3: Save Entity Relationships")
print("-" * 80)

# Create relationships if we have enough entities
if '렌고쿠' in entity_ids and '무한열차' in entity_ids:
    rel_id = db.save_entity_relationship(
        source_entity_id=entity_ids['렌고쿠'],
        target_entity_id=entity_ids['무한열차'],
        relationship_type='LOCATED_IN',
        strength=0.9,
        confidence=0.95,
        provenance="test_script"
    )

    if rel_id:
        print(f"✅ 관계 생성: 렌고쿠 -> 무한열차 (LOCATED_IN)")
    else:
        print(f"❌ 관계 생성 실패")

if '렌고쿠' in entity_ids and '탄지로' in entity_ids:
    rel_id = db.save_entity_relationship(
        source_entity_id=entity_ids['렌고쿠'],
        target_entity_id=entity_ids['탄지로'],
        relationship_type='TRAINS_WITH',
        strength=0.8,
        confidence=0.9,
        provenance="test_script"
    )

    if rel_id:
        print(f"✅ 관계 생성: 렌고쿠 -> 탄지로 (TRAINS_WITH)")
    else:
        print(f"❌ 관계 생성 실패")

# ============================================================================
# Test 4: Get Related Entities
# ============================================================================
print("\n📋 Test 4: Get Related Entities")
print("-" * 80)

if '렌고쿠' in entity_ids:
    related = db.get_related_entities(entity_ids['렌고쿠'])

    if related:
        print(f"✅ 렌고쿠와 관련된 엔티티: {len(related)}개")
        for r in related:
            print(f"   - {r['entity_name']} ({r['relationship_type']}, "
                  f"strength={r['strength']:.2f})")
    else:
        print("❌ 관련 엔티티 없음")

# ============================================================================
# Test 5: Vector Similarity Search
# ============================================================================
print("\n📋 Test 5: Vector Similarity Search")
print("-" * 80)

# Search for entities similar to "불의 호흡을 사용하는 강한 검사"
query_text = "불의 호흡을 사용하는 강한 검사"
query_embedding = embedding_client.embed(query_text)

similar = db.find_similar_entities(query_embedding, limit=3)

if similar:
    print(f"✅ '{query_text}'와 유사한 엔티티:")
    for s in similar:
        print(f"   - {s['entity_name']} ({s['entity_type']}, "
              f"distance={s['distance']:.4f})")
else:
    print("❌ 유사 엔티티 없음")

print("\n" + "=" * 80)
print("🎉 Entity Management Test 완료!")
print("=" * 80)
