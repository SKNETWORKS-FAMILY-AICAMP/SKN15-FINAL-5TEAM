#!/usr/bin/env python3
"""
🎯 미션 관리자 (Mission Manager)
- 턴제 시스템 완전 구현
- 이노스케→젠이츠 순서 검증
- 친밀도 자동 적용
- 위기 메시지 자동 삽입
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class MissionStatus(Enum):
    """미션 상태"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class CharacterProgress:
    """캐릭터별 설득 진행도"""
    character_id: str
    current_stage: int = 0
    recruited: bool = False
    attempts: int = 0
    recruitment_turn: Optional[int] = None


@dataclass
class MissionState:
    """미션 상태"""
    mission_id: str
    current_turn: int = 0
    max_turns: int = 6
    status: MissionStatus = MissionStatus.NOT_STARTED
    character_progress: Dict[str, CharacterProgress] = field(default_factory=dict)
    recruitment_order: List[str] = field(default_factory=list)
    crisis_level: int = 0


class MissionManager:
    """미션 관리자"""

    def __init__(self, mission_data: Dict):
        self.mission_data = mission_data
        self.max_turns = mission_data.get("max_turns", 6)
        self.characters = mission_data.get("characters", {})
        self.crisis_messages = mission_data.get("crisis_progression", {}).get("messages", [])

        # 올바른 순서 추출
        self.correct_order = []
        for char_id, char_data in self.characters.items():
            order = char_data.get("correct_order", 999)
            self.correct_order.append((order, char_id))
        self.correct_order.sort()
        self.correct_order = [char_id for _, char_id in self.correct_order]

        print(f"[MISSION] Initialized with correct order: {self.correct_order}")

    def start_mission(self) -> MissionState:
        """미션 시작"""
        state = MissionState(
            mission_id=self.mission_data.get("title", "unknown"),
            max_turns=self.max_turns
        )

        # 캐릭터 진행도 초기화
        for char_id in self.characters.keys():
            state.character_progress[char_id] = CharacterProgress(character_id=char_id)

        state.status = MissionStatus.IN_PROGRESS
        return state

    def process_user_input(
        self,
        state: MissionState,
        user_input: str,
        current_character: Optional[str] = None,
        increment_turn_on_success: bool = True
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        유저 입력 처리

        Args:
            state: 현재 미션 상태
            user_input: 유저 입력 텍스트
            current_character: 대상 캐릭터 ID (None이면 자동 탐지)
            increment_turn_on_success: 성공 시 턴 자동 증가 여부

        Returns:
            (success: bool, message: str, response_data: Optional[Dict])
        """
        # 현재 진행 중인 캐릭터 찾기
        if not current_character:
            # 아직 모집 안 된 첫 번째 캐릭터
            for char_id in self.correct_order:
                if not state.character_progress[char_id].recruited:
                    current_character = char_id
                    break

        if not current_character or current_character not in self.characters:
            return False, "❌ 대상 캐릭터를 찾을 수 없습니다.", None

        # 🔥 순서 검증: 올바른 순서대로만 진행 가능
        expected_next = None
        for char_id in self.correct_order:
            if not state.character_progress[char_id].recruited:
                expected_next = char_id
                break

        if expected_next and current_character != expected_next:
            expected_name = self.characters[expected_next].get("name", expected_next)
            return False, f"❌ 순서 오류! 먼저 {expected_name}를 설득해야 합니다.", None

        char_data = self.characters[current_character]
        progress = state.character_progress[current_character]

        # 현재 단계 데이터
        conv_stages = char_data.get("conversation_stages", [])
        if progress.current_stage >= len(conv_stages):
            return False, "❌ 이미 완료된 캐릭터입니다.", None

        stage_data = conv_stages[progress.current_stage]

        # 키워드 매칭
        required_keywords = stage_data.get("required_keywords", [])
        user_input_lower = user_input.lower()

        matched = any(keyword.lower() in user_input_lower for keyword in required_keywords)

        response_data = None

        if matched:
            # 성공 - 턴 자동 증가
            if increment_turn_on_success:
                state.current_turn += 1
                # 위기 메시지 체크
                crisis_msg = self.get_crisis_message(state.current_turn)
                if crisis_msg:
                    for crisis_data in self.crisis_messages:
                        if crisis_data.get("turn") == state.current_turn:
                            state.crisis_level = crisis_data.get("crisis_level", state.crisis_level)

            response_data = stage_data.get("success_response", {})

            # 친밀도 적용
            affinity_impact = response_data.get("affinity_impact", {})

            # 다음 단계로
            progress.current_stage += 1
            progress.attempts = 0

            # 최종 단계 완료 시 모집 성공
            if "success_flag" in stage_data:
                progress.recruited = True
                progress.recruitment_turn = state.current_turn
                state.recruitment_order.append(current_character)

                # Tanjiro 지원 메시지 추가
                tanjiro_support = stage_data.get("tanjiro_support")
                if tanjiro_support:
                    response_data["tanjiro_support"] = tanjiro_support

                return True, f"✅ {char_data.get('name', current_character)} 모집 성공!", response_data

            return True, f"💬 {char_data.get('name', current_character)} 설득 진행 중...", response_data

        else:
            # 실패 - 턴 증가하지 않음 (재시도 가능)
            response_data = stage_data.get("failure_response", {})
            progress.attempts += 1

            # 최대 시도 횟수 초과
            max_attempts = char_data.get("max_attempts", 5)
            if progress.attempts >= max_attempts:
                return False, f"❌ {char_data.get('name', current_character)} 설득 실패 (시도 횟수 초과)", response_data

            return False, f"⚠️ 키워드가 맞지 않습니다. ({progress.attempts}/{max_attempts})", response_data

    def validate_order(self, state: MissionState) -> Tuple[bool, str]:
        """모집 순서 검증"""
        if len(state.recruitment_order) != len(self.correct_order):
            return True, "진행 중..."

        for i, char_id in enumerate(state.recruitment_order):
            if char_id != self.correct_order[i]:
                return False, f"❌ 순서 오류! 올바른 순서: {' → '.join(self.correct_order)}"

        return True, "✅ 순서 정확!"

    def check_completion(self, state: MissionState) -> Tuple[MissionStatus, str]:
        """미션 완료 체크"""
        # 턴 초과
        if state.current_turn >= self.max_turns:
            all_recruited = all(p.recruited for p in state.character_progress.values())

            if all_recruited:
                # 순서 검증
                order_valid, order_msg = self.validate_order(state)
                if order_valid:
                    state.status = MissionStatus.SUCCESS
                    return MissionStatus.SUCCESS, "🏆 미션 성공! 모든 동료 모집 완료!"
                else:
                    state.status = MissionStatus.FAILED
                    return MissionStatus.FAILED, f"❌ 미션 실패: {order_msg}"
            else:
                state.status = MissionStatus.TIMEOUT
                return MissionStatus.TIMEOUT, "⏰ 시간 초과! 모든 동료를 모집하지 못했습니다."

        # 모든 캐릭터 모집 완료
        if all(p.recruited for p in state.character_progress.values()):
            order_valid, order_msg = self.validate_order(state)
            if order_valid:
                state.status = MissionStatus.SUCCESS
                return MissionStatus.SUCCESS, "🏆 미션 성공! 모든 동료 모집 완료!"
            else:
                state.status = MissionStatus.FAILED
                return MissionStatus.FAILED, f"❌ 미션 실패: {order_msg}"

        # 진행 중
        return MissionStatus.IN_PROGRESS, "진행 중..."

    def get_crisis_message(self, turn: int) -> Optional[str]:
        """턴에 맞는 위기 메시지 반환"""
        for crisis_data in self.crisis_messages:
            if crisis_data.get("turn") == turn:
                return crisis_data.get("message")
        return None

    def increment_turn(self, state: MissionState) -> Tuple[int, Optional[str]]:
        """턴 증가 및 위기 메시지"""
        state.current_turn += 1
        crisis_msg = self.get_crisis_message(state.current_turn)

        if crisis_msg:
            # 위기 레벨도 업데이트
            for crisis_data in self.crisis_messages:
                if crisis_data.get("turn") == state.current_turn:
                    state.crisis_level = crisis_data.get("crisis_level", state.crisis_level)

        return state.current_turn, crisis_msg


# 테스트
if __name__ == "__main__":
    # 테스트 데이터
    test_mission = {
        "title": "동료 규합",
        "max_turns": 6,
        "characters": {
            "inosuke": {
                "name": "이노스케",
                "correct_order": 1,
                "conversation_stages": [
                    {
                        "stage": 0,
                        "name": "first_encounter",
                        "required_keywords": ["이노스케", "돼지"],
                        "success_response": {"speaker": "inosuke", "content": "크하하!", "affinity_impact": {"inosuke": 10}},
                        "failure_response": {"speaker": "inosuke", "content": "뭐야!"}
                    },
                    {
                        "stage": 1,
                        "name": "provocation",
                        "required_keywords": ["약", "겁쟁"],
                        "success_response": {"speaker": "inosuke", "content": "뭐라고!?", "affinity_impact": {"inosuke": 15}},
                        "failure_response": {"speaker": "inosuke", "content": "흥!"}
                    },
                    {
                        "stage": 2,
                        "name": "final",
                        "required_keywords": ["함께", "싸우자"],
                        "success_response": {"speaker": "inosuke", "content": "좋아!", "affinity_impact": {"inosuke": 30}},
                        "success_flag": "inosuke_recruited",
                        "failure_response": {"speaker": "inosuke", "content": "아직!"}
                    }
                ],
                "max_attempts": 5
            },
            "zenitsu": {
                "name": "젠이츠",
                "correct_order": 2,
                "conversation_stages": [
                    {
                        "stage": 0,
                        "name": "sleeping",
                        "required_keywords": ["젠이츠", "깨워"],
                        "success_response": {"speaker": "zenitsu", "content": "으응?", "affinity_impact": {"zenitsu": 10}},
                        "failure_response": {"speaker": "zenitsu", "content": "Zzz"}
                    },
                    {
                        "stage": 1,
                        "name": "waking",
                        "required_keywords": ["네즈코", "위험"],
                        "success_response": {"speaker": "zenitsu", "content": "네즈코!?", "affinity_impact": {"zenitsu": 20}},
                        "failure_response": {"speaker": "zenitsu", "content": "무서워"}
                    },
                    {
                        "stage": 2,
                        "name": "final",
                        "required_keywords": ["함께", "지키자"],
                        "success_response": {"speaker": "zenitsu", "content": "가자!", "affinity_impact": {"zenitsu": 30}},
                        "success_flag": "zenitsu_recruited",
                        "failure_response": {"speaker": "zenitsu", "content": "무서워"}
                    }
                ],
                "max_attempts": 5
            }
        },
        "crisis_progression": {
            "messages": [
                {"turn": 2, "message": "위기 레벨 2", "crisis_level": 2},
                {"turn": 4, "message": "위기 레벨 3", "crisis_level": 3},
                {"turn": 6, "message": "위기 레벨 4", "crisis_level": 4}
            ]
        }
    }

    print("=== 미션 관리자 테스트 ===\n")

    manager = MissionManager(test_mission)
    state = manager.start_mission()

    print(f"올바른 순서: {manager.correct_order}\n")

    # 시뮬레이션
    test_inputs = [
        ("이노스케", "inosuke"),
        ("약한 녀석", "inosuke"),
        ("함께 싸우자", "inosuke"),
        ("젠이츠 깨워", "zenitsu"),
        ("네즈코 위험해", "zenitsu"),
        ("함께 지키자", "zenitsu")
    ]

    for idx, (user_input, target) in enumerate(test_inputs):
        print(f"\n시도 {idx + 1}: '{user_input}'")

        # 입력 처리 (성공 시 자동으로 턴 증가)
        success, msg, response = manager.process_user_input(state, user_input, target, increment_turn_on_success=True)
        print(f"  {msg}")

        if response:
            print(f"  응답: {response.get('content', '')}")

        # 위기 메시지 표시
        if success:
            crisis = manager.get_crisis_message(state.current_turn)
            if crisis:
                print(f"  🚨 {crisis}")

        print(f"  현재 턴: {state.current_turn}/{state.max_turns}")

        # 완료 체크
        status, status_msg = manager.check_completion(state)
        if status != MissionStatus.IN_PROGRESS:
            print(f"\n{status_msg}")
            break

    print(f"\n최종 모집 순서: {state.recruitment_order}")
    print(f"최종 상태: {state.status.value}")
