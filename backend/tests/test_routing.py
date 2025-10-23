"""
분기 전환 검증 테스트
"""
import pytest
from agent_state_enhanced import create_enhanced_initial_state, UserChatInput
from langgraph_workflow import KimeChatWorkflow
from scenario_loader import scenario_loader
from datetime import datetime


class TestStageTransitions:
    """스테이지 전환 테스트"""

    def test_intro_to_fork_transition(self):
        """intro → fork 전환 검증"""
        workflow = KimeChatWorkflow()
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "intro"

        # intro는 4턴
        for i in range(5):
            state.user_input = UserChatInput(content="다음", chat_no=i+1, timestamp=datetime.now().isoformat())
            state = workflow.invoke(state)

        # fork로 전환되었는지 확인
        assert state.game.current_stage == "fork"

    def test_fork_to_recruit_mission(self):
        """fork → recruit_mission 전환 검증"""
        workflow = KimeChatWorkflow()
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        # 선택지 "1" 입력
        state.user_input = UserChatInput(content="1", chat_no=1, timestamp=datetime.now().isoformat())
        state = workflow.invoke(state)

        # recruit_mission으로 전환
        assert state.game.current_stage == "recruit_mission"

    def test_fork_to_direct_approach(self):
        """fork → direct_approach_scene 전환 검증"""
        workflow = KimeChatWorkflow()
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        # 선택지 "2" 입력
        state.user_input = UserChatInput(content="2", chat_no=1, timestamp=datetime.now().isoformat())
        state = workflow.invoke(state)

        # direct_approach_scene 또는 end_medium 전환 확인
        assert state.game.current_stage in ["direct_approach_scene", "end_medium"]

    def test_fork_to_reckless_sacrifice(self):
        """fork → reckless_sacrifice_scene 전환 검증"""
        workflow = KimeChatWorkflow()
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        # 선택지 "3" 입력
        state.user_input = UserChatInput(content="3", chat_no=1, timestamp=datetime.now().isoformat())
        state = workflow.invoke(state)

        # reckless_sacrifice_scene 또는 end_bad 전환 확인
        assert state.game.current_stage in ["reckless_sacrifice_scene", "end_bad"]
