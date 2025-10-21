#!/usr/bin/env python3
"""
백엔드 로직 종합 검증 스크립트
- 50회 워크플로우 반복 테스트
- 분기 엣지케이스 검증
- 전체 유닛 테스트 실행
- 커버리지 리포트 생성
"""
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path

# 환경변수 설정
os.environ["USE_LLM"] = "false"
os.environ["DEBUG"] = "false"


class BackendVerification:
    """백엔드 검증 실행기"""

    def __init__(self):
        self.results = {
            "workflow_iterations": {"passed": 0, "failed": 0, "errors": []},
            "branching_edge_cases": {"passed": 0, "failed": 0, "errors": []},
            "unit_tests": {"passed": 0, "failed": 0, "total": 0},
            "coverage": {"percentage": 0, "target": 90}
        }
        self.start_time = datetime.now()

    def print_header(self, title):
        """섹션 헤더 출력"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")

    def run_workflow_iterations(self, iterations=50):
        """워크플로우 50회 반복 테스트"""
        self.print_header(f"1️⃣ 워크플로우 경계 반복 테스트 ({iterations}회)")

        from agent_state_enhanced import create_enhanced_initial_state, UserChatInput
        from langgraph_workflow import KimeChatWorkflow
        from scenario_loader import scenario_loader
        from datetime import datetime as dt

        workflow = KimeChatWorkflow()
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")

        for i in range(iterations):
            try:
                # 새로운 상태 생성
                state = create_enhanced_initial_state(f"iteration_{i}")
                state.game.scenario_data = scenario
                state.game.current_stage = "intro"

                user_input = UserChatInput(
                    content="다음",
                    chat_no=1,
                    timestamp=dt.now().isoformat()
                )

                # dict로 변환
                state_dict = {
                    "session_id": state.meta.session_id,
                    "user_input": {
                        "content": user_input.content,
                        "chat_no": user_input.chat_no,
                        "timestamp": user_input.timestamp
                    },
                    "game": {
                        "scenario_id": state.game.scenario_id,
                        "scenario_data": state.game.scenario_data,
                        "current_stage": state.game.current_stage,
                        "turn": state.game.turn,
                        "flags": state.game.flags if isinstance(state.game.flags, list) else list(state.game.flags),
                        "temp_data": state.game.temp_data
                    },
                    "characters": {
                        "available_characters": state.characters.available_characters,
                        "affinity": state.characters.affinity
                    },
                    "output": {
                        "dialogues": [],
                        "choices": [],
                        "system_messages": []
                    },
                    "meta": {
                        "processed_by": state.meta.processed_by,
                        "timestamp": state.meta.timestamp
                    },
                    "next_node": state.next_node
                }

                result = workflow.invoke(state_dict)

                if result and "game" in result:
                    self.results["workflow_iterations"]["passed"] += 1
                    if (i + 1) % 10 == 0:
                        print(f"  ✅ {i + 1}/{iterations} iterations completed")
                else:
                    raise Exception("Invalid workflow result")

            except Exception as e:
                self.results["workflow_iterations"]["failed"] += 1
                self.results["workflow_iterations"]["errors"].append(f"Iteration {i}: {str(e)}")
                print(f"  ❌ Failed at iteration {i + 1}: {str(e)}")
                if self.results["workflow_iterations"]["failed"] > 5:
                    print(f"  ⚠️ Too many failures, stopping workflow test")
                    break

        total = self.results["workflow_iterations"]["passed"] + self.results["workflow_iterations"]["failed"]
        success_rate = (self.results["workflow_iterations"]["passed"] / total * 100) if total > 0 else 0
        print(f"\n  📊 워크플로우 테스트: {self.results['workflow_iterations']['passed']}/{total} ({success_rate:.1f}%)")

    def run_branching_edge_cases(self):
        """분기 엣지케이스 테스트"""
        self.print_header("2️⃣ 분기 엣지케이스 검증")

        from parent_agent_enhanced import ParentAgent
        from agent_state_enhanced import create_enhanced_initial_state, UserChatInput
        from scenario_loader import scenario_loader
        from datetime import datetime as dt

        agent = ParentAgent(use_llm=False)
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")

        # 테스트할 잘못된 입력들
        invalid_choices = [
            ("빈 문자열", ""),
            ("공백만", "   "),
            ("범위 밖 숫자", "99"),
            ("음수", "-1"),
            ("잘못된 텍스트", "INVALID_CHOICE"),
        ]

        for test_name, choice_input in invalid_choices:
            try:
                state = create_enhanced_initial_state("test")
                state.game.scenario_data = scenario
                state.game.current_stage = "fork"

                state.user_input = UserChatInput(
                    content=choice_input,
                    chat_no=1,
                    timestamp=dt.now().isoformat()
                )

                result = agent.process(state)

                # 잘못된 입력은 스테이지 변경 없이 처리되어야 함
                if result.game.current_stage == "fork" or len(result.output.system_messages) > 0:
                    self.results["branching_edge_cases"]["passed"] += 1
                    print(f"  ✅ {test_name}: 올바르게 처리됨")
                else:
                    self.results["branching_edge_cases"]["failed"] += 1
                    print(f"  ❌ {test_name}: 예상치 못한 전환 발생")

            except Exception as e:
                self.results["branching_edge_cases"]["errors"].append(f"{test_name}: {str(e)}")
                print(f"  ⚠️ {test_name}: {str(e)}")

        total = self.results["branching_edge_cases"]["passed"] + self.results["branching_edge_cases"]["failed"]
        print(f"\n  📊 분기 테스트: {self.results['branching_edge_cases']['passed']}/{total} 통과")

    def run_unit_tests(self):
        """전체 유닛 테스트 실행"""
        self.print_header("3️⃣ 유닛 테스트 실행")

        test_files = [
            "tests/test_turn_system.py",
            "tests/test_affinity.py",
            "tests/test_process_depth.py",
            "tests/test_affinity_edge_cases.py",
        ]

        print(f"  실행할 테스트 파일:")
        for f in test_files:
            print(f"    - {f}")
        print()

        result = subprocess.run(
            ["python", "-m", "pytest"] + test_files + ["-v", "--tb=short", "-q"],
            capture_output=True,
            text=True
        )

        # 결과 파싱
        output = result.stdout + result.stderr
        print(output)

        # 통과/실패 카운트 추출
        if "passed" in output:
            for line in output.split("\n"):
                if "passed" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "passed" in part:
                            try:
                                self.results["unit_tests"]["passed"] = int(parts[i-1])
                            except:
                                pass
                        if "failed" in part:
                            try:
                                self.results["unit_tests"]["failed"] = int(parts[i-1])
                            except:
                                pass

        self.results["unit_tests"]["total"] = self.results["unit_tests"]["passed"] + self.results["unit_tests"]["failed"]

        return result.returncode == 0

    def run_coverage_report(self):
        """커버리지 리포트 생성"""
        self.print_header("4️⃣ 커버리지 리포트")

        test_files = [
            "tests/test_turn_system.py",
            "tests/test_affinity.py",
            "tests/test_process_depth.py",
            "tests/test_affinity_edge_cases.py",
        ]

        print("  커버리지 측정 중...")
        result = subprocess.run(
            ["python", "-m", "pytest"] + test_files +
            ["--cov=affinity_system", "--cov=mission_manager", "--cov=agent_state_enhanced",
             "--cov-report=term", "--cov-report=html", "-q"],
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr
        print(output)

        # 커버리지 파싱
        for line in output.split("\n"):
            if "TOTAL" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        try:
                            self.results["coverage"]["percentage"] = int(part.replace("%", ""))
                        except:
                            pass

        cov_pct = self.results["coverage"]["percentage"]
        target = self.results["coverage"]["target"]

        print(f"\n  📊 전체 커버리지: {cov_pct}%")
        if cov_pct >= target:
            print(f"  ✅ 목표 달성! (≥{target}%)")
        else:
            print(f"  ⚠️ 목표 미달 (목표: {target}%, 현재: {cov_pct}%)")

    def generate_final_report(self):
        """최종 리포트 생성"""
        self.print_header("📋 최종 검증 리포트")

        elapsed = (datetime.now() - self.start_time).total_seconds()

        print(f"  실행 시간: {elapsed:.2f}초\n")

        print(f"  1️⃣ 워크플로우 반복 테스트:")
        print(f"     - 통과: {self.results['workflow_iterations']['passed']}")
        print(f"     - 실패: {self.results['workflow_iterations']['failed']}")

        print(f"\n  2️⃣ 분기 엣지케이스:")
        print(f"     - 통과: {self.results['branching_edge_cases']['passed']}")
        print(f"     - 실패: {self.results['branching_edge_cases']['failed']}")

        print(f"\n  3️⃣ 유닛 테스트:")
        print(f"     - 통과: {self.results['unit_tests']['passed']}")
        print(f"     - 실패: {self.results['unit_tests']['failed']}")
        print(f"     - 전체: {self.results['unit_tests']['total']}")

        print(f"\n  4️⃣ 커버리지:")
        print(f"     - 현재: {self.results['coverage']['percentage']}%")
        print(f"     - 목표: {self.results['coverage']['target']}%")

        # 전체 성공 여부
        all_passed = (
            self.results['workflow_iterations']['failed'] == 0 and
            self.results['branching_edge_cases']['failed'] == 0 and
            self.results['unit_tests']['failed'] == 0
        )

        print(f"\n{'='*70}")
        if all_passed:
            print("  🚀 ALL BACKEND TESTS PASS!")
        else:
            print("  ⚠️ 일부 테스트 실패 (상세 내용 확인 필요)")
        print(f"{'='*70}\n")

        # 리포트 파일 저장
        report_path = Path("results") / f"backend_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"백엔드 로직 검증 리포트\n")
            f.write(f"생성 시간: {datetime.now().isoformat()}\n")
            f.write(f"실행 시간: {elapsed:.2f}초\n\n")
            f.write(f"워크플로우: {self.results['workflow_iterations']}\n")
            f.write(f"분기: {self.results['branching_edge_cases']}\n")
            f.write(f"유닛 테스트: {self.results['unit_tests']}\n")
            f.write(f"커버리지: {self.results['coverage']}\n")

        print(f"  📁 리포트 저장: {report_path}")

        return all_passed


def main():
    """메인 실행 함수"""
    verifier = BackendVerification()

    try:
        # 1. 워크플로우 반복 테스트
        verifier.run_workflow_iterations(iterations=50)

        # 2. 분기 엣지케이스
        verifier.run_branching_edge_cases()

        # 3. 유닛 테스트
        tests_passed = verifier.run_unit_tests()

        # 4. 커버리지
        verifier.run_coverage_report()

        # 5. 최종 리포트
        all_passed = verifier.generate_final_report()

        # 종료 코드
        sys.exit(0 if all_passed else 1)

    except Exception as e:
        print(f"\n❌ 검증 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
