"""
멀티캐릭터 대화 티키타카 시스템

컷신 종료 후 현장의 모든 캐릭터들이 3-4회 상호 대화를 나누는 시스템
하드코딩 금지, 제이슨 시나리오 기반 동적 생성
"""
# ============================================================
# 👪 멀티 캐릭터 대화 생성기 — 합창형 장면 지원
# ============================================================
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional


class MultiCharacterConversation:
    """멀티캐릭터 대화 관리자"""

    def __init__(self, prompts_file: str = "data/conversation_prompts.json"):
        """
        초기화

        Args:
            prompts_file: 대화 프롬프트 JSON 파일 경로
        """
        self.prompts_file = Path(prompts_file)
        self.prompts_data = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        """대화 프롬프트 JSON 로드"""
        if not self.prompts_file.exists():
            print(f"[WARNING] Prompts file not found: {self.prompts_file}")
            return {}

        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse prompts JSON: {e}")
            return {}

    def get_participants(
        self,
        scene_key: str,
        state: Optional[Any] = None
    ) -> List[str]:
        """
        현재 씬의 참여 캐릭터 목록 반환

        Args:
            scene_key: 씬 키 (예: "cutscene5_victory")
            state: 게임 상태 (옵션)

        Returns:
            참여 캐릭터 목록
        """
        if scene_key not in self.prompts_data:
            print(f"[WARNING] Scene key not found: {scene_key}")
            return ["tanjiro", "user"]  # 기본값

        scene_data = self.prompts_data[scene_key]
        participants = scene_data.get("participants", [])

        # 상태 기반 동적 필터링 (옵션)
        if state:
            # 예: 특정 플래그가 있는 경우에만 특정 캐릭터 포함
            if hasattr(state, 'game') and hasattr(state.game, 'flags'):
                flags = state.game.flags

                if "inosuke_recruited" not in flags and "inosuke" in participants:
                    participants = [p for p in participants if p != "inosuke"]

                if "zenitsu_recruited" not in flags and "zenitsu" in participants:
                    participants = [p for p in participants if p != "zenitsu"]

        return participants

    def generate_conversation(
        self,
        scene_key: str,
        state: Optional[Any] = None,
        num_exchanges: int = 4,
        use_llm: bool = False
    ) -> List[Dict[str, str]]:
        """
        멀티캐릭터 대화 생성

        Args:
            scene_key: 씬 키 (예: "cutscene5_victory")
            state: 게임 상태 (옵션)
            num_exchanges: 대화 교환 횟수 (기본 4회)
            use_llm: LLM 사용 여부 (기본 False, 템플릿 기반)

        Returns:
            대화 메시지 리스트 [{"speaker": "tanjiro", "content": "...", "listener": "rengoku"}, ...]
        """
        if scene_key not in self.prompts_data:
            print(f"[ERROR] Scene key not found: {scene_key}")
            return []

        participants = self.get_participants(scene_key, state)
        scene_data = self.prompts_data[scene_key]
        prompts = scene_data.get("prompts", {})

        if len(participants) < 2:
            print(f"[WARNING] Not enough participants for conversation: {participants}")
            return []

        messages = []

        # 티키타카 대화 루프
        for i in range(num_exchanges):
            # 현재 말하는 사람과 듣는 사람 선택
            speaker = participants[i % len(participants)]
            listener = participants[(i + 1) % len(participants)]

            # 해당 캐릭터의 프롬프트 선택
            if speaker not in prompts:
                print(f"[WARNING] No prompts for speaker: {speaker}")
                continue

            speaker_prompts = prompts[speaker]

            if not speaker_prompts:
                print(f"[WARNING] Empty prompts for speaker: {speaker}")
                continue

            # 무작위로 프롬프트 선택
            prompt_template = random.choice(speaker_prompts)

            content = prompt_template.format(listener=self._get_display_name(listener))

            # LLM 사용 시 추가 처리 (향후 구현)
            if use_llm:
                content = self._enhance_with_llm(content, speaker, listener, state)

            messages.append({
                "speaker": speaker,
                "content": content,
                "listener": listener,
                "turn": i
            })

        return messages

    def _get_display_name(self, character: str) -> str:
        """캐릭터 표시 이름 반환"""
        display_names = {
            "tanjiro": "탄지로",
            "rengoku": "렌고쿠",
            "inosuke": "이노스케",
            "zenitsu": "젠이츠",
            "akaza": "아카자",
            "user": "당신"
        }
        return display_names.get(character, character)

    def _enhance_with_llm(
        self,
        base_content: str,
        speaker: str,
        listener: str,
        state: Optional[Any]
    ) -> str:
        """
        LLM으로 대화 내용 강화 (향후 구현)

        Args:
            base_content: 기본 템플릿 내용
            speaker: 말하는 캐릭터
            listener: 듣는 캐릭터
            state: 게임 상태

        Returns:
            강화된 대화 내용
        """
        # TODO: LLM API를 호출해 더 풍부한 대화를 생성하도록 확장
        # 현재는 기본 템플릿 그대로 반환
        return base_content

    def apply_to_state(
        self,
        state: Any,
        scene_key: str,
        num_exchanges: int = 4,
        use_llm: bool = False
    ) -> None:
        """
        생성된 대화를 게임 상태에 적용

        Args:
            state: 게임 상태
            scene_key: 씬 키
            num_exchanges: 대화 교환 횟수
            use_llm: LLM 사용 여부
        """
        messages = self.generate_conversation(scene_key, state, num_exchanges, use_llm)

        if not messages:
            print(f"[WARNING] No messages generated for scene: {scene_key}")
            return

        # 상태에 대화 메시지 추가
        for msg in messages:
            speaker = msg["speaker"]
            content = msg["content"]

            # 상태 객체에 대화를 추가
            if hasattr(state, 'output') and hasattr(state.output, 'add_dialogue'):
                state.output.add_dialogue(
                    speaker=speaker,
                    content=content,
                    emotion="friendly",
                    affinity_level=None
                )

            # 콘솔 출력
            display_name = self._get_display_name(speaker)
            listener_name = self._get_display_name(msg["listener"])
            print(f"\n[{display_name} → {listener_name}] {content}", flush=True)

        print(f"\n[CONVERSATION] Generated {len(messages)} multi-character exchanges", flush=True)


# 편의 함수
def simulate_conversation(
    scene_key: str,
    num_exchanges: int = 4,
    state: Optional[Any] = None,
    use_llm: bool = False
) -> List[Dict[str, str]]:
    """
    멀티캐릭터 대화 시뮬레이션 편의 함수

    Args:
        scene_key: 씬 키
        num_exchanges: 대화 교환 횟수
        state: 게임 상태 (옵션)
        use_llm: LLM 사용 여부

    Returns:
        대화 메시지 리스트
    """
    conv = MultiCharacterConversation()
    return conv.generate_conversation(scene_key, state, num_exchanges, use_llm)


if __name__ == "__main__":
    # 테스트
    print("=== 멀티캐릭터 대화 시스템 테스트 ===\n")

    conv = MultiCharacterConversation()

    # 컷신5 승리 후 대화
    print("📍 컷신5 승리 후 대화:")
    print("-" * 70)
    messages = conv.generate_conversation("cutscene5_victory", num_exchanges=4)

    for msg in messages:
        speaker_name = conv._get_display_name(msg["speaker"])
        listener_name = conv._get_display_name(msg["listener"])
        print(f"\n[{speaker_name} → {listener_name}]")
        print(f"  {msg['content']}")

    # 컷신5 동료 규합 후 대화
    print("\n\n📍 컷신5 동료 규합 성공 후 대화:")
    print("-" * 70)
    messages = conv.generate_conversation("cutscene5_recruit", num_exchanges=4)

    for msg in messages:
        speaker_name = conv._get_display_name(msg["speaker"])
        listener_name = conv._get_display_name(msg["listener"])
        print(f"\n[{speaker_name} → {listener_name}]")
        print(f"  {msg['content']}")

    print("\n\n✅ 테스트 완료!")
