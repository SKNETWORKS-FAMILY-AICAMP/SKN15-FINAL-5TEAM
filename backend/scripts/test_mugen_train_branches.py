#!/usr/bin/env python3
"""
무한열차(Mugen Train) 시나리오 분기 도달 가능성 테스트

실제 API를 호출하여 AI가 생성한 실시간 응답을 받으면서
모든 분기점에 도달 가능한지 검증합니다.

주요 분기점:
1. DREAM_QUESTION: "약자를 지킨다" 답변 vs 기타 답변
2. ROUTE_CHOICE: 동료 경로 vs 무모한 경로
3. RECRUIT Mission: 젠이츠/이노스케 설득
4. END_ROUTER: 히든/기본/배드 엔딩

목적:
- 로직을 바꾸지 않고 실제 AI 응답으로 모든 분기 도달 테스트
- 도달 불가능한 분기 식별
- 분기 판단 로직의 유효성 검증
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
import httpx
from datetime import datetime

# API 설정
API_BASE_URL = "http://localhost:8000"
SCENARIO_ID = "mugen-train"


class BranchTester:
    """무한열차 분기 테스트 실행기"""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token = None
        self.user_id = None
        self.username = None

        # 테스트 결과 저장
        self.branch_results = {}
        self.unreachable_branches = []
        self.session_traces = []

    async def setup(self):
        """테스트 사용자 생성 및 로그인"""
        print("=" * 80)
        print("🎯 Mugen Train Branch Reachability Test")
        print("=" * 80)

        # 랜덤 사용자명 생성
        timestamp = int(time.time())
        self.username = f"branch{timestamp}"
        password = "testpass123"

        print(f"\n📝 Creating test user: {self.username}")

        # 사용자 등록
        try:
            register_response = await self.client.post(
                f"{self.api_base_url}/api/auth/register",
                json={
                    "username": self.username,
                    "password": password,
                    "display_name": f"Branch Tester {timestamp}"
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

    async def send_message(self, user_input: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """메시지 전송 및 응답 수신"""
        start_time = time.time()

        try:
            payload = {
                "scenario_id": SCENARIO_ID,
                "user_input": user_input,
                "user_name": self.username
            }

            if session_id:
                payload["session_id"] = session_id

            response = await self.client.post(
                f"{self.api_base_url}/api/chat",
                json=payload
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
                                # 메타데이터에서 세션 ID 추출
                                session_id_from_response = data.get("session_id")

                            elif msg_type == "dialogue":
                                # 대화 데이터
                                dialogues.append(data.get("dialogue", {}))

                            elif msg_type == "done":
                                # done 메시지에서 current_stage 추출 (가장 중요!)
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
            elapsed = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "elapsed": elapsed,
            }

    async def test_branch_path(
        self,
        path_name: str,
        user_inputs: List[str],
        expected_stages: List[str],
        description: str
    ) -> Dict[str, Any]:
        """
        특정 분기 경로 테스트

        Args:
            path_name: 경로 이름 (예: "allies_path_to_hidden_ending")
            user_inputs: 사용자 입력 시퀀스
            expected_stages: 예상되는 스테이지 시퀀스
            description: 테스트 설명

        Returns:
            테스트 결과
        """
        print(f"\n{'=' * 80}")
        print(f"🧪 Testing Branch Path: {path_name}")
        print(f"   {description}")
        print(f"{'=' * 80}\n")

        session_id = None
        current_stage = "START"
        actual_stages = []
        trace = []

        for i, user_input in enumerate(user_inputs, 1):
            print(f"[{i}/{len(user_inputs)}] 📤 Input: \"{user_input}\"")

            result = await self.send_message(user_input, session_id)

            if not result["success"]:
                print(f"   ❌ API Error: {result.get('error')}")
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
                print(f"   ⚠️  Warning: No current_stage in response")
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

            # 약간의 지연 (서버 부하 방지)
            await asyncio.sleep(0.5)

        # 결과 분석
        stages_match = actual_stages == expected_stages[:len(actual_stages)]
        reached_final_stage = len(actual_stages) == len(expected_stages)

        result_summary = {
            "path_name": path_name,
            "description": description,
            "success": stages_match and reached_final_stage,
            "stages_match": stages_match,
            "reached_final_stage": reached_final_stage,
            "expected_stages": expected_stages,
            "actual_stages": actual_stages,
            "trace": trace,
            "session_id": session_id,
        }

        # 결과 출력
        print(f"\n{'─' * 80}")
        print(f"📊 Path Test Result: {path_name}")
        print(f"{'─' * 80}")
        print(f"   Expected Stages: {expected_stages}")
        print(f"   Actual Stages:   {actual_stages}")
        print(f"   Stages Match:    {'✅' if stages_match else '❌'}")
        print(f"   Reached Final:   {'✅' if reached_final_stage else '❌'}")
        print(f"   Overall:         {'✅ SUCCESS' if result_summary['success'] else '❌ FAILED'}")

        self.branch_results[path_name] = result_summary
        self.session_traces.append(trace)

        if not result_summary['success']:
            self.unreachable_branches.append({
                "path": path_name,
                "expected": expected_stages,
                "actual": actual_stages,
                "reason": "Stage mismatch" if not stages_match else "Did not reach final stage"
            })

        return result_summary

    async def run_all_branch_tests(self):
        """모든 분기 경로 테스트 실행"""
        print("\n" + "=" * 80)
        print("🚀 Starting Comprehensive Branch Testing")
        print("=" * 80)

        # ============================================================
        # Test 1: DREAM_QUESTION - 정답 경로 ("약자를 지킨다")
        # ============================================================
        await self.test_branch_path(
            path_name="dream_question_correct_answer",
            user_inputs=[
                "안녕하세요",  # START -> TRAIN_START
                "네, 괜찮아요",  # TRAIN_START -> DREAM_QUESTION
                "약자를 지키는 것이 강자의 책무입니다",  # DREAM_QUESTION -> DREAM_ESCAPE_SUCCESS (정답)
            ],
            expected_stages=["TRAIN_START", "DREAM_QUESTION", "DREAM_ESCAPE_SUCCESS"],
            description="꿈 질문에 '약자를 지킨다' 정답을 선택하여 성공적으로 탈출"
        )

        # ============================================================
        # Test 2: DREAM_QUESTION - 오답 경로
        # ============================================================
        await self.test_branch_path(
            path_name="dream_question_wrong_answer",
            user_inputs=[
                "안녕하세요",
                "네, 괜찮아요",
                "저는 강해지고 싶어요",  # 오답 -> DREAM_ESCAPE_FAIL -> 다시 DREAM_QUESTION
            ],
            expected_stages=["TRAIN_START", "DREAM_QUESTION", "DREAM_QUESTION"],  # 루프
            description="꿈 질문에 오답을 선택하여 다시 꿈에 갇힘"
        )

        # ============================================================
        # Test 3: ROUTE_CHOICE - 동료 경로 (Allies Path)
        # ============================================================
        await self.test_branch_path(
            path_name="route_choice_allies_path",
            user_inputs=[
                "안녕하세요",
                "네, 괜찮아요",
                "약자를 지키는 것이 강자의 책무입니다",  # DREAM_ESCAPE_SUCCESS
                "계속 진행할게요",  # -> ROUTE_CHOICE
                "동료들을 데려올게요",  # choose_allies_path -> RECRUIT
            ],
            expected_stages=["TRAIN_START", "DREAM_QUESTION", "DREAM_ESCAPE_SUCCESS", "ROUTE_CHOICE", "RECRUIT"],
            description="동료 경로를 선택하여 RECRUIT 미션 스테이지로 진입"
        )

        # ============================================================
        # Test 4: ROUTE_CHOICE - 무모한 경로 (Reckless Path)
        # ============================================================
        await self.test_branch_path(
            path_name="route_choice_reckless_path",
            user_inputs=[
                "안녕하세요",
                "네, 괜찮아요",
                "약자를 지키는 것이 강자의 책무입니다",
                "계속 진행할게요",
                "렌고쿠씨와 함께 싸울래요",  # choose_reckless_path -> INTERVENE
            ],
            expected_stages=["TRAIN_START", "DREAM_QUESTION", "DREAM_ESCAPE_SUCCESS", "ROUTE_CHOICE", "INTERVENE"],
            description="무모한 경로를 선택하여 직접 전투 참여"
        )

        # ============================================================
        # Test 5: RECRUIT Mission - 젠이츠 설득 (네즈코 키워드 사용)
        # ============================================================
        await self.test_branch_path(
            path_name="recruit_zenitsu_success",
            user_inputs=[
                "안녕하세요",
                "네, 괜찮아요",
                "약자를 지키는 것이 강자의 책무입니다",
                "계속 진행할게요",
                "동료들을 데려올게요",  # -> RECRUIT
                "젠이츠, 네즈코가 위험해! 함께 싸우자!",  # 젠이츠 설득 (네즈코 키워드)
            ],
            expected_stages=["TRAIN_START", "DREAM_QUESTION", "DREAM_ESCAPE_SUCCESS", "ROUTE_CHOICE", "RECRUIT", "RECRUIT"],
            description="젠이츠를 '네즈코' 키워드로 설득 시도"
        )

        # ============================================================
        # Test 6: RECRUIT Mission - 이노스케 설득 (도발 키워드 사용)
        # ============================================================
        await self.test_branch_path(
            path_name="recruit_inosuke_success",
            user_inputs=[
                "안녕하세요",
                "네, 괜찮아요",
                "약자를 지키는 것이 강자의 책무입니다",
                "계속 진행할게요",
                "동료들을 데려올게요",
                "이노스케, 혼자서는 약하니까 도와줘!",  # 이노스케 설득 (겁쟁이 도발)
            ],
            expected_stages=["TRAIN_START", "DREAM_QUESTION", "DREAM_ESCAPE_SUCCESS", "ROUTE_CHOICE", "RECRUIT", "RECRUIT"],
            description="이노스케를 '약하다' 도발로 설득 시도"
        )

        # ============================================================
        # Test 7: HIDDEN Ending Path - 두 동료 모두 설득
        # ============================================================
        await self.test_branch_path(
            path_name="hidden_ending_path",
            user_inputs=[
                "안녕하세요",
                "네, 괜찮아요",
                "약자를 지키는 것이 강자의 책무입니다",
                "계속 진행할게요",
                "동료들을 데려올게요",
                "젠이츠, 네즈코를 지켜야 해! 함께 가자!",  # 젠이츠 설득
                "이노스케, 겁쟁이야? 싸우러 가자!",  # 이노스케 설득
                "모두 함께 싸우러 가요!",  # RECRUIT 완료 -> END_ROUTER -> END_HIDDEN
            ],
            expected_stages=[
                "TRAIN_START",
                "DREAM_QUESTION",
                "DREAM_ESCAPE_SUCCESS",
                "ROUTE_CHOICE",
                "RECRUIT",
                "RECRUIT",
                "RECRUIT",
                "END_HIDDEN"
            ],
            description="두 동료 모두 설득하여 히든 엔딩 도달"
        )

        # ============================================================
        # Test 8: BAD Ending Path - 무모한 희생
        # ============================================================
        await self.test_branch_path(
            path_name="bad_ending_path",
            user_inputs=[
                "안녕하세요",
                "네, 괜찮아요",
                "약자를 지키는 것이 강자의 책무입니다",
                "계속 진행할게요",
                "렌고쿠씨와 함께 싸울래요",  # 무모한 경로
                "제가 막아낼게요!",  # INTERVENE -> RECKLESS_SACRIFICE -> END_BAD
            ],
            expected_stages=[
                "TRAIN_START",
                "DREAM_QUESTION",
                "DREAM_ESCAPE_SUCCESS",
                "ROUTE_CHOICE",
                "INTERVENE",
                "RECKLESS_SACRIFICE"
            ],
            description="무모한 경로를 선택하여 배드 엔딩 도달"
        )

        # ============================================================
        # Test 9: BASIC Ending Path - 부분 성공 (동료 1명만 설득)
        # ============================================================
        await self.test_branch_path(
            path_name="basic_ending_path",
            user_inputs=[
                "안녕하세요",
                "네, 괜찮아요",
                "약자를 지키는 것이 강자의 책무입니다",
                "계속 진행할게요",
                "동료들을 데려올게요",
                "젠이츠, 네즈코를 지켜야 해!",  # 젠이츠만 설득
                "이제 가야겠어요",  # 포기
                "렌고쿠를 도우러 갑니다",  # RECRUIT 종료 -> END_ROUTER -> END_BASIC
            ],
            expected_stages=[
                "TRAIN_START",
                "DREAM_QUESTION",
                "DREAM_ESCAPE_SUCCESS",
                "ROUTE_CHOICE",
                "RECRUIT",
                "RECRUIT",
                "RECRUIT",
                "END_BASIC"
            ],
            description="동료 1명만 설득하여 기본 엔딩 도달"
        )

    async def generate_report(self):
        """최종 테스트 결과 리포트 생성"""
        print("\n\n" + "=" * 80)
        print("📊 FINAL BRANCH REACHABILITY REPORT")
        print("=" * 80)

        total_tests = len(self.branch_results)
        successful_tests = sum(1 for r in self.branch_results.values() if r["success"])
        failed_tests = total_tests - successful_tests

        print(f"\n📈 Overall Statistics:")
        print(f"   Total Branch Paths Tested: {total_tests}")
        print(f"   ✅ Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"   ❌ Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")

        # 성공한 분기
        if successful_tests > 0:
            print(f"\n✅ Reachable Branches ({successful_tests}):")
            for path_name, result in self.branch_results.items():
                if result["success"]:
                    print(f"   • {path_name}")
                    print(f"     └─ {result['description']}")

        # 실패한 분기
        if failed_tests > 0:
            print(f"\n❌ Unreachable or Failed Branches ({failed_tests}):")
            for path_name, result in self.branch_results.items():
                if not result["success"]:
                    print(f"   • {path_name}")
                    print(f"     └─ {result['description']}")
                    print(f"     └─ Expected: {result['expected_stages']}")
                    print(f"     └─ Actual:   {result['actual_stages']}")

        # 분기점별 분석
        print(f"\n🎯 Critical Decision Points Analysis:")

        decision_points = {
            "DREAM_QUESTION": [
                "dream_question_correct_answer",
                "dream_question_wrong_answer"
            ],
            "ROUTE_CHOICE": [
                "route_choice_allies_path",
                "route_choice_reckless_path"
            ],
            "RECRUIT Mission": [
                "recruit_zenitsu_success",
                "recruit_inosuke_success"
            ],
            "Endings": [
                "hidden_ending_path",
                "basic_ending_path",
                "bad_ending_path"
            ]
        }

        for decision_point, paths in decision_points.items():
            reachable = sum(1 for p in paths if p in self.branch_results and self.branch_results[p]["success"])
            total = len(paths)
            status = "✅" if reachable == total else "⚠️" if reachable > 0 else "❌"
            print(f"   {status} {decision_point}: {reachable}/{total} paths reachable")

        # 권장 사항
        print(f"\n💡 Recommendations:")
        if failed_tests == 0:
            print("   ✅ All tested branch paths are reachable!")
            print("   ✅ Branching logic is working correctly.")
            print("   ✅ Ready for production testing.")
        else:
            print(f"   ⚠️  {failed_tests} branch path(s) could not be reached.")
            print("   • Review intent mapping for failed branches")
            print("   • Check if heuristic keywords are working correctly")
            print("   • Verify stage transition logic")
            print("   • Consider adjusting AI prompts for better classification")

        # 세부 추적 정보 저장
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "username": self.username,
            "user_id": self.user_id,
            "statistics": {
                "total_tests": total_tests,
                "successful": successful_tests,
                "failed": failed_tests,
                "success_rate": f"{successful_tests/total_tests*100:.1f}%"
            },
            "results": self.branch_results,
            "unreachable_branches": self.unreachable_branches,
            "session_traces": self.session_traces,
        }

        # JSON 파일로 저장
        report_path = f"/tmp/mugen_train_branch_test_{int(time.time())}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"\n📄 Detailed report saved to: {report_path}")

        return report_data

    async def cleanup(self):
        """정리"""
        await self.client.aclose()
        print("\n✅ Cleanup completed\n")


async def main():
    """메인 함수"""
    tester = BranchTester(API_BASE_URL)

    try:
        # 1. 설정
        await tester.setup()

        # 2. 모든 분기 테스트 실행
        await tester.run_all_branch_tests()

        # 3. 최종 리포트 생성
        await tester.generate_report()

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
