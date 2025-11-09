"""
대화 요약 백필 스크립트

conversation_summary가 없는 세션들에 대해 대화 요약을 생성합니다.
"""

import os
import sys
import time
import asyncio
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DatabaseManager
from src.utils.conversation_summarizer import generate_conversation_summary


def format_dialogues_to_conversations(dialogues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    dialogues를 conversation format으로 변환

    Args:
        dialogues: DB에서 가져온 dialogues 목록

    Returns:
        List[Dict]: conversation format
    """
    # 턴별로 그룹화
    conversations = {}

    for dialogue in dialogues:
        turn = dialogue['turn_number']

        if turn not in conversations:
            conversations[turn] = {
                'turn': turn,
                'user_input': '',
                'agent_responses': []
            }

        # speaker가 'user' 또는 '사용자'인 경우 user_input으로 처리
        speaker = dialogue.get('speaker', '')
        content = dialogue.get('content', '')

        if speaker.lower() in ['user', '사용자']:
            conversations[turn]['user_input'] = content
        else:
            conversations[turn]['agent_responses'].append({
                'speaker': speaker,
                'text': content,
                'emotion': dialogue.get('emotion'),
                'emotion_intensity': dialogue.get('emotion_intensity')
            })

    # 턴 순서대로 정렬
    sorted_conversations = sorted(conversations.values(), key=lambda x: x['turn'])

    return sorted_conversations


def get_scenario_context_from_session(session: Dict[str, Any]) -> str:
    """
    세션에서 시나리오 컨텍스트 추출

    Args:
        session: 세션 정보

    Returns:
        str: 시나리오 컨텍스트
    """
    context_parts = []

    scenario_id = session.get('scenario_id', 'unknown')
    context_parts.append(f"시나리오: {scenario_id}")

    current_stage = session.get('current_stage', 'unknown')
    if current_stage:
        context_parts.append(f"현재 스테이지: {current_stage}")

    user_name = session.get('user_name', '사용자')
    if user_name:
        context_parts.append(f"사용자: {user_name}")

    return "\n".join(context_parts)


async def summarize_session(
    session: Dict[str, Any],
    db: DatabaseManager
) -> Optional[str]:
    """
    세션의 대화를 요약

    Args:
        session: 세션 정보
        db: DatabaseManager 인스턴스

    Returns:
        Optional[str]: 생성된 요약 또는 None
    """
    try:
        session_id = session['session_id']

        # dialogues 가져오기
        dialogues = db.load_dialogues(session_id=str(session_id), limit=200)

        if not dialogues:
            return None

        # conversation format으로 변환
        conversations = format_dialogues_to_conversations(dialogues)

        if not conversations:
            return None

        # 시나리오 컨텍스트
        scenario_context = get_scenario_context_from_session(session)

        # 요약 생성
        summary = await generate_conversation_summary(
            conversations=conversations,
            existing_summary=None,
            scenario_context=scenario_context
        )

        return summary

    except Exception as e:
        print(f"  ❌ Error summarizing session: {e}")
        return None


async def backfill_conversation_summaries_async(
    min_turn_count: int = 5,
    max_sessions: int = 100
):
    """
    대화 요약 백필 (비동기)

    Args:
        min_turn_count: 최소 턴 수 (너무 짧은 대화는 스킵)
        max_sessions: 최대 처리 세션 수
    """
    print("=" * 60)
    print("대화 요약 백필 스크립트")
    print("=" * 60)

    # Initialize DatabaseManager
    db = DatabaseManager(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5433")),
        dbname=os.getenv("DB_NAME", "kimedb"),
        user=os.getenv("DB_USER", "kime"),
        password=os.getenv("DB_PASSWORD", "dev123")
    )

    # Get sessions without summary
    print(f"\n📊 요약이 없는 세션 검색 중 (최소 {min_turn_count}턴)...")

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    session_id, scenario_id, user_name,
                    turn_count, current_stage
                FROM sessions
                WHERE (
                    conversation_summary IS NULL
                    OR conversation_summary = ''
                )
                AND turn_count >= %s
                ORDER BY turn_count DESC
                LIMIT %s
            """, (min_turn_count, max_sessions))

            sessions = []
            for row in cur.fetchall():
                sessions.append({
                    'session_id': str(row[0]),
                    'scenario_id': row[1],
                    'user_name': row[2],
                    'turn_count': row[3],
                    'current_stage': row[4]
                })

    if not sessions:
        print("✅ 모든 세션에 요약이 존재합니다!")
        return

    print(f"🚀 처리 대상 세션: {len(sessions)}개")
    print(f"📝 총 턴 수: {sum(s['turn_count'] for s in sessions)}")
    print("-" * 60)

    processed = 0
    success = 0
    errors = 0
    skipped = 0
    start_time = time.time()

    for session in sessions:
        session_id = session['session_id']
        turn_count = session['turn_count']

        try:
            print(f"\n[{processed + 1}/{len(sessions)}] Session {session_id[:8]}... ({turn_count}턴)")

            # 요약 생성
            summary = await summarize_session(session, db)

            if not summary or summary.strip() == "":
                print(f"  ⏭️  요약 생성 실패 또는 빈 결과, 스킵")
                skipped += 1
            else:
                # DB 업데이트
                db.update_session(
                    session_id=session_id,
                    updates={
                        'conversation_summary': summary,
                        'summary_turn_count': turn_count
                    }
                )

                print(f"  ✅ 요약 생성 완료 ({len(summary)}자)")
                success += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            errors += 1

        processed += 1

        # Rate limiting (OpenAI: 3000 RPM)
        await asyncio.sleep(0.5)

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("📊 백필 완료")
    print("=" * 60)
    print(f"✅ 성공: {success}")
    print(f"⏭️  스킵: {skipped}")
    print(f"❌ 실패: {errors}")
    print(f"⏱️  소요 시간: {elapsed:.1f}초")
    if success > 0:
        print(f"⚡ 처리 속도: {success / elapsed:.2f} sessions/s")
    print("=" * 60)


def backfill_conversation_summaries(
    min_turn_count: int = 5,
    max_sessions: int = 100
):
    """
    대화 요약 백필 (동기 wrapper)

    Args:
        min_turn_count: 최소 턴 수
        max_sessions: 최대 처리 세션 수
    """
    asyncio.run(backfill_conversation_summaries_async(
        min_turn_count=min_turn_count,
        max_sessions=max_sessions
    ))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="대화 요약 백필")
    parser.add_argument("--min-turns", type=int, default=5, help="최소 턴 수 (기본: 5)")
    parser.add_argument("--max-sessions", type=int, default=100, help="최대 세션 수 (기본: 100)")

    args = parser.parse_args()

    backfill_conversation_summaries(
        min_turn_count=args.min_turns,
        max_sessions=args.max_sessions
    )
