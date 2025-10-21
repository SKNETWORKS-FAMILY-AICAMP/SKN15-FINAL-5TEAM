#!/usr/bin/env python3
"""
미커버 경로 테스트 - Coverage 향상용

affinity_system.py, mission_manager.py의 미커버 분기 및 엣지케이스 테스트
"""
import pytest
from affinity_system import AffinitySystem, AffinityLevel
from mission_manager import MissionManager
from agent_state_enhanced import CharacterData


class TestAffinitySystemUncoveredPaths:
    """AffinitySystem 미커버 경로 테스트"""

    def test_get_tone_with_unknown_character(self):
        """알 수 없는 캐릭터 말투 조회"""
        affinity_system = AffinitySystem()

        # 존재하지 않는 캐릭터
        tone = affinity_system.get_tone("unknown_character", 500)
        assert tone is None

    def test_get_level_description_all_levels(self):
        """모든 레벨의 설명 조회"""
        affinity_system = AffinitySystem()

        test_cases = [
            (0, "낯선 사람 (0-199)"),
            (200, "아는 사이 (200-399)"),
            (400, "친구 (400-599)"),
            (600, "절친 (600-799)"),
            (800, "영혼의 동반자 (800-1000)")
        ]

        for score, expected_desc in test_cases:
            desc = affinity_system.get_level_description(score)
            assert expected_desc in desc

    def test_calculate_change_with_all_positive_actions(self):
        """모든 긍정 액션 조합 테스트"""
        affinity_system = AffinitySystem()

        # 모든 긍정 액션 한번에
        actions = {
            "dialogue_frequency": 1,    # +5
            "alignment_match": 1,       # +10
            "cooperation": 1,           # +15
            "praise": 1,                # +20
            "gift": 1,                  # +25
            "save_life": 1              # +50
        }

        change = affinity_system.calculate_change(actions)
        expected = 5 + 10 + 15 + 20 + 25 + 50  # 125
        assert change == expected

    def test_calculate_change_with_all_negative_actions(self):
        """모든 부정 액션 조합 테스트"""
        affinity_system = AffinitySystem()

        # 모든 부정 액션 한번에
        actions = {
            "rudeness": 1,      # -10
            "selfishness": 1,   # -15
            "betrayal": 1,      # -30
            "attack": 1         # -50
        }

        change = affinity_system.calculate_change(actions)
        expected = -(10 + 15 + 30 + 50)  # -105
        assert change == expected

    def test_update_affinity_extreme_values(self):
        """극단적인 친밀도 값 업데이트"""
        affinity_system = AffinitySystem()

        # 매우 큰 증가
        new_affinity, msg = affinity_system.update_affinity(900, 500)
        assert new_affinity == 1000
        assert "1000" in msg

        # 매우 큰 감소
        new_affinity, msg = affinity_system.update_affinity(100, -500)
        assert new_affinity == 0
        assert "0" in msg


class TestMissionManagerUncoveredPaths:
    """MissionManager 미커버 경로 테스트"""

    def test_wrong_order_detection(self):
        """잘못된 순서 감지"""
        mission_data = {
            "title": "테스트 미션",
            "max_turns": 6,
            "characters": {
                "inosuke": {
                    "name": "이노스케",
                    "correct_order": 1,
                    "conversation_stages": [
                        {
                            "stage": 0,
                            "required_keywords": ["이노스케"],
                            "success_response": {"content": "OK"},
                            "failure_response": {"content": "NO"}
                        }
                    ],
                    "max_attempts": 3
                },
                "zenitsu": {
                    "name": "젠이츠",
                    "correct_order": 2,
                    "conversation_stages": [
                        {
                            "stage": 0,
                            "required_keywords": ["젠이츠"],
                            "success_response": {"content": "OK"},
                            "failure_response": {"content": "NO"}
                        }
                    ],
                    "max_attempts": 3
                }
            },
            "crisis_progression": {
                "messages": [
                    {"turn": 2, "message": "위기!", "crisis_level": 2}
                ]
            }
        }

        manager = MissionManager(mission_data)
        state = manager.start_mission()

        # zenitsu를 먼저 시도 (잘못된 순서)
        success, msg, _ = manager.process_user_input(
            state, "젠이츠", "zenitsu", increment_turn_on_success=False
        )

        assert success is False
        assert "순서" in msg or "먼저" in msg

    def test_max_attempts_exceeded(self):
        """최대 시도 횟수 초과"""
        mission_data = {
            "title": "테스트 미션",
            "max_turns": 6,
            "characters": {
                "inosuke": {
                    "name": "이노스케",
                    "correct_order": 1,
                    "conversation_stages": [
                        {
                            "stage": 0,
                            "required_keywords": ["정답"],
                            "success_response": {"content": "OK"},
                            "failure_response": {"content": "NO"}
                        }
                    ],
                    "max_attempts": 2  # 최대 2번
                }
            },
            "crisis_progression": {"messages": []}
        }

        manager = MissionManager(mission_data)
        state = manager.start_mission()

        # 2번 실패
        for _ in range(2):
            success, msg, _ = manager.process_user_input(
                state, "틀린답", "inosuke", increment_turn_on_success=False
            )
            assert success is False

        # 3번째 시도 - 최대 시도 초과
        success, msg, _ = manager.process_user_input(
            state, "틀린답", "inosuke", increment_turn_on_success=False
        )

        assert success is False
        assert "최대" in msg or "시도" in msg

    def test_crisis_message_retrieval(self):
        """위기 메시지 조회"""
        mission_data = {
            "title": "테스트 미션",
            "max_turns": 6,
            "characters": {},
            "crisis_progression": {
                "messages": [
                    {"turn": 2, "message": "위기 레벨 2", "crisis_level": 2},
                    {"turn": 4, "message": "위기 레벨 4", "crisis_level": 4},
                    {"turn": 6, "message": "위기 레벨 6", "crisis_level": 6}
                ]
            }
        }

        manager = MissionManager(mission_data)
        state = manager.start_mission()

        # 턴 2에서 위기 메시지
        state.current_turn = 2
        crisis = manager.get_crisis_message(2)
        assert crisis == "위기 레벨 2"

        # 턴 3에서는 위기 메시지 없음
        crisis = manager.get_crisis_message(3)
        assert crisis is None

        # 턴 4에서 위기 메시지
        crisis = manager.get_crisis_message(4)
        assert crisis == "위기 레벨 4"


class TestCharacterDataUncoveredPaths:
    """CharacterData 미커버 경로 테스트"""

    def test_get_affinity_for_new_character(self):
        """새 캐릭터의 기본 친밀도"""
        char_data = CharacterData()

        # 새 캐릭터는 친밀도 0
        affinity = char_data.get_affinity("new_character")
        assert affinity == 0

    def test_update_affinity_multiple_times(self):
        """여러 번 친밀도 업데이트"""
        char_data = CharacterData()

        # 첫 업데이트
        char_data.update_affinity("tanjiro", 100)
        assert char_data.affinity["tanjiro"] == 100

        # 두 번째 업데이트 (누적)
        char_data.update_affinity("tanjiro", 50)
        assert char_data.affinity["tanjiro"] == 150

        # 세 번째 업데이트 (감소)
        char_data.update_affinity("tanjiro", -30)
        assert char_data.affinity["tanjiro"] == 120

    def test_affinity_clamping(self):
        """친밀도 범위 제한"""
        char_data = CharacterData()

        # 1000 초과 방지
        char_data.update_affinity("test", 2000)
        assert char_data.affinity["test"] == 1000

        # 0 미만 방지
        char_data.update_affinity("test2", -100)
        assert char_data.affinity["test2"] == 0

    def test_affinity_level_calculation(self):
        """친밀도 레벨 계산"""
        char_data = CharacterData()

        # Low level (< 300)
        char_data.update_affinity("char1", 100)
        assert char_data.affinity_levels["char1"] == "low"

        # Mid level (300-699)
        char_data.update_affinity("char2", 500)
        assert char_data.affinity_levels["char2"] == "mid"

        # High level (>= 700)
        char_data.update_affinity("char3", 800)
        assert char_data.affinity_levels["char3"] == "high"
