#!/usr/bin/env python3
"""
무한열차 시나리오 종합 분기 테스트
- 20개 테스트 케이스로 모든 분기 및 이미지 전환 확인
- LLM 기반 이미지 선택 시스템 검증
"""

import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime

API_URL = "http://localhost:8000/api/chat"
SCENARIO_ID = "cutscene5_llm_driven"

class Colors:
    """터미널 색상"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class TestCase:
    """테스트 케이스"""
    def __init__(self, name: str, description: str, steps: List[str],
                 expected_stages: List[str], expected_images: List[str]):
        self.name = name
        self.description = description
        self.steps = steps
        self.expected_stages = expected_stages
        self.expected_images = expected_images
        self.session_id: Optional[str] = None
        self.actual_stages: List[str] = []
        self.actual_images: List[str] = []
        self.passed = False
        self.error: Optional[str] = None

def send_message(user_input: str, session_id: Optional[str] = None,
                 user_name: str = "테스터") -> Dict:
    """API로 메시지 전송"""
    payload = {
        "scenario_id": SCENARIO_ID,
        "user_input": user_input,
        "user_name": user_name
    }

    if session_id:
        payload["session_id"] = session_id

    try:
        response = requests.post(API_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"{Colors.FAIL}❌ API 오류: {e}{Colors.ENDC}")
        raise

def run_test_case(test: TestCase) -> bool:
    """단일 테스트 케이스 실행"""
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}🧪 {test.name}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{test.description}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}")

    try:
        for i, step in enumerate(test.steps, 1):
            print(f"\n{Colors.BOLD}[Step {i}/{len(test.steps)}]{Colors.ENDC} 입력: {Colors.OKCYAN}{step}{Colors.ENDC}")

            # API 호출
            response = send_message(step, test.session_id)

            # 세션 ID 저장
            if not test.session_id:
                test.session_id = response.get("session_id")
                print(f"  📍 Session: {test.session_id}")

            # 현재 상태 추출
            current_stage = response.get("current_stage", "UNKNOWN")
            current_image = response.get("current_image", "none")
            dialogue_count = len(response.get("dialogues", []))

            test.actual_stages.append(current_stage)
            test.actual_images.append(current_image)

            print(f"  📊 Stage: {Colors.OKGREEN}{current_stage}{Colors.ENDC}")
            print(f"  🖼️  Image: {Colors.OKGREEN}{current_image}{Colors.ENDC}")
            print(f"  💬 Dialogues: {dialogue_count}개")

            # 대화 일부 출력 (디버깅용)
            dialogues = response.get("dialogues", [])
            if dialogues:
                for d in dialogues[:3]:  # 처음 3개만
                    speaker = d.get("speaker", "?")
                    text = d.get("text", "")[:60]
                    print(f"    [{speaker}] {text}...")

            # API 부하 방지를 위한 딜레이
            time.sleep(0.5)

        # 결과 검증
        print(f"\n{Colors.BOLD}📋 검증 결과:{Colors.ENDC}")

        # 스테이지 검증
        stage_match = any(stage in test.actual_stages for stage in test.expected_stages)
        print(f"  ✓ 예상 스테이지: {', '.join(test.expected_stages)}")
        print(f"  ✓ 실제 스테이지: {', '.join(set(test.actual_stages))}")

        if stage_match:
            print(f"  {Colors.OKGREEN}✅ 스테이지 일치{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}❌ 스테이지 불일치{Colors.ENDC}")

        # 이미지 검증
        image_match = any(img in test.actual_images for img in test.expected_images)
        print(f"  ✓ 예상 이미지: {', '.join(test.expected_images)}")
        print(f"  ✓ 실제 이미지: {', '.join(set(test.actual_images))}")

        if image_match:
            print(f"  {Colors.OKGREEN}✅ 이미지 일치{Colors.ENDC}")
        else:
            print(f"  {Colors.WARNING}⚠️  이미지 불일치 (LLM 선택 결과일 수 있음){Colors.ENDC}")

        test.passed = stage_match and image_match
        return test.passed

    except Exception as e:
        test.error = str(e)
        print(f"\n{Colors.FAIL}❌ 테스트 실패: {e}{Colors.ENDC}")
        return False

def create_test_cases() -> List[TestCase]:
    """20개 테스트 케이스 생성"""
    return [
        # ==================== INTRO 분기 (4개) ====================
        TestCase(
            name="TEST-01: 초기 탈선 장면",
            description="게임 시작 직후 탈선 장면 확인",
            steps=["시작"],
            expected_stages=["INTRO"],
            expected_images=["1", "2", "3"]  # 탈선 → 렌고쿠 → 아카자
        ),

        TestCase(
            name="TEST-02: 아카자 등장 대화 진행",
            description="여러 대화를 통해 아카자 등장 씬 확인",
            steps=["시작", "렌고쿠 님 괜찮으세요?", "어떻게 해야 하죠?"],
            expected_stages=["INTRO"],
            expected_images=["3", "5", "6"]  # 아카자 등장 → 술식 전개 → 전투 시작
        ),

        TestCase(
            name="TEST-03: INTRO에서 많은 대화 진행",
            description="INTRO 스테이지에서 대화 카운트 증가 확인",
            steps=["시작", "무슨 일이죠?", "저도 도와야 해요!", "같이 싸우고 싶어요"],
            expected_stages=["INTRO", "ROUTE_CHOICE"],
            expected_images=["1", "2", "3", "5", "6"]
        ),

        TestCase(
            name="TEST-04: 빠른 갈림길 도달",
            description="최소 대화로 ROUTE_CHOICE 도달",
            steps=["시작", "어떻게 해야 하죠?", "도와드릴게요!"],
            expected_stages=["INTRO", "ROUTE_CHOICE"],
            expected_images=["1", "2", "3"]
        ),

        # ==================== RECRUIT 분기 (6개) ====================
        TestCase(
            name="TEST-05: 이노스케 발견 루트",
            description="동료 규합 선택 후 이노스케 먼저 찾기",
            steps=[
                "시작",
                "동료들을 찾아서 도움을 받아야겠어요!",
                "이노스케를 먼저 찾을게요",
                "이노스케! 함께 싸우자!"
            ],
            expected_stages=["INTRO", "ROUTE_CHOICE", "RECRUIT"],
            expected_images=["8", "9"]  # 이노스케 발견 → 합류
        ),

        TestCase(
            name="TEST-06: 젠이츠 발견 루트",
            description="동료 규합 선택 후 젠이츠 먼저 찾기",
            steps=[
                "시작",
                "동료를 모아야 해요!",
                "젠이츠를 찾을게요",
                "젠이츠! 네즈코가 위험해!"
            ],
            expected_stages=["INTRO", "ROUTE_CHOICE", "RECRUIT"],
            expected_images=["11", "12"]  # 젠이츠 발견 → 합류
        ),

        TestCase(
            name="TEST-07: 이노스케 설득 실패",
            description="이노스케 발견했지만 설득 실패",
            steps=[
                "시작",
                "동료를 규합할게요",
                "이노스케를 찾아요",
                "뭐 하냐 임마"  # 부적절한 설득
            ],
            expected_stages=["INTRO", "ROUTE_CHOICE", "RECRUIT"],
            expected_images=["8"]  # 이노스케 발견만
        ),

        TestCase(
            name="TEST-08: 젠이츠 설득 성공",
            description="젠이츠를 네즈코로 설득",
            steps=[
                "시작",
                "동료가 필요해요",
                "젠이츠를 찾아요",
                "네즈코가 걱정하고 있어. 지금 싸워야 해!"
            ],
            expected_stages=["RECRUIT"],
            expected_images=["11", "12"]
        ),

        TestCase(
            name="TEST-09: 둘 다 규합 성공",
            description="이노스케와 젠이츠 모두 규합",
            steps=[
                "시작",
                "동료들을 모아요",
                "이노스케부터 찾을게요",
                "이노스케! 함께 싸우자!",
                "이제 젠이츠를 찾아요",
                "젠이츠! 네즈코를 위해 싸우자!"
            ],
            expected_stages=["RECRUIT", "RETURN_TO_FRONT"],
            expected_images=["8", "9", "11", "12", "15", "16"]  # 삼인삼색
        ),

        TestCase(
            name="TEST-10: 동료 규합 타임아웃",
            description="동료 찾기 시간 초과",
            steps=[
                "시작",
                "동료를 찾아야죠",
                "어디 있을까요?",
                "찾아보겠습니다",
                "계속 찾아요",
                "아직도 못 찾았어요",
                "시간이 없는데..."
            ],
            expected_stages=["RECRUIT", "END_BAD"],
            expected_images=["14", "18", "19", "20"]  # 실패 엔딩
        ),

        # ==================== INTERVENE/전투 분기 (4개) ====================
        TestCase(
            name="TEST-11: 직접 개입 선택",
            description="동료 대신 직접 싸움 개입",
            steps=[
                "시작",
                "지금 바로 렌고쿠 님을 도울게요!",
                "제가 도와드리겠습니다!"
            ],
            expected_stages=["INTRO", "INTERVENE"],
            expected_images=["4", "6", "7", "10"]  # 나침반 전투 → 격렬한 전투
        ),

        TestCase(
            name="TEST-12: 전투 중 지원",
            description="전투에서 원거리 지원",
            steps=[
                "시작",
                "직접 개입할게요",
                "원거리에서 지원하겠습니다",
                "공격의 틈을 노릴게요"
            ],
            expected_stages=["INTERVENE"],
            expected_images=["6", "7", "10", "17"]  # 전투 → 오의
        ),

        TestCase(
            name="TEST-13: 무모한 돌진",
            description="혼자서 아카자에게 돌진",
            steps=[
                "시작",
                "제가 막겠습니다!",
                "혼자서도 싸울 수 있어요!"
            ],
            expected_stages=["INTRO", "RECKLESS_SACRIFICE"],
            expected_images=["13", "14"]  # 꿰뚫린 복부 → 남겨진 불꽃
        ),

        TestCase(
            name="TEST-14: 렌고쿠 오의 발동",
            description="전투 중 렌고쿠의 최후 오의",
            steps=[
                "시작",
                "개입할게요",
                "계속 싸워요",
                "힘을 내세요!",
                "포기하지 마세요!"
            ],
            expected_stages=["INTERVENE"],
            expected_images=["17"]  # 불꽃의 호흡, 오의: 연옥
        ),

        # ==================== 엔딩 분기 (6개) ====================
        TestCase(
            name="TEST-15: 히든 엔딩 도달",
            description="이노+젠 규합 후 승리",
            steps=[
                "시작",
                "동료를 모아요",
                "이노스케부터",
                "이노스케! 함께!",
                "젠이츠도",
                "젠이츠! 네즈코!",
                "함께 싸워요!",
                "승리하자!"
            ],
            expected_stages=["RETURN_TO_FRONT", "END_HIDDEN"],
            expected_images=["16", "21"]  # 삼인삼색 → 히든 엔딩
        ),

        TestCase(
            name="TEST-16: 기본 엔딩 (패배)",
            description="동료 없이 패배",
            steps=[
                "시작",
                "혼자 싸울게요",
                "계속 공격해요"
            ],
            expected_stages=["RECKLESS_SACRIFICE", "END_BAD"],
            expected_images=["13", "14", "18", "19", "20"]
        ),

        TestCase(
            name="TEST-17: 렌고쿠 희생 엔딩",
            description="렌고쿠가 희생하는 원작 엔딩",
            steps=[
                "시작",
                "직접 도울게요",
                "함께 싸워요",
                "계속 지원해요",
                "끝까지 버텨요"
            ],
            expected_stages=["INTERVENE", "END_BASIC"],
            expected_images=["14", "18", "19", "20"]
        ),

        TestCase(
            name="TEST-18: 빠른 배드 엔딩",
            description="초반 무모한 선택으로 즉시 패배",
            steps=[
                "시작",
                "혼자 돌진!"
            ],
            expected_stages=["RECKLESS_SACRIFICE", "END_BAD"],
            expected_images=["13", "14"]
        ),

        TestCase(
            name="TEST-19: 여명과 눈물 엔딩",
            description="패배 후 슬픈 장면",
            steps=[
                "시작",
                "싸울게요",
                "계속",
                "계속",
                "계속"
            ],
            expected_stages=["INTERVENE", "END_BASIC", "END_BAD"],
            expected_images=["18"]  # 여명, 그리고 패배의 눈물
        ),

        TestCase(
            name="TEST-20: 마음을 불태워라 엔딩",
            description="렌고쿠의 마지막 유언",
            steps=[
                "시작",
                "도와드릴게요",
                "함께 버텨요",
                "포기하지 않아요",
                "계속 싸워요",
                "끝까지"
            ],
            expected_stages=["INTERVENE", "END_BASIC"],
            expected_images=["20"]  # 마음을 불태워라
        ),
    ]

def print_summary(test_cases: List[TestCase]):
    """테스트 결과 요약 출력"""
    print(f"\n\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}📊 종합 테스트 결과{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    passed = sum(1 for t in test_cases if t.passed)
    failed = len(test_cases) - passed

    print(f"총 테스트: {len(test_cases)}개")
    print(f"{Colors.OKGREEN}✅ 성공: {passed}개{Colors.ENDC}")
    print(f"{Colors.FAIL}❌ 실패: {failed}개{Colors.ENDC}")
    print(f"성공률: {(passed/len(test_cases)*100):.1f}%\n")

    # 실패한 테스트 목록
    if failed > 0:
        print(f"{Colors.FAIL}{Colors.BOLD}실패한 테스트:{Colors.ENDC}")
        for test in test_cases:
            if not test.passed:
                print(f"  ❌ {test.name}")
                if test.error:
                    print(f"     오류: {test.error}")
        print()

    # 분기별 커버리지
    print(f"{Colors.BOLD}분기별 커버리지:{Colors.ENDC}")
    all_stages = set()
    for test in test_cases:
        all_stages.update(test.actual_stages)

    expected_stages = [
        "INTRO", "ROUTE_CHOICE", "RECRUIT", "INTERVENE",
        "RECKLESS_SACRIFICE", "RETURN_TO_FRONT",
        "END_HIDDEN", "END_BASIC", "END_BAD"
    ]

    for stage in expected_stages:
        covered = stage in all_stages
        symbol = f"{Colors.OKGREEN}✓{Colors.ENDC}" if covered else f"{Colors.FAIL}✗{Colors.ENDC}"
        print(f"  {symbol} {stage}")

    # 이미지 커버리지
    print(f"\n{Colors.BOLD}이미지 커버리지 (21개 중):{Colors.ENDC}")
    all_images = set()
    for test in test_cases:
        all_images.update(test.actual_images)

    used_images = [img for img in all_images if img not in ["none", "UNKNOWN"]]
    print(f"  사용된 이미지: {len(used_images)}개")
    print(f"  이미지 목록: {', '.join(sorted(used_images, key=lambda x: int(x) if x.isdigit() else 999))}")

def main():
    """메인 실행 함수"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("="*80)
    print("🎬 무한열차 시나리오 종합 분기 테스트")
    print("="*80)
    print(f"{Colors.ENDC}")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"시나리오: {SCENARIO_ID}")
    print(f"API URL: {API_URL}\n")

    # 테스트 케이스 생성
    test_cases = create_test_cases()
    print(f"총 {len(test_cases)}개의 테스트 케이스 생성됨\n")

    # 각 테스트 실행
    for i, test in enumerate(test_cases, 1):
        print(f"\n{Colors.BOLD}[{i}/{len(test_cases)}]{Colors.ENDC}")
        run_test_case(test)
        time.sleep(1)  # 테스트 간 딜레이

    # 결과 요약
    print_summary(test_cases)

    print(f"\n종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

if __name__ == "__main__":
    main()
