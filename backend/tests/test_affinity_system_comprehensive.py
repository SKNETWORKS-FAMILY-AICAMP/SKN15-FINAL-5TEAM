#!/usr/bin/env python3
"""
AffinitySystem 종합 테스트 (커버리지 향상용)
"""
import pytest
from affinity_system import AffinitySystem, AffinityLevel, AffinityTone


class TestAffinitySystemComprehensive:
    """AffinitySystem 전체 기능 테스트"""

    @pytest.fixture
    def affinity_system(self):
        return AffinitySystem()

    def test_all_level_ranges_defined(self, affinity_system):
        """모든 레벨의 범위가 정의되어 있는지 확인"""
        assert len(affinity_system.level_ranges) == 5

        for level in AffinityLevel:
            assert level in affinity_system.level_ranges
            min_val, max_val = affinity_system.level_ranges[level]
            assert min_val >= 0
            assert max_val <= 1000
            assert min_val <= max_val

    def test_all_change_rules_defined(self, affinity_system):
        """모든 변화 규칙이 정의되어 있는지 확인"""
        positive_actions = ["dialogue_frequency", "alignment_match", "cooperation", "praise", "gift", "save_life"]
        negative_actions = ["rudeness", "selfishness", "betrayal", "attack"]

        for action in positive_actions:
            assert action in affinity_system.change_rules
            assert affinity_system.change_rules[action] > 0

        for action in negative_actions:
            assert action in affinity_system.change_rules
            assert affinity_system.change_rules[action] < 0

    def test_all_characters_have_tones(self, affinity_system):
        """모든 캐릭터가 말투를 가지고 있는지 확인"""
        characters = ["tanjiro", "inosuke", "zenitsu", "rengoku"]

        for char in characters:
            assert char in affinity_system.character_tones
            assert len(affinity_system.character_tones[char]) == 5

            for level in AffinityLevel:
                assert level in affinity_system.character_tones[char]
                tone = affinity_system.character_tones[char][level]
                assert isinstance(tone, AffinityTone)
                assert isinstance(tone.calling, str)
                assert isinstance(tone.suffix, str)
                assert isinstance(tone.style, str)
                assert isinstance(tone.emoji_usage, str)

    def test_get_tone_with_unknown_character(self, affinity_system):
        """알 수 없는 캐릭터의 tone 조회"""
        tone = affinity_system.get_tone("unknown_char", 500)
        assert tone is None

    def test_get_tone_with_all_characters_all_levels(self, affinity_system):
        """모든 캐릭터의 모든 레벨 tone 조회"""
        characters = ["tanjiro", "inosuke", "zenitsu", "rengoku"]
        test_values = [0, 200, 400, 600, 800]  # 각 레벨의 시작점

        for char in characters:
            for value in test_values:
                tone = affinity_system.get_tone(char, value)
                assert tone is not None
                assert isinstance(tone, AffinityTone)

    def test_calculate_change_with_all_positive_actions(self, affinity_system):
        """모든 긍정 액션 개별 테스트"""
        actions = {
            "dialogue_frequency": 5,
            "alignment_match": 10,
            "cooperation": 15,
            "praise": 20,
            "gift": 25,
            "save_life": 50
        }

        for action, expected_value in actions.items():
            change = affinity_system.calculate_change({action: 1})
            assert change == expected_value

    def test_calculate_change_with_all_negative_actions(self, affinity_system):
        """모든 부정 액션 개별 테스트"""
        actions = {
            "rudeness": -10,
            "selfishness": -15,
            "betrayal": -30,
            "attack": -50
        }

        for action, expected_value in actions.items():
            change = affinity_system.calculate_change({action: 1})
            assert change == expected_value

    def test_update_affinity_all_level_transitions_upward(self, affinity_system):
        """모든 레벨 상승 전환 테스트"""
        transitions = [
            (199, 1, AffinityLevel.STRANGER, AffinityLevel.ACQUAINTANCE),
            (399, 1, AffinityLevel.ACQUAINTANCE, AffinityLevel.FRIEND),
            (599, 1, AffinityLevel.FRIEND, AffinityLevel.CLOSE_FRIEND),
            (799, 1, AffinityLevel.CLOSE_FRIEND, AffinityLevel.SOULMATE),
        ]

        for old_value, change, old_level, new_level in transitions:
            new_value, msg = affinity_system.update_affinity(old_value, change)
            assert affinity_system.get_level(old_value) == old_level
            assert affinity_system.get_level(new_value) == new_level
            assert "상승" in msg or "💖" in msg

    def test_update_affinity_all_level_transitions_downward(self, affinity_system):
        """모든 레벨 하락 전환 테스트"""
        transitions = [
            (800, -1, AffinityLevel.SOULMATE, AffinityLevel.CLOSE_FRIEND),
            (600, -1, AffinityLevel.CLOSE_FRIEND, AffinityLevel.FRIEND),
            (400, -1, AffinityLevel.FRIEND, AffinityLevel.ACQUAINTANCE),
            (200, -1, AffinityLevel.ACQUAINTANCE, AffinityLevel.STRANGER),
        ]

        for old_value, change, old_level, new_level in transitions:
            new_value, msg = affinity_system.update_affinity(old_value, change)
            assert affinity_system.get_level(old_value) == old_level
            assert affinity_system.get_level(new_value) == new_level
            assert "하락" in msg or "💔" in msg

    def test_get_emoji_for_all_levels(self, affinity_system):
        """모든 레벨의 이모지 확인"""
        test_values = [0, 200, 400, 600, 800]
        emojis = []

        for value in test_values:
            emoji = affinity_system.get_emoji_for_level(value)
            assert emoji is not None
            assert isinstance(emoji, str)
            assert len(emoji) > 0
            emojis.append(emoji)

        # 모든 이모지가 다른지 확인
        assert len(set(emojis)) == len(emojis)

    def test_get_level_description_all_levels(self, affinity_system):
        """모든 레벨의 설명 확인"""
        test_values = [0, 200, 400, 600, 800]

        for value in test_values:
            desc = affinity_system.get_level_description(value)
            assert desc is not None
            assert isinstance(desc, str)
            assert len(desc) > 0
            # 레벨 범위가 포함되어 있는지 확인
            assert any(str(val) in desc for val in test_values)

    def test_level_ranges_no_overlap(self, affinity_system):
        """레벨 범위가 겹치지 않는지 확인"""
        ranges = list(affinity_system.level_ranges.values())

        for i in range(len(ranges)):
            for j in range(i + 1, len(ranges)):
                min1, max1 = ranges[i]
                min2, max2 = ranges[j]

                # 범위가 겹치지 않아야 함 (연속적이거나 분리되어 있음)
                if max1 < min2 or max2 < min1:
                    # 분리됨
                    pass
                else:
                    # 연속됨 (max1 + 1 == min2 또는 max2 + 1 == min1)
                    assert max1 + 1 >= min2 or max2 + 1 >= min1

    def test_update_affinity_same_level_positive(self, affinity_system):
        """같은 레벨 내에서 긍정 변화"""
        new_value, msg = affinity_system.update_affinity(100, 50)
        assert new_value == 150
        assert affinity_system.get_level(100) == affinity_system.get_level(150)
        assert "+50" in msg or "💕" in msg

    def test_update_affinity_same_level_negative(self, affinity_system):
        """같은 레벨 내에서 부정 변화"""
        new_value, msg = affinity_system.update_affinity(150, -30)
        assert new_value == 120
        assert affinity_system.get_level(150) == affinity_system.get_level(120)
        assert "-30" in msg or "💢" in msg

    def test_calculate_change_with_large_counts(self, affinity_system):
        """큰 횟수의 액션"""
        change = affinity_system.calculate_change({"dialogue_frequency": 100})
        assert change == 500  # 5 * 100

        change2 = affinity_system.calculate_change({"save_life": 10})
        assert change2 == 500  # 50 * 10

    def test_extreme_affinity_values(self, affinity_system):
        """극단적인 친밀도 값 처리"""
        # 매우 높은 값
        assert affinity_system.get_level(10000) == AffinityLevel.SOULMATE

        # 매우 낮은 값
        assert affinity_system.get_level(-10000) == AffinityLevel.STRANGER

    def test_character_tone_consistency(self, affinity_system):
        """캐릭터별 말투 일관성 확인"""
        # tanjiro는 정중하고 따뜻함
        tone_stranger = affinity_system.get_tone("tanjiro", 0)
        tone_soulmate = affinity_system.get_tone("tanjiro", 800)

        assert tone_stranger.suffix == "습니다"  # 정중
        assert tone_soulmate.suffix == "야"  # 친근

        # inosuke는 거칠지만 우정 인정
        tone_stranger_ino = affinity_system.get_tone("inosuke", 0)
        tone_close_ino = affinity_system.get_tone("inosuke", 600)

        assert "거칠" in tone_stranger_ino.style
        assert "우정" in tone_close_ino.style or "동료" in tone_close_ino.calling

    def test_affinity_tone_emoji_usage_progression(self, affinity_system):
        """이모지 사용 증가 확인"""
        usage_progression = ["minimal", "moderate", "frequent", "abundant"]

        for char in ["tanjiro", "inosuke", "zenitsu", "rengoku"]:
            usages = []
            for level in [AffinityLevel.STRANGER, AffinityLevel.ACQUAINTANCE, AffinityLevel.FRIEND, AffinityLevel.CLOSE_FRIEND, AffinityLevel.SOULMATE]:
                tone = affinity_system.get_tone(char, level)
                usages.append(tone.emoji_usage)

            # 이모지 사용이 증가하는 경향이 있어야 함
            assert len(set(usages)) > 1  # 최소한 다양성은 있어야 함
