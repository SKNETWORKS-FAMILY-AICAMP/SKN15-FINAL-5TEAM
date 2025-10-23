#!/usr/bin/env python3
"""
AgentState 종합 테스트 (커버리지 향상용)
"""
import pytest
from agent_state_enhanced import (
    create_enhanced_initial_state,
    MetaData,
    UserChatInput,
    GameState,
    CharacterData,
    OutputData,
    AgentState,
    NodeType
)
from datetime import datetime


class TestAgentStateComprehensive:
    """AgentState 전체 기능 테스트"""

    def test_create_initial_state_default_params(self):
        """기본 파라미터로 초기 상태 생성"""
        state = create_enhanced_initial_state("test_session")

        assert state.meta.session_id == "test_session"
        assert state.meta.version == "1.0"
        assert state.game.scenario_id == "scenario_001"
        assert state.game.scene_id == "scene5_cutscene_intro"
        assert state.game.turn == 0
        assert state.game.max_turns == 10
        assert "tanjiro" in state.characters.available_characters  # Default includes tanjiro
        assert state.output.dialogues == []
        assert state.next_node == NodeType.PARENT.value

    def test_create_initial_state_custom_params(self):
        """커스텀 파라미터로 초기 상태 생성"""
        state = create_enhanced_initial_state(
            session_id="custom_session",
            game_mode="daily",
            scenario_id="custom_scenario"
        )

        assert state.meta.session_id == "custom_session"
        assert state.game.scenario_id == "custom_scenario"

    def test_game_state_increment_turn(self):
        """턴 증가 기능"""
        state = create_enhanced_initial_state("test")
        initial_turn = state.game.turn

        state.game.increment_turn()
        assert state.game.turn == initial_turn + 1

        state.game.increment_turn()
        assert state.game.turn == initial_turn + 2

    def test_game_state_add_flag(self):
        """플래그 추가 기능"""
        state = create_enhanced_initial_state("test")
        initial_flags = len(state.game.flags)

        state.game.add_flag("test_flag_1")
        assert len(state.game.flags) == initial_flags + 1
        assert "test_flag_1" in state.game.flags

        state.game.add_flag("test_flag_2")
        assert len(state.game.flags) == initial_flags + 2

    def test_game_state_has_flag(self):
        """플래그 존재 확인"""
        state = create_enhanced_initial_state("test")

        state.game.add_flag("existing_flag")
        assert state.game.has_flag("existing_flag") is True
        assert state.game.has_flag("nonexistent_flag") is False

    def test_character_data_update_affinity(self):
        """친밀도 업데이트"""
        char_data = CharacterData()
        char_data.affinity["tanjiro"] = 100

        char_data.update_affinity("tanjiro", 50)
        assert char_data.affinity["tanjiro"] == 150

        char_data.update_affinity("tanjiro", -30)
        assert char_data.affinity["tanjiro"] == 120

    def test_character_data_get_affinity_new_character(self):
        """새로운 캐릭터의 친밀도 조회"""
        char_data = CharacterData()

        # 새 캐릭터는 기본값 0
        affinity = char_data.get_affinity("new_character")
        assert affinity == 0

    def test_character_data_get_affinity_existing_character(self):
        """기존 캐릭터의 친밀도 조회"""
        char_data = CharacterData()
        char_data.affinity["tanjiro"] = 500

        affinity = char_data.get_affinity("tanjiro")
        assert affinity == 500

    def test_character_data_add_character(self):
        """캐릭터 추가"""
        char_data = CharacterData()
        initial_count = len(char_data.available_characters)

        char_data.add_character("tanjiro")
        assert len(char_data.available_characters) == initial_count + 1
        assert "tanjiro" in char_data.available_characters

    def test_character_data_remove_character(self):
        """캐릭터 제거"""
        char_data = CharacterData()
        char_data.add_character("tanjiro")

        char_data.remove_character("tanjiro")
        assert "tanjiro" not in char_data.available_characters

    def test_character_data_remove_nonexistent_character(self):
        """존재하지 않는 캐릭터 제거 시도"""
        char_data = CharacterData()

        # 오류 없이 처리되어야 함
        char_data.remove_character("nonexistent")
        assert "nonexistent" not in char_data.available_characters

    def test_output_data_add_dialogue(self):
        """대화 추가"""
        output = OutputData()
        initial_count = len(output.dialogues)

        output.add_dialogue("tanjiro", "안녕하세요!", "friendly")
        assert len(output.dialogues) == initial_count + 1

        last_dialogue = output.dialogues[-1]
        assert last_dialogue.speaker == "tanjiro"
        assert last_dialogue.content == "안녕하세요!"
        assert last_dialogue.emotion == "friendly"

    def test_output_data_add_multiple_dialogues(self):
        """여러 대화 추가"""
        output = OutputData()

        output.add_dialogue("tanjiro", "첫 번째", "neutral")
        output.add_dialogue("inosuke", "두 번째", "angry")
        output.add_dialogue("zenitsu", "세 번째", "scared")

        assert len(output.dialogues) == 3
        assert output.dialogues[0].speaker == "tanjiro"
        assert output.dialogues[1].speaker == "inosuke"
        assert output.dialogues[2].speaker == "zenitsu"

    def test_output_data_add_choice(self):
        """선택지 추가"""
        output = OutputData()
        initial_count = len(output.choices)

        output.add_choice("choice_1", "첫 번째 선택")
        assert len(output.choices) == initial_count + 1

        last_choice = output.choices[-1]
        assert last_choice.id == "choice_1"
        assert last_choice.text == "첫 번째 선택"

    def test_output_data_add_system_message(self):
        """시스템 메시지 추가"""
        output = OutputData()
        initial_count = len(output.system_messages)

        output.add_system_message("시스템 알림")
        assert len(output.system_messages) == initial_count + 1
        assert output.system_messages[-1] == "시스템 알림"

    def test_user_chat_input_creation(self):
        """UserChatInput 생성"""
        user_input = UserChatInput(
            content="테스트 입력",
            chat_no=1,
            timestamp=datetime.now().isoformat()
        )

        assert user_input.content == "테스트 입력"
        assert user_input.chat_no == 1
        assert user_input.input_method == "text"

    def test_meta_data_creation(self):
        """MetaData 생성"""
        meta = MetaData(
            session_id="test_session",
            timestamp=datetime.now().isoformat(),
            version="1.0"
        )

        assert meta.session_id == "test_session"
        assert meta.version == "1.0"
        assert meta.processed_by == ""

    def test_game_state_flags_default_empty(self):
        """플래그 기본값은 빈 리스트"""
        state = create_enhanced_initial_state("test")
        assert isinstance(state.game.flags, list)
        assert len(state.game.flags) == 0

    def test_game_state_temp_data_default_empty(self):
        """temp_data 기본값은 빈 dict"""
        state = create_enhanced_initial_state("test")
        assert isinstance(state.game.temp_data, dict)
        assert len(state.game.temp_data) == 0

    def test_character_data_affinity_default_empty(self):
        """affinity 기본값은 빈 dict"""
        char_data = CharacterData()
        assert isinstance(char_data.affinity, dict)
        assert len(char_data.affinity) == 0

    def test_node_type_enum_values(self):
        """NodeType enum 값 확인"""
        assert NodeType.PARENT.value == "parent_agent"
        assert NodeType.CHILDREN.value == "children_agent"
        assert NodeType.END.value == "end"

    def test_state_next_node_transitions(self):
        """상태의 next_node 전환"""
        state = create_enhanced_initial_state("test")

        state.next_node = NodeType.PARENT.value
        assert state.next_node == "parent_agent"

        state.next_node = NodeType.CHILDREN.value
        assert state.next_node == "children_agent"

        state.next_node = NodeType.END.value
        assert state.next_node == "end"

    def test_game_state_character_remaining_turns(self):
        """캐릭터별 남은 턴 초기화"""
        state = create_enhanced_initial_state("test")

        assert isinstance(state.game.character_remaining_turns, dict)
        assert "inosuke" in state.game.character_remaining_turns
        assert "zenitsu" in state.game.character_remaining_turns
        assert state.game.character_remaining_turns["inosuke"] == 3
        assert state.game.character_remaining_turns["zenitsu"] == 3

    def test_affinity_update_multiple_characters(self):
        """여러 캐릭터 친밀도 동시 업데이트"""
        char_data = CharacterData()

        char_data.update_affinity("tanjiro", 100)
        char_data.update_affinity("inosuke", 50)
        char_data.update_affinity("zenitsu", 75)

        assert char_data.affinity["tanjiro"] == 100
        assert char_data.affinity["inosuke"] == 50
        assert char_data.affinity["zenitsu"] == 75

    def test_output_data_clear_dialogues(self):
        """대화 초기화"""
        output = OutputData()
        output.add_dialogue("tanjiro", "테스트", "neutral")
        output.add_dialogue("inosuke", "테스트2", "angry")

        output.dialogues = []
        assert len(output.dialogues) == 0

    def test_game_state_scenario_data_assignment(self):
        """시나리오 데이터 할당"""
        state = create_enhanced_initial_state("test")

        test_scenario = {
            "scenario_id": "test_scenario",
            "title": "테스트 시나리오",
            "stages": {}
        }

        state.game.scenario_data = test_scenario
        assert state.game.scenario_data == test_scenario
        assert state.game.scenario_data["scenario_id"] == "test_scenario"

    def test_game_state_current_stage_transitions(self):
        """현재 스테이지 전환"""
        state = create_enhanced_initial_state("test")

        state.game.current_stage = "intro"
        assert state.game.current_stage == "intro"

        state.game.current_stage = "fork"
        assert state.game.current_stage == "fork"

        state.game.current_stage = "recruit_mission"
        assert state.game.current_stage == "recruit_mission"

    def test_meta_data_timestamp_update(self):
        """메타데이터 타임스탬프 업데이트"""
        state = create_enhanced_initial_state("test")
        old_timestamp = state.meta.timestamp

        import time
        time.sleep(0.01)

        state.meta.timestamp = datetime.now().isoformat()
        assert state.meta.timestamp != old_timestamp

    def test_meta_data_processed_by_update(self):
        """처리자 정보 업데이트"""
        state = create_enhanced_initial_state("test")

        state.meta.processed_by = "parent_agent"
        assert state.meta.processed_by == "parent_agent"

        state.meta.processed_by = "dialogue_agent"
        assert state.meta.processed_by == "dialogue_agent"
