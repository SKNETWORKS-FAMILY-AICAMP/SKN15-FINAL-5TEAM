#!/usr/bin/env python3
"""
기존 training_logs에 임베딩 추가

처리 순서:
1. embedding IS NULL인 로그 조회 (배치 단위)
2. 각 로그에서 텍스트 추출 및 임베딩 생성
3. training_logs 업데이트
4. 진행 상황 출력
"""

import sys
import os
sys.path.insert(0, '/Users/jtm427/Desktop/workspace/backend')

from src.database.db_manager import DatabaseManager
from src.utils.embedding_matcher import EmbeddingClient
import json
import time
from typing import Dict, Any

print("=" * 80)
print("🔄 Training Logs 임베딩 백필 스크립트")
print("=" * 80)


def extract_dialogue_text(model_output: Dict[str, Any]) -> str:
    """model_output에서 대사 텍스트 추출"""
    if not model_output:
        return ""

    text_parts = []

    # dialogues 배열
    if "dialogues" in model_output and isinstance(model_output["dialogues"], list):
        for dialogue in model_output["dialogues"]:
            if isinstance(dialogue, dict) and "dialogue" in dialogue:
                text_parts.append(dialogue["dialogue"])

    # 단일 dialogue
    elif "dialogue" in model_output:
        text_parts.append(str(model_output["dialogue"]))

    # agent_inputs
    if "agent_inputs" in model_output and isinstance(model_output["agent_inputs"], dict):
        agent_inputs = model_output["agent_inputs"]
        if "user_input" in agent_inputs:
            text_parts.append(str(agent_inputs["user_input"]))

    return " ".join(text_parts)


def backfill_embeddings(batch_size: int = 50):
    """임베딩 백필 실행"""

    # 초기화
    db = DatabaseManager(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5433")),
        dbname=os.getenv("DB_NAME", "kimedb"),
        user=os.getenv("DB_USER", "kime"),
        password=os.getenv("DB_PASSWORD", "dev123")
    )

    embedding_client = EmbeddingClient()

    print(f"\n⚙️  설정:")
    print(f"  - Batch size: {batch_size}")
    print(f"  - Embedding model: {embedding_client.model}")

    # 전체 카운트
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM training_logs WHERE embedding IS NULL
            """)
            total_count = cur.fetchone()[0]

    print(f"\n📊 통계:")
    print(f"  - 임베딩 필요 로그: {total_count}개")

    if total_count == 0:
        print("\n✅ 모든 로그에 이미 임베딩이 있습니다!")
        return

    # 배치 처리
    processed = 0
    failed = 0
    start_time = time.time()

    while processed < total_count:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # 배치 조회
                cur.execute("""
                    SELECT id, user_input, model_output, context
                    FROM training_logs
                    WHERE embedding IS NULL
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
                    context = log[3] or {}

                    try:
                        # 텍스트 준비
                        text = user_input

                        # model_output에서 대사 추출
                        dialogue_text = extract_dialogue_text(model_output)
                        if dialogue_text:
                            text += f" {dialogue_text}"

                        # context에서 최근 히스토리 추가
                        if isinstance(context, dict) and "history" in context:
                            history = context["history"]
                            if isinstance(history, list) and len(history) > 0:
                                recent_history = history[-2:]  # 최근 2턴
                                history_text = " ".join([str(h) for h in recent_history if h])
                                text = f"{history_text} {text}"

                        # 임베딩 생성
                        if text.strip():
                            embedding = embedding_client.embed(text)

                            # 업데이트
                            with conn.cursor() as update_cur:
                                update_cur.execute("""
                                    UPDATE training_logs
                                    SET embedding = %s
                                    WHERE id = %s
                                """, (embedding, log_id))

                            processed += 1

                            if processed % 10 == 0:
                                elapsed = time.time() - start_time
                                rate = processed / elapsed
                                eta = (total_count - processed) / rate if rate > 0 else 0
                                print(f"  ✅ {processed}/{total_count} 완료 ({rate:.1f} logs/s, ETA: {eta:.0f}s)")

                        else:
                            print(f"  ⚠️  Log {log_id}: 빈 텍스트, 건너뜀")
                            processed += 1

                    except Exception as e:
                        print(f"  ❌ Log {log_id} 실패: {e}")
                        failed += 1
                        processed += 1

    # 최종 통계
    elapsed = time.time() - start_time
    print(f"\n" + "=" * 80)
    print(f"✅ 백필 완료!")
    print(f"=" * 80)
    print(f"  - 처리된 로그: {processed - failed}개")
    print(f"  - 실패한 로그: {failed}개")
    print(f"  - 소요 시간: {elapsed:.1f}초")
    print(f"  - 평균 속도: {(processed / elapsed):.1f} logs/s")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Training logs 임베딩 백필")
    parser.add_argument("--batch-size", type=int, default=50, help="배치 크기 (기본: 50)")
    args = parser.parse_args()

    backfill_embeddings(batch_size=args.batch_size)
