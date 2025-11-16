#!/usr/bin/env python3
"""
귀칼 상담소 대화 품질 테스트

Stage 전환과 무관하게 자유대화의 품질을 평가합니다.
- 대화 맥락 유지 확인
- 캐릭터별 반응 적절성 검증
- 연속 대화 자연스러움 평가
"""
import asyncio
import httpx
import json
import time
from typing import List, Dict, Any


# API 설정
API_BASE_URL = "http://localhost:8000"
SCENARIO_ID = "counseling"


class CounselingQualityTester:
    """귀칼 상담소 대화 품질 테스터"""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token = None
        self.user_id = None
        self.username = None
        self.session_id = None

    async def setup(self):
        """테스트 사용자 생성 및 로그인"""
        print("=" * 80)
        print("💬 Counseling Quality Test - Free Conversation Focus")
        print("=" * 80)

        # 랜덤 사용자명 생성
        timestamp = int(time.time())
        self.username = f"counseling_quality_{timestamp}"
        password = "testpass123"

        print(f"\n📝 Creating test user: {self.username}")

        # 사용자 등록
        try:
            register_response = await self.client.post(
                f"{self.api_base_url}/api/auth/register",
                json={
                    "username": self.username,
                    "password": password,
                    "display_name": f"Quality Tester {timestamp}"
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

                # 세션 ID 저장
                if session_id_from_response:
                    self.session_id = session_id_from_response

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

    def print_dialogue(self, dialogues: List[Dict[str, Any]], turn: int):
        """대화 내용 출력"""
        print(f"\n{'─' * 80}")
        print(f"Turn {turn}")
        print(f"{'─' * 80}")

        for dialogue in dialogues:
            speaker = dialogue.get("speaker", "Unknown")
            text = dialogue.get("text", "")
            emotion = dialogue.get("emotion", "")

            # 화자에 따라 다른 색상 표시 (터미널 지원)
            if speaker == "narr":
                print(f"  📖 [나레이션] {text}")
            elif speaker == "tanjiro":
                print(f"  🔴 [탄지로] {text}")
            elif speaker == "zenitsu":
                print(f"  ⚡ [젠이츠] {text}")
            elif speaker == "inosuke":
                print(f"  🐗 [이노스케] {text}")
            elif speaker == "rengoku":
                print(f"  🔥 [렌고쿠] {text}")
            elif speaker == "nezuko":
                print(f"  🌸 [네즈코] {text}")
            else:
                print(f"  💭 [{speaker}] {text}")

            if emotion:
                print(f"      감정: {emotion}")

    async def quality_conversation_test(self):
        """자유 대화 품질 테스트"""
        print("\n" + "=" * 80)
        print("🎯 Free Conversation Quality Test")
        print("=" * 80)
        print("📌 Focus: 대화 맥락 유지, 캐릭터 반응, 자연스러움")
        print("📌 Stage 전환은 무시하고 대화 품질만 평가합니다.\n")

        # 테스트 대화 시나리오
        conversation_flow = [
            {
                "turn": 1,
                "input": "안녕하세요",
                "expect": "탄지로의 따뜻한 인사, 상담소 소개"
            },
            {
                "turn": 2,
                "input": "여기가 귀칼 상담소인가요?",
                "expect": "상담소 설명, 어떤 고민이 있는지 물어봄"
            },
            {
                "turn": 3,
                "input": "사실 연애 고민이 좀 있어요...",
                "expect": "젠이츠가 나타나서 반응, 연애 전문가라고 말함"
            },
            {
                "turn": 4,
                "input": "좋아하는 사람이 있는데 어떻게 고백해야 할지 모르겠어요",
                "expect": "젠이츠의 공감과 조언, 감정적 반응"
            },
            {
                "turn": 5,
                "input": "고백하기가 너무 무서워요",
                "expect": "젠이츠의 위로와 격려, 자신의 경험 공유"
            },
            {
                "turn": 6,
                "input": "용기를 내려면 어떻게 해야 할까요?",
                "expect": "구체적인 조언, 활동 제안 가능"
            },
            {
                "turn": 7,
                "input": "산책하면서 이야기하고 싶어요",
                "expect": "산책 활동으로 전환, 분위기 변화"
            },
            {
                "turn": 8,
                "input": "이야기 들어주셔서 정말 고마워요",
                "expect": "따뜻한 응원, 다른 동료들 등장 가능"
            },
            {
                "turn": 9,
                "input": "모두에게 인사드리고 싶어요",
                "expect": "단체 모임 분위기, 여러 캐릭터 반응"
            },
            {
                "turn": 10,
                "input": "다음에 또 올게요!",
                "expect": "따뜻한 작별 인사, 언제든 오라는 말"
            }
        ]

        quality_scores = []
        context_issues = []
        character_issues = []

        for scenario in conversation_flow:
            turn = scenario["turn"]
            user_input = scenario["input"]
            expectation = scenario["expect"]

            print(f"\n{'🎬' * 40}")
            print(f"Turn {turn}: {user_input}")
            print(f"예상: {expectation}")
            print(f"{'🎬' * 40}")

            result = await self.send_message(user_input)

            if not result["success"]:
                print(f"❌ Error: {result.get('error')}")
                quality_scores.append(0)
                continue

            # 대화 출력
            self.print_dialogue(result["dialogues"], turn)

            # 응답 시간
            print(f"\n⏱️  Response Time: {result['elapsed']:.2f}s")
            print(f"📊 Stage: {result.get('current_stage', 'UNKNOWN')}")
            print(f"📊 Turn Count: {result.get('turn_count', 'N/A')}")

            # 대화 품질 평가 (간단한 휴리스틱)
            dialogues = result["dialogues"]

            # 1. 응답이 있는가?
            has_response = len(dialogues) > 0

            # 2. 적절한 화자가 있는가?
            speakers = [d.get("speaker") for d in dialogues]
            has_appropriate_speaker = any(s in ["tanjiro", "zenitsu", "inosuke", "rengoku", "nezuko", "narr"] for s in speakers)

            # 3. 텍스트가 의미 있는가? (최소 10자 이상)
            has_meaningful_text = any(len(d.get("text", "")) >= 10 for d in dialogues)

            # 4. 맥락 관련성 (키워드 체크)
            if turn == 3 or turn == 4 or turn == 5 or turn == 6:
                # 연애 고민 관련 대화
                conversation_text = " ".join([d.get("text", "") for d in dialogues])
                has_context = any(keyword in conversation_text for keyword in ["연애", "사랑", "고백", "용기", "마음"])
            else:
                has_context = True  # 다른 턴은 맥락 체크 생략

            # 점수 계산
            score = sum([has_response, has_appropriate_speaker, has_meaningful_text, has_context])
            quality_scores.append(score)

            # 문제 기록
            if not has_context:
                context_issues.append(f"Turn {turn}: 맥락 유지 실패")
            if not has_appropriate_speaker:
                character_issues.append(f"Turn {turn}: 부적절한 화자")

            print(f"\n✅ Quality Score: {score}/4")

            # 짧은 대기
            await asyncio.sleep(0.3)

        # 최종 평가
        print("\n" + "=" * 80)
        print("📊 Conversation Quality Summary")
        print("=" * 80)

        avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        print(f"\n평균 품질 점수: {avg_score:.2f}/4.0")
        print(f"총 대화 턴: {len(conversation_flow)}")
        print(f"성공한 턴: {sum(1 for s in quality_scores if s >= 3)}/{len(quality_scores)}")

        if context_issues:
            print(f"\n⚠️  맥락 유지 문제: {len(context_issues)}건")
            for issue in context_issues:
                print(f"   - {issue}")

        if character_issues:
            print(f"\n⚠️  캐릭터 문제: {len(character_issues)}건")
            for issue in character_issues:
                print(f"   - {issue}")

        # 최종 판정
        if avg_score >= 3.5:
            print("\n✅ 대화 품질: 우수")
            print("   자유대화 시스템이 잘 작동하고 있습니다!")
        elif avg_score >= 2.5:
            print("\n⚠️  대화 품질: 보통")
            print("   일부 개선이 필요합니다.")
        else:
            print("\n❌ 대화 품질: 미흡")
            print("   대화 시스템에 문제가 있습니다.")

        return {
            "average_score": avg_score,
            "total_turns": len(conversation_flow),
            "successful_turns": sum(1 for s in quality_scores if s >= 3),
            "context_issues": len(context_issues),
            "character_issues": len(character_issues),
        }

    async def cleanup(self):
        """정리"""
        await self.client.aclose()


async def main():
    """메인 함수"""
    tester = CounselingQualityTester(API_BASE_URL)

    try:
        await tester.setup()
        result = await tester.quality_conversation_test()

        # 성공 여부 반환
        avg_score = result["average_score"]
        if avg_score >= 3.0:
            print("\n✅ Counseling quality test passed!")
            return 0
        else:
            print("\n❌ Counseling quality test failed")
            return 1

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 2
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
