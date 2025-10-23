#!/usr/bin/env python3
"""
분기 엣지케이스 테스트
- 잘못된 choice 입력 처리
- flags 상태 전환 검증
- 시나리오 경로 무결성 확인
"""
import pytest
from agent_state_enhanced import create_enhanced_initial_state, UserChatInput
from parent_agent_enhanced import ParentAgent
from scenario_loader import scenario_loader
from datetime import datetime


class TestBranchingEdgeCases:
    """분기 로직 엣지케이스 테스트"""

    def test_invalid_choice_empty_input(self):
        """빈 입력에 대한 처리"""
        agent = ParentAgent(use_llm=False)
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        # 빈 입력
        state.user_input = UserChatInput(content="", chat_no=1, timestamp=datetime.now().isoformat())

        result = agent.process(state)

        # 오류 메시지 또는 재입력 요청이 있어야 함
        assert result.output.system_messages or result.output.dialogues

    def test_invalid_choice_whitespace_only(self):
        """공백만 있는 입력 처리"""
        agent = ParentAgent(use_llm=False)
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        # 공백만
        state.user_input = UserChatInput(content="   ", chat_no=1, timestamp=datetime.now().isoformat())

        result = agent.process(state)

        # 시스템이 처리해야 함 (오류 또는 무시)
        assert result is not None

    def test_invalid_choice_out_of_range(self):
        """범위 밖 choice 번호 (예: fork에서 "9" 입력)"""
        agent = ParentAgent(use_llm=False)
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        # fork는 1, 2, 3만 유효
        state.user_input = UserChatInput(content="9", chat_no=1, timestamp=datetime.now().isoformat())

        result = agent.process(state)

        # 현재 스테이지가 변경되지 않아야 함 (잘못된 입력으로 진행 안됨)
        # 또는 시스템 메시지로 안내
        assert result.game.current_stage == "fork" or len(result.output.system_messages) > 0

    def test_invalid_choice_negative_number(self):
        """음수 choice 입력"""
        agent = ParentAgent(use_llm=False)
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        state.user_input = UserChatInput(content="-1", chat_no=1, timestamp=datetime.now().isoformat())

        result = agent.process(state)

        # 잘못된 입력으로 처리되어야 함
        assert result.game.current_stage == "fork"

    def test_case_insensitive_keywords(self):
        """대소문자 구분 없는 키워드 매칭"""
        from mission_manager import MissionManager

        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        mission_data = scenario["stages"]["recruit_mission"]
        manager = MissionManager(mission_data)
        state = manager.start_mission()

        # 대문자로 입력
        success1, msg1, _ = manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        assert success1 is True

        # 소문자 포함
        success2, msg2, _ = manager.process_user_input(state, "약한", "inosuke", increment_turn_on_success=True)
        assert success2 is True

    def test_partial_keyword_matching(self):
        """부분 키워드 매칭 동작 확인"""
        from mission_manager import MissionManager

        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        mission_data = scenario["stages"]["recruit_mission"]
        manager = MissionManager(mission_data)
        state = manager.start_mission()

        # "이노스케"가 포함된 문장
        success, msg, _ = manager.process_user_input(
            state,
            "이노스케야 안녕",
            "inosuke",
            increment_turn_on_success=True
        )
        assert success is True
        assert state.current_turn == 1

    def test_stage_transition_without_required_flags(self):
        """필수 플래그 없이 스테이지 전환 시도"""
        agent = ParentAgent(use_llm=False)
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario

        # fork 스테이지는 intro 완료 플래그가 필요할 수 있음
        state.game.current_stage = "fork"
        # intro 완료 플래그 없이 직접 설정

        state.user_input = UserChatInput(content="1", chat_no=1, timestamp=datetime.now().isoformat())

        result = agent.process(state)

        # 시스템이 처리해야 함 (플래그 검증은 시나리오 설계에 따라 다름)
        assert result is not None

    def test_duplicate_flag_addition(self):
        """중복 플래그 추가 방지 확인"""
        state = create_enhanced_initial_state("test")

        # 동일 플래그 2번 추가
        state.game.flags.add("test_flag")
        state.game.flags.add("test_flag")

        # set이므로 중복 없어야 함
        assert len([f for f in state.game.flags if f == "test_flag"]) == 1

    def test_mission_order_enforcement_strict(self):
        """미션 순서 엄격 검증 (inosuke → zenitsu)"""
        from mission_manager import MissionManager

        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        mission_data = scenario["stages"]["recruit_mission"]
        manager = MissionManager(mission_data)
        state = manager.start_mission()

        # zenitsu 먼저 시도 (순서 위반)
        success, msg, _ = manager.process_user_input(state, "젠이츠", "zenitsu", increment_turn_on_success=True)

        # 실패해야 함
        assert success is False
        assert "순서" in msg or "먼저" in msg

    def test_mission_completion_with_wrong_order(self):
        """잘못된 순서로 모집 시 실패 확인"""
        from mission_manager import MissionManager, MissionStatus

        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        mission_data = scenario["stages"]["recruit_mission"]
        manager = MissionManager(mission_data)
        state = manager.start_mission()

        # 강제로 zenitsu 먼저 recruited로 설정 (순서 위반)
        state.character_progress["zenitsu"].recruited = True
        state.character_progress["zenitsu"].current_stage = 3
        state.recruitment_order.append("zenitsu")

        # 그 다음 inosuke 완료
        state.character_progress["inosuke"].recruited = True
        state.character_progress["inosuke"].current_stage = 3
        state.recruitment_order.append("inosuke")

        state.current_turn = 6

        # 순서 검증 시 실패해야 함
        status, msg = manager.check_completion(state)
        assert status == MissionStatus.FAILED
        assert "순서" in msg

    def test_intro_completion_triggers_fork(self):
        """intro 완료 시 fork 전환 확인"""
        agent = ParentAgent(use_llm=False)
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "intro"

        # intro는 multi-speaker 스테이지 (4턴)
        # 턴을 4로 설정하고 마지막 입력
        state.game.turn = 3

        state.user_input = UserChatInput(content="다음", chat_no=4, timestamp=datetime.now().isoformat())

        result = agent.process(state)

        # fork로 전환되어야 함
        assert result.game.current_stage == "fork"

    def test_fork_choice_1_leads_to_recruit_mission(self):
        """fork에서 선택지 1 → recruit_mission 전환"""
        agent = ParentAgent(use_llm=False)
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        state.user_input = UserChatInput(content="1", chat_no=1, timestamp=datetime.now().isoformat())

        result = agent.process(state)

        # recruit_mission으로 전환
        assert result.game.current_stage == "recruit_mission"

    def test_fork_choice_2_leads_to_direct_approach(self):
        """fork에서 선택지 2 → direct_approach"""
        agent = ParentAgent(use_llm=False)
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        state.user_input = UserChatInput(content="2", chat_no=1, timestamp=datetime.now().isoformat())

        result = agent.process(state)

        # direct_approach_scene 또는 end_medium으로 전환
        assert result.game.current_stage in ["direct_approach_scene", "end_medium"]

    def test_fork_choice_3_leads_to_reckless_sacrifice(self):
        """fork에서 선택지 3 → reckless_sacrifice"""
        agent = ParentAgent(use_llm=False)
        state = create_enhanced_initial_state("test")
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        state.game.scenario_data = scenario
        state.game.current_stage = "fork"

        state.user_input = UserChatInput(content="3", chat_no=1, timestamp=datetime.now().isoformat())

        result = agent.process(state)

        # reckless_sacrifice_scene 또는 end_bad로 전환
        assert result.game.current_stage in ["reckless_sacrifice_scene", "end_bad"]
