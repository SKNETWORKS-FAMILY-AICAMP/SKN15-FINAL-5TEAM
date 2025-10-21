"""
친밀도 시스템 단위 테스트
"""
import pytest
from affinity_system import AffinitySystem, AffinityLevel


class TestAffinityLevels:
    """친밀도 레벨 테스트"""

    def test_affinity_level_boundaries(self, affinity_system):
        """레벨 경계 테스트 (0, 199, 200, 399, 400, 599, 600, 799, 800, 1000)"""
        # STRANGER: 0-199
        assert affinity_system.get_level(0) == AffinityLevel.STRANGER
        assert affinity_system.get_level(100) == AffinityLevel.STRANGER
        assert affinity_system.get_level(199) == AffinityLevel.STRANGER

        # ACQUAINTANCE: 200-399
        assert affinity_system.get_level(200) == AffinityLevel.ACQUAINTANCE
        assert affinity_system.get_level(300) == AffinityLevel.ACQUAINTANCE
        assert affinity_system.get_level(399) == AffinityLevel.ACQUAINTANCE

        # FRIEND: 400-599
        assert affinity_system.get_level(400) == AffinityLevel.FRIEND
        assert affinity_system.get_level(500) == AffinityLevel.FRIEND
        assert affinity_system.get_level(599) == AffinityLevel.FRIEND

        # CLOSE_FRIEND: 600-799
        assert affinity_system.get_level(600) == AffinityLevel.CLOSE_FRIEND
        assert affinity_system.get_level(700) == AffinityLevel.CLOSE_FRIEND
        assert affinity_system.get_level(799) == AffinityLevel.CLOSE_FRIEND

        # SOULMATE: 800-1000
        assert affinity_system.get_level(800) == AffinityLevel.SOULMATE
        assert affinity_system.get_level(900) == AffinityLevel.SOULMATE
        assert affinity_system.get_level(1000) == AffinityLevel.SOULMATE

    def test_affinity_value_clamping(self, affinity_system):
        """친밀도 값이 0-1000 범위로 제한되는지 확인"""
        # 음수는 0으로
        assert affinity_system.get_level(-100) == AffinityLevel.STRANGER

        # 1000 초과는 1000으로
        assert affinity_system.get_level(1500) == AffinityLevel.SOULMATE


class TestAffinityChangeRules:
    """친밀도 변화 규칙 테스트"""

    def test_positive_affinity_changes(self, affinity_system):
        """긍정적 행동에 따른 친밀도 증가"""
        # dialogue_frequency: +5
        change = affinity_system.calculate_change({"dialogue_frequency": 1})
        assert change == 5

        # cooperation: +15
        change = affinity_system.calculate_change({"cooperation": 1})
        assert change == 15

        # praise: +20
        change = affinity_system.calculate_change({"praise": 1})
        assert change == 20

        # save_life: +50
        change = affinity_system.calculate_change({"save_life": 1})
        assert change == 50

    def test_negative_affinity_changes(self, affinity_system):
        """부정적 행동에 따른 친밀도 감소"""
        # rudeness: -10
        change = affinity_system.calculate_change({"rudeness": 1})
        assert change == -10

        # selfishness: -15
        change = affinity_system.calculate_change({"selfishness": 1})
        assert change == -15

        # betrayal: -30
        change = affinity_system.calculate_change({"betrayal": 1})
        assert change == -30

        # attack: -50
        change = affinity_system.calculate_change({"attack": 1})
        assert change == -50

    def test_multiple_action_accumulation(self, affinity_system):
        """여러 행동의 누적 계산"""
        actions = {
            "dialogue_frequency": 2,  # +10
            "cooperation": 1,         # +15
            "praise": 1               # +20
        }
        change = affinity_system.calculate_change(actions)
        assert change == 45  # 10 + 15 + 20

    def test_mixed_actions(self, affinity_system):
        """긍정/부정 행동 혼합"""
        actions = {
            "cooperation": 1,  # +15
            "rudeness": 1      # -10
        }
        change = affinity_system.calculate_change(actions)
        assert change == 5  # 15 - 10


class TestAffinityTones:
    """친밀도별 말투 테스트"""

    def test_tanjiro_tone_retrieval(self, affinity_system):
        """탄지로 말투 조회"""
        # STRANGER
        tone = affinity_system.get_tone("tanjiro", AffinityLevel.STRANGER)
        assert tone.calling == "님"
        assert tone.suffix == "습니다"

        # FRIEND
        tone = affinity_system.get_tone("tanjiro", AffinityLevel.FRIEND)
        assert tone.calling == ""
        assert tone.suffix == "어"

        # SOULMATE
        tone = affinity_system.get_tone("tanjiro", AffinityLevel.SOULMATE)
        assert tone.calling == ""
        assert tone.suffix == "야"

    def test_inosuke_tone_retrieval(self, affinity_system):
        """이노스케 말투 조회"""
        # STRANGER
        tone = affinity_system.get_tone("inosuke", AffinityLevel.STRANGER)
        assert tone.calling == "놈"
        assert tone.suffix == "다"

        # CLOSE_FRIEND
        tone = affinity_system.get_tone("inosuke", AffinityLevel.CLOSE_FRIEND)
        assert tone.calling == "친구"
        assert tone.suffix == "다"

    def test_zenitsu_tone_retrieval(self, affinity_system):
        """젠이츠 말투 조회"""
        # STRANGER
        tone = affinity_system.get_tone("zenitsu", AffinityLevel.STRANGER)
        assert tone.calling == "님"
        assert tone.suffix == "어요"

        # FRIEND
        tone = affinity_system.get_tone("zenitsu", AffinityLevel.FRIEND)
        assert tone.calling == ""
        assert tone.suffix == "어"

    def test_rengoku_tone_retrieval(self, affinity_system):
        """렌고쿠 말투 조회"""
        # STRANGER
        tone = affinity_system.get_tone("rengoku", AffinityLevel.STRANGER)
        assert tone.calling == "군"
        assert tone.suffix == "하오"

        # FRIEND
        tone = affinity_system.get_tone("rengoku", AffinityLevel.FRIEND)
        assert tone.calling == "자네"
        assert tone.suffix == "하게"


class TestAffinityProgression:
    """친밀도 진행 시뮬레이션"""

    def test_level_up_from_stranger_to_acquaintance(self, affinity_system):
        """낯선 사람 → 아는 사이로 레벨업"""
        current_affinity = 150  # STRANGER

        # cooperation 4회 (+60)
        change = affinity_system.calculate_change({"cooperation": 4})
        new_affinity = current_affinity + change
        assert new_affinity == 210

        # 레벨 확인
        assert affinity_system.get_level(new_affinity) == AffinityLevel.ACQUAINTANCE

    def test_level_up_chain(self, affinity_system):
        """연속 레벨업 시뮬레이션"""
        affinity = 0

        # STRANGER → ACQUAINTANCE (0 → 200)
        change = affinity_system.calculate_change({"save_life": 4})  # +200
        affinity += change
        assert affinity_system.get_level(affinity) == AffinityLevel.ACQUAINTANCE

        # ACQUAINTANCE → FRIEND (200 → 400)
        change = affinity_system.calculate_change({"save_life": 4})  # +200
        affinity += change
        assert affinity_system.get_level(affinity) == AffinityLevel.FRIEND

        # FRIEND → CLOSE_FRIEND (400 → 600)
        change = affinity_system.calculate_change({"save_life": 4})  # +200
        affinity += change
        assert affinity_system.get_level(affinity) == AffinityLevel.CLOSE_FRIEND

        # CLOSE_FRIEND → SOULMATE (600 → 800)
        change = affinity_system.calculate_change({"save_life": 4})  # +200
        affinity += change
        assert affinity_system.get_level(affinity) == AffinityLevel.SOULMATE

    def test_level_down_from_betrayal(self, affinity_system):
        """배신으로 인한 친밀도 하락"""
        affinity = 450  # FRIEND

        # betrayal 2회 (-60)
        change = affinity_system.calculate_change({"betrayal": 2})
        affinity += change
        assert affinity == 390

        # 레벨 하락 확인
        assert affinity_system.get_level(affinity) == AffinityLevel.ACQUAINTANCE

    def test_affinity_cannot_go_below_zero(self, affinity_system):
        """친밀도가 0 아래로 내려가지 않음"""
        affinity = 20

        # 큰 부정 변화
        change = affinity_system.calculate_change({"attack": 10})  # -500
        affinity += change

        # 0 이하 확인
        assert affinity < 0

        # 하지만 get_level은 0으로 클램핑
        level = affinity_system.get_level(affinity)
        assert level == AffinityLevel.STRANGER

    def test_realistic_dialogue_progression(self, affinity_system):
        """현실적인 대화 진행 시뮬레이션"""
        affinity = 0

        # 10번 대화 (+50)
        affinity += affinity_system.calculate_change({"dialogue_frequency": 10})
        assert affinity == 50
        assert affinity_system.get_level(affinity) == AffinityLevel.STRANGER

        # 5번 협력 (+75)
        affinity += affinity_system.calculate_change({"cooperation": 5})
        assert affinity == 125
        assert affinity_system.get_level(affinity) == AffinityLevel.STRANGER

        # 3번 칭찬 (+60)
        affinity += affinity_system.calculate_change({"praise": 3})
        assert affinity == 185
        assert affinity_system.get_level(affinity) == AffinityLevel.STRANGER

        # 1번 생명 구조 (+50)
        affinity += affinity_system.calculate_change({"save_life": 1})
        assert affinity == 235
        assert affinity_system.get_level(affinity) == AffinityLevel.ACQUAINTANCE
