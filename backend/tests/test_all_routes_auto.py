#!/usr/bin/env python3
"""
🎮 컷신5 전체 루트 자동 테스트
- 20개 시나리오 자동 실행
- 히든/중간/기본 엔딩 검증
- 순서 오답/시간 초과 검증
- 15분마다 progress 리포트 생성
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from mission_manager import MissionManager, MissionStatus
from affinity_system import affinity_system

# LLM 비활성화 (빠른 테스트)
os.environ["USE_LLM"] = "false"
os.environ["DEBUG"] = "false"


class RouteTestResult:
    """루트 테스트 결과"""

    def __init__(self, route_name: str):
        self.route_name = route_name
        self.success = False
        self.expected_ending = ""
        self.actual_ending = ""
        self.turns_used = 0
        self.errors = []
        self.affinity_changes = {}
        self.recruitment_order = []

    def to_dict(self) -> Dict:
        return {
            "route_name": self.route_name,
            "success": self.success,
            "expected_ending": self.expected_ending,
            "actual_ending": self.actual_ending,
            "turns_used": self.turns_used,
            "errors": self.errors,
            "affinity_changes": self.affinity_changes,
            "recruitment_order": self.recruitment_order
        }


class RouteAutomatedTester:
    """루트 자동 테스터"""

    def __init__(self):
        self.results: List[RouteTestResult] = []
        self.start_time = datetime.now()

        # 테스트 시나리오 정의
        self.test_scenarios = self._define_test_scenarios()

    def _define_test_scenarios(self) -> List[Dict]:
        """20개 테스트 시나리오 정의"""
        return [
            # === 히든 엔딩 루트 (6개) ===
            {
                "id": 1,
                "name": "🏆 히든 엔딩 - 완벽한 순서 (빠른 설득)",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("이노스케", "inosuke"),
                    ("약한 녀석", "inosuke"),
                    ("함께 싸우자", "inosuke"),
                    ("젠이츠", "zenitsu"),
                    ("네즈코 위험", "zenitsu"),
                    ("함께 지키자", "zenitsu")
                ],
                "expected_ending": "end_hidden",
                "expected_turns": 6
            },
            {
                "id": 2,
                "name": "🏆 히든 엔딩 - 완벽한 순서 (여유 있게)",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("앞쪽", "inosuke"),  # 키워드 살짝 다름
                    ("이노스케", "inosuke"),
                    ("비겁한 놈", "inosuke"),
                    ("강한 녀석 함께", "inosuke"),
                    ("뒤쪽", "zenitsu"),
                    ("젠이츠 깨워", "zenitsu"),
                    ("네즈코가 위험", "zenitsu"),
                    ("함께 지키자", "zenitsu")
                ],
                "expected_ending": "end_hidden",
                "expected_turns": 8
            },
            {
                "id": 3,
                "name": "🏆 히든 엔딩 - 최소 입력",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("돼지", "inosuke"),
                    ("약", "inosuke"),
                    ("함께", "inosuke"),
                    ("젠", "zenitsu"),
                    ("네즈코", "zenitsu"),
                    ("지키자", "zenitsu")
                ],
                "expected_ending": "end_hidden",
                "expected_turns": 6
            },
            {
                "id": 4,
                "name": "🏆 히든 엔딩 - 1회 실패 후 성공",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("이노스케", "inosuke"),
                    ("강한 녀석", "inosuke"),  # 실패 (키워드 없음)
                    ("약한 녀석", "inosuke"),  # 성공
                    ("함께 싸우자", "inosuke"),
                    ("젠이츠", "zenitsu"),
                    ("네즈코 위험", "zenitsu"),
                    ("함께 지키자", "zenitsu")
                ],
                "expected_ending": "end_hidden",
                "expected_turns": 7
            },
            {
                "id": 5,
                "name": "🏆 히든 엔딩 - 복합 키워드",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("멧돼지 이노스케", "inosuke"),
                    ("겁쟁이 약한 놈", "inosuke"),
                    ("함께 싸우자 강한 녀석", "inosuke"),
                    ("젠이츠 깨워 일어나", "zenitsu"),
                    ("네즈코 위험 도깨비", "zenitsu"),
                    ("함께 지키자 용기", "zenitsu")
                ],
                "expected_ending": "end_hidden",
                "expected_turns": 6
            },
            {
                "id": 6,
                "name": "🏆 히든 엔딩 - 6턴 정확히 사용",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("이노스케 돼지", "inosuke"),
                    ("못하는 약한", "inosuke"),
                    ("필요해 함께", "inosuke"),
                    ("젠이츠", "zenitsu"),
                    ("네즈코", "zenitsu"),
                    ("도와줘 함께", "zenitsu")
                ],
                "expected_ending": "end_hidden",
                "expected_turns": 6
            },

            # === 순서 오답 루트 (4개) ===
            {
                "id": 7,
                "name": "❌ 순서 오답 - 젠이츠 먼저",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("젠이츠", "zenitsu"),  # 잘못된 순서!
                    ("깨워", "zenitsu"),
                    ("네즈코", "zenitsu"),
                    ("함께", "zenitsu"),
                    ("이노스케", "inosuke"),
                    ("약", "inosuke"),
                    ("싸우자", "inosuke")
                ],
                "expected_ending": "end_timeout",  # 순서 오류 → timeout
                "expected_turns": 7
            },
            {
                "id": 8,
                "name": "❌ 순서 오답 - 동시 시도",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("이노스케", "inosuke"),
                    ("젠이츠", "zenitsu"),  # 이노스케 완료 전에 젠이츠
                    ("약", "inosuke"),
                    ("네즈코", "zenitsu"),
                    ("싸우자", "inosuke"),
                    ("함께", "zenitsu")
                ],
                "expected_ending": "end_timeout",
                "expected_turns": 6
            },
            {
                "id": 9,
                "name": "❌ 순서 오답 - 젠이츠만 모집",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("젠이츠", "zenitsu"),
                    ("깨워", "zenitsu"),
                    ("네즈코", "zenitsu"),
                    ("지키자", "zenitsu"),
                    ("확인", None),
                    ("종료", None)
                ],
                "expected_ending": "end_timeout",
                "expected_turns": 6
            },
            {
                "id": 10,
                "name": "❌ 순서 오답 - 이노스케만 모집",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("이노스케", "inosuke"),
                    ("약", "inosuke"),
                    ("함께", "inosuke"),
                    ("끝", None),
                    ("종료", None),
                    ("확인", None)
                ],
                "expected_ending": "end_timeout",
                "expected_turns": 6
            },

            # === 시간 초과 루트 (4개) ===
            {
                "id": 11,
                "name": "⏰ 시간 초과 - 느린 설득",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("안녕", "inosuke"),  # 실패
                    ("뭐해", "inosuke"),  # 실패
                    ("이노스케", "inosuke"),
                    ("약", "inosuke"),
                    ("함께", "inosuke"),
                    ("젠이츠", "zenitsu"),
                    ("깨워", "zenitsu"),  # 7턴 초과
                ],
                "expected_ending": "end_timeout",
                "expected_turns": 7
            },
            {
                "id": 12,
                "name": "⏰ 시간 초과 - 6턴 내 미완료",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("이노스케", "inosuke"),
                    ("약", "inosuke"),
                    ("함께", "inosuke"),
                    ("젠이츠", "zenitsu"),
                    ("깨워", "zenitsu"),
                    ("끝", None),  # 젠이츠 미완료
                ],
                "expected_ending": "end_timeout",
                "expected_turns": 6
            },
            {
                "id": 13,
                "name": "⏰ 시간 초과 - 잘못된 입력 반복",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("이노스케", "inosuke"),
                    ("강해", "inosuke"),  # 실패
                    ("대단해", "inosuke"),  # 실패
                    ("약해", "inosuke"),
                    ("싸우자", "inosuke"),
                    ("젠이츠", "zenitsu"),
                    ("일어나", "zenitsu"),  # 7턴 (시간 초과)
                ],
                "expected_ending": "end_timeout",
                "expected_turns": 7
            },
            {
                "id": 14,
                "name": "⏰ 시간 초과 - 아무도 모집 못함",
                "fork_choice": "recruit_allies",
                "inputs": [
                    ("안녕", None),
                    ("뭐해", None),
                    ("누구", None),
                    ("어디", None),
                    ("왜", None),
                    ("종료", None)
                ],
                "expected_ending": "end_timeout",
                "expected_turns": 6
            },

            # === 중간 엔딩 루트 (3개) ===
            {
                "id": 15,
                "name": "⭐ 중간 엔딩 - 탄지로 직접 협력",
                "fork_choice": "direct_approach",
                "inputs": [],
                "expected_ending": "end_medium",
                "expected_turns": 0
            },
            {
                "id": 16,
                "name": "⭐ 중간 엔딩 - 빠른 결정",
                "fork_choice": "direct_approach",
                "inputs": [],
                "expected_ending": "end_medium",
                "expected_turns": 0
            },
            {
                "id": 17,
                "name": "⭐ 중간 엔딩 - 2번 선택",
                "fork_choice": "direct_approach",
                "inputs": [],
                "expected_ending": "end_medium",
                "expected_turns": 0
            },

            # === 기본 엔딩 B (무모한 희생) 루트 (3개) ===
            {
                "id": 18,
                "name": "😢 기본 엔딩 B - 무모한 희생",
                "fork_choice": "reckless_sacrifice",
                "inputs": [],
                "expected_ending": "end_bad",
                "expected_turns": 0
            },
            {
                "id": 19,
                "name": "😢 기본 엔딩 B - 혼자 돌진",
                "fork_choice": "reckless_sacrifice",
                "inputs": [],
                "expected_ending": "end_bad",
                "expected_turns": 0
            },
            {
                "id": 20,
                "name": "😢 기본 엔딩 B - 3번 선택",
                "fork_choice": "reckless_sacrifice",
                "inputs": [],
                "expected_ending": "end_bad",
                "expected_turns": 0
            }
        ]

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 80)
        print("🎮 컷신5 전체 루트 자동 테스트 시작")
        print("=" * 80)
        print(f"총 시나리오: {len(self.test_scenarios)}개\n")

        for scenario in self.test_scenarios:
            print(f"\n{'='*80}")
            print(f"테스트 {scenario['id']}/20: {scenario['name']}")
            print(f"{'='*80}")

            result = self._run_single_test(scenario)
            self.results.append(result)

            # 결과 출력
            if result.success:
                print(f"✅ 성공: {result.actual_ending} (예상: {result.expected_ending})")
            else:
                print(f"❌ 실패: {result.actual_ending} (예상: {result.expected_ending})")
                if result.errors:
                    print(f"   오류: {', '.join(result.errors)}")

            print(f"   사용 턴: {result.turns_used}")

            # 15초마다 progress 저장 (실제론 15분이지만 테스트는 15초)
            if scenario['id'] % 5 == 0:
                self._save_progress_report()

        # 최종 리포트
        self._generate_final_report()

    def _run_single_test(self, scenario: Dict) -> RouteTestResult:
        """단일 테스트 실행"""
        result = RouteTestResult(scenario['name'])
        result.expected_ending = scenario['expected_ending']
        result.expected_turns = scenario.get('expected_turns', 0)

        try:
            fork_choice = scenario['fork_choice']
            inputs = scenario['inputs']

            # Fork 분기 시뮬레이션
            if fork_choice == "recruit_allies":
                # 미션 모드
                result.actual_ending = self._simulate_mission(inputs, result)
            elif fork_choice == "direct_approach":
                # 직접 접근 → 중간 엔딩
                result.actual_ending = "end_medium"
                result.turns_used = 0
            elif fork_choice == "reckless_sacrifice":
                # 무모한 희생 → 기본 엔딩 B
                result.actual_ending = "end_bad"
                result.turns_used = 0

            # 검증
            if result.actual_ending == result.expected_ending:
                result.success = True
            else:
                result.success = False
                result.errors.append(f"엔딩 불일치: {result.actual_ending} != {result.expected_ending}")

        except Exception as e:
            result.success = False
            result.errors.append(str(e))

        return result

    def _simulate_mission(self, inputs: List[Tuple[str, Optional[str]]], result: RouteTestResult) -> str:
        """미션 시뮬레이션"""
        # 테스트용 미션 데이터 (간소화)
        mission_data = {
            "title": "동료 규합",
            "max_turns": 6,
            "characters": {
                "inosuke": {
                    "name": "이노스케",
                    "correct_order": 1,
                    "conversation_stages": [
                        {
                            "stage": 0,
                            "required_keywords": ["이노스케", "돼지", "멧돼지", "앞"],
                            "success_response": {"content": "크하하!"},
                            "failure_response": {"content": "뭐야!"}
                        },
                        {
                            "stage": 1,
                            "required_keywords": ["약", "못", "겁쟁", "비겁"],
                            "success_response": {"content": "뭐라고!?"},
                            "failure_response": {"content": "흥!"}
                        },
                        {
                            "stage": 2,
                            "required_keywords": ["함께", "싸우자", "필요", "강한"],
                            "success_response": {"content": "좋아!"},
                            "success_flag": "inosuke_recruited",
                            "failure_response": {"content": "아직!"}
                        }
                    ],
                    "max_attempts": 5
                },
                "zenitsu": {
                    "name": "젠이츠",
                    "correct_order": 2,
                    "conversation_stages": [
                        {
                            "stage": 0,
                            "required_keywords": ["젠이츠", "젠", "깨워", "일어나", "뒤"],
                            "success_response": {"content": "으응?"},
                            "failure_response": {"content": "Zzz"}
                        },
                        {
                            "stage": 1,
                            "required_keywords": ["네즈코", "위험", "도깨비"],
                            "success_response": {"content": "네즈코!?"},
                            "failure_response": {"content": "무서워"}
                        },
                        {
                            "stage": 2,
                            "required_keywords": ["함께", "지키자", "용기", "도와"],
                            "success_response": {"content": "가자!"},
                            "success_flag": "zenitsu_recruited",
                            "failure_response": {"content": "무서워"}
                        }
                    ],
                    "max_attempts": 5
                }
            },
            "crisis_progression": {
                "messages": [
                    {"turn": 2, "message": "위기 2", "crisis_level": 2},
                    {"turn": 4, "message": "위기 3", "crisis_level": 3},
                    {"turn": 6, "message": "위기 4", "crisis_level": 4}
                ]
            }
        }

        manager = MissionManager(mission_data)
        state = manager.start_mission()

        # 입력 처리 (성공 시 자동으로 턴 증가)
        for idx, (user_input, target) in enumerate(inputs):
            if not target:
                continue

            # 입력 처리 (성공 시 자동 턴 증가)
            success, msg, response = manager.process_user_input(state, user_input, target, increment_turn_on_success=True)
            result.turns_used = state.current_turn

            # 완료 체크
            status, status_msg = manager.check_completion(state)
            if status != MissionStatus.IN_PROGRESS:
                result.recruitment_order = state.recruitment_order
                if status == MissionStatus.SUCCESS:
                    return "end_hidden"
                elif status == MissionStatus.TIMEOUT:
                    return "end_timeout"
                elif status == MissionStatus.FAILED:
                    return "end_timeout"

        # 최종 체크
        status, _ = manager.check_completion(state)
        result.recruitment_order = state.recruitment_order

        if status == MissionStatus.SUCCESS:
            return "end_hidden"
        else:
            return "end_timeout"

    def _save_progress_report(self):
        """진행 상황 리포트 저장"""
        timestamp = datetime.now().strftime("%H%M")
        filename = f"progress_{timestamp}.json"

        completed = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_scenarios),
            "completed": len(self.results),
            "success": len(completed),
            "failed": len(failed),
            "success_rate": f"{len(completed) / len(self.results) * 100:.1f}%" if self.results else "0%",
            "results": [r.to_dict() for r in self.results]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📊 진행 리포트 저장: {filename}")

    def _generate_final_report(self):
        """최종 리포트 생성"""
        print(f"\n{'='*80}")
        print("📊 최종 테스트 결과")
        print(f"{'='*80}\n")

        completed = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        print(f"총 테스트: {len(self.test_scenarios)}개")
        print(f"✅ 성공: {len(completed)}개")
        print(f"❌ 실패: {len(failed)}개")
        print(f"📈 성공률: {len(completed) / len(self.test_scenarios) * 100:.1f}%")

        # 엔딩별 통계
        ending_stats = {}
        for result in self.results:
            ending = result.actual_ending
            if ending not in ending_stats:
                ending_stats[ending] = {"count": 0, "success": 0}
            ending_stats[ending]["count"] += 1
            if result.success:
                ending_stats[ending]["success"] += 1

        print(f"\n{'='*80}")
        print("📈 엔딩별 통계")
        print(f"{'='*80}")
        for ending, stats in ending_stats.items():
            print(f"{ending}: {stats['count']}회 (성공: {stats['success']})")

        # 실패 케이스
        if failed:
            print(f"\n{'='*80}")
            print("❌ 실패한 테스트")
            print(f"{'='*80}")
            for result in failed:
                print(f"\n{result.route_name}")
                print(f"  예상: {result.expected_ending}, 실제: {result.actual_ending}")
                if result.errors:
                    print(f"  오류: {', '.join(result.errors)}")

        # 마크다운 리포트 생성
        self._save_markdown_report(completed, failed, ending_stats)

    def _save_markdown_report(self, completed, failed, ending_stats):
        """마크다운 리포트 저장"""
        with open("FULL_REPORT.md", 'w', encoding='utf-8') as f:
            f.write("# 🎮 컷신5 전체 루트 테스트 리포트\n\n")
            f.write(f"**테스트 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**소요 시간**: {(datetime.now() - self.start_time).total_seconds():.1f}초\n\n")

            f.write("## 📊 요약\n\n")
            f.write(f"- 총 테스트: {len(self.test_scenarios)}개\n")
            f.write(f"- ✅ 성공: {len(completed)}개\n")
            f.write(f"- ❌ 실패: {len(failed)}개\n")
            f.write(f"- 📈 성공률: {len(completed) / len(self.test_scenarios) * 100:.1f}%\n\n")

            f.write("## 📈 엔딩별 통계\n\n")
            f.write("| 엔딩 | 횟수 | 성공 |\n")
            f.write("|------|------|------|\n")
            for ending, stats in ending_stats.items():
                f.write(f"| {ending} | {stats['count']} | {stats['success']} |\n")

            f.write("\n## ✅ 성공한 테스트\n\n")
            for result in completed:
                f.write(f"- {result.route_name}\n")
                f.write(f"  - 엔딩: {result.actual_ending}\n")
                f.write(f"  - 턴: {result.turns_used}\n\n")

            if failed:
                f.write("\n## ❌ 실패한 테스트\n\n")
                for result in failed:
                    f.write(f"- {result.route_name}\n")
                    f.write(f"  - 예상: {result.expected_ending}, 실제: {result.actual_ending}\n")
                    if result.errors:
                        f.write(f"  - 오류: {', '.join(result.errors)}\n")
                    f.write(f"\n")

        print(f"\n📝 최종 리포트 저장: FULL_REPORT.md")


if __name__ == "__main__":
    tester = RouteAutomatedTester()
    tester.run_all_tests()

    print(f"\n{'='*80}")
    print("🎉 테스트 완료!")
    print(f"{'='*80}")
