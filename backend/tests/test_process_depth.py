"""
무한루프 방지 로직 테스트
"""
import pytest
from agent_state_enhanced import create_enhanced_initial_state, UserChatInput
from parent_agent_enhanced import ParentAgent
from datetime import datetime


class TestProcessDepthLimit:
    """process_depth 무한루프 방지 테스트"""

    def test_process_depth_limit_11(self):
        """process_depth 11 이상 시 차단"""
        state = create_enhanced_initial_state("test")
        state.user_input = UserChatInput(content="테스트", chat_no=1, timestamp=datetime.now().isoformat())

        # process_depth를 11로 설정
        state.game.temp_data["_process_depth"] = 11

        agent = ParentAgent(use_llm=False)
        result = agent.process(state)

        # 시스템 오류 메시지 확인
        assert len(result.output.system_messages) > 0
        assert "시스템 오류" in result.output.system_messages[0]

    def test_process_depth_increments(self):
        """process_depth가 정상적으로 증가하는지 확인"""
        state = create_enhanced_initial_state("test")
        state.user_input = UserChatInput(content="테스트", chat_no=1, timestamp=datetime.now().isoformat())

        from scenario_loader import scenario_loader
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "intro"

        # 초기 depth는 0
        initial_depth = state.game.temp_data.get("_process_depth", 0)
        assert initial_depth == 0

        agent = ParentAgent(use_llm=False)
        result = agent.process(state)

        # depth가 1로 증가
        new_depth = result.game.temp_data.get("_process_depth", 0)
        assert new_depth == 1

    def test_process_depth_below_limit(self):
        """process_depth 10 이하일 때 정상 처리"""
        state = create_enhanced_initial_state("test")
        state.user_input = UserChatInput(content="테스트", chat_no=1, timestamp=datetime.now().isoformat())

        from scenario_loader import scenario_loader
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "intro"

        # process_depth를 10으로 설정 (한계 바로 아래)
        state.game.temp_data["_process_depth"] = 10

        agent = ParentAgent(use_llm=False)
        result = agent.process(state)

        # 정상 처리됨 (오류 메시지 없음)
        # 11로 증가하므로 다음 호출부터 차단됨
        assert result.game.temp_data["_process_depth"] == 11
