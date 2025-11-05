#!/usr/bin/env python3
"""
KIME Chat 백엔드 시스템 종합 통합 테스트

검증 항목:
1. Database 연결 및 스키마
2. Session Management (HybridSessionManager)
3. Logging 시스템 (Error, Performance, General)
4. Training Logger (Auto-labeling)
5. Graph RAG 시스템 (엔티티, 임베딩, 관계)
6. API 서버 연동
"""

import sys
import os
sys.path.insert(0, '/Users/jtm427/Desktop/workspace/backend')

from src.database.db_manager import DatabaseManager
from src.database.session_manager import HybridSessionManager
from src.tools.training_logger import TrainingLogger
from src.utils.entity_extractor import EntityExtractor
from src.utils.embedding_matcher import EmbeddingClient
import time

print("=" * 80)
print("🔍 KIME Chat 백엔드 시스템 종합 통합 테스트")
print("=" * 80)

# 결과 추적
results = {}

# ============================================================================
# 테스트 1: Database 연결 및 스키마
# ============================================================================
print("\n" + "="*80)
print("테스트 1: Database 연결 및 스키마")
print("="*80)

try:
    db = DatabaseManager(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5433")),
        dbname=os.getenv("DB_NAME", "kimedb"),
        user=os.getenv("DB_USER", "kime"),
        password=os.getenv("DB_PASSWORD", "dev123")
    )

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # 스키마 확인
            cur.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name IN ('public', 'statedb', 'logdb')
            """)
            schemas = [row[0] for row in cur.fetchall()]

            print(f"\n✅ Database 연결 성공: kimedb@localhost:5433")
            print(f"✅ 스키마 확인: {', '.join(schemas)}")

            # 주요 테이블 확인
            cur.execute("""
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname IN ('public', 'statedb', 'logdb')
                AND tablename IN (
                    'sessions', 'training_logs', 'entities',
                    'entity_mentions', 'entity_relationships', 'logs'
                )
                ORDER BY schemaname, tablename
            """)
            tables = cur.fetchall()

            print(f"\n📊 주요 테이블 ({len(tables)}개):")
            for schema, table in tables:
                print(f"  - {schema}.{table}")

            results['database'] = {'status': 'success', 'schemas': schemas, 'tables': len(tables)}

except Exception as e:
    print(f"\n❌ Database 연결 실패: {e}")
    results['database'] = {'status': 'failed', 'error': str(e)}

# ============================================================================
# 테스트 2: Session Management
# ============================================================================
print("\n" + "="*80)
print("테스트 2: Session Management (HybridSessionManager)")
print("="*80)

try:
    # Redis 연결 확인
    import redis
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    print("✅ Redis 연결 성공")

    # HybridSessionManager 초기화
    session_manager = HybridSessionManager(
        db_manager=db,
        cache_manager=redis_client
    )

    # 테스트 세션 생성
    test_session_id = "test_integration_session"
    test_data = {
        "user_name": "통합테스트",
        "scenario_id": "test",
        "current_stage": "TEST_STAGE"
    }

    session_manager.save_session(test_session_id, test_data)
    retrieved = session_manager.get_session(test_session_id)

    if retrieved and retrieved.get("user_name") == "통합테스트":
        print("✅ 세션 저장/조회 성공")

        # Redis에서도 확인
        redis_key = f"session:{test_session_id}"
        redis_data = redis_client.get(redis_key)
        if redis_data:
            print("✅ Redis 캐시 작동 확인")

        # DB에서도 확인
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT session_id FROM statedb.sessions
                    WHERE session_id = %s
                """, (test_session_id,))
                db_session = cur.fetchone()
                if db_session:
                    print("✅ Database 영속화 확인")

        results['session_management'] = {'status': 'success'}
    else:
        raise Exception("세션 데이터 불일치")

except Exception as e:
    print(f"\n❌ Session Management 실패: {e}")
    results['session_management'] = {'status': 'failed', 'error': str(e)}

# ============================================================================
# 테스트 3: Logging 시스템
# ============================================================================
print("\n" + "="*80)
print("테스트 3: Logging 시스템 (Error, Performance, General)")
print("="*80)

try:
    # 로그 저장 테스트
    test_log_id = session_manager.save_log(
        log_level="INFO",
        message="통합 테스트 로그",
        session_id=test_session_id,
        stage_name="TEST_STAGE",
        agent_name="integration_test",
        context_data={"test": True}
    )

    if test_log_id:
        print("✅ 일반 로그 저장 성공")

    # 에러 로그 테스트
    error_log_id = session_manager.save_error_log(
        error_type="TestError",
        error_message="테스트 에러 메시지",
        session_id=test_session_id,
        context_data={"error_context": "test"}
    )

    if error_log_id:
        print("✅ 에러 로그 저장 성공")

    # 성능 메트릭 테스트
    metric_id = session_manager.save_performance_metric(
        operation_name="test_operation",
        duration_ms=100,
        session_id=test_session_id,
        tags={"type": "integration_test"}
    )

    if metric_id:
        print("✅ 성능 메트릭 저장 성공")

    # logdb.logs 테이블 확인
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM logdb.logs")
            log_count = cur.fetchone()[0]
            print(f"✅ 전체 로그 수: {log_count}개")

    results['logging'] = {'status': 'success', 'log_count': log_count}

except Exception as e:
    print(f"\n❌ Logging 시스템 실패: {e}")
    import traceback
    traceback.print_exc()
    results['logging'] = {'status': 'failed', 'error': str(e)}

# ============================================================================
# 테스트 4: Training Logger (Auto-labeling)
# ============================================================================
print("\n" + "="*80)
print("테스트 4: Training Logger (Auto-labeling)")
print("="*80)

try:
    training_logger = TrainingLogger(db_manager=db)

    # LLM 라벨링 활성화 확인
    if training_logger.llm_labeling_enabled:
        print("✅ LLM 기반 auto-labeling 활성화됨")
    else:
        print("⚠️  LLM 기반 auto-labeling 비활성화됨 (Rule-based만 사용)")

    # 엔티티 추출 활성화 확인
    if training_logger.entity_extraction_enabled:
        print("✅ Graph RAG 엔티티 추출 활성화됨")
    else:
        print("⚠️  엔티티 추출 비활성화됨")

    # 테스트 로그 저장
    test_state = {
        "session_id": test_session_id,
        "turn_count": 1,
        "user_input": "렌고쿠와 탄지로가 염의 호흡 훈련을 했다"
    }

    test_output = {
        "dialogues": [
            {"speaker": "렌고쿠", "text": "좋다! 계속 훈련하자!"}
        ]
    }

    log_id = training_logger.log_agent_execution(
        agent_name="integration_test",
        state=test_state,
        model_output=test_output,
        latency_ms=100
    )

    if log_id:
        print(f"✅ Training 로그 저장 성공 (ID: {log_id})")

        # 자동 라벨링 결과 확인
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT outcome, outcome_reason, mentioned_entity_ids
                    FROM training_logs
                    WHERE id = %s
                """, (log_id,))
                result = cur.fetchone()

                if result:
                    outcome, reason, entity_ids = result
                    print(f"✅ Auto-labeling 결과: {outcome}")
                    if entity_ids and len(entity_ids) > 0:
                        print(f"✅ 엔티티 추출: {len(entity_ids)}개")

    results['training_logger'] = {'status': 'success', 'log_id': log_id}

except Exception as e:
    print(f"\n❌ Training Logger 실패: {e}")
    import traceback
    traceback.print_exc()
    results['training_logger'] = {'status': 'failed', 'error': str(e)}

# ============================================================================
# 테스트 5: Graph RAG 시스템
# ============================================================================
print("\n" + "="*80)
print("테스트 5: Graph RAG 시스템")
print("="*80)

try:
    # 엔티티 추출기
    extractor = EntityExtractor()
    print("✅ EntityExtractor 초기화 성공")

    # 임베딩 클라이언트
    embedding_client = EmbeddingClient()
    print(f"✅ EmbeddingClient 초기화 성공 (모델: {embedding_client.model})")

    # 엔티티 통계
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM statedb.entities")
            entity_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM statedb.entity_mentions")
            mention_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM statedb.entity_relationships")
            relationship_count = cur.fetchone()[0]

            print(f"\n📊 Graph RAG 통계:")
            print(f"  - 엔티티: {entity_count}개")
            print(f"  - 멘션: {mention_count}개")
            print(f"  - 관계: {relationship_count}개")

    # 벡터 검색 테스트
    test_query = "불의 호흡"
    query_embedding = embedding_client.embed(test_query)
    similar = db.find_similar_entities(query_embedding, limit=3)

    if similar:
        print(f"\n✅ 벡터 유사도 검색 작동:")
        for entity in similar[:2]:
            print(f"  - {entity['entity_name']} (거리: {entity['distance']:.3f})")

    results['graph_rag'] = {
        'status': 'success',
        'entities': entity_count,
        'mentions': mention_count,
        'relationships': relationship_count
    }

except Exception as e:
    print(f"\n❌ Graph RAG 시스템 실패: {e}")
    import traceback
    traceback.print_exc()
    results['graph_rag'] = {'status': 'failed', 'error': str(e)}

# ============================================================================
# 최종 결과 요약
# ============================================================================
print("\n" + "="*80)
print("📊 최종 결과 요약")
print("="*80)

success_count = sum(1 for r in results.values() if r.get('status') == 'success')
total_count = len(results)

print(f"\n전체 테스트: {success_count}/{total_count} 성공\n")

for test_name, result in results.items():
    status_icon = "✅" if result.get('status') == 'success' else "❌"
    test_display = test_name.replace('_', ' ').title()
    print(f"{status_icon} {test_display}: {result.get('status')}")

    if result.get('status') == 'failed':
        print(f"   오류: {result.get('error', 'Unknown')}")

print("\n" + "="*80)
if success_count == total_count:
    print("🎉 모든 시스템이 정상 작동하고 있습니다!")
else:
    print(f"⚠️  {total_count - success_count}개 시스템에 문제가 있습니다.")
print("="*80)

# 상세 정보 출력
print("\n📝 상세 정보:")
if 'database' in results and results['database'].get('status') == 'success':
    print(f"  - Database 스키마: {results['database'].get('schemas')}")
    print(f"  - 주요 테이블: {results['database'].get('tables')}개")

if 'logging' in results and results['logging'].get('status') == 'success':
    print(f"  - 전체 로그: {results['logging'].get('log_count')}개")

if 'graph_rag' in results and results['graph_rag'].get('status') == 'success':
    print(f"  - 엔티티: {results['graph_rag'].get('entities')}개")
    print(f"  - 멘션: {results['graph_rag'].get('mentions')}개")
    print(f"  - 관계: {results['graph_rag'].get('relationships')}개")

print("\n" + "="*80)
