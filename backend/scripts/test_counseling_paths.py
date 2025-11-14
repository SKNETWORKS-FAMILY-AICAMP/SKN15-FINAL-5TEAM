#!/usr/bin/env python3
"""
귀칼 상담소 시나리오 경로 테스트

목적:
- 5가지 고민 유형별 상담 경로 테스트
- 3가지 힐링 활동 경로 테스트
- 스테이지 전환 로직 검증
"""
import asyncio
import httpx
import json
import time
from typing import List, Dict, Any


# API 설정
API_BASE_URL = "http://localhost:8000"
SCENARIO_ID = "counseling"


# 테스트 경로 정의
TEST_PATHS = [
    {
        "path_id": "love_walk",
        "description": "연애 고민 → 산책",
        "expected_stages": ["WELCOME", "CONCERN_CHECK", "LOVE_COUNSELING", "ACTIVITY_CHOICE", "ACTIVITY_WALK", "GROUP_GATHERING", "GIFT_GIVING", "FAREWELL"],
        "inputs": [
            "안녕하세요",
            "좋아하는 사람이 있는데 고백을 못하겠어요",
            "어떻게 해야 할까요?",
            "산책하면서 이야기할래요",
            "고마워요",
            "응원해주셔서 감사합니다",
            "선물 고마워요",
            "다음에 또 올게요"
        ]
    },
    {
        "path_id": "career_meditation",
        "description": "진로 고민 → 명상",
        "expected_stages": ["WELCOME", "CONCERN_CHECK", "CAREER_COUNSELING", "ACTIVITY_CHOICE", "ACTIVITY_MEDITATION", "GROUP_GATHERING", "GIFT_GIVING", "FAREWELL"],
        "inputs": [
            "안녕하세요",
            "제 진로에 대해 고민이 많아요",
            "어떤 일을 해야 할지 모르겠어요",
            "명상을 해보고 싶어요",
            "마음이 편안해졌어요",
            "모두 고마워요",
            "선물 감사합니다",
            "다음에 또 올게요"
        ]
    },
    {
        "path_id": "relationship_cooking",
        "description": "대인관계 고민 → 요리",
        "expected_stages": ["WELCOME", "CONCERN_CHECK", "RELATIONSHIP_COUNSELING", "ACTIVITY_CHOICE", "ACTIVITY_COOKING", "GROUP_GATHERING", "GIFT_GIVING", "FAREWELL"],
        "inputs": [
            "안녕하세요",
            "사람들과 어울리는 게 너무 어려워요",
            "친구를 사귀고 싶은데...",
            "함께 요리하고 싶어요",
            "즐거웠어요",
            "여러분 감사합니다",
            "선물 잘 받을게요",
            "다음에 또 올게요"
        ]
    },
    {
        "path_id": "confidence_skip",
        "description": "자신감 고민 → 활동 생략",
        "expected_stages": ["WELCOME", "CONCERN_CHECK", "CONFIDENCE_COUNSELING", "ACTIVITY_CHOICE", "GROUP_GATHERING", "GIFT_GIVING", "FAREWELL"],
        "inputs": [
            "안녕하세요",
            "자신감이 없어요",
            "제가 잘할 수 있을까요?",
            "바로 마무리할게요",
            "응원 감사합니다",
            "선물 고마워요",
            "안녕히 계세요"
        ]
    },
    {
        "path_id": "stress_walk",
        "description": "스트레스 고민 → 산책",
        "expected_stages": ["WELCOME", "CONCERN_CHECK", "STRESS_COUNSELING", "ACTIVITY_CHOICE", "ACTIVITY_WALK", "GROUP_GATHERING", "GIFT_GIVING", "FAREWELL"],
        "inputs": [
            "안녕하세요",
            "요즘 스트레스가 너무 심해요",
            "어떻게 풀면 좋을까요?",
            "밖에서 바람 쐴래요",
            "기분이 좋아졌어요",
            "모두 감사해요",
            "선물 잘 받을게요",
            "다음에 또 만나요"
        ]
    }
]


class CounselingTester:
    """귀칼 상담소 경로 테스터"""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token = None
        self.user_id = None
        self.username = None

    async def setup(self):
        """테스트 사용자 생성 및 로그인"""
        print("=" * 80)
        print("🏥 Counseling Scenario Path Test")
        print("=" * 80)

        # 랜덤 사용자명 생성
        timestamp = int(time.time())
        self.username = f"counseling{timestamp}"
        password = "testpass123"

        print(f"\n📝 Creating test user: {self.username}")

        # 사용자 등록
        try:
            register_response = await self.client.post(
                f"{self.api_base_url}/api/auth/register",
                json={
                    "username": self.username,
                    "password": password,
                    "display_name": f"Counseling Tester {timestamp}"
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

        # 헤더 설정
        self.client.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })

        print(f"   User ID: {self.user_id}")
        print("   ✅ Setup completed!\n")

    async def send_message(self, user_input: str) -> Dict[str, Any]:
        """메시지 전송 및 응답 수신"""
        try:
            start_time = time.time()

            response = await self.client.post(
                f"{self.api_base_url}/api/chat",
                json={
                    "scenario_id": SCENARIO_ID,
                    "user_input": user_input,
                    "user_name": self.username
                }
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                # SSE 스트리밍 응답 파싱
                response_text = response.text
                lines = response_text.strip().split('\n')

                dialogues = []
                session_id_from_response = None
                current_stage = None
                turn_count = None
                is_ended = False

                for line in lines:
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            msg_type = data.get("type")

                            if msg_type == "metadata":
                                session_id_from_response = data.get("session_id")

                            elif msg_type == "dialogue":
                                dialogues.append(data.get("dialogue", {}))

                            elif msg_type == "done":
                                current_stage = data.get("current_stage")
                                turn_count = data.get("turn_count")
                                is_ended = data.get("is_ended", False)

                        except json.JSONDecodeError:
                            continue

                return {
                    "success": True,
                    "dialogues": dialogues,
                    "session_id": session_id_from_response,
                    "current_stage": current_stage,
                    "turn_count": turn_count,
                    "is_ended": is_ended,
                    "elapsed": elapsed,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_text": response.text,
                    "elapsed": elapsed,
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "elapsed": 0,
            }

    async def test_path(self, path_config: Dict[str, Any]) -> Dict[str, Any]:
        """하나의 경로 테스트"""
        path_id = path_config["path_id"]
        description = path_config["description"]
        expected_stages = path_config["expected_stages"]
        inputs = path_config["inputs"]

        print("=" * 80)
        print(f"🧪 Testing Path: {path_id}")
        print(f"   {description}")
        print("=" * 80)

        session_id = None
        actual_stages = []
        trace = []

        for i, user_input in enumerate(inputs, 1):
            result = await self.send_message(user_input)

            if not result["success"]:
                print(f"[{i}/{len(inputs)}] ❌ Error: {result.get('error')}")
                trace.append({
                    "turn": i,
                    "input": user_input,
                    "error": result.get("error"),
                    "success": False
                })
                break

            # 세션 ID 및 스테이지 추출
            if result.get("session_id") and not session_id:
                session_id = result["session_id"]

            current_stage = result.get("current_stage")
            if not current_stage:
                current_stage = "UNKNOWN"

            actual_stages.append(current_stage)

            # 대화 내용 요약
            dialogue_count = len(result["dialogues"])
            dialogue_preview = ""
            if result["dialogues"]:
                first_dialogue = result["dialogues"][0]
                speaker = first_dialogue.get("speaker", "Unknown")
                text = first_dialogue.get("text", "")[:50]
                dialogue_preview = f"{speaker}: {text}..."

            print(f"[{i}/{len(inputs)}] 📤 Input: \"{user_input}\"")
            print(f"   ✅ Stage: {current_stage}")
            print(f"   💬 Dialogues: {dialogue_count} | {dialogue_preview}")
            print(f"   ⏱️  Time: {result['elapsed']:.2f}s\n")

            trace.append({
                "turn": i,
                "input": user_input,
                "stage": current_stage,
                "dialogue_count": dialogue_count,
                "elapsed": result["elapsed"],
                "success": True
            })

            # 짧은 대기
            await asyncio.sleep(0.2)

        # 결과 검증
        stages_match = actual_stages == expected_stages
        reached_final = actual_stages[-1] == expected_stages[-1] if actual_stages and expected_stages else False

        print("\n" + "─" * 80)
        print(f"📊 Path Test Result: {path_id}")
        print("─" * 80)
        print(f"   Expected Stages: {expected_stages}")
        print(f"   Actual Stages:   {actual_stages}")
        print(f"   Stages Match:    {'✅' if stages_match else '❌'}")
        print(f"   Reached Final:   {'✅' if reached_final else '❌'}")
        print(f"   Overall:         {'✅ PASSED' if stages_match else '❌ FAILED'}\n")

        return {
            "path_id": path_id,
            "description": description,
            "success": stages_match,
            "expected_stages": expected_stages,
            "actual_stages": actual_stages,
            "trace": trace
        }

    async def run_all_tests(self):
        """모든 경로 테스트 실행"""
        print("\n" + "=" * 80)
        print("🚀 Starting Comprehensive Path Testing")
        print("=" * 80)
        print()

        results = []
        for path_config in TEST_PATHS:
            result = await self.test_path(path_config)
            results.append(result)
            print()

        # 최종 요약
        print("=" * 80)
        print("📊 Final Summary")
        print("=" * 80)

        success_count = sum(1 for r in results if r["success"])
        failure_count = len(results) - success_count

        print(f"\nTotal Paths Tested: {len(results)}")
        print(f"✅ Passed: {success_count}")
        print(f"❌ Failed: {failure_count}")
        print(f"Success Rate: {success_count / len(results) * 100:.1f}%\n")

        # 실패한 경로 상세
        if failure_count > 0:
            print("⚠️  Failed Paths:")
            for r in results:
                if not r["success"]:
                    print(f"   - {r['path_id']}: {r['description']}")
                    print(f"     Expected: {' → '.join(r['expected_stages'])}")
                    print(f"     Got:      {' → '.join(r['actual_stages'])}")
            print()

        return results

    async def cleanup(self):
        """정리"""
        await self.client.aclose()


async def main():
    """메인 함수"""
    tester = CounselingTester(API_BASE_URL)

    try:
        await tester.setup()
        results = await tester.run_all_tests()

        # 성공 여부 반환
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        if success_rate == 1.0:
            print("✅ All counseling paths are working correctly!")
            return 0
        elif success_rate >= 0.8:
            print("⚠️  Most paths working, but some issues found")
            return 1
        else:
            print("❌ Multiple path failures detected")
            return 2

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 3
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
