"""
user_memories 임베딩 백필 스크립트

임베딩이 없는 user_memories에 대해 임베딩을 생성하고 저장합니다.
"""

import os
import sys
import time
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DatabaseManager
from src.utils.embedding_matcher import EmbeddingClient
from src.utils.entity_extractor import EntityExtractor


def prepare_memory_text(memory: Dict[str, Any]) -> str:
    """
    기억을 임베딩 생성에 적합한 텍스트로 변환

    Args:
        memory: user_memory 레코드

    Returns:
        str: 임베딩 생성용 텍스트
    """
    parts = []

    # 기억 타입
    memory_type = memory.get('memory_type', 'fact')
    parts.append(f"Type: {memory_type}")

    # 기억 키
    memory_key = memory.get('memory_key', '')
    if memory_key:
        parts.append(f"Key: {memory_key}")

    # 기억 내용 (메인)
    memory_value = memory.get('memory_value', '')
    if memory_value:
        parts.append(memory_value)

    # 컨텍스트 (있으면 추가)
    context = memory.get('context')
    if context and isinstance(context, dict):
        context_str = ', '.join([f"{k}: {v}" for k, v in context.items()])
        if context_str:
            parts.append(f"Context: {context_str}")

    # 태그 (있으면 추가)
    tags = memory.get('tags')
    if tags and isinstance(tags, list):
        tags_str = ', '.join(tags)
        if tags_str:
            parts.append(f"Tags: {tags_str}")

    return ' | '.join(parts)


def extract_entities_from_memory(
    memory: Dict[str, Any],
    extractor: EntityExtractor,
    db: DatabaseManager
) -> List[int]:
    """
    기억에서 엔티티를 추출하고 DB에 저장

    Args:
        memory: user_memory 레코드
        extractor: EntityExtractor 인스턴스
        db: DatabaseManager 인스턴스

    Returns:
        List[int]: 추출된 엔티티 ID 목록
    """
    try:
        # 기억 내용에서 엔티티 추출
        memory_value = memory.get('memory_value', '')
        if not memory_value:
            return []

        # 컨텍스트 준비
        context = {
            'memory_type': memory.get('memory_type'),
            'memory_key': memory.get('memory_key'),
        }
        if memory.get('context'):
            context.update(memory['context'])

        # 엔티티 추출
        entities = extractor.extract_entities(memory_value, context=context)

        entity_ids = []
        for entity in entities:
            # 임베딩 생성 (엔티티명과 타입)
            entity_embedding_client = EmbeddingClient()
            entity_text = f"{entity.entity_type}: {entity.entity_name}"
            if entity.description:
                entity_text += f" - {entity.description}"

            entity_embedding = entity_embedding_client.embed(entity_text)

            # DB에 저장
            entity_id = db.save_entity(
                entity_type=entity.entity_type,
                entity_name=entity.entity_name,
                canonical_name=entity.canonical_name,
                description=entity.description,
                properties=entity.properties,
                embedding=entity_embedding,
                importance_score=entity.confidence
            )

            if entity_id:
                entity_ids.append(entity_id)

                # mention 저장 (source_type='user_memory')
                db.save_entity_mention(
                    entity_id=entity_id,
                    source_type='user_memory',
                    source_id=memory['id'],
                    session_id=memory.get('source_session_id'),
                    mention_context=memory_value[:500],  # 처음 500자만
                    extraction_method=entity.extraction_method,
                    confidence=entity.confidence
                )

        return entity_ids

    except Exception as e:
        print(f"  ⚠️  Error extracting entities: {e}")
        return []


def backfill_memory_embeddings(
    batch_size: int = 30,
    enable_entity_extraction: bool = True
):
    """
    user_memories에 임베딩 백필

    Args:
        batch_size: 한 번에 처리할 기억 개수
        enable_entity_extraction: 엔티티 추출 활성화 여부
    """
    print("=" * 60)
    print("user_memories 임베딩 백필 스크립트")
    print("=" * 60)

    # Initialize components
    db = DatabaseManager(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5433")),
        dbname=os.getenv("DB_NAME", "kimedb"),
        user=os.getenv("DB_USER", "kime"),
        password=os.getenv("DB_PASSWORD", "dev123")
    )

    embedding_client = EmbeddingClient()

    extractor = None
    if enable_entity_extraction:
        try:
            extractor = EntityExtractor()
            print("✅ EntityExtractor 활성화됨")
        except Exception as e:
            print(f"⚠️  EntityExtractor 비활성화됨: {e}")
            extractor = None

    # Get total count
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM statedb.user_memories
                WHERE embedding IS NULL AND is_active = TRUE
            """)
            total_count = cur.fetchone()[0]

    print(f"\n📊 임베딩이 없는 기억: {total_count}개")

    if total_count == 0:
        print("✅ 모든 기억에 임베딩이 존재합니다!")
        return

    print(f"🚀 배치 크기: {batch_size}")
    print(f"🔍 엔티티 추출: {'활성화' if extractor else '비활성화'}")
    print("-" * 60)

    processed = 0
    success = 0
    errors = 0
    start_time = time.time()

    while processed < total_count:
        # Get batch
        memories = db.get_user_memories_without_embeddings(
            limit=batch_size,
            active_only=True
        )

        if not memories:
            break

        print(f"\n[Batch {processed + 1}-{processed + len(memories)}]")

        for memory in memories:
            memory_id = memory['id']
            memory_key = memory.get('memory_key', '???')

            try:
                # Prepare text
                text = prepare_memory_text(memory)

                if not text or text.strip() == "":
                    print(f"  ⏭️  {memory_key}: 빈 내용, 스킵")
                    processed += 1
                    continue

                # Generate embedding
                embedding = embedding_client.embed(text)

                # Extract entities (optional)
                entity_ids = []
                if extractor:
                    entity_ids = extract_entities_from_memory(memory, extractor, db)

                # Update database
                db.update_user_memory_embedding(
                    memory_id=memory_id,
                    embedding=embedding,
                    related_entity_ids=entity_ids
                )

                entity_info = f" ({len(entity_ids)} entities)" if entity_ids else ""
                print(f"  ✅ {memory_key}{entity_info}")
                success += 1

            except Exception as e:
                print(f"  ❌ {memory_key}: {e}")
                errors += 1

            processed += 1

        # Rate limiting (OpenAI: 3000 RPM)
        time.sleep(0.02 * len(memories))

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("📊 백필 완료")
    print("=" * 60)
    print(f"✅ 성공: {success}")
    print(f"❌ 실패: {errors}")
    print(f"⏱️  소요 시간: {elapsed:.1f}초")
    if success > 0:
        print(f"⚡ 처리 속도: {success / elapsed:.1f} memories/s")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="user_memories 임베딩 백필")
    parser.add_argument("--batch-size", type=int, default=30, help="배치 크기 (기본: 30)")
    parser.add_argument("--no-entities", action="store_true", help="엔티티 추출 비활성화")

    args = parser.parse_args()

    backfill_memory_embeddings(
        batch_size=args.batch_size,
        enable_entity_extraction=not args.no_entities
    )
