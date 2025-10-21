#!/usr/bin/env python3
"""
🎯 친밀도 시스템 (Affinity System)
- 범위: 0-1000
- 레벨별 말투, 보상, 배경 자동 적용
- 상승/하락 규칙 자동 계산
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class AffinityLevel(Enum):
    """친밀도 레벨"""
    STRANGER = "stranger"      # 0-199: 낯선 사람
    ACQUAINTANCE = "acquaint"  # 200-399: 아는 사이
    FRIEND = "friend"          # 400-599: 친구
    CLOSE_FRIEND = "close"     # 600-799: 절친
    SOULMATE = "soulmate"      # 800-1000: 영혼의 동반자


@dataclass
class AffinityTone:
    """친밀도별 말투"""
    calling: str        # 호칭 (님, 씨, 야 등)
    suffix: str         # 어미 (습니다, 어요, 어 등)
    style: str          # 말투 스타일
    emoji_usage: str    # 이모지 사용 정도


class AffinitySystem:
    """친밀도 시스템 관리"""

    def __init__(self):
        # 레벨별 구간 정의
        self.level_ranges = {
            AffinityLevel.STRANGER: (0, 199),
            AffinityLevel.ACQUAINTANCE: (200, 399),
            AffinityLevel.FRIEND: (400, 599),
            AffinityLevel.CLOSE_FRIEND: (600, 799),
            AffinityLevel.SOULMATE: (800, 1000)
        }

        # 캐릭터별 말투 템플릿
        self.character_tones = {
            "tanjiro": {
                AffinityLevel.STRANGER: AffinityTone("님", "습니다", "조심스럽고 예의바른", "minimal"),
                AffinityLevel.ACQUAINTANCE: AffinityTone("씨", "어요", "정중하지만 친근한", "moderate"),
                AffinityLevel.FRIEND: AffinityTone("", "어", "따뜻하고 친근한", "frequent"),
                AffinityLevel.CLOSE_FRIEND: AffinityTone("", "야", "결연하고 따뜻한", "frequent"),
                AffinityLevel.SOULMATE: AffinityTone("", "야", "영혼의 동료", "abundant")
            },
            "inosuke": {
                AffinityLevel.STRANGER: AffinityTone("놈", "다", "거칠고 경계하는", "minimal"),
                AffinityLevel.ACQUAINTANCE: AffinityTone("녀석", "지", "장난스럽지만 거친", "moderate"),
                AffinityLevel.FRIEND: AffinityTone("너", "다", "친근하지만 거친", "frequent"),
                AffinityLevel.CLOSE_FRIEND: AffinityTone("친구", "다", "우정을 인정하는", "frequent"),
                AffinityLevel.SOULMATE: AffinityTone("동료", "다", "평생 동료", "abundant")
            },
            "zenitsu": {
                AffinityLevel.STRANGER: AffinityTone("님", "어요", "불안하고 조심스러운", "minimal"),
                AffinityLevel.ACQUAINTANCE: AffinityTone("씨", "어", "덜 불안한", "moderate"),
                AffinityLevel.FRIEND: AffinityTone("", "어", "의지하는", "frequent"),
                AffinityLevel.CLOSE_FRIEND: AffinityTone("", "야", "신뢰하는", "frequent"),
                AffinityLevel.SOULMATE: AffinityTone("", "야", "영혼의 친구", "abundant")
            },
            "rengoku": {
                AffinityLevel.STRANGER: AffinityTone("군", "하오", "위엄있고 격식있는", "minimal"),
                AffinityLevel.ACQUAINTANCE: AffinityTone("군", "하네", "친근하지만 위엄있는", "moderate"),
                AffinityLevel.FRIEND: AffinityTone("자네", "하게", "따뜻하고 격려하는", "frequent"),
                AffinityLevel.CLOSE_FRIEND: AffinityTone("자네", "하게", "믿음직한", "frequent"),
                AffinityLevel.SOULMATE: AffinityTone("자네", "하게", "영혼을 나눈", "abundant")
            }
        }

        # 친밀도 변화 규칙
        self.change_rules = {
            # 긍정적 행동
            "dialogue_frequency": 5,      # 대화 빈도
            "alignment_match": 10,        # 성향 일치
            "cooperation": 15,            # 협력
            "praise": 20,                 # 칭찬
            "gift": 25,                   # 선물
            "save_life": 50,              # 생명 구조

            # 부정적 행동
            "rudeness": -10,              # 무례
            "selfishness": -15,           # 이기적 행동
            "betrayal": -30,              # 배신
            "attack": -50                 # 공격
        }

    def get_level(self, affinity_value: int) -> AffinityLevel:
        """친밀도 수치로 레벨 계산"""
        affinity_value = max(0, min(1000, affinity_value))  # 0-1000 범위 제한

        for level, (min_val, max_val) in self.level_ranges.items():
            if min_val <= affinity_value <= max_val:
                return level

        return AffinityLevel.STRANGER

    def get_tone(self, character: str, affinity_value) -> Optional[AffinityTone]:
        """캐릭터와 친밀도에 맞는 말투 반환"""
        if character not in self.character_tones:
            return None

        # Handle both int and AffinityLevel enum
        if isinstance(affinity_value, AffinityLevel):
            level = affinity_value
        else:
            level = self.get_level(affinity_value)

        return self.character_tones[character].get(level)

    def calculate_change(self, actions: Dict[str, int]) -> int:
        """행동에 따른 친밀도 변화량 계산 (중복 시 합산)"""
        total_change = 0

        for action, count in actions.items():
            if action in self.change_rules:
                change_value = self.change_rules[action] * count
                total_change += change_value

        return total_change

    def update_affinity(self, current_value: int, change: int) -> Tuple[int, str]:
        """친밀도 업데이트 및 레벨 변화 메시지"""
        old_value = current_value
        new_value = max(0, min(1000, current_value + change))

        old_level = self.get_level(old_value)
        new_level = self.get_level(new_value)

        message = ""
        if new_level != old_level:
            if new_value > old_value:
                message = f"💖 친밀도 상승! {old_level.value} → {new_level.value}"
            else:
                message = f"💔 친밀도 하락! {old_level.value} → {new_level.value}"
        elif change > 0:
            message = f"💕 +{change} 친밀도 상승 ({new_value}/1000)"
        elif change < 0:
            message = f"💢 {change} 친밀도 하락 ({new_value}/1000)"

        return new_value, message

    # def get_emoji_for_level(self, affinity_value: int) -> str:
    #     """친밀도에 맞는 이모지 반환"""
    #     level = self.get_level(affinity_value)

    #     emoji_map = {
    #         AffinityLevel.STRANGER: "🙂",
    #         AffinityLevel.ACQUAINTANCE: "😊",
    #         AffinityLevel.FRIEND: "😄",
    #         AffinityLevel.CLOSE_FRIEND: "🥰",
    #         AffinityLevel.SOULMATE: "💖"
    #     }

    #     return emoji_map.get(level, "🙂")

    def get_level_description(self, affinity_value: int) -> str:
        """친밀도 레벨 설명"""
        level = self.get_level(affinity_value)

        descriptions = {
            AffinityLevel.STRANGER: "😐 낯선 사람 (0-199)",
            AffinityLevel.ACQUAINTANCE: "😊 아는 사이 (200-399)",
            AffinityLevel.FRIEND: "😄 친구 (400-599)",
            AffinityLevel.CLOSE_FRIEND: "🥰 절친 (600-799)",
            AffinityLevel.SOULMATE: "💖 영혼의 동반자 (800-1000)"
        }

        return descriptions.get(level, "알 수 없음")


# 전역 친밀도 시스템 인스턴스
affinity_system = AffinitySystem()


if __name__ == "__main__":
    # 테스트
    print("=== 친밀도 시스템 테스트 ===\n")

    # 탄지로 친밀도 테스트
    tanjiro_affinity = 0
    print(f"탄지로 초기 친밀도: {tanjiro_affinity}")
    print(f"레벨: {affinity_system.get_level_description(tanjiro_affinity)}")

    # 대화 빈도 증가
    change = affinity_system.calculate_change({"dialogue_frequency": 3})
    tanjiro_affinity, msg = affinity_system.update_affinity(tanjiro_affinity, change)
    print(f"\n대화 3회: {msg}")

    # 협력 행동
    change = affinity_system.calculate_change({"cooperation": 2, "praise": 1})
    tanjiro_affinity, msg = affinity_system.update_affinity(tanjiro_affinity, change)
    print(f"협력 2회 + 칭찬 1회: {msg}")

    # 생명 구조
    change = affinity_system.calculate_change({"save_life": 1})
    tanjiro_affinity, msg = affinity_system.update_affinity(tanjiro_affinity, change)
    print(f"생명 구조: {msg}")

    # 말투 확인
    tone = affinity_system.get_tone("tanjiro", tanjiro_affinity)
    if tone:
        print(f"\n탄지로 말투:")
        print(f"  호칭: {tone.calling}")
        print(f"  어미: {tone.suffix}")
        print(f"  스타일: {tone.style}")
        print(f"  이모지: {tone.emoji_usage}")

    # 이노스케 친밀도 테스트
    print(f"\n{'='*50}\n")
    inosuke_affinity = 0
    print(f"이노스케 초기 친밀도: {inosuke_affinity}")

    # 무례한 행동
    change = affinity_system.calculate_change({"rudeness": 1})
    inosuke_affinity, msg = affinity_system.update_affinity(inosuke_affinity, change)
    print(f"무례한 행동: {msg}")

    # 협력으로 만회
    change = affinity_system.calculate_change({"cooperation": 5})
    inosuke_affinity, msg = affinity_system.update_affinity(inosuke_affinity, change)
    print(f"협력 5회: {msg}")

    print(f"\n최종 이노스케 레벨: {affinity_system.get_level_description(inosuke_affinity)}")
