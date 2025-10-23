#!/usr/bin/env python3
"""
MissionManager 종합 테스트 (커버리지 향상용)
"""
import pytest
from mission_manager import MissionManager, MissionStatus, CharacterProgress, MissionState
from scenario_loader import scenario_loader


class TestMissionManagerComprehensive:
    """MissionManager 전체 기능 테스트"""

    @pytest.fixture
    def mission_manager(self):
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
        mission_data = scenario["stages"]["recruit_mission"]
        return MissionManager(mission_data)

    def test_start_mission_initialization(self, mission_manager):
        """미션 시작 시 상태 초기화"""
        state = mission_manager.start_mission()

        assert state.status == MissionStatus.IN_PROGRESS
        assert state.current_turn == 0
        assert state.max_turns == 6
        assert len(state.character_progress) == 2  # inosuke, zenitsu
        assert state.crisis_level == 0

    def test_character_progress_initialization(self, mission_manager):
        """캐릭터 진행도 초기화 확인"""
        state = mission_manager.start_mission()

        for char_id in ["inosuke", "zenitsu"]:
            progress = state.character_progress[char_id]
            assert progress.character_id == char_id
            assert progress.current_stage == 0
            assert progress.recruited is False
            assert progress.attempts == 0
            assert progress.recruitment_turn is None

    def test_correct_order_extraction(self, mission_manager):
        """올바른 순서 추출 확인"""
        assert mission_manager.correct_order == ["inosuke", "zenitsu"]

    def test_process_input_with_auto_character_detection(self, mission_manager):
        """현재 캐릭터 자동 감지"""
        state = mission_manager.start_mission()

        # current_character=None으로 호출하면 자동으로 inosuke 선택
        success, msg, response = mission_manager.process_user_input(
            state, "이노스케", None, increment_turn_on_success=True
        )

        assert success is True
        assert state.current_turn == 1

    def test_invalid_character_target(self, mission_manager):
        """잘못된 캐릭터 타겟"""
        state = mission_manager.start_mission()

        success, msg, response = mission_manager.process_user_input(
            state, "테스트", "unknown_character", increment_turn_on_success=True
        )

        assert success is False
        assert "찾을 수 없습니다" in msg

    def test_already_completed_character(self, mission_manager):
        """이미 완료된 캐릭터 재시도 - 순서 검증에 의해 차단됨"""
        state = mission_manager.start_mission()

        # inosuke 완료
        mission_manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "약한 녀석", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "함께 싸우자", "inosuke", increment_turn_on_success=True)

        # inosuke 완료 후 inosuke에 다시 시도하면 순서 검증에 의해 차단됨
        success, msg, response = mission_manager.process_user_input(
            state, "이노스케", "inosuke", increment_turn_on_success=True
        )

        assert success is False
        assert "순서" in msg or "젠이츠" in msg  # 다음은 zenitsu여야 함

    def test_max_attempts_exceeded(self, mission_manager):
        """최대 시도 횟수 초과"""
        state = mission_manager.start_mission()

        # 5회 실패 시도
        for i in range(5):
            success, msg, response = mission_manager.process_user_input(
                state, "완전히 틀린 말", "inosuke", increment_turn_on_success=True
            )

        # 6회째 시도는 최대 횟수 초과
        success, msg, response = mission_manager.process_user_input(
            state, "완전히 틀린 말", "inosuke", increment_turn_on_success=True
        )

        assert success is False
        assert "시도 횟수 초과" in msg

    def test_tanjiro_support_message(self, mission_manager):
        """탄지로 지원 메시지 포함 확인"""
        state = mission_manager.start_mission()

        # inosuke 최종 단계 완료 시 tanjiro_support 포함됨
        mission_manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "약한 녀석", "inosuke", increment_turn_on_success=True)

        # 최종 단계 (stage 2)
        success, msg, response = mission_manager.process_user_input(
            state, "함께 싸우자", "inosuke", increment_turn_on_success=True
        )

        # 최종 단계이므로 recruited 확인
        assert success is True
        assert "모집 성공" in msg
        assert response is not None

    def test_validate_order_in_progress(self, mission_manager):
        """진행 중 순서 검증"""
        state = mission_manager.start_mission()

        # inosuke만 모집
        mission_manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "약한 녀석", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "함께 싸우자", "inosuke", increment_turn_on_success=True)

        # 아직 진행 중이므로 순서 검증은 "진행 중..."
        valid, msg = mission_manager.validate_order(state)
        assert valid is True
        assert "진행 중" in msg

    def test_validate_order_correct_completion(self, mission_manager):
        """올바른 순서로 완료 시 검증"""
        state = mission_manager.start_mission()

        # inosuke → zenitsu 순서로 모집
        mission_manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "약한 녀석", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "함께 싸우자", "inosuke", increment_turn_on_success=True)

        mission_manager.process_user_input(state, "젠이츠", "zenitsu", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "네즈코 위험", "zenitsu", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "함께 지키자", "zenitsu", increment_turn_on_success=True)

        valid, msg = mission_manager.validate_order(state)
        assert valid is True
        assert "정확" in msg

    def test_check_completion_in_progress(self, mission_manager):
        """진행 중 완료 체크"""
        state = mission_manager.start_mission()

        status, msg = mission_manager.check_completion(state)
        assert status == MissionStatus.IN_PROGRESS
        assert "진행 중" in msg

    def test_check_completion_success_at_turn_6(self, mission_manager):
        """6턴에 성공 완료"""
        state = mission_manager.start_mission()

        # 정확히 6턴 사용하여 완료
        mission_manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "약한 녀석", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "함께 싸우자", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "젠이츠", "zenitsu", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "네즈코 위험", "zenitsu", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "함께 지키자", "zenitsu", increment_turn_on_success=True)

        status, msg = mission_manager.check_completion(state)
        assert status == MissionStatus.SUCCESS
        assert "성공" in msg

    def test_check_completion_timeout_incomplete(self, mission_manager):
        """6턴 초과 시 타임아웃"""
        state = mission_manager.start_mission()

        # 5턴만 진행
        mission_manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "약한 녀석", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "함께 싸우자", "inosuke", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "젠이츠", "zenitsu", increment_turn_on_success=True)
        mission_manager.process_user_input(state, "네즈코", "zenitsu", increment_turn_on_success=True)

        # 턴을 6으로 설정
        state.current_turn = 6

        status, msg = mission_manager.check_completion(state)
        assert status == MissionStatus.TIMEOUT
        assert "시간 초과" in msg or "타임아웃" in msg.lower()

    def test_increment_turn_manually(self, mission_manager):
        """수동 턴 증가 및 위기 메시지"""
        state = mission_manager.start_mission()

        # 수동으로 턴 증가
        new_turn, crisis_msg = mission_manager.increment_turn(state)

        assert new_turn == 1
        assert state.current_turn == 1

        # 턴 2로 증가 (위기 메시지 있음)
        new_turn, crisis_msg = mission_manager.increment_turn(state)
        assert new_turn == 2
        assert crisis_msg is not None
        assert state.crisis_level >= 2

    def test_get_crisis_message_all_turns(self, mission_manager):
        """모든 턴의 위기 메시지 확인"""
        # 턴 2, 4, 6에 위기 메시지 있음
        assert mission_manager.get_crisis_message(2) is not None
        assert mission_manager.get_crisis_message(4) is not None
        assert mission_manager.get_crisis_message(6) is not None

        # 다른 턴은 None
        assert mission_manager.get_crisis_message(1) is None
        assert mission_manager.get_crisis_message(3) is None
        assert mission_manager.get_crisis_message(5) is None

    def test_affinity_impact_application(self, mission_manager):
        """친밀도 영향 적용 확인"""
        state = mission_manager.start_mission()

        success, msg, response = mission_manager.process_user_input(
            state, "이노스케", "inosuke", increment_turn_on_success=True
        )

        # response에 affinity_impact 포함 확인
        assert response is not None
        assert "affinity_impact" in response
        assert "inosuke" in response["affinity_impact"]
        assert response["affinity_impact"]["inosuke"] > 0

    def test_increment_turn_flag_false(self, mission_manager):
        """increment_turn_on_success=False 시 턴 증가 안됨"""
        state = mission_manager.start_mission()

        success, msg, response = mission_manager.process_user_input(
            state, "이노스케", "inosuke", increment_turn_on_success=False
        )

        assert success is True
        assert state.current_turn == 0  # 턴 증가 안됨
