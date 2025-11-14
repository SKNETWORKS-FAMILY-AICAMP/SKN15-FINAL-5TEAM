#!/usr/bin/env python3
"""
300개 대화 테스트 스크립트 - 무한성(Infinity Castle) 시나리오

목적:
- 실제 API 호출로 300개의 대화 생성
- 의사결정 데이터 수집 (ml.decision_logs)
- 지식 그래프 구축 준비
"""
import asyncio
import json
import random
import time
from typing import List, Dict, Any
import httpx
from datetime import datetime

# API 설정
API_BASE_URL = "http://localhost:8000"
SCENARIO_ID = "infinity_castle"  # 무한성
TOTAL_CONVERSATIONS = 300

# 다양한 사용자 입력 패턴 (무한성 시나리오에 적합)
USER_INPUT_PATTERNS = [
    # 전투 관련
    "무잔과 싸운다",
    "무잔을 공격한다",
    "무잔에게 달려든다",
    "강하게 공격한다",
    "검을 휘두른다",
    "호흡을 사용한다",
    "전력을 다해 싸운다",
    "방어한다",
    "피한다",
    "공격을 막는다",

    # 대화/설득
    "무잔과 대화한다",
    "무잔을 설득한다",
    "무잔에게 말을 건다",
    "이야기한다",
    "질문한다",
    "대답한다",

    # 탐색/이동
    "주변을 살핀다",
    "조심스럽게 다가간다",
    "뒤로 물러난다",
    "도망친다",
    "숨는다",
    "관찰한다",
    "기다린다",

    # 감정 표현
    "두렵다",
    "화가 난다",
    "슬프다",
    "기쁘다",
    "놀란다",
    "걱정된다",

    # 동료 관련
    "동료를 부른다",
    "도움을 요청한다",
    "함께 싸운다",
    "동료를 지킨다",

    # 기타
    "힘을 모은다",
    "준비한다",
    "집중한다",
    "생각한다",
    "결심한다",
]

# 추가 변형을 위한 수식어
MODIFIERS = [
    "강하게", "약하게", "조심스럽게", "빠르게", "천천히",
    "격렬하게", "차분하게", "신중하게", "과감하게", "용감하게"
]


class ConversationTester:
    """300개 대화 테스트 실행기"""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token = None
        self.user_id = None
        self.username = None
        self.session_id = None
        self.conversation_count = 0
        self.total_api_time = 0.0
        self.errors = []

    async def setup(self):
        """테스트 사용자 생성 및 로그인"""
        print("=" * 80)
        print("🚀 300 Conversations Test - Infinity Castle Scenario")
        print("=" * 80)

        # 1. 랜덤 사용자명 생성
        timestamp = int(time.time())
        self.username = f"graphrag_test_{timestamp}"
        password = "testpass123"

        print(f"\n📝 Step 1: Creating test user...")
        print(f"   Username: {self.username}")

        # 2. 사용자 등록
        try:
            register_response = await self.client.post(
                f"{self.api_base_url}/api/auth/register",
                json={
                    "username": self.username,
                    "password": password,
                    "email": f"{self.username}@test.com"
                }
            )

            if register_response.status_code == 201:
                print("   ✅ User created successfully")
                register_data = register_response.json()
                self.token = register_data.get("access_token")
                self.user_id = register_data.get("user_id")
            else:
                print(f"   ❌ Registration failed: {register_response.status_code}")
                print(f"   Response: {register_response.text}")
                raise Exception("User registration failed")

        except Exception as e:
            print(f"   ❌ Error during registration: {e}")
            raise

        print(f"   User ID: {self.user_id}")
        print(f"   Token: {self.token[:20]}...")

        # 3. 헤더 설정
        self.client.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })

        print("\n✅ Setup completed!\n")

    async def send_message(self, user_input: str) -> Dict[str, Any]:
        """메시지 전송 및 응답 수신"""
        start_time = time.time()

        try:
            response = await self.client.post(
                f"{self.api_base_url}/api/chat",
                json={
                    "scenario_id": SCENARIO_ID,
                    "user_input": user_input,
                    "user_name": self.username
                }
            )

            elapsed = time.time() - start_time
            self.total_api_time += elapsed

            if response.status_code == 200:
                # SSE 스트리밍 응답 파싱
                response_text = response.text
                lines = response_text.strip().split('\n')

                dialogues = []
                for line in lines:
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # "data: " 제거
                            if data.get("type") == "dialogue":
                                dialogues.append(data.get("data", {}))
                        except json.JSONDecodeError:
                            continue

                return {
                    "success": True,
                    "dialogues": dialogues,
                    "elapsed": elapsed,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "elapsed": elapsed,
                }

        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "elapsed": elapsed,
            }

    def generate_user_input(self) -> str:
        """다양한 사용자 입력 생성"""
        # 80% 확률로 패턴에서 선택, 20% 확률로 수식어 추가
        pattern = random.choice(USER_INPUT_PATTERNS)

        if random.random() < 0.2:
            modifier = random.choice(MODIFIERS)
            return f"{modifier} {pattern}"

        return pattern

    async def run_conversations(self, total: int = TOTAL_CONVERSATIONS):
        """N개의 대화 실행"""
        print(f"💬 Starting {total} conversations with '{SCENARIO_ID}' scenario...")
        print(f"   Estimated time: {total * 2}~{total * 5} seconds")
        print()

        success_count = 0
        error_count = 0

        for i in range(1, total + 1):
            # 사용자 입력 생성
            user_input = self.generate_user_input()

            # 메시지 전송
            result = await self.send_message(user_input)

            self.conversation_count = i

            if result["success"]:
                success_count += 1
                dialogue_count = len(result["dialogues"])

                # 진행 상황 출력 (10개마다)
                if i % 10 == 0 or i == 1:
                    avg_time = self.total_api_time / i
                    remaining = total - i
                    eta_seconds = int(avg_time * remaining)

                    print(f"[{i:3d}/{total}] ✅ '{user_input[:30]:30s}' → {dialogue_count} dialogues "
                          f"({result['elapsed']:.2f}s) | ETA: {eta_seconds}s")
            else:
                error_count += 1
                self.errors.append({
                    "turn": i,
                    "input": user_input,
                    "error": result.get("error")
                })

                print(f"[{i:3d}/{total}] ❌ '{user_input[:30]:30s}' → ERROR: {result.get('error')}")

            # 서버 부하 방지를 위한 짧은 대기
            await asyncio.sleep(0.1)

        print()
        print("=" * 80)
        print("📊 Test Summary")
        print("=" * 80)
        print(f"Total conversations: {total}")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {error_count}")
        print(f"⏱️  Total API time: {self.total_api_time:.2f}s")
        print(f"⏱️  Average response time: {self.total_api_time / total:.2f}s")
        print()

        if self.errors:
            print(f"⚠️  Errors ({len(self.errors)}):")
            for err in self.errors[:10]:  # 처음 10개만 출력
                print(f"   Turn {err['turn']}: {err['input']} → {err['error']}")
            if len(self.errors) > 10:
                print(f"   ... and {len(self.errors) - 10} more errors")
            print()

    async def check_data_collection(self):
        """데이터 수집 확인"""
        print("=" * 80)
        print("🔍 Checking Data Collection")
        print("=" * 80)

        # decision_logs 확인
        print("\n📊 Checking ml.decision_logs...")
        check_script = """
import asyncio
from app.core.db import get_async_session
from sqlalchemy import text

async def check():
    async with get_async_session() as db:
        # decision_logs 개수
        result = await db.execute(text("SELECT COUNT(*) FROM ml.decision_logs"))
        decision_count = result.scalar()
        print(f"   Total decision logs: {decision_count}")

        # agent별 통계
        result = await db.execute(text('''
            SELECT agent_name, decision_type, COUNT(*) as count
            FROM ml.decision_logs
            GROUP BY agent_name, decision_type
            ORDER BY count DESC
            LIMIT 10
        '''))
        print("   Top decision types:")
        for row in result:
            print(f"      {row.agent_name}/{row.decision_type}: {row.count}")

        # graph_nodes 개수
        result = await db.execute(text("SELECT COUNT(*) FROM knowledge.graph_nodes"))
        node_count = result.scalar()
        print(f"\\n   Total graph nodes: {node_count}")

        # graph_edges 개수
        result = await db.execute(text("SELECT COUNT(*) FROM knowledge.graph_edges"))
        edge_count = result.scalar()
        print(f"   Total graph edges: {edge_count}")

asyncio.run(check())
"""

        # 임시 파일로 저장 후 실행
        import tempfile
        import subprocess

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(check_script)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["python", temp_path],
                cwd="/Users/jtm427/Desktop/workspace/backend",
                capture_output=True,
                text=True
            )
            print(result.stdout)
            if result.stderr:
                print(f"   Errors: {result.stderr}")
        finally:
            import os
            os.unlink(temp_path)

    async def cleanup(self):
        """정리"""
        await self.client.aclose()
        print("\n✅ Cleanup completed")


async def main():
    """메인 함수"""
    tester = ConversationTester(API_BASE_URL)

    try:
        # 1. 설정
        await tester.setup()

        # 2. 300개 대화 실행
        await tester.run_conversations(TOTAL_CONVERSATIONS)

        # 3. 데이터 수집 확인
        await tester.check_data_collection()

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        print(f"   Completed: {tester.conversation_count}/{TOTAL_CONVERSATIONS} conversations")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
