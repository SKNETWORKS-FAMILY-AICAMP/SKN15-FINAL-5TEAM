#!/usr/bin/env python3
"""
친밀도 계산 엣지케이스 테스트
- 레벨 경계값 정확성
- 복합 액션 합산
- 오버플로우/언더플로우 방지
"""
import pytest
from affinity_system import AffinitySystem, AffinityLevel


class TestAffinityEdgeCases:
    """친밀도 시스템 엣지케이스"""

    @pytest.mark.parametrize("score,expected_level", [
        (0, AffinityLevel.STRANGER),
        (1, AffinityLevel.STRANGER),
        (199, AffinityLevel.STRANGER),
        (200, AffinityLevel.ACQUAINTANCE),
        (201, AffinityLevel.ACQUAINTANCE),
        (399, AffinityLevel.ACQUAINTANCE),
        (400, AffinityLevel.FRIEND),
        (401, AffinityLevel.FRIEND),
        (599, AffinityLevel.FRIEND),
        (600, AffinityLevel.CLOSE_FRIEND),
        (601, AffinityLevel.CLOSE_FRIEND),
        (799, AffinityLevel.CLOSE_FRIEND),
        (800, AffinityLevel.SOULMATE),
        (801, AffinityLevel.SOULMATE),
        (999, AffinityLevel.SOULMATE),
        (1000, AffinityLevel.SOULMATE),
    ])
    def test_level_exact_boundaries(self, score, expected_level):
        """레벨 경계값 정확성 (0, 200, 400, 600, 800, 1000)"""
        affinity_system = AffinitySystem()
        assert affinity_system.get_level(score) == expected_level

    def test_negative_score_clamping(self):
        """음수 점수 → 0으로 클램핑"""
        affinity_system = AffinitySystem()
        assert affinity_system.get_level(-100) == AffinityLevel.STRANGER
        assert affinity_system.get_level(-1) == AffinityLevel.STRANGER

    def test_overflow_score_clamping(self):
        """1000 초과 점수 → 1000으로 클램핑"""
        affinity_system = AffinitySystem()
        assert affinity_system.get_level(1001) == AffinityLevel.SOULMATE
        assert affinity_system.get_level(9999) == AffinityLevel.SOULMATE

    def test_combined_positive_actions(self):
        """복합 긍정 액션 합산"""
        affinity_system = AffinitySystem()

        # dialogue_frequency(5) + cooperation(15) + praise(20) = 40
        change = affinity_system.calculate_change({
            "dialogue_frequency": 1,
            "cooperation": 1,
            "praise": 1
        })
        assert change == 40

    def test_combined_negative_actions(self):
        """복합 부정 액션 합산"""
        affinity_system = AffinitySystem()

        # rudeness(-10) + betrayal(-30) = -40
        change = affinity_system.calculate_change({
            "rudeness": 1,
            "betrayal": 1
        })
        assert change == -40

    def test_mixed_positive_negative_actions(self):
        """긍정/부정 혼합 액션"""
        affinity_system = AffinitySystem()

        # save_life(50) + attack(-50) = 0
        change = affinity_system.calculate_change({
            "save_life": 1,
            "attack": 1
        })
        assert change == 0

        # praise(20) + rudeness(-10) = 10
        change2 = affinity_system.calculate_change({
            "praise": 1,
            "rudeness": 1
        })
        assert change2 == 10

    def test_multiple_same_action(self):
        """동일 액션 여러 번"""
        affinity_system = AffinitySystem()

        # dialogue_frequency(5) × 3 = 15
        change = affinity_system.calculate_change({
            "dialogue_frequency": 3
        })
        assert change == 15

        # cooperation(15) × 5 = 75
        change2 = affinity_system.calculate_change({
            "cooperation": 5
        })
        assert change2 == 75

    def test_update_affinity_underflow_protection(self):
        """친밀도 업데이트 시 0 미만 방지"""
        affinity_system = AffinitySystem()

        # 0에서 -100 시도 → 0으로 클램핑
        new_value, msg = affinity_system.update_affinity(0, -100)
        assert new_value == 0
        assert "하락" in msg or "💢" in msg

    def test_update_affinity_overflow_protection(self):
        """친밀도 업데이트 시 1000 초과 방지"""
        affinity_system = AffinitySystem()

        # 950에서 +100 시도 → 1000으로 클램핑
        new_value, msg = affinity_system.update_affinity(950, 100)
        assert new_value == 1000

    def test_level_transition_upward(self):
        """레벨 상승 시 메시지"""
        affinity_system = AffinitySystem()

        # STRANGER(199) → ACQUAINTANCE(200)
        new_value, msg = affinity_system.update_affinity(199, 1)
        assert new_value == 200
        assert "상승" in msg or "💖" in msg
        assert "acquaint" in msg

    def test_level_transition_downward(self):
        """레벨 하락 시 메시지"""
        affinity_system = AffinitySystem()

        # ACQUAINTANCE(200) → STRANGER(199)
        new_value, msg = affinity_system.update_affinity(200, -1)
        assert new_value == 199
        assert "하락" in msg or "💔" in msg

    def test_no_level_change_small_increase(self):
        """레벨 변화 없는 작은 증가"""
        affinity_system = AffinitySystem()

        # STRANGER(100) → STRANGER(110) (레벨 동일)
        new_value, msg = affinity_system.update_affinity(100, 10)
        assert new_value == 110
        assert "💕" in msg  # 레벨 변화 없이 점수만 증가

    def test_unknown_action_ignored(self):
        """알 수 없는 액션은 무시"""
        affinity_system = AffinitySystem()

        change = affinity_system.calculate_change({
            "unknown_action": 10,
            "invalid_key": 5
        })
        assert change == 0

    def test_zero_count_actions(self):
        """0회 액션은 영향 없음"""
        affinity_system = AffinitySystem()

        change = affinity_system.calculate_change({
            "dialogue_frequency": 0,
            "cooperation": 0
        })
        assert change == 0

    def test_realistic_progression_sequence(self):
        """현실적인 친밀도 상승 시퀀스"""
        affinity_system = AffinitySystem()

        affinity = 0

        # 1. 대화 5회
        change1 = affinity_system.calculate_change({"dialogue_frequency": 5})
        affinity, msg1 = affinity_system.update_affinity(affinity, change1)
        assert affinity == 25  # 5 × 5 = 25

        # 2. 협력 3회
        change2 = affinity_system.calculate_change({"cooperation": 3})
        affinity, msg2 = affinity_system.update_affinity(affinity, change2)
        assert affinity == 70  # 25 + (15 × 3) = 70

        # 3. 칭찬 2회
        change3 = affinity_system.calculate_change({"praise": 2})
        affinity, msg3 = affinity_system.update_affinity(affinity, change3)
        assert affinity == 110  # 70 + (20 × 2) = 110

        # 4. 생명 구조 1회
        change4 = affinity_system.calculate_change({"save_life": 1})
        affinity, msg4 = affinity_system.update_affinity(affinity, change4)
        assert affinity == 160  # 110 + 50 = 160

        assert affinity_system.get_level(affinity) == AffinityLevel.STRANGER

    def test_character_tone_retrieval_with_enum(self):
        """AffinityLevel enum으로 직접 tone 조회"""
        affinity_system = AffinitySystem()

        # enum 직접 전달
        tone = affinity_system.get_tone("tanjiro", AffinityLevel.FRIEND)
        assert tone is not None
        assert tone.calling == ""
        assert tone.suffix == "어"

    def test_character_tone_retrieval_with_int(self):
        """int 점수로 tone 조회"""
        affinity_system = AffinitySystem()

        # int 전달 (자동으로 레벨 계산)
        tone = affinity_system.get_tone("tanjiro", 450)
        assert tone is not None
        assert tone.style == "따뜻하고 친근한"

    def test_all_characters_have_all_levels(self):
        """모든 캐릭터가 5개 레벨 모두 가지고 있는지"""
        affinity_system = AffinitySystem()
        characters = ["tanjiro", "inosuke", "zenitsu", "rengoku"]
        levels = [
            AffinityLevel.STRANGER,
            AffinityLevel.ACQUAINTANCE,
            AffinityLevel.FRIEND,
            AffinityLevel.CLOSE_FRIEND,
            AffinityLevel.SOULMATE
        ]

        for char in characters:
            for level in levels:
                tone = affinity_system.get_tone(char, level)
                assert tone is not None, f"{char}의 {level.value} 레벨 tone이 없음"

    def test_emoji_usage_progression(self):
        """친밀도에 따른 이모지 사용 증가"""
        affinity_system = AffinitySystem()

        emoji_0 = affinity_system.get_emoji_for_level(0)
        emoji_200 = affinity_system.get_emoji_for_level(200)
        emoji_400 = affinity_system.get_emoji_for_level(400)
        emoji_600 = affinity_system.get_emoji_for_level(600)
        emoji_800 = affinity_system.get_emoji_for_level(800)

        # 모두 다른 이모지여야 함
        emojis = [emoji_0, emoji_200, emoji_400, emoji_600, emoji_800]
        assert len(set(emojis)) == 5

    def test_massive_betrayal_recovery(self):
        """배신 후 회복 시나리오"""
        affinity_system = AffinitySystem()

        # 800 (SOULMATE)에서 시작
        affinity = 800

        # 배신 2회 (-60)
        change1 = affinity_system.calculate_change({"betrayal": 2})
        affinity, _ = affinity_system.update_affinity(affinity, change1)
        assert affinity == 740  # 800 - 60 = 740

        # 레벨이 CLOSE_FRIEND로 하락
        assert affinity_system.get_level(affinity) == AffinityLevel.CLOSE_FRIEND

        # 생명 구조 2회 (+100) + 칭찬 3회 (+60)로 회복
        change2 = affinity_system.calculate_change({"save_life": 2, "praise": 3})
        affinity, _ = affinity_system.update_affinity(affinity, change2)
        assert affinity == 900  # 740 + 160 = 900

        # SOULMATE로 복귀
        assert affinity_system.get_level(affinity) == AffinityLevel.SOULMATE
