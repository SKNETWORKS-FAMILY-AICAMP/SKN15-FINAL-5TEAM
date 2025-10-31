#!/usr/bin/env python3
"""
문제 3 테스트: Training Log 시스템 검증
training_logs 테이블에 에이전트 실행 로그가 저장되는지 확인
"""
import requests
import subprocess
import sys
import time

API_URL = "http://localhost:8000"

def check_db(query):
    """PostgreSQL 쿼리 실행"""
    cmd = f'docker exec kime-postgres psql -U kime -d kimedb -t -c "{query}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

print("\n" + "="*60)
print("문제 3 테스트: Training Log 시스템")
print("="*60)

# 테이블 존재 확인
print("\n[확인] training_logs 테이블 존재 여부")
print("-" * 60)

table_check = check_db("""
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_name = 'training_logs';
""")

if int(table_check.strip()) > 0:
    print("✅ training_logs 테이블이 존재합니다")
else:
    print("❌ training_logs 테이블이 없습니다")
    sys.exit(1)

# 기존 레코드 수 확인
existing_count = check_db("SELECT COUNT(*) FROM training_logs;").strip()
print(f"\n📊 기존 training_logs 레코드: {existing_count}개")

# 테스트: 인증된 사용자로 채팅 (에이전트 로그 발생)
print("\n[테스트] 채팅을 통한 에이전트 로그 생성")
print("-" * 60)

# 로그인
login_data = {
    "username": "finaltest001",
    "password": "test1234"
}

try:
    login_response = requests.post(f"{API_URL}/api/auth/login", json=login_data, timeout=10)
    login_result = login_response.json()

    if login_response.status_code == 200 and login_result.get('success'):
        access_token = login_result.get('access_token')
        user_id = login_result.get('user_id')
        username = login_result.get('username')

        print(f"✅ 로그인 성공: {username}")

        # 채팅 요청 (에이전트들이 실행되면서 로그 생성)
        headers = {"Authorization": f"Bearer {access_token}"}
        chat_data = {
            "scenario_id": "cutscene5_llm_driven",
            "user_input": "Training log 테스트",
            "user_name": username
        }

        print(f"\n📤 채팅 요청 중 (에이전트 실행)...")
        chat_start = time.time()

        chat_response = requests.post(
            f"{API_URL}/api/chat",
            json=chat_data,
            headers=headers,
            timeout=120
        )

        chat_duration = time.time() - chat_start

        if chat_response.status_code == 200:
            result = chat_response.json()
            session_id = result.get('session_id')
            dialogues = result.get('dialogues', [])

            print(f"✅ 채팅 성공 (소요시간: {chat_duration:.2f}초)")
            print(f"   Session ID: {session_id}")
            print(f"   응답 대화 수: {len(dialogues)}개")

            # 잠시 대기 (비동기 로깅이 있을 경우 대비)
            time.sleep(1)

            # DB 확인 - training_logs 전체
            new_count = check_db("SELECT COUNT(*) FROM training_logs;").strip()

            print(f"\n📊 training_logs 테이블 확인:")
            print(f"   이전 레코드: {existing_count}개")
            print(f"   현재 레코드: {new_count}개")
            print(f"   새로 추가된 로그: {int(new_count) - int(existing_count)}개")

            if int(new_count) > int(existing_count):
                print(f"   ✅✅✅ training_logs에 새 로그 저장됨! (문제 3 해결)")

                # 이번 세션의 로그만 조회
                session_logs = check_db(f"""
                    SELECT agent_name, outcome, latency_ms, llm_model
                    FROM training_logs
                    WHERE session_id = '{session_id}'
                    ORDER BY created_at;
                """)

                print(f"\n   이번 세션의 에이전트 로그:")
                for line in session_logs.split('\n'):
                    if line.strip():
                        parts = line.strip().split('|')
                        if len(parts) >= 4:
                            agent = parts[0].strip()
                            outcome = parts[1].strip()
                            latency = parts[2].strip()
                            model = parts[3].strip()
                            print(f"      - {agent:12} | outcome: {outcome:8} | latency: {latency:>5}ms | model: {model}")
                        else:
                            print(f"      {line}")

                # 에이전트별 통계
                print(f"\n📊 에이전트별 로그 통계:")
                agent_stats = check_db("""
                    SELECT
                        agent_name,
                        COUNT(*) as count,
                        COALESCE(AVG(latency_ms)::int, 0) as avg_latency,
                        COUNT(CASE WHEN outcome = 'success' THEN 1 END) as success_count,
                        COUNT(CASE WHEN outcome = 'failure' THEN 1 END) as failure_count,
                        COUNT(CASE WHEN outcome = 'partial' THEN 1 END) as partial_count
                    FROM training_logs
                    GROUP BY agent_name
                    ORDER BY count DESC;
                """)

                print("   Agent        | Total | Avg Latency | Success | Failure | Partial")
                print("   " + "-" * 70)
                for line in agent_stats.split('\n'):
                    if line.strip() and '|' in line:
                        print(f"   {line}")

                # 최근 로그 샘플 (context와 model_output 미리보기)
                print(f"\n📊 최근 로그 샘플 (JSONB 데이터):")
                recent_log = check_db("""
                    SELECT
                        agent_name,
                        context->>'scenario_id' as scenario,
                        context->>'current_stage' as stage,
                        jsonb_typeof(model_output) as output_type,
                        feedback_score
                    FROM training_logs
                    ORDER BY created_at DESC
                    LIMIT 3;
                """)

                for line in recent_log.split('\n'):
                    if line.strip():
                        print(f"   {line}")

            else:
                print(f"   ❌ training_logs에 새 로그가 저장 안 됨 (문제 3 미해결)")
                print(f"   💡 힌트: TrainingLogger가 비활성화되어 있거나 에러 발생")

        else:
            print(f"❌ 채팅 실패: {chat_response.text}")
    else:
        print(f"❌ 로그인 실패: {login_result}")

except Exception as e:
    print(f"❌ 에러 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("테스트 완료")
print("="*60 + "\n")
