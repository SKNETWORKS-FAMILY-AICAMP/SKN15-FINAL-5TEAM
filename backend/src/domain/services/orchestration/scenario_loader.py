"""
시나리오 로더 개요
- 시나리오 JSON 파일을 로드하고 구조를 검증
- 스테이지 유형(cutscene, choice, mission, branch 등)을 파싱
- 후속 스테이지 정보를 기반으로 분기 흐름을 결정
- 잘못된 데이터는 검증 단계에서 차단
"""

# ============================================================
# 📚 시나리오 로더 — 제이슨 스테이지 파싱 도구
# ============================================================
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ScenarioStage:
    """시나리오 스테이지 구조"""
    stage_id: str
    stage_type: str  # "cutscene", "choice", "mission", "branch"
    data: Dict[str, Any]
    next_stage: Optional[str] = None


class ScenarioLoader:
    def __init__(self, scenarios_path: str = "data/scenarios/"):
        """Scenario Loader 초기화"""
        self.scenarios_path = scenarios_path
        self.loaded_scenarios = {}  # 캐시용

    def load_scenario(self, scenario_file: str) -> Optional[Dict[str, Any]]:
        """
        시나리오 JSON 파일 로드

        Args:
            scenario_file: 파일명 (예: "example_scene.json")

        Returns:
            로드된 시나리오 전체 데이터
        """
        # 캐시 확인
        if scenario_file in self.loaded_scenarios:
            print(f"✅ 캐시에서 시나리오 로드: {scenario_file}")
            return self.loaded_scenarios[scenario_file]

        # 파일 경로 구성 (확장자가 없으면 .json 자동 추가)
        _, ext = os.path.splitext(scenario_file)
        if not ext:
            scenario_file = f"{scenario_file}.json"

        file_path = os.path.join(self.scenarios_path, scenario_file)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)

            # 검증
            if not self._validate_scenario(scenario_data):
                print(f"❌ 시나리오 검증 실패: {scenario_file}")
                return None

            # 캐시에 저장
            self.loaded_scenarios[scenario_file] = scenario_data
            print(f"✅ 시나리오 로드 성공: {scenario_file}")
            print(f"   - scenario_id: {scenario_data.get('scenario_id')}")
            print(f"   - title: {scenario_data.get('title')}")
            print(f"   - stages: {len(scenario_data.get('stages', {}))}")

            return scenario_data

        except FileNotFoundError:
            print(f"❌ 시나리오 파일을 찾을 수 없음: {file_path}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {file_path}, {str(e)}")
            return None
        except Exception as e:
            print(f"❌ 시나리오 로드 오류: {str(e)}")
            return None

    def _validate_scenario(self, scenario_data: Dict[str, Any]) -> bool:
        """시나리오 JSON 구조 검증"""
        # 필수 필드 확인
        required_fields = ["scenario_id", "title", "stages"]
        for field in required_fields:
            if field not in scenario_data:
                print(f"❌ 필수 필드 누락: {field}")
                return False

        stages = scenario_data.get("stages")
        if not stages:
            print("❌ stages가 비어있습니다")
            return False

        if isinstance(stages, list):
            stages_dict = {}
            for stage in stages:
                tag = stage.get("tag")
                if not tag:
                    print("❌ 스테이지 tag 누락")
                    return False
                stages_dict[tag] = stage
            scenario_data["stages"] = stages_dict
            stages = stages_dict

        if not isinstance(stages, dict):
            print("❌ stages가 잘못된 형식입니다")
            return False

        # 각 스테이지 검증
        for stage_id, stage_data in stages.items():
            if not isinstance(stage_data, dict):
                print(f"❌ 스테이지 데이터 형식 오류: {stage_id}")
                return False

            # 타입별 필수 필드 확인
            stage_type = stage_data.get("type")
            if not self._validate_stage_type(stage_id, stage_type, stage_data):
                return False

        return True

    def _validate_stage_type(self, stage_id: str, stage_type: Optional[str],
                           stage_data: Dict[str, Any]) -> bool:
        """스테이지 타입별 검증"""
        if not stage_type:
            print(f"❌ 스테이지 타입 누락: {stage_id}")
            return False

        stage_type_norm = stage_type.lower()

        if stage_type_norm in ("cutscene", "scene"):
            # 하이브리드 지원: 대사 또는 상황 중 하나는 있어야 함
            has_dialogues = "dialogues" in stage_data
            has_situations = "situations" in stage_data
            has_beats = "beats" in stage_data or "beats_i18n" in stage_data
            has_variants = "variants" in stage_data
            has_llm_beats = stage_data.get("llm_beats") is True  # LLM이 동적으로 beats 생성

            if not (has_dialogues or has_situations or has_beats or has_variants or has_llm_beats):
                print(f"❌ {stage_type} 스테이지에 컨텐츠(dialogues/beats/variants/llm_beats)가 필요: {stage_id}")
                return False

        elif stage_type_norm == "choice":
            if "choices" not in stage_data:
                print(f"❌ choice 스테이지에 choices 누락: {stage_id}")
                return False

            # 각 선택지 검증
            for choice in stage_data["choices"]:
                if "id" not in choice or "text" not in choice or "next_stage" not in choice:
                    print(f"❌ choice에 필수 필드 누락: {stage_id}")
                    return False

        elif stage_type_norm == "mission":
            if "objective" not in stage_data:
                print(f"❌ mission 스테이지에 objective 누락: {stage_id}")
                return False

        elif stage_type_norm == "branch":
            if "branches" not in stage_data:
                print(f"❌ branch 스테이지에 branches 누락: {stage_id}")
                return False

            # 각 분기 검증
            for branch in stage_data["branches"]:
                if "id" not in branch or "conditions" not in branch or "next_stage" not in branch:
                    print(f"❌ branch에 필수 필드 누락: {stage_id}")
                    return False

        elif stage_type_norm == "free_intent":
            if not any(stage_data.get(key) for key in ("speaker_pool", "beats", "beats_i18n", "orchestrator")):
                print(f"❌ free_intent 스테이지에 speaker_pool 또는 beats 필요: {stage_id}")
                return False

        elif stage_type_norm == "router":
            if "rules" not in stage_data and "next_by_outcome" not in stage_data:
                print(f"❌ router 스테이지에 rules 또는 next_by_outcome 필요: {stage_id}")
                return False

        elif stage_type_norm == "ending":
            if not any(stage_data.get(key) for key in ("final_message", "beats", "beats_i18n", "variants")):
                print(f"⚠️ ending 스테이지에 final_message 또는 beats 권장: {stage_id}")

        elif stage_type_norm == "open_narrative":
            if "max_turns" not in stage_data:
                print(f"⚠️ open_narrative 스테이지에 max_turns 권장: {stage_id}")

        elif stage_type_norm == "llm_beats":
            if not any(stage_data.get(key) for key in ("speaker_pool", "context")):
                print(f"⚠️ llm_beats 스테이지에 speaker_pool 또는 context 권장: {stage_id}")

        else:
            print(f"⚠️ 알 수 없는 스테이지 타입: {stage_type} in {stage_id}")

        return True

    def get_stage(self, scenario_data: Dict[str, Any],
                 stage_id: str) -> Optional[ScenarioStage]:
        """
        특정 스테이지 정보 가져오기

        Args:
            scenario_data: 로드된 시나리오 데이터
            stage_id: 스테이지 ID (예: "intro", "fork", "recruit_mission")

        Returns:
            ScenarioStage 객체
        """
        stages = scenario_data.get("stages", {})

        if stage_id not in stages:
            print(f"❌ 스테이지를 찾을 수 없음: {stage_id}")
            return None

        stage_data = stages[stage_id]
        stage_type = stage_data.get("type")
        next_stage = stage_data.get("next_stage")

        return ScenarioStage(
            stage_id=stage_id,
            stage_type=stage_type,
            data=stage_data,
            next_stage=next_stage
        )

    def get_next_stage_id(self, scenario_data: Dict[str, Any],
                         current_stage_id: str,
                         user_choice: Optional[str] = None,
                         conditions: Optional[Dict[str, bool]] = None) -> Optional[str]:
        """
        다음 스테이지 ID 결정

        Args:
            scenario_data: 시나리오 데이터
            current_stage_id: 현재 스테이지 ID
            user_choice: 사용자 선택 (choice 타입용)
            conditions: 조건 플래그 (branch 타입용)

        Returns:
            다음 스테이지 ID
        """
        current_stage = self.get_stage(scenario_data, current_stage_id)

        if not current_stage:
            return None

        stage_type = current_stage.stage_type
        stage_data = current_stage.data

        if stage_type == "cutscene":
            return stage_data.get("next_stage")

        # 2. : 사용자 선택에 따라 분기
        elif stage_type == "choice":
            if not user_choice:
                print(f"⚠️ choice 스테이지에서 사용자 선택 필요: {current_stage_id}")
                return None

            choices = stage_data.get("choices", [])
            for choice in choices:
                if choice["id"] == user_choice:
                    return choice["next_stage"]

            print(f"❌ 선택지를 찾을 수 없음: {user_choice}")
            return None

        elif stage_type == "mission":
            return stage_data.get("next_stage")

        # 4. : 조건에 따라 분기
        elif stage_type == "branch":
            if not conditions:
                print(f"⚠️ branch 스테이지에서 조건 필요: {current_stage_id}")
                return None

            branches = stage_data.get("branches", [])

            # 조건을 순서대로 확인
            for branch in branches:
                branch_conditions = branch.get("conditions", [])

                # "" 조건은 항상 
                if "default" in branch_conditions:
                    return branch["next_stage"]

                # 모든 조건이 만족되면 해당 분기 선택
                if all(conditions.get(cond, False) for cond in branch_conditions):
                    print(f"✅ 분기 조건 만족: {branch['id']}")
                    return branch["next_stage"]

            print(f"❌ 만족하는 분기 조건이 없음: {current_stage_id}")
            return None

        else:
            print(f"❌ 알 수 없는 스테이지 타입: {stage_type}")
            return None

    def get_initial_stage_id(self, scenario_data: Dict[str, Any]) -> Optional[str]:
        """시나리오의 첫 스테이지 ID 가져오기"""
        stages = scenario_data.get("stages", {})

        # 일반적으로 첫 번째 스테이지가 시작점
        # 또는 ""라는 이름 찾기
        if "intro" in stages:
            return "intro"

        # 의 첫 번째 키 반환
        if stages:
            return list(stages.keys())[0]

        return None

    def evaluate_branch_conditions(self, state, stage_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        🔄 branch 조건 평가 (완전 동적 - 시나리오 JSON 기반)

        Args:
            state: AgentState 객체
            stage_data: branch 스테이지 데이터

        Returns:
            조건명: 만족여부 딕셔너리
        """
        conditions = {}

        branches = stage_data.get("branches", [])
        for branch in branches:
            branch_conditions = branch.get("conditions", [])
            for cond in branch_conditions:
                if cond != "default":
                    # 플래그 직접 체크
                    conditions[cond] = state.game.has_flag(cond)

        # 🔄 2. 레거시 동적 조건 평가 시스템 (하위 호환성)
        if state.game.scenario_data:
            stages = state.game.scenario_data.get("stages", {})

            # 미션 스테이지에서 캐릭터 순서 파악
            for stage_id, stage_info in stages.items():
                if stage_info.get("type") == "mission":
                    characters = stage_info.get("characters", {})
                    char_ids = list(characters.keys())

                    # 첫 번째 캐릭터가 먼저 대화했는지 확인
                    first_char = char_ids[0] if char_ids else None
                    all_recruited = all(state.game.has_flag(f"{c}_recruited") for c in char_ids)
                    first_talk_correct = state.game.has_flag(f"{first_char}_first") if first_char else False

                    conditions["recruited_allies_in_order"] = first_talk_correct and all_recruited
                    break

        if "within_turns" not in conditions:
            conditions["within_turns"] = state.game.total_remaining_turns > 0

        # 🔄 4. 동적 친밀도 조건 (시나리오 에서 캐릭터와 임계값 파악)
        if state.game.scenario_data:
            stages = state.game.scenario_data.get("stages", {})
            for stage_id, stage_info in stages.items():
                if stage_info.get("type") == "mission":
                    characters = stage_info.get("characters", {})
                    for char_id, char_data in characters.items():
                        threshold = char_data.get("affinity_bonus", 30) * 10  # 30 -> 300
                        conditions[f"high_affinity_{char_id}"] = (
                            state.characters.affinity.get(char_id, 0) >= threshold
                        )

        conditions["default"] = True

        return conditions


# 전역 로더 인스턴스
scenario_loader = ScenarioLoader()


def get_current_scene_data(state: dict) -> dict:
    """
    GraphState에서 현재 시나리오와 씬 ID를 기반으로 해당 씬의 데이터를 반환합니다.

    Args:
        state: GraphState (dict 형식)

    Returns:
        현재 씬의 데이터 (dict)
    """
    scenario_id = state.get("scenario_id")
    current_stage = state.get("current_stage")

    if not scenario_id:
        print("[get_current_scene_data] scenario_id가 없습니다")
        return {}

    if not current_stage:
        print("[get_current_scene_data] current_stage가 없습니다")
        return {}

    # 전역 로더로 시나리오 로드
    full_scenario = scenario_loader.load_scenario(f"{scenario_id}.json")

    if not full_scenario:
        print(f"[get_current_scene_data] 시나리오를 로드할 수 없습니다: {scenario_id}")
        return {}

    # 스테이지 데이터 가져오기
    stages = full_scenario.get("stages", {})
    if current_stage in stages:
        stage_data = stages[current_stage]
        print(f"[get_current_scene_data] 현재 스테이지: {current_stage}, 타입: {stage_data.get('type')}")
        return stage_data
    else:
        print(f"[get_current_scene_data] 스테이지를 찾을 수 없음: {current_stage}")
        return {}


def load_scenario_for_state(state, scenario_file: str):
    """
    AgentState에 시나리오 로드 및 초기화

    Args:
        state: AgentState 객체
        scenario_file: 시나리오 파일명
    """
    scenario_data = scenario_loader.load_scenario(scenario_file)

    if not scenario_data:
        print(f"❌ 시나리오 로드 실패: {scenario_file}")
        return False

    # 에 시나리오 데이터 설정
    state.game.scenario_data = scenario_data
    state.game.scenario_id = scenario_data.get("scenario_id")

    # 첫 스테이지 설정
    initial_stage_id = scenario_loader.get_initial_stage_id(scenario_data)
    if initial_stage_id:
        state.game.current_stage = initial_stage_id
        state.game.stage_history = [initial_stage_id]
        print(f"✅ 시나리오 초기화 완료: {state.game.scenario_id}")
        print(f"   - 시작 스테이지: {initial_stage_id}")
    else:
        print(f"❌ 초기 스테이지를 찾을 수 없음")
        return False

    return True


# 테스트 코드
if __name__ == "__main__":
    print("=== Scenario Loader 테스트 ===\n")

    loader = ScenarioLoader()

    # 1. 시나리오 로드
    scenario = loader.load_scenario("example_scene.json")

    if scenario:
        print(f"\n=== 시나리오 정보 ===")
        print(f"ID: {scenario['scenario_id']}")
        print(f"제목: {scenario['title']}")
        print(f"스테이지 수: {len(scenario['stages'])}")

        # 2. 스테이지 순회
        print(f"\n=== 스테이지 목록 ===")
        for stage_id in scenario['stages'].keys():
            stage = loader.get_stage(scenario, stage_id)
            print(f"- {stage_id}: {stage.stage_type} -> {stage.next_stage}")

        # 3. 다음 스테이지 결정 테스트
        print(f"\n=== 다음 스테이지 결정 테스트 ===")

        next_stage = loader.get_next_stage_id(scenario, "intro")
        print(f"intro 다음: {next_stage}")

        next_stage = loader.get_next_stage_id(scenario, "fork", user_choice="recruit_allies")
        print(f"fork (선택: recruit_allies) 다음: {next_stage}")

        from src.core.graph_state import create_enhanced_initial_state

        test_state = create_enhanced_initial_state("test")
        test_state.game.add_flag("inosuke_first")
        test_state.game.add_flag("inosuke_recruited")
        test_state.game.add_flag("zenitsu_recruited")
        test_state.game.total_remaining_turns = 3
        test_state.characters.update_affinity("inosuke", 50)
        test_state.characters.update_affinity("zenitsu", 50)

        stage = loader.get_stage(scenario, "evaluate_end")
        conditions = loader.evaluate_branch_conditions(test_state, stage.data)
        print(f"\n조건 평가 결과: {conditions}")

        next_stage = loader.get_next_stage_id(scenario, "evaluate_end", conditions=conditions)
        print(f"evaluate_end (조건 평가) 다음: {next_stage}")

    print("\n=== 테스트 완료 ===")
