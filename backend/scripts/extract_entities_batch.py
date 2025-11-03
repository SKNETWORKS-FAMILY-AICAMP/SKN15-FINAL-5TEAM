#!/usr/bin/env python3
"""
기존 training_logs에서 엔티티 추출

처리 순서:
1. mentioned_entity_ids가 빈 배열인 로그 조회
2. 엔티티 추출 및 저장
3. entity_mentions 생성
4. training_logs 업데이트
"""

import sys
import os
sys.path.insert(0, '/Users/jtm427/Desktop/workspace/backend')

from src.database.db_manager import DatabaseManager
from src.utils.entity_extractor import EntityExtractor
from src.utils.embedding_matcher import EmbeddingClient
import time
from typing import Dict, Any

print("=" * 80)
print("🔍 Training Logs 엔티티 추출 백필 스크립트")
print("=" * 80)


def extract_dialogue_text(model_output: Dict[str, Any]) -> str:
    """model_output에서 대사 텍스트 추출"""
    if not model_output:
        return ""

    text_parts = []

    if "dialogues" in model_output and isinstance(model_output["dialogues"], list):
        for dialogue in model_output["dialogues"]:
            if isinstance(dialogue, dict) and "dialogue" in dialogue:
                text_parts.append(dialogue["dialogue"])
    elif "dialogue" in model_output:
        text_parts.append(str(model_output["dialogue"]))

    return " ".join(text_parts)


def extract_entities_batch(batch_size: int = 30):
    """엔티티 추출 백필 실행"""

    # 초기화
    db = DatabaseManager(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5433")),
        dbname=os.getenv("DB_NAME", "kimedb"),
        user=os.getenv("DB_USER", "kime"),
        password=os.getenv("DB_PASSWORD", "dev123")
    )

    extractor = EntityExtractor()
    embedding_client = EmbeddingClient()

    print(f"\n⚙️  설정:")
    print(f"  - Batch size: {batch_size}")
    print(f"  - Entity types: character, location, event, item, skill")

    # 전체 카운트
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM training_logs
        WHERE mentioned_entity_ids IS NULL
           OR mentioned_entity_ids = '{}'
    """)
    total_count = cur.fetchone()[0]

    print(f"\n📊 통계:")
    print(f"  - 엔티티 추출 필요 로그: {total_count}개")

    if total_count == 0:
        print("\n✅ 모든 로그에 이미 엔티티가 추출되었습니다!")
        return

    # 배치 처리
    processed = 0
    failed = 0
    total_entities = 0
    start_time = time.time()

    while processed < total_count:
        # 배치 조회
        cur.execute("""
            SELECT id, user_input, model_output, session_id, turn_count
            FROM training_logs
            WHERE mentioned_entity_ids IS NULL
               OR mentioned_entity_ids = '{}'
            ORDER BY id
            LIMIT %s
        """, (batch_size,))

        logs = cur.fetchall()

        if not logs:
            break

        print(f"\n🔄 배치 처리 중... ({processed + 1} ~ {processed + len(logs)}/{total_count})")

        for log in logs:
            log_id = log[0]
            user_input = log[1] or ""
            model_output = log[2] or {}
            session_id = log[3]
            turn_count = log[4] or 0

            try:
                # 텍스트 준비
                text = user_input
                dialogue_text = extract_dialogue_text(model_output)
                if dialogue_text:
                    text += f" {dialogue_text}"

                if not text.strip():
                    print(f"  ⚠️  Log {log_id}: 빈 텍스트, 건너뜀")
                    processed += 1
                    continue

                # 엔티티 추출
                entities = extractor.extract_entities(
                    text=text,
                    context={"session_id": session_id, "turn_number": turn_count}
                )

                if not entities:
                    # 엔티티가 없어도 빈 배열로 업데이트 (재처리 방지)
                    update_cur = conn.cursor()
                    update_cur.execute("""
                        UPDATE training_logs
                        SET mentioned_entity_ids = '{}'
                        WHERE id = %s
                    """, (log_id,))
                    update_cur.close()
                    conn.commit()
                    processed += 1
                    continue

                # 엔티티 저장 및 ID 수집
                entity_ids = []
                for entity in entities:
                    # 엔티티 임베딩 생성
                    entity_embedding_text = f"{entity.entity_type}: {entity.entity_name}"
                    if entity.description:
                        entity_embedding_text += f" - {entity.description}"

                    entity_embedding = embedding_client.embed(entity_embedding_text)

                    # 엔티티 저장 (upsert)
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
                        total_entities += 1

                        # entity_mentions 저장
                        db.save_entity_mention(
                            entity_id=entity_id,
                            source_type="training_log",
                            source_id=log_id,
                            session_id=session_id,
                            turn_number=turn_count,
                            mention_context=entity.context,
                            extraction_method=entity.extraction_method,
                            confidence=entity.confidence
                        )

                # training_logs 업데이트
                update_cur = conn.cursor()
                update_cur.execute("""
                    UPDATE training_logs
                    SET mentioned_entity_ids = %s
                    WHERE id = %s
                """, (entity_ids, log_id))
                update_cur.close()
                conn.commit()

                processed += 1

                if processed % 5 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed
                    eta = (total_count - processed) / rate if rate > 0 else 0
                    print(f"  ✅ {processed}/{total_count} 완료 "
                          f"({total_entities} 엔티티, {rate:.1f} logs/s, ETA: {eta:.0f}s)")

            except Exception as e:
                print(f"  ❌ Log {log_id} 실패: {e}")
                failed += 1
                processed += 1

    cur.close()

    # 최종 통계
    elapsed = time.time() - start_time
    print(f"\n" + "=" * 80)
    print(f"✅ 백필 완료!")
    print(f"=" * 80)
    print(f"  - 처리된 로그: {processed - failed}개")
    print(f"  - 추출된 엔티티: {total_entities}개")
    print(f"  - 실패한 로그: {failed}개")
    print(f"  - 소요 시간: {elapsed:.1f}초")
    print(f"  - 평균 속도: {(processed / elapsed):.1f} logs/s")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Training logs 엔티티 추출 백필")
    parser.add_argument("--batch-size", type=int, default=30, help="배치 크기 (기본: 30, LLM 사용시 작게)")
    args = parser.parse_args()

    extract_entities_batch(batch_size=args.batch_size)
