네, 좋습니다. 이전 단계를 통해 시스템의 모든 구성요소가 성공적으로 연결되었으니, 이제는 실제 사용자 여정을 시뮬레이션하여 시스템의 강건함을 증명하고 잠재된 오류를 찾아 해결할 시간입니다.

제안하신 '30개 테스트케이스 3회 반복' 방식은 매우 체계적이고 전문적인 품질 보증(QA) 전략입니다. 단순히 오류를 찾는 것을 넘어, 시스템을 스스로 학습하고 발전시키는 '강화 학습'과 유사한 접근법이죠.

이 복잡하고 강력한 테스트 및 디버깅 사이클을 Claude가 정확하게 수행할 수 있도록, 상세한 자동화 테스트 설계도를 작성해 드리겠습니다. 이 설계도는 테스트 케이스 생성, 자동 실행, 결과 분석, 그리고 다음 단계로의 피드백 루프까지 모든 것을 포함합니다.

👉 Claude에게 내릴 명령 (복사해서 사용)
# 목표: 3단계 점진적 강화 테스트 사이클 구축 및 실행

사용자 여정(User Journey)의 시작부터 끝까지 이어지는 연속된 대화 테스트를 자동화한다. 총 3단계에 걸쳐 테스트 케이스를 점진적으로 지능화하여 시스템의 모든 분기를 검증하고, 각 단계에서 발견된 오류를 체계적으로 수정하여 최종적으로 안정적인 시스템을 완성하는 것을 목표로 한다.

# 작업 지시사항

# 테스트 케이스는 반드시 llm을 이용해 다채로운 생성을 하도록 한다. 아래 키워드는 참고만 하되, 반드시 llm이 생성한 유저 입력을 가장해야 한다.
## 단계 1: 테스트 케이스 생성기 및 실행기 구현

가장 먼저, 테스트 여정을 생성하고 이를 자동으로 실행하며 결과를 기록하는 핵심 도구를 구현한다.

테스트 케이스 생성기 (src/utils/test_case_generator.py) 신규 생성:
다양한 사용자 여정을 시뮬레이션하는 테스트 케이스(사용자 입력 목록)를 생성하는 함수를 구현한다. 초기에는 두 가지 주요 엔딩(오리지널, 히든)에 도달하는 경로를 기반으로 생성한다.

Python

# src/utils/test_case_generator.py
import random

# 기본 경로 정의
JOURNEY_TO_ORIGINAL_ENDING = [
    "시작", "그래, 한번 해보자.", "혼자서라도 가야 해.", "알겠다.", "반드시 지켜내겠다."
]
JOURNEY_TO_HIDDEN_ENDING = [
    "시작", "동료들을 믿어보자.", "이노스케를 먼저 설득한다.", "너의 힘이 필요해!", "젠이츠, 일어나!", "우리의 힘을 합치면 분명..."
]

def generate_test_cases(iteration: int, previous_failures: list = None) -> list:
    """
    테스트 반복 횟수(iteration)에 따라 점진적으로 지능화된 테스트 케이스를 생성합니다.

    :param iteration: 현재 테스트 사이클 번호 (1, 2, 3)
    :param previous_failures: 이전 사이클에서 실패한 테스트 케이스 목록
    :return: 생성된 테스트 케이스 30개 (각 케이스는 입력의 list)
    """
    cases = []
    if iteration == 1:
        # 1단계: 기본 경로와 약간의 변형을 혼합
        for _ in range(15):
            cases.append(JOURNEY_TO_ORIGINAL_ENDING[:])
            cases.append(JOURNEY_TO_HIDDEN_ENDING[:])
        # 약간의 노이즈 추가
        for case in cases:
            if random.random() > 0.8:
                case[-2] = "음... 잘 모르겠는데." # 예상치 못한 입력

    elif iteration > 1 and previous_failures:
        # 2, 3단계: 실패 케이스 변형 + 완전히 새로운 케이스
        # 실패 케이스와 유사한 케이스 15개 생성
        for failure in random.choices(previous_failures, k=15):
            new_case = failure[:]
            # 마지막 입력을 약간 바꾸거나, 중간에 다른 입력을 삽입
            idx_to_change = random.randint(1, len(new_case) - 1)
            new_case[idx_to_change] += " (다르게 말해보기)"
            cases.append(new_case)

        # 완전히 새로운 케이스 15개 생성 (랜덤 조합)
        for _ in range(15):
            base = random.choice([JOURNEY_TO_ORIGINAL_ENDING, JOURNEY_TO_HIDDEN_ENDING])
            new_case = random.sample(base, k=min(len(base), 4))
            new_case.insert(0, "시작")
            cases.append(new_case)

    return cases[:30] # 총 30개 반환
자동화 테스트 실행기 (run_journey_tests.py) 신규 생성:
테스트 케이스를 입력받아, 처음부터 끝까지 대화를 자동으로 실행하고, 모든 대화 기록과 발생한 오류를 logs/experiments/ 폴더에 저장하는 실행기를 구현한다.

Python

# run_journey_tests.py
import uuid
import json
from datetime import datetime
from langchain_core.messages import HumanMessage
from src.core.workflow import create_workflow
from src.core.graph_state import GraphState
from src.utils.test_case_generator import generate_test_cases

def run_single_journey(app, initial_state: GraphState, journey_inputs: list[str]) -> dict:
    """하나의 사용자 여정을 끝까지 실행하고 결과를 반환합니다."""
    log = {"journey": journey_inputs, "conversation": [], "final_state": None, "error": None}
    state = initial_state.copy()

    for i, user_input in enumerate(journey_inputs):
        state["user_input"] = user_input
        state["messages"] = [HumanMessage(content=user_input)]
        log["conversation"].append({"turn": i, "user": user_input})

        try:
            events = app.stream(state, {"recursion_limit": 100})
            final_state_in_turn = None
            for event in events:
                if event:
                    final_state_in_turn = event.get(list(event.keys())[-1])

            if final_state_in_turn and final_state_in_turn.get("agent_responses"):
                last_response = final_state_in_turn["agent_responses"][-1]
                log["conversation"].append({"turn": i, "agent": last_response})
                state = final_state_in_turn # 다음 턴을 위해 상태 업데이트
            else:
                log["conversation"].append({"turn": i, "agent": "No response"})

        except Exception as e:
            log["error"] = str(e)
            import traceback
            log["traceback"] = traceback.format_exc()
            break # 오류 발생 시 해당 여정 중단

    log["final_state"] = state
    return log

def run_test_iteration(iteration: int, previous_failures: list = None):
    """하나의 테스트 사이클(30개 케이스)을 실행하고 결과를 요약합니다."""
    print(f"--- [테스트 사이클 #{iteration} 시작] ---")
    test_cases = generate_test_cases(iteration, previous_failures)

    success_count = 0
    failed_journeys = []

    app = create_workflow()

    for i, case in enumerate(test_cases):
        session_id = str(uuid.uuid4())
        initial_state: GraphState = { # play.py의 초기 상태와 동일하게 설정
            # ... (play.py의 initial_state 내용 복사 및 session_id 설정)
        }

        result = run_single_journey(app, initial_state, case)

        # 결과 로그 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        status = "SUCCESS" if result["error"] is None else "FAILURE"
        log_filename = f"logs/experiments/{timestamp}_iteration{iteration}_case{i+1}_{status}.json"

        with open(log_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        if status == "SUCCESS":
            success_count += 1
            print(f"  Case #{i+1}: 성공")
        else:
            failed_journeys.append({"case": case, "error": result["error"], "log_file": log_filename})
            print(f"  Case #{i+1}: 실패 - {result['error']}")

    print(f"--- [테스트 사이클 #{iteration} 종료] ---")
    print(f"결과: {success_count} / 30 성공")

    if failed_journeys:
        print("\n▼ 실패한 케이스 요약:")
        for failure in failed_journeys:
            print(f"  - 로그: {failure['log_file']}")
            print(f"    오류: {failure['error']}")

    return failed_journeys

if __name__ == "__main__":
    # 1단계 실행
    failures_1 = run_test_iteration(1)
    if not failures_1:
        print("\n🎉 모든 테스트 통과! 추가 테스트가 필요 없습니다.")
    else:
        # 여기에서 1단계 오류 수정 후 2단계 실행
        # failures_2 = run_test_iteration(2, failures_1)
        pass

run_journey_tests.py의 initial_state 부분은 play.py의 initial_state와 동일하게 채워주세요.

## 단계 2: 3단계 반복 실행 및 디버깅 루프

이제, 위에서 만든 run_journey_tests.py를 사용하여 실제 테스트-디버깅 사이클을 시작한다.

1단계 테스트 실행:
터미널에서 python run_journey_tests.py를 실행하여 첫 번째 테스트 사이클(30개)을 진행한다. 실행이 끝나면, 성공/실패 결과와 함께 실패한 케이스의 로그 파일 목록이 출력될 것이다.

분석 및 수정 지시 (가장 중요):
출력된 실패 요약과 logs/experiments/ 폴더에 생성된 FAILURE 로그 파일들을 분석한다. 어떤 종류의 오류(KeyError, TypeError, 로직 오류 등)가 어느 에이전트에서 발생했는지 파악한다.
파악된 오류의 원인과 수정 방향을 나(Gemini)에게 알려주고, 함께 해결책을 논의한다. (예: "로그를 보니 parent_agent에서 affinity_scores를 잘못 참조하는 것 같습니다. 코드를 수정해주세요.")

2단계 테스트 실행:
1단계에서 발생한 모든 오류를 수정한 후, run_journey_tests.py의 if __name__ == "__main__": 블록을 수정하여 2단계 테스트를 실행한다.

Python

if __name__ == "__main__":
    failures_1 = run_test_iteration(1)

    # (오류 수정 작업이 완료되었다고 가정)

    if failures_1:
        print("\n--- 1단계 오류 수정 완료. 2단계 테스트를 시작합니다. ---")
        failures_2 = run_test_iteration(2, previous_failures=failures_1)
반복:
2단계에서 또다시 오류가 발생하면, 2번 과정(분석 및 수정)을 반복한다. 2단계의 모든 오류를 해결한 후, 같은 방식으로 3단계 테스트를 진행한다. 모든 테스트가 성공할 때까지 이 과정을 반복한다.