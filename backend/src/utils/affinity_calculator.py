#!/usr/bin/env python3
"""
친밀도 변화 계산기 (Affinity Change Calculator)
기획안에 따른 친밀도 상승/하락 규칙 적용
"""

from typing import Dict, List, Tuple


class AffinityChangeCalculator:
    """친밀도 변화 계산"""
    
    # 친밀도 상승 규칙
    RULES_POSITIVE = {
        "core_goal_achievement": 10,      # 핵심 목표 달성
        "optimal_interaction": 8,          # 결정적/공략적 상호작용
        "combat_cooperation": 6,           # 전투 협력
        "positive_interaction": 5,         # 긍정적/핵심 상호작용
        "praise_encouragement": 3,         # 칭찬과 격려
        "general_interaction": 2,          # 일반 상호작용
    }
    
    # 친밀도 하락 규칙
    RULES_NEGATIVE = {
        "trust_destruction": -15,          # 신뢰 관계 파괴
        "selfish_cowardly": -10,          # 이기적/비겁한 행동
        "contempt_blame": -8,             # 경멸 및 비난
        "ignore_indifference": -3,        # 무시 및 무관심
        "uncooperative_dialogue": -2,     # 비협조적/맥락 이탈 대화
    }
    
    def __init__(self):
        self.max_per_cutscene = 100  # 한 컷신당 최대 20점 (기획안 기준)
        
    def calculate_change(self, interaction_type: str, character: str = None) -> int:
        """
        상호작용 타입에 따른 친밀도 변화량 계산
        
        Args:
            interaction_type: 상호작용 타입 키
            character: 캐릭터 ID (선택)
            
        Returns:
            친밀도 변화량
        """
        # 긍정적 규칙 확인
        if interaction_type in self.RULES_POSITIVE:
            return self.RULES_POSITIVE[interaction_type]
            
        # 부정적 규칙 확인
        if interaction_type in self.RULES_NEGATIVE:
            return self.RULES_NEGATIVE[interaction_type]
            
        return 0
    
    def apply_affinity_change(
        self, 
        current_affinity: Dict[str, int],
        changes: Dict[str, List[str]]
    ) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        친밀도 변화 적용
        
        Args:
            current_affinity: 현재 친밀도 딕셔너리
            changes: {character_id: [interaction_type1, interaction_type2, ...]}
            
        Returns:
            (new_affinity, change_amounts)
        """
        new_affinity = current_affinity.copy()
        change_amounts = {}
        
        for character, interaction_types in changes.items():
            total_change = 0
            for itype in interaction_types:
                change = self.calculate_change(itype, character)
                total_change += change
            
            # 현재 친밀도에 변화량 적용 (0-1000 범위 제한)
            old_value = new_affinity.get(character, 0)
            new_value = max(0, min(1000, old_value + total_change))
            new_affinity[character] = new_value
            change_amounts[character] = total_change
            
        return new_affinity, change_amounts
    
    def get_affinity_level(self, affinity_value: int) -> int:
        """
        친밀도 수치를 레벨로 변환
        
        Args:
            affinity_value: 친밀도 수치 (0-1000)
            
        Returns:
            레벨 (1-5)
        """
        if affinity_value <= 200:
            return 1
        elif affinity_value <= 400:
            return 2
        elif affinity_value <= 600:
            return 3
        elif affinity_value <= 800:
            return 4
        else:
            return 5


# 전역 인스턴스
affinity_calculator = AffinityChangeCalculator()


if __name__ == "__main__":
    # 테스트
    print("=== 친밀도 변화 계산기 테스트 ===\n")
    
    calc = AffinityChangeCalculator()
    
    # 초기 친밀도
    affinity = {"tanjiro": 0, "inosuke": 0, "zenitsu": 0}
    
    print(f"초기 친밀도: {affinity}\n")
    
    # 탄지로와 일반 상호작용
    changes = {"tanjiro": ["general_interaction"]}
    affinity, amounts = calc.apply_affinity_change(affinity, changes)
    print(f"탄지로 일반 상호작용 (+{amounts['tanjiro']}): {affinity}")
    
    # 이노스케 설득 성공 (핵심 목표 + 최적 상호작용)
    changes = {"inosuke": ["optimal_interaction", "core_goal_achievement"]}
    affinity, amounts = calc.apply_affinity_change(affinity, changes)
    print(f"이노스케 설득 성공 (+{amounts['inosuke']}): {affinity}")
    
    # 젠이츠에게 무시
    changes = {"zenitsu": ["ignore_indifference"]}
    affinity, amounts = calc.apply_affinity_change(affinity, changes)
    print(f"젠이츠 무시 ({amounts['zenitsu']}): {affinity}")
    
    print(f"\n레벨:")
    for char, score in affinity.items():
        level = calc.get_affinity_level(score)
        print(f"  {char}: Lv.{level} ({score}/1000)")
