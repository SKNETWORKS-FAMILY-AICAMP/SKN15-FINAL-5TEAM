"""
테스트 케이스 생성기 (Blueprint 6)
LLM을 활용하여 창의적이고 다양한 사용자 여정 시뮬레이션 생성
"""
import random
from typing import List, Dict, Optional
from src.utils.llm_client import get_llm_client


# 시나리오 컨텍스트
SCENARIO_CONTEXT = """
당신은 '기메츠노야이바' 세계관의 사용자 여정을 생성하는 AI입니다.

게임 배경:
- 무한열차에서 엔무를 쓰러뜨린 직후
- 상현의 삼 아카자가 등장
- 렌고쿠가 위험에 처함
- 플레이어의 선택에 따라 2가지 엔딩 존재:
  1) 오리지널 엔딩: 혼자 돌진하여 렌고쿠를 구하지 못함
  2) 히든 엔딩: 동료를 설득하여 함께 싸워 렌고쿠를 구함

주요 캐릭터:
- 탄지로 (주인공)
- 이노스케 (멧돼지 머리, 거칠지만 강함)
- 젠이츠 (겁쟁이지만 잠들면 강함)
- 렌고쿠 (염주, 강력한 스승)
"""

JOURNEY_TEMPLATES = {
    "original_ending": [
        "게임 시작",
        "상황 파악하기",
        "혼자서 돌진하는 선택",
        "렌고쿠를 도우려 함",
        "결과 확인"
    ],
    "hidden_ending": [
        "게임 시작",
        "동료들을 돌아봄",
        "이노스케 설득",
        "젠이츠 격려",
        "함께 전투 시작",
        "승리"
    ],
    "exploration": [
        "게임 시작",
        "주변 탐색",
        "캐릭터와 대화",
        "질문하기",
        "선택하기"
    ]
}


def generate_llm_test_cases(iteration: int, count: int = 10, previous_failures: List[Dict] = None) -> List[List[str]]:
    """
    LLM을 사용하여 창의적인 테스트 케이스를 생성합니다.

    Args:
        iteration: 현재 테스트 반복 횟수
        count: 생성할 케이스 수
        previous_failures: 이전에 실패한 케이스 정보

    Returns:
        사용자 입력 시퀀스 리스트
    """
    print(f"[LLM Generator] Generating {count} creative test cases (iteration {iteration})...")

    try:
        client = get_llm_client()
        cases = []

        for i in range(count):
            # LLM에게 요청할 프롬프트 구성
            if previous_failures and iteration > 1:
                # 실패 케이스를 참고하여 변형 생성
                failure_info = random.choice(previous_failures)
                prompt = f"""
{SCENARIO_CONTEXT}

이전 테스트에서 다음 입력 시퀀스가 실패했습니다:
{failure_info.get('case', [])}

이와 유사하지만 약간 다른 창의적인 사용자 입력 시퀀스를 생성해주세요.
5-7개의 자연스러운 사용자 입력을 순서대로 나열하되, JSON 배열 형식으로 반환하세요.

예시 형식:
["시작", "주변을 둘러본다", "동료들에게 말을 건다", "함께 싸우자고 제안한다", "결의를 다진다"]

요구사항:
- 자연스러운 한국어 구어체 사용
- 게임 상황에 맞는 현실적인 입력
- 다양한 감정과 의도 표현 (두려움, 결의, 혼란, 용기 등)
"""
            else:
                # 새로운 케이스 생성
                journey_type = random.choice(list(JOURNEY_TEMPLATES.keys()))
                template = JOURNEY_TEMPLATES[journey_type]

                prompt = f"""
{SCENARIO_CONTEXT}

다음 템플릿을 참고하여 창의적이고 자연스러운 사용자 입력 시퀀스를 생성해주세요:
템플릿: {template}

5-7개의 구체적이고 다양한 사용자 입력을 JSON 배열로 반환하세요.

예시:
["게임 시작해줘", "뭐가 일어나고 있는 거지?", "렌고쿠 형님은 어디 있어?", "이노스케야, 괜찮아?", "우리 같이 싸우자!"]

요구사항:
- 실제 게이머가 입력할 법한 자연스러운 표현
- 짧은 대화체부터 긴 문장까지 다양하게
- 질문, 명령, 감탄사 등 다양한 문장 형태
- 게임 맥락을 이해한 입력
"""

            system_prompt = "당신은 게임 테스트 케이스를 생성하는 전문가입니다. JSON 형식으로만 응답하세요."

            # LLM 호출
            response = client.call_json(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.9  # 높은 창의성
            )

            # 응답에서 케이스 추출
            if isinstance(response, dict):
                # {"inputs": [...]} 형식일 수 있음
                case = response.get("inputs") or response.get("sequence") or response.get("journey")
                if not case and len(response) == 1:
                    # 단일 키를 가진 경우
                    case = list(response.values())[0]
            elif isinstance(response, list):
                case = response
            else:
                case = None

            if case and isinstance(case, list) and len(case) >= 3:
                cases.append(case)
                print(f"  ✓ Case {i+1}/{count}: {len(case)} inputs - {case[0][:30]}...")
            else:
                # LLM 실패시 기본 템플릿 사용
                print(f"  ⚠ Case {i+1}/{count}: LLM 응답 실패, 템플릿 사용")
                cases.append(generate_template_case(journey_type))

        return cases

    except Exception as e:
        print(f"[LLM Generator] Error: {e}, falling back to templates")
        return [generate_template_case(random.choice(list(JOURNEY_TEMPLATES.keys())))
                for _ in range(count)]


def generate_template_case(journey_type: str) -> List[str]:
    """템플릿 기반으로 간단한 케이스 생성 (LLM 폴백용)"""
    templates = {
        "original_ending": [
            "시작",
            "상황을 살핀다",
            "혼자 가겠다",
            "렌고쿠를 돕는다",
            "마무리한다"
        ],
        "hidden_ending": [
            "시작",
            "동료들을 본다",
            "이노스케를 설득한다",
            "젠이츠를 깨운다",
            "함께 싸운다"
        ],
        "exploration": [
            "시작",
            "주변을 둘러본다",
            "이야기를 나눈다",
            "선택한다"
        ]
    }

    base = templates.get(journey_type, templates["exploration"])
    # 약간의 변형 추가
    result = base[:]
    if random.random() > 0.5 and len(result) > 2:
        result.insert(2, "잠깐, 생각해보자")

    return result


def generate_test_cases(iteration: int, previous_failures: List[Dict] = None) -> List[List[str]]:
    """
    테스트 반복 횟수에 따라 30개의 테스트 케이스를 생성합니다.

    Args:
        iteration: 현재 테스트 사이클 번호 (1, 2, 3)
        previous_failures: 이전 사이클에서 실패한 테스트 케이스 목록

    Returns:
        생성된 테스트 케이스 30개
    """
    print(f"\n{'='*70}")
    print(f"테스트 케이스 생성 - Iteration {iteration}")
    print(f"{'='*70}")

    cases = []

    if iteration == 1:
        # 1단계: LLM으로 다양한 케이스 생성
        print(f"[Phase 1] LLM 기반 다양한 케이스 생성")

        # LLM으로 20개 생성
        llm_cases = generate_llm_test_cases(iteration, count=20)
        cases.extend(llm_cases)

        # 템플릿 기반 안전 케이스 10개 추가
        print(f"[Phase 1] 템플릿 기반 안전 케이스 추가")
        for journey_type in ["original_ending", "hidden_ending", "exploration"]:
            for _ in range(3):
                cases.append(generate_template_case(journey_type))

        # 하나 더 추가
        cases.append(generate_template_case("original_ending"))

    elif iteration > 1:
        # 2, 3단계: 실패 케이스 기반 + 새로운 창의적 케이스
        if previous_failures:
            print(f"[Phase {iteration}] 실패 케이스 기반 변형 생성")
            # 실패 케이스 기반으로 15개 생성
            failure_cases = generate_llm_test_cases(
                iteration,
                count=15,
                previous_failures=previous_failures
            )
            cases.extend(failure_cases)
        else:
            print(f"[Phase {iteration}] 이전 실패 없음, 새로운 케이스 생성")

        # 완전히 새로운 창의적 케이스 15개
        print(f"[Phase {iteration}] 새로운 창의적 케이스 생성")
        new_cases = generate_llm_test_cases(iteration, count=15)
        cases.extend(new_cases)

    # 정확히 30개로 맞추기
    cases = cases[:30]
    if len(cases) < 30:
        # 부족하면 템플릿으로 채우기
        while len(cases) < 30:
            cases.append(generate_template_case(random.choice(list(JOURNEY_TEMPLATES.keys()))))

    print(f"\n✓ 총 {len(cases)}개 테스트 케이스 생성 완료")
    print(f"{'='*70}\n")

    return cases


if __name__ == "__main__":
    # 테스트
    print("=== LLM 기반 Test Case Generator 테스트 ===\n")

    cases_1 = generate_test_cases(1)
    print(f"\n생성된 케이스 수: {len(cases_1)}")
    print(f"\n샘플 케이스 #1:")
    for i, inp in enumerate(cases_1[0]):
        print(f"  {i+1}. {inp}")

    print(f"\n샘플 케이스 #15:")
    for i, inp in enumerate(cases_1[14]):
        print(f"  {i+1}. {inp}")
