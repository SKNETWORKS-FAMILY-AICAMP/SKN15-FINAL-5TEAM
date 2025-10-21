#!/usr/bin/env python3
"""
멀티캐릭터 대화 자동 트리거 시스템

시나리오 진행 중 자연스럽게 멀티캐릭터 대화가 발생하는 조건들을 정의하고 관리
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ConversationTrigger:
    """대화 트리거 조건"""
    scene_key: str  # conversation_prompts.json의 키
    num_exchanges: int  # 대화 교환 횟수
    description: str  # 설명


class ConversationTriggerManager:
    """멀티캐릭터 대화 트리거 관리자"""

    def __init__(self):
        """초기화"""
        # 트리거 조건 정의
        self.triggers = {
            # === 스테이지 종료 시 ===
            "stage_intro_complete": ConversationTrigger(
                scene_key="intro_complete",
                num_exchanges=3,
                description="인트로 씬 종료 - 아카자 등장 직후"
            ),
            "stage_fork_after_choice": ConversationTrigger(
                scene_key="fork_discussion",
                num_exchanges=3,
                description="선택지 이후 - 동료들과 작전 회의"
            ),

            # === 플래그 기반 트리거 ===
            "chose_teamwork": ConversationTrigger(
                scene_key="teamwork_decision",
                num_exchanges=4,
                description="팀워크 선택 - 동료 규합 결정 직후"
            ),
            "inosuke_recruited": ConversationTrigger(
                scene_key="inosuke_joined",
                num_exchanges=2,
                description="이노스케 규합 성공 - 환영 대화"
            ),
            "zenitsu_recruited": ConversationTrigger(
                scene_key="zenitsu_joined",
                num_exchanges=2,
                description="젠이츠 규합 성공 - 환영 대화"
            ),
            "both_recruited": ConversationTrigger(
                scene_key="cutscene5_recruit",
                num_exchanges=4,
                description="둘 다 규합 완료 - 출격 전 대화"
            ),

            # === 전투/이벤트 후 ===
            "cutscene5_victory": ConversationTrigger(
                scene_key="cutscene5_victory",
                num_exchanges=4,
                description="컷신5 승리 - 아카자 격퇴 후"
            ),
            "cutscene5_defeat": ConversationTrigger(
                scene_key="cutscene5_defeat",
                num_exchanges=4,
                description="컷신5 패배 - 렌고쿠 사망 후"
            ),
            "reckless_sacrifice": ConversationTrigger(
                scene_key="sacrifice_aftermath",
                num_exchanges=3,
                description="무모한 희생 선택 후 - 후회와 위로"
            ),

            # === 컷신6 관련 ===
            "cutscene6_start": ConversationTrigger(
                scene_key="cutscene6_preparation",
                num_exchanges=3,
                description="컷신6 시작 - 마음에 불을 붙여라"
            ),
            "cutscene6_final_victory": ConversationTrigger(
                scene_key="cutscene6_final",
                num_exchanges=4,
                description="컷신6 최종 승리 - 렌고쿠 생존"
            ),

            # === 특수 조건 ===
            "high_affinity_moment": ConversationTrigger(
                scene_key="high_affinity_celebration",
                num_exchanges=3,
                description="높은 친밀도 달성 - 특별 대화"
            ),
            "crisis_averted": ConversationTrigger(
                scene_key="crisis_relief",
                num_exchanges=2,
                description="위기 상황 해결 - 안도의 대화"
            ),
            "discovery_moment": ConversationTrigger(
                scene_key="discovery_reaction",
                num_exchanges=3,
                description="중요한 발견/깨달음 - 반응 공유"
            ),
        }

    def check_triggers(self, state: Any) -> Optional[ConversationTrigger]:
        """
        현재 상태에서 트리거될 조건 확인

        Args:
            state: 게임 상태

        Returns:
            트리거된 조건 또는 None
        """
        if not hasattr(state, 'game'):
            return None

        flags = state.game.flags if hasattr(state.game, 'flags') else []
        current_stage = state.game.current_stage if hasattr(state.game, 'current_stage') else ""
        temp_data = state.game.temp_data if hasattr(state.game, 'temp_data') else {}

        # 이미 실행된 트리거는 건너뛰기
        executed_triggers = temp_data.get("executed_conversation_triggers", [])

        # === 1. 스테이지 종료 트리거 ===
        stage_complete_flag = f"stage_{current_stage}_complete"
        if stage_complete_flag in flags:
            trigger_key = f"stage_{current_stage}_complete"
            if trigger_key in self.triggers and trigger_key not in executed_triggers:
                return self._mark_and_return(state, trigger_key)

        # === 2. 플래그 기반 트리거 (우선순위 순) ===

        # 둘 다 규합 완료
        if "inosuke_recruited" in flags and "zenitsu_recruited" in flags:
            if "both_recruited" not in executed_triggers:
                return self._mark_and_return(state, "both_recruited")

        # 개별 규합 성공
        if "inosuke_recruited" in flags and "inosuke_recruited" not in executed_triggers:
            return self._mark_and_return(state, "inosuke_recruited")

        if "zenitsu_recruited" in flags and "zenitsu_recruited" not in executed_triggers:
            return self._mark_and_return(state, "zenitsu_recruited")

        # 팀워크 선택
        if "chose_teamwork" in flags and "chose_teamwork" not in executed_triggers:
            return self._mark_and_return(state, "chose_teamwork")

        # 무모한 희생
        if "chose_sacrifice" in flags and "reckless_sacrifice" not in executed_triggers:
            return self._mark_and_return(state, "reckless_sacrifice")

        # === 3. 전투 결과 트리거 ===
        if "cutscene5_victory" in flags and "cutscene5_victory" not in executed_triggers:
            return self._mark_and_return(state, "cutscene5_victory")

        if "cutscene5_defeat" in flags and "cutscene5_defeat" not in executed_triggers:
            return self._mark_and_return(state, "cutscene5_defeat")

        if "cutscene6_final_victory" in flags and "cutscene6_final_victory" not in executed_triggers:
            return self._mark_and_return(state, "cutscene6_final_victory")

        # === 4. 특수 조건 트리거 ===

        # 높은 친밀도 (평균 600 이상)
        if hasattr(state, 'characters') and hasattr(state.characters, 'affinity'):
            avg_affinity = self._calculate_average_affinity(state.characters.affinity)
            if avg_affinity >= 600 and "high_affinity_moment" not in executed_triggers:
                return self._mark_and_return(state, "high_affinity_moment")

        # 위기 상황 해결 (턴 6에서 생존)
        if state.game.turn >= 6 and "crisis_averted" not in executed_triggers:
            # 중요 플래그 확인 (렌고쿠 생존 등)
            if "rengoku_alive" in flags or "victory" in flags:
                return self._mark_and_return(state, "crisis_averted")

        return None

    def _mark_and_return(self, state: Any, trigger_key: str) -> ConversationTrigger:
        """트리거 실행 마크 및 반환"""
        if not hasattr(state.game, 'temp_data'):
            return self.triggers[trigger_key]

        executed = state.game.temp_data.get("executed_conversation_triggers", [])
        if trigger_key not in executed:
            executed.append(trigger_key)
            state.game.temp_data["executed_conversation_triggers"] = executed

        return self.triggers[trigger_key]

    def _calculate_average_affinity(self, affinity_dict: Dict[str, int]) -> float:
        """평균 친밀도 계산"""
        if not affinity_dict:
            return 0.0

        values = [v for v in affinity_dict.values() if isinstance(v, (int, float))]
        return sum(values) / len(values) if values else 0.0

    def should_trigger_conversation(
        self,
        state: Any,
        event_type: str = "auto"
    ) -> Optional[ConversationTrigger]:
        """
        대화 트리거 여부 확인 (편의 함수)

        Args:
            state: 게임 상태
            event_type: 이벤트 타입 ("auto", "stage_complete", "flag_added" 등)

        Returns:
            트리거 조건 또는 None
        """
        return self.check_triggers(state)

    def get_trigger_by_key(self, trigger_key: str) -> Optional[ConversationTrigger]:
        """특정 트리거 조건 조회"""
        return self.triggers.get(trigger_key)

    def list_all_triggers(self) -> List[str]:
        """모든 트리거 키 목록"""
        return list(self.triggers.keys())


# 싱글톤 인스턴스
_trigger_manager_instance = None


def get_trigger_manager() -> ConversationTriggerManager:
    """트리거 매니저 싱글톤 인스턴스 반환"""
    global _trigger_manager_instance
    if _trigger_manager_instance is None:
        _trigger_manager_instance = ConversationTriggerManager()
    return _trigger_manager_instance


if __name__ == "__main__":
    # 테스트
    manager = ConversationTriggerManager()

    print("=== 멀티캐릭터 대화 트리거 목록 ===\n")

    for key, trigger in manager.triggers.items():
        print(f"🔔 {key}")
        print(f"   씬: {trigger.scene_key}")
        print(f"   횟수: {trigger.num_exchanges}회")
        print(f"   설명: {trigger.description}")
        print()

    print(f"총 {len(manager.triggers)}개 트리거 정의됨")
