"""
턴제 로직 단위 테스트
"""
import pytest
from mission_manager import MissionManager, MissionStatus


class TestTurnSystem:
    """턴제 시스템 테스트"""

    def test_mission_turn_limit_6(self, mission_manager):
        """미션 전체 턴 제한 6턴 검증"""
        state = mission_manager.start_mission()

        # 6턴까지 성공 입력
        test_inputs = [
            ("이노스케", "inosuke"),
            ("약한 녀석", "inosuke"),
            ("함께 싸우자", "inosuke"),
            ("젠이츠", "zenitsu"),
            ("네즈코 위험해", "zenitsu"),
            ("함께 지키자", "zenitsu")
        ]

        for user_input, target in test_inputs:
            mission_manager.process_user_input(state, user_input, target, increment_turn_on_success=True)

        # 6턴 사용 확인
        assert state.current_turn == 6

        # 미션 상태 확인
        status, msg = mission_manager.check_completion(state)
        assert status == MissionStatus.SUCCESS

    def test_turn_only_increments_on_success(self, mission_manager):
        """성공 시에만 턴 증가 확인"""
        state = mission_manager.start_mission()

        # 실패 입력 (키워드 불일치)
        success, msg, response = mission_manager.process_user_input(
            state, "잘못된 입력", "inosuke", increment_turn_on_success=True
        )

        assert success is False
        assert state.current_turn == 0  # 턴 증가 안 함

        # 성공 입력
        success, msg, response = mission_manager.process_user_input(
            state, "이노스케", "inosuke", increment_turn_on_success=True
        )

        assert success is True
        assert state.current_turn == 1  # 턴 증가

    def test_crisis_messages_at_correct_turns(self, mission_manager):
        """위기 메시지가 턴 2, 4, 6에 정확히 표시되는지 확인"""
        state = mission_manager.start_mission()

        # 턴 1: 위기 메시지 없음
        mission_manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        crisis = mission_manager.get_crisis_message(1)
        assert crisis is None

        # 턴 2: 위기 메시지 있음
        mission_manager.process_user_input(state, "약한 녀석", "inosuke", increment_turn_on_success=True)
        crisis = mission_manager.get_crisis_message(2)
        assert crisis is not None
        assert "강철" in crisis or "굉음" in crisis

        # 턴 3: 위기 메시지 없음
        mission_manager.process_user_input(state, "함께 싸우자", "inosuke", increment_turn_on_success=True)
        crisis = mission_manager.get_crisis_message(3)
        assert crisis is None

        # 턴 4: 위기 메시지 있음
        mission_manager.process_user_input(state, "젠이츠", "zenitsu", increment_turn_on_success=True)
        crisis = mission_manager.get_crisis_message(4)
        assert crisis is not None
        assert "렌고쿠" in crisis or "신음" in crisis

    def test_turn_count_persists_across_attempts(self, mission_manager):
        """여러 시도에 걸쳐 턴 카운트가 유지되는지 확인"""
        state = mission_manager.start_mission()

        # 첫 번째 성공
        mission_manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        assert state.current_turn == 1

        # 실패 (턴 유지)
        mission_manager.process_user_input(state, "완전히 틀린 말", "inosuke", increment_turn_on_success=True)
        assert state.current_turn == 1

        # 두 번째 성공
        mission_manager.process_user_input(state, "약한 녀석", "inosuke", increment_turn_on_success=True)
        assert state.current_turn == 2

    def test_max_turns_timeout(self, mission_manager):
        """6턴 초과 시 타임아웃 확인"""
        state = mission_manager.start_mission()

        # 5턴 성공 입력 (inosuke 완료 3턴, zenitsu 2턴만 완료)
        inputs = [
            ("이노스케", "inosuke"),       # turn 1
            ("약한 녀석", "inosuke"),       # turn 2
            ("함께", "inosuke"),           # turn 3 - inosuke recruited
            ("젠이츠", "zenitsu"),          # turn 4
            ("네즈코", "zenitsu"),         # turn 5 - zenitsu stage 1 complete, but not recruited
        ]

        for user_input, target in inputs:
            mission_manager.process_user_input(state, user_input, target, increment_turn_on_success=True)

        # 5턴 후, 1번 더 실패 시도하여 6턴 도달하지 않음
        # 대신 수동으로 턴을 6으로 설정
        state.current_turn = 6

        # 미션 완료 체크 (zenitsu 설득 미완료)
        status, msg = mission_manager.check_completion(state)

        # 설득 완료되지 않았으므로 TIMEOUT
        assert status == MissionStatus.TIMEOUT

    def test_increment_turn_flag_false(self, mission_manager):
        """increment_turn_on_success=False 시 턴 증가하지 않음"""
        state = mission_manager.start_mission()

        # 성공이지만 increment_turn_on_success=False
        success, msg, response = mission_manager.process_user_input(
            state, "이노스케", "inosuke", increment_turn_on_success=False
        )

        assert success is True
        assert state.current_turn == 0  # 턴 증가 안 함


class TestTurnProgression:
    """턴 진행 시뮬레이션 테스트"""

    def test_perfect_6_turn_sequence(self, mission_manager):
        """완벽한 6턴 시퀀스로 히든 엔딩 달성"""
        state = mission_manager.start_mission()

        sequence = [
            ("이노스케", "inosuke", 1),
            ("약한 녀석", "inosuke", 2),
            ("함께 싸우자", "inosuke", 3),
            ("젠이츠", "zenitsu", 4),
            ("네즈코 위험해", "zenitsu", 5),
            ("함께 지키자", "zenitsu", 6)
        ]

        for user_input, target, expected_turn in sequence:
            mission_manager.process_user_input(state, user_input, target, increment_turn_on_success=True)
            assert state.current_turn == expected_turn

        # 최종 상태 확인
        status, msg = mission_manager.check_completion(state)
        assert status == MissionStatus.SUCCESS
        assert state.current_turn == 6

    def test_turn_with_retries(self, mission_manager):
        """실패 재시도를 포함한 턴 진행"""
        state = mission_manager.start_mission()

        # 첫 번째 단계: 성공
        mission_manager.process_user_input(state, "이노스케", "inosuke", increment_turn_on_success=True)
        assert state.current_turn == 1

        # 두 번째 단계: 실패 2회 + 성공
        mission_manager.process_user_input(state, "완전히 틀린 말 1", "inosuke", increment_turn_on_success=True)
        assert state.current_turn == 1  # 턴 유지

        mission_manager.process_user_input(state, "완전히 틀린 말 2", "inosuke", increment_turn_on_success=True)
        assert state.current_turn == 1  # 턴 유지

        mission_manager.process_user_input(state, "약한 녀석", "inosuke", increment_turn_on_success=True)
        assert state.current_turn == 2  # 턴 증가
