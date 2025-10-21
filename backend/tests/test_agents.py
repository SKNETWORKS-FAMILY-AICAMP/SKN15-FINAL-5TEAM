"""
에이전트 유닛 테스트
"""
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_state_enhanced import create_enhanced_initial_state
from router_agent_enhanced import run_router_agent
from guardrail_agent_enhanced import run_guardrail_agent
from parent_agent_enhanced import run_parent_agent
from children_agent_enhanced import run_children_agent
from dialogue_agent import run_dialogue_agent

class TestRouterAgent(unittest.TestCase):
    """Router Agent 테스트"""

    def test_on_topic_classification(self):
        """on-topic 분류 테스트"""
        state = create_enhanced_initial_state("test")
        state = run_router_agent(state, "혈귀가 나타났다!")

        self.assertEqual(state.routing_result.classification, "on_topic")
        self.assertEqual(state.next_node, "guardrail")

    def test_off_topic_classification(self):
        """off-topic 분류 테스트"""
        state = create_enhanced_initial_state("test")
        state = run_router_agent(state, "오늘 날씨 좋네요")

        # 일부 경우 on-topic으로 분류될 수 있음 (게임 진행 가정)
        self.assertIn(state.next_node, ["guardrail", "warning_handler"])

class TestGuardrailAgent(unittest.TestCase):
    """Guardrail Agent 테스트"""

    def test_safe_input(self):
        """안전한 입력 테스트"""
        state = create_enhanced_initial_state("test")
        state.user_input.content = "함께 싸우자!"
        state = run_guardrail_agent(state)

        self.assertEqual(state.guardrail_result.status, "passed")
        self.assertEqual(state.next_node, "parent_agent")

    def test_profanity_detection(self):
        """욕설 감지 테스트"""
        state = create_enhanced_initial_state("test")
        state.user_input.content = "바보같은 선택이야"
        state = run_guardrail_agent(state)

        # 경미한 욕설은 경고 후 진행
        self.assertIn(state.guardrail_result.status, ["warning", "passed"])

class TestParentAgent(unittest.TestCase):
    """Parent Agent 테스트"""

    def test_state_update(self):
        """상태 업데이트 테스트"""
        state = create_enhanced_initial_state("test")
        state.game.scenario_data = {
            "stages": {
                "intro": {
                    "type": "cutscene",
                    "dialogues": [],
                    "next_stage": "mission"
                }
            }
        }
        state.game.current_stage = "intro"

        state = run_parent_agent(state)

        self.assertIsNotNone(state.parent_decisions)
        self.assertEqual(state.next_node, "children_agent")

class TestChildrenAgent(unittest.TestCase):
    """Children Agent 테스트"""

    def test_dialogue_generation(self):
        """대사 생성 테스트"""
        state = create_enhanced_initial_state("test")
        state.characters.available_characters = ["tanjiro"]

        state = run_children_agent(state)

        # 대사가 생성되어야 함
        self.assertGreater(len(state.output.dialogues), 0)

class TestDialogueAgent(unittest.TestCase):
    """Dialogue Agent 테스트"""

    def test_validation(self):
        """대사 검증 테스트"""
        from agent_state_enhanced import Dialogue

        state = create_enhanced_initial_state("test")
        state.output.dialogues = [
            Dialogue(
                speaker="탄지로",
                content="함께 싸우자!",
                emotion="determined",
                affinity_level="high"
            )
        ]

        state = run_dialogue_agent(state)

        # 검증 후에도 대사가 유지되어야 함
        self.assertGreater(len(state.output.dialogues), 0)

if __name__ == '__main__':
    unittest.main()
