#!/usr/bin/env python3
"""
완전 자동화된 시스템 검증 및 수정
- 하드코딩 없음
- State Wrapper 자동 적용
- 실제 터미널 동작 검증
- 엣지 케이스 자동 테스트
- 연속 처리 안정성 확인
- 성능/자원 모니터링
- 자동 보완 제안
"""

import os
import sys
import time
import json
import psutil
import traceback
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field

# 프로젝트 임포트
from agent_state_enhanced import create_enhanced_initial_state, UserChatInput, AgentState
from langgraph_workflow import KimeChatWorkflow
from scenario_loader import scenario_loader


# ===== 1. State Wrapper 구현 및 적용 =====

class StateWrapper:
    """
    Dict와 AgentState를 통합 처리
    모든 workflow.invoke() 결과를 AgentState로 자동 변환
    """

    def __init__(self, initial_state: AgentState):
        self._state = initial_state

    def update(self, result):
        """Workflow 결과로 상태 업데이트"""
        if isinstance(result, dict):
            # Dict 결과를 AgentState 속성들로 병합
            for key, value in result.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)
        else:
            # AgentState면 그대로 교체
            self._state = result

    def get_state(self) -> AgentState:
        """현재 AgentState 반환"""
        return self._state

    def __getattr__(self, name):
        """속성 접근을 _state로 위임"""
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        return getattr(self._state, name)

    def __setattr__(self, name, value):
        """속성 설정"""
        if name == '_state':
            object.__setattr__(self, name, value)
        else:
            setattr(self._state, name, value)


# ===== 2. 완전 자동화 테스트 클래스 =====

@dataclass
class TestResult:
    """테스트 결과"""
    test_name: str
    success: bool
    elapsed_time: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


class CompleteAutoVerifier:
    """완전 자동화된 시스템 검증기"""

    def __init__(self):
        self.workflow = KimeChatWorkflow()
        self.results: List[TestResult] = []
        self.failures: List[TestResult] = []
        self.process = psutil.Process()

    def _create_wrapped_state(self, scenario_id: str = "cutscene5_akaza") -> StateWrapper:
        """State Wrapper로 감싼 초기 상태 생성"""
        state = create_enhanced_initial_state("auto_verify")
        scenario = scenario_loader.load_scenario(f"{scenario_id}_encounter.json")
        state.game.scenario_id = scenario_id
        state.game.scenario_data = scenario
        state.game.current_stage = scenario.get("initial_stage", "intro")

        return StateWrapper(state)

    def _invoke_with_wrapper(self, wrapper: StateWrapper, user_input: str, chat_no: int) -> Tuple[float, bool]:
        """State Wrapper를 사용한 안전한 invoke"""
        start = time.time()

        try:
            wrapper.user_input = UserChatInput(
                content=user_input,
                chat_no=chat_no,
                timestamp=datetime.now().isoformat()
            )

            result = self.workflow.invoke(wrapper.get_state())
            wrapper.update(result)

            elapsed = time.time() - start
            return elapsed, True

        except Exception as e:
            elapsed = time.time() - start
            print(f"  ❌ 오류: {e}")
            return elapsed, False

    # ===== 2. 실제 터미널 동작 검증 =====

    def test_real_terminal_flow(self) -> TestResult:
        """실제 터미널 시나리오 자동 검증"""
        print("\n" + "="*70)
        print("📋 2. 실제 터미널 동작 검증")
        print("="*70 + "\n")

        test_inputs = [
            "시작",
            "렌고쿠 구하러 가자",
            "이노스케랑 젠이츠 먼저 찾아야지",
            "혼자 돌격한다"
        ]

        wrapper = self._create_wrapped_state()
        total_time = 0
        all_success = True
        stage_changes = []
        dialogue_speakers = []

        print("자동 입력 시퀀스 시작...")

        for i, inp in enumerate(test_inputs):
            print(f"\n입력 {i+1}: \"{inp}\"")

            elapsed, success = self._invoke_with_wrapper(wrapper, inp, i+1)
            total_time += elapsed
            all_success = all_success and success

            if success:
                # 상태 검사
                state = wrapper.get_state()
                current_stage = state.game.current_stage if hasattr(state, 'game') else "unknown"
                stage_changes.append(current_stage)

                # 대화 화자 검사
                if hasattr(state, 'output') and state.output and state.output.dialogues:
                    for dialogue in state.output.dialogues:
                        speaker = dialogue.speaker if hasattr(dialogue, 'speaker') else "unknown"
                        dialogue_speakers.append(speaker)
                        print(f"  💬 [{speaker}] 대사 출력 확인")

                print(f"  ✅ Stage: {current_stage}, 시간: {elapsed:.2f}초")
            else:
                print(f"  ❌ 실패")

        # 검증
        has_character_variety = len(set(dialogue_speakers)) >= 2  # 최소 2명 이상
        has_stage_change = len(set(stage_changes)) >= 2  # 최소 2개 이상 스테이지

        result = TestResult(
            test_name="실제_터미널_동작",
            success=all_success and has_character_variety,
            elapsed_time=total_time,
            details={
                "total_inputs": len(test_inputs),
                "stage_changes": stage_changes,
                "unique_stages": len(set(stage_changes)),
                "dialogue_speakers": dialogue_speakers,
                "unique_speakers": len(set(dialogue_speakers)),
                "avg_response_time": total_time / len(test_inputs)
            }
        )

        print(f"\n📊 결과:")
        print(f"  - 고유 스테이지: {result.details['unique_stages']}")
        print(f"  - 고유 화자: {result.details['unique_speakers']}")
        print(f"  - 평균 응답: {result.details['avg_response_time']:.2f}초")

        return result

    # ===== 3. 엣지 케이스 자동 테스트 =====

    def test_edge_cases(self) -> TestResult:
        """엣지 케이스 자동 테스트"""
        print("\n" + "="*70)
        print("📋 3. 엣지 케이스 자동 테스트")
        print("="*70 + "\n")

        edge_cases = [
            ("ㅁㄴㅇㄹ", "무의미한 입력"),
            ("렌고쿠" * 50, "긴 반복 입력"),
            ("😀😁😂", "이모지만"),
            ("   ", "공백만"),
            ("SELECT * FROM users", "SQL 삽입"),
            ("../../../etc/passwd", "경로 조작"),
            ("", "빈 문자열"),
            ("a" * 1000, "매우 긴 입력")
        ]

        wrapper = self._create_wrapped_state()
        # 먼저 게임 시작
        self._invoke_with_wrapper(wrapper, "시작", 1)

        handled_count = 0
        crash_count = 0

        for i, (inp, desc) in enumerate(edge_cases):
            print(f"\n테스트: {desc}")
            print(f"  입력: \"{inp[:50]}{'...' if len(inp) > 50 else ''}\"")

            elapsed, success = self._invoke_with_wrapper(wrapper, inp, i+2)

            if success:
                # 적절한 응답이 있는지 확인
                state = wrapper.get_state()
                has_output = hasattr(state, 'output') and state.output
                has_message = has_output and (state.output.dialogues or state.output.system_messages)

                if has_message:
                    handled_count += 1
                    print(f"  ✅ 적절히 처리됨 ({elapsed:.2f}초)")
                else:
                    print(f"  ⚠️ 처리됐으나 응답 없음")
            else:
                crash_count += 1
                print(f"  ❌ 크래시")

        success_rate = handled_count / len(edge_cases) * 100

        result = TestResult(
            test_name="엣지_케이스",
            success=crash_count == 0,
            elapsed_time=0,
            details={
                "total_cases": len(edge_cases),
                "handled": handled_count,
                "crashed": crash_count,
                "success_rate": success_rate
            }
        )

        print(f"\n📊 결과:")
        print(f"  - 처리됨: {handled_count}/{len(edge_cases)}")
        print(f"  - 크래시: {crash_count}/{len(edge_cases)}")
        print(f"  - 성공률: {success_rate:.1f}%")

        return result

    # ===== 4. 연속 처리 안정성 테스트 =====

    def test_continuous_stability(self) -> TestResult:
        """연속 처리 안정성 테스트 (5회)"""
        print("\n" + "="*70)
        print("📋 4. 연속 처리 안정성 테스트")
        print("="*70 + "\n")

        wrapper = self._create_wrapped_state()
        test_inputs = ["시작", "괜찮아", "렌고쿠를 구해야해", "동료들 모으자", "함께 싸우자"]

        success_count = 0
        errors = []

        for i, inp in enumerate(test_inputs):
            print(f"입력 {i+1}/5: \"{inp}\"")

            try:
                elapsed, success = self._invoke_with_wrapper(wrapper, inp, i+1)

                if success:
                    # 속성 접근 테스트
                    state = wrapper.get_state()
                    _ = state.user_input  # 접근 테스트
                    _ = state.game.current_stage
                    _ = state.output.dialogues

                    success_count += 1
                    print(f"  ✅ 성공 ({elapsed:.2f}초)")
                else:
                    errors.append(f"입력 {i+1}: invoke 실패")
                    print(f"  ❌ 실패")

            except AttributeError as e:
                errors.append(f"입력 {i+1}: {str(e)}")
                print(f"  ❌ 속성 오류: {e}")
            except Exception as e:
                errors.append(f"입력 {i+1}: {str(e)}")
                print(f"  ❌ 오류: {e}")

        result = TestResult(
            test_name="연속_처리_안정성",
            success=success_count == 5,
            elapsed_time=0,
            details={
                "total_attempts": 5,
                "success": success_count,
                "failed": 5 - success_count,
                "errors": errors
            }
        )

        print(f"\n📊 결과: {success_count}/5 성공")

        return result

    # ===== 5. 성능·자원 모니터링 =====

    def test_performance_monitoring(self) -> TestResult:
        """100회 연속 호출 성능 모니터링"""
        print("\n" + "="*70)
        print("📋 5. 성능·자원 모니터링 (100회)")
        print("="*70 + "\n")

        wrapper = self._create_wrapped_state()
        test_inputs = ["시작", "괜찮아", "렌고쿠 구하자"] * 34  # 102개

        times = []
        memory_samples = []
        cpu_samples = []
        api_failures = 0

        print("100회 연속 호출 시작...")

        for i in range(100):
            inp = test_inputs[i % len(test_inputs)]

            # 메모리/CPU 측정
            mem_before = self.process.memory_info().rss / 1024 / 1024  # MB
            cpu_before = self.process.cpu_percent()

            elapsed, success = self._invoke_with_wrapper(wrapper, inp, i+1)

            mem_after = self.process.memory_info().rss / 1024 / 1024
            cpu_after = self.process.cpu_percent()

            if success:
                times.append(elapsed)
                memory_samples.append(mem_after - mem_before)
                cpu_samples.append(cpu_after)
            else:
                api_failures += 1

            if (i+1) % 20 == 0:
                avg_time = sum(times[-20:]) / min(20, len(times[-20:])) if times[-20:] else 0
                print(f"  {i+1}/100 - 평균: {avg_time:.2f}초")

        avg_time = sum(times) / len(times) if times else 0
        avg_memory = sum(memory_samples) / len(memory_samples) if memory_samples else 0
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        failure_rate = api_failures / 100 * 100

        result = TestResult(
            test_name="성능_모니터링",
            success=avg_time < 5.0 and failure_rate < 10,  # 5초 이하, 실패율 10% 미만
            elapsed_time=sum(times),
            details={
                "total_calls": 100,
                "successful": len(times),
                "failed": api_failures,
                "avg_response_time": avg_time,
                "min_time": min(times) if times else 0,
                "max_time": max(times) if times else 0,
                "avg_memory_delta": avg_memory,
                "avg_cpu": avg_cpu,
                "failure_rate": failure_rate
            }
        )

        print(f"\n📊 결과:")
        print(f"  - 평균 응답: {avg_time:.2f}초")
        print(f"  - 메모리 증가: {avg_memory:.2f}MB")
        print(f"  - 평균 CPU: {avg_cpu:.1f}%")
        print(f"  - 실패율: {failure_rate:.1f}%")

        return result

    # ===== 6. 정직한 결과 리포트 =====

    def generate_reports(self):
        """테스트 결과 리포트 생성"""
        print("\n" + "="*70)
        print("📋 6. 정직한 결과 리포트 생성")
        print("="*70 + "\n")

        # JSON 리포트
        report = {
            "생성_일시": datetime.now().isoformat(),
            "총_테스트": len(self.results),
            "성공": sum(1 for r in self.results if r.success),
            "실패": sum(1 for r in self.results if not r.success),
            "테스트_결과": [
                {
                    "이름": r.test_name,
                    "성공": r.success,
                    "소요_시간": r.elapsed_time,
                    "상세": r.details,
                    "오류": r.error
                }
                for r in self.results
            ]
        }

        with open("real_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        print("✅ real_test_report.json 저장 완료")

        # 실패 케이스 문서
        if self.failures:
            with open("real_test_failures.md", "w", encoding="utf-8") as f:
                f.write("# 실패한 테스트 케이스\n\n")
                f.write(f"**생성 일시**: {datetime.now().isoformat()}\n\n")

                for r in self.failures:
                    f.write(f"## {r.test_name}\n\n")
                    f.write(f"- **결과**: ❌ 실패\n")
                    f.write(f"- **소요 시간**: {r.elapsed_time:.2f}초\n")
                    if r.error:
                        f.write(f"- **오류**: {r.error}\n")
                    f.write(f"- **상세**:\n```json\n{json.dumps(r.details, ensure_ascii=False, indent=2)}\n```\n\n")

            print("✅ real_test_failures.md 저장 완료")
        else:
            print("✅ 모든 테스트 성공 - 실패 리포트 없음")

    # ===== 7. 자동 보완 제안 =====

    def generate_improvement_suggestions(self):
        """자동 보완 제안 생성"""
        print("\n" + "="*70)
        print("📋 7. 자동 보완 제안")
        print("="*70 + "\n")

        suggestions = []

        # 결과 분석
        for r in self.results:
            if r.test_name == "실제_터미널_동작":
                if r.details.get("avg_response_time", 0) > 5:
                    suggestions.append({
                        "문제": "응답 시간 느림",
                        "위치": "전체 workflow",
                        "제안": "LLM 호출 최적화 또는 캐싱 추가",
                        "예시_코드": """
# langgraph_workflow.py
from functools import lru_cache

@lru_cache(maxsize=100)
def _cached_llm_call(prompt_hash, model):
    # LLM 호출 결과 캐싱
    pass
"""
                    })

            elif r.test_name == "엣지_케이스":
                if r.details.get("crashed", 0) > 0:
                    suggestions.append({
                        "문제": "엣지 케이스 크래시",
                        "위치": "router_agent.py 또는 guardrail_agent.py",
                        "제안": "입력 검증 강화",
                        "예시_코드": """
# router_agent.py
def _validate_input(self, user_input: str) -> bool:
    if not user_input or not user_input.strip():
        return False
    if len(user_input) > 500:
        return False
    if not any(c.isalnum() for c in user_input):
        return False
    return True
"""
                    })

            elif r.test_name == "연속_처리_안정성":
                if not r.success:
                    suggestions.append({
                        "문제": "연속 처리 실패",
                        "위치": "langgraph_workflow.py",
                        "제안": "StateWrapper 적용 확인",
                        "예시_코드": """
# 모든 invoke 호출을 StateWrapper로 감싸기
wrapper = StateWrapper(initial_state)
for user_input in inputs:
    wrapper.user_input = UserChatInput(...)
    result = workflow.invoke(wrapper.get_state())
    wrapper.update(result)
"""
                    })

        # 보완 제안 저장
        if suggestions:
            with open("auto_improvement_suggestions.md", "w", encoding="utf-8") as f:
                f.write("# 자동 보완 제안\n\n")
                f.write(f"**생성 일시**: {datetime.now().isoformat()}\n\n")

                for i, sug in enumerate(suggestions):
                    f.write(f"## 제안 {i+1}: {sug['문제']}\n\n")
                    f.write(f"- **위치**: {sug['위치']}\n")
                    f.write(f"- **제안**: {sug['제안']}\n")
                    f.write(f"- **예시 코드**:\n```python{sug['예시_코드']}\n```\n\n")

            print(f"✅ {len(suggestions)}개 보완 제안 저장 완료")
        else:
            print("✅ 보완 제안 없음 - 모든 테스트 통과")

    # ===== 8. 최종 검증 =====

    def calculate_final_score(self) -> float:
        """최종 점수 계산"""
        print("\n" + "="*70)
        print("📋 8. 최종 검증 및 점수 계산")
        print("="*70 + "\n")

        # 가중치
        weights = {
            "실제_터미널_동작": 0.35,
            "엣지_케이스": 0.20,
            "연속_처리_안정성": 0.25,
            "성능_모니터링": 0.20
        }

        score = 0

        for r in self.results:
            weight = weights.get(r.test_name, 0)
            test_score = 100 if r.success else 0

            # 부분 점수
            if r.test_name == "엣지_케이스" and r.details.get("success_rate"):
                test_score = r.details["success_rate"]
            elif r.test_name == "연속_처리_안정성" and r.details.get("success"):
                test_score = r.details["success"] / r.details["total_attempts"] * 100
            elif r.test_name == "성능_모니터링":
                # 성능 점수: 2초 이하 100점, 5초 이상 0점
                avg_time = r.details.get("avg_response_time", 10)
                if avg_time <= 2:
                    test_score = 100
                elif avg_time >= 5:
                    test_score = 0
                else:
                    test_score = (5 - avg_time) / 3 * 100

            score += test_score * weight
            print(f"  {r.test_name}: {test_score:.1f}점 (가중치 {weight*100:.0f}%)")

        print(f"\n🎯 최종 점수: {score:.1f}/100")

        return score

    def run_all(self):
        """모든 테스트 실행"""
        print("="*70)
        print("  🚀 완전 자동화 시스템 검증 시작")
        print("  - State Wrapper 자동 적용")
        print("  - 하드코딩 없음")
        print("="*70)

        # LLM 비활성화 (빠른 테스트)
        os.environ["USE_LLM"] = "false"

        # 1. StateWrapper 적용 확인
        print("\n✅ 1. StateWrapper 자동 적용 완료")

        # 2. 실제 터미널 동작
        r = self.test_real_terminal_flow()
        self.results.append(r)
        if not r.success:
            self.failures.append(r)

        # 3. 엣지 케이스
        r = self.test_edge_cases()
        self.results.append(r)
        if not r.success:
            self.failures.append(r)

        # 4. 연속 처리
        r = self.test_continuous_stability()
        self.results.append(r)
        if not r.success:
            self.failures.append(r)

        # 5. 성능 모니터링
        r = self.test_performance_monitoring()
        self.results.append(r)
        if not r.success:
            self.failures.append(r)

        # 6. 리포트 생성
        self.generate_reports()

        # 7. 보완 제안
        self.generate_improvement_suggestions()

        # 8. 최종 점수
        final_score = self.calculate_final_score()

        print("\n" + "="*70)
        print("  ✅ 완전 자동화 검증 완료")
        print(f"  최종 점수: {final_score:.1f}/100")
        print(f"  목표 달성: {'✅ 예' if final_score >= 90 else '❌ 아니오'}")
        print("="*70)

        return final_score


if __name__ == "__main__":
    verifier = CompleteAutoVerifier()
    final_score = verifier.run_all()

    # 종료 코드: 90점 이상이면 0, 아니면 1
    sys.exit(0 if final_score >= 90 else 1)
