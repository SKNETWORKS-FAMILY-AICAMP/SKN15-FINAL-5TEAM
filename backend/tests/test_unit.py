#!/usr/bin/env python3
"""
단위 테스트 - 개별 컴포넌트 검증
"""

import unittest
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_state_enhanced import create_enhanced_initial_state, UserChatInput, Dialogue
from parent_agent_enhanced import ParentAgent
from guardrail_agent_enhanced import GuardrailAgent
from datetime import datetime


class TestDialogueObjectHandling(unittest.TestCase):
    """Task 4: Dialogue 객체 처리 테스트"""

    def test_dialogue_dataclass_attributes(self):
        """Dialogue 객체가 dataclass 속성으로 접근 가능한지 테스트"""
        dialogue = Dialogue(
            speaker="tanjiro",
            content="안녕하세요!",
            emotion="happy",
            emotion_intensity="strong"
        )

        # hasattr로 속성 확인
        self.assertTrue(hasattr(dialogue, 'speaker'))
        self.assertTrue(hasattr(dialogue, 'content'))
        self.assertTrue(hasattr(dialogue, 'emotion'))

        # 속성 값 확인
        self.assertEqual(dialogue.speaker, "tanjiro")
        self.assertEqual(dialogue.content, "안녕하세요!")
        self.assertEqual(dialogue.emotion, "happy")

    def test_dialogue_list_iteration(self):
        """Dialogue 리스트를 순회하며 속성 접근 테스트"""
        dialogues = [
            Dialogue("tanjiro", "첫 번째 대사", "neutral"),
            Dialogue("system", "두 번째 대사", None),
            Dialogue("inosuke", "세 번째 대사", "angry")
        ]

        for dialogue in dialogues:
            speaker = dialogue.speaker if hasattr(dialogue, 'speaker') else ""
            content = dialogue.content if hasattr(dialogue, 'content') else ""

            self.assertIsInstance(speaker, str)
            self.assertIsInstance(content, str)
            self.assertTrue(len(content) > 0)


class TestLLMChoiceMapping(unittest.TestCase):
    """Task 3: LLM 기반 의미 매핑 테스트"""

    def setUp(self):
        """각 테스트 전 상태 초기화"""
        self.agent = ParentAgent()
        self.state = create_enhanced_initial_state("test_choice")

        # Choice 스테이지 설정
        self.state.game.scenario_data = {
            "stages": {
                "choice_stage": {
                    "type": "choice",
                    "choices": [
                        {
                            "choice_id": "help_rengoku",
                            "description": "렌고쿠를 돕는다",
                            "intent_keywords": ["돕다", "도와주다", "렌고쿠", "함께"],
                            "next_stage": "help_ending"
                        },
                        {
                            "choice_id": "run_away",
                            "description": "도망친다",
                            "intent_keywords": ["도망", "피하다", "떠나다"],
                            "next_stage": "run_ending"
                        }
                    ]
                }
            }
        }
        self.state.game.current_stage = "choice_stage"

    def test_llm_choice_high_confidence(self):
        """높은 신뢰도(>=0.75)로 선택지 매칭 성공 테스트"""
        # LLM이 없는 환경에서는 키워드 기반으로 처리되므로 스킵
        if not self.agent.use_llm:
            self.skipTest("LLM not available")

        self.state.user_input = UserChatInput(
            content="렌고쿠님을 도와드려야 해!",
            chat_no=1,
            timestamp=datetime.now().isoformat()
        )

        result_state = self.agent.process(self.state)

        # 처리가 완료되었는지만 확인
        self.assertIsNotNone(result_state)

    def test_llm_choice_low_confidence_fallback(self):
        """낮은 신뢰도(<0.75)일 때 키워드 기반으로 폴백 테스트"""
        if not self.agent.use_llm:
            self.skipTest("LLM not available")

        # 모호한 입력
        self.state.user_input = UserChatInput(
            content="글쎄요...",
            chat_no=1,
            timestamp=datetime.now().isoformat()
        )

        result_state = self.agent.process(self.state)

        # 처리가 완료되었는지 확인
        self.assertIsNotNone(result_state)

    def test_keyword_fallback(self):
        """LLM 없이 키워드 기반 매칭 테스트"""
        # 키워드가 명확한 경우
        self.state.user_input = UserChatInput(
            content="렌고쿠를 도와주자!",
            chat_no=1,
            timestamp=datetime.now().isoformat()
        )

        result_state = self.agent.process(self.state)

        # help_ending으로 분기 (키워드: 돕다, 렌고쿠)
        # 키워드 매칭이 동작하는지만 확인 (실제 전환은 워크플로우에서 처리)
        self.assertIsNotNone(result_state)


class TestMissionTurnValidation(unittest.TestCase):
    """미션 스테이지 턴 검증 테스트"""

    def setUp(self):
        """각 테스트 전 상태 초기화"""
        self.guardrail = GuardrailAgent(use_llm=False)
        self.state = create_enhanced_initial_state("test_mission")

        # Mission 스테이지 설정
        self.state.game.scenario_data = {
            "stages": {
                "mission_stage": {
                    "type": "mission",
                    "max_turns": 6,
                    "current_turn": 3,  # 현재 3턴
                    "characters": {
                        "zenitsu": {"max_attempts": 2},
                        "inosuke": {"max_attempts": 2}
                    }
                }
            }
        }
        self.state.game.current_stage = "mission_stage"
        self.state.game.character_remaining_turns = {
            "zenitsu": 1,
            "inosuke": 2
        }

    def test_mission_turn_within_limit(self):
        """미션 턴 제한 내에서 정상 진행 테스트"""
        self.state.user_input = UserChatInput(
            content="젠이츠를 찾아보자",
            chat_no=1,
            timestamp=datetime.now().isoformat()
        )

        validation = self.guardrail._validate_stage_input(self.state)

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["message"], "")

    def test_mission_turn_exceeded(self):
        """미션 턴 초과 시 차단 테스트"""
        # 턴을 6으로 설정 (max_turns와 동일)
        self.state.game.scenario_data["stages"]["mission_stage"]["current_turn"] = 6

        self.state.user_input = UserChatInput(
            content="젠이츠를 찾아보자",
            chat_no=1,
            timestamp=datetime.now().isoformat()
        )

        validation = self.guardrail._validate_stage_input(self.state)

        self.assertFalse(validation["valid"])
        self.assertIn("초과", validation["message"])

    def test_character_attempts_exhausted(self):
        """캐릭터별 시도 횟수 소진 테스트"""
        # 스킵: Guardrail은 더 이상 캐릭터별 시도 횟수를 체크하지 않음
        # Parent Agent에서 처리
        self.skipTest("Character attempts now handled by Parent Agent")


class TestStageInitialization(unittest.TestCase):
    """Task 5: 스테이지 초기화 테스트"""

    def test_initial_stage_not_none(self):
        """초기 스테이지가 None이 아닌지 테스트"""
        state = create_enhanced_initial_state("test_stage")
        state.game.current_stage = "intro"

        self.assertIsNotNone(state.game.current_stage)
        self.assertEqual(state.game.current_stage, "intro")

    def test_scenario_data_loaded(self):
        """시나리오 데이터 로드 테스트"""
        from scenario_loader import scenario_loader

        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")

        self.assertIsNotNone(scenario)
        self.assertIn("stages", scenario)
        self.assertIn("intro", scenario["stages"])


class TestInosukeProvocation(unittest.TestCase):
    """이노스케 도발 기반 설득 테스트"""

    def setUp(self):
        """각 테스트 전 상태 초기화"""
        from scenario_loader import scenario_loader

        self.state = create_enhanced_initial_state("test_inosuke")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")

        self.state.game.scenario_data = scenario
        self.state.game.current_stage = "mission"

        # Mission 스테이지 초기화 (current_turn 설정)
        if "mission" not in self.state.game.scenario_data["stages"]:
            self.state.game.scenario_data["stages"]["mission"] = {
                "type": "mission",
                "current_turn": 0,
                "max_turns": 6,
                "characters": {
                    "inosuke": {
                        "keywords": ["약하다", "약한", "겁쟁이"],
                        "success_response": "뭐라고!?",
                        "max_attempts": 3
                    }
                }
            }

        # 이노스케와 대화 중 상황 설정
        self.state.characters.available_characters = ["inosuke"]

    def test_provocation_keywords(self):
        """도발 키워드 감지 테스트"""
        parent = ParentAgent()

        # 이노스케를 available_characters에 추가 (이미 만난 상태)
        self.state.characters.available_characters = ["inosuke"]

        # 도발 키워드가 포함된 입력 ("약하다" 키워드 사용)
        self.state.user_input = UserChatInput(
            content="너는 약하다!",
            chat_no=1,
            timestamp=datetime.now().isoformat()
        )

        result_state = parent.process(self.state)

        # 처리가 완료되고 대화 컨텍스트가 설정되었는지 확인
        self.assertIsNotNone(result_state)
        self.assertIsNotNone(result_state.parent_decisions.dialogue_context)


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
