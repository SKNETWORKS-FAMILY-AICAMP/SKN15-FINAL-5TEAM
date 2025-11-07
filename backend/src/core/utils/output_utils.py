"""
출력 유틸리티 - 순차적인 대화 출력
"""

import time
from typing import List
from src.core.graph_state import Dialogue


def display_dialogues_sequentially(dialogues: List[Dialogue], delay: float = 2.0):
    """
    대사를 순차적으로 출력 (채팅 느낌)

    Args:
        dialogues: 대사 리스트
        delay: 각 대사 사이의 딜레이 (초)
    """
    # 이모지 매핑
    emotion_emoji = {
        "happy": "😊",
        "sad": "😢",
        "angry": "😠",
        "worried": "😰",
        "determined": "💪",
        "neutral": "😐",
        "excited": "🤩"
    }

    for i, dialogue in enumerate(dialogues):
        # Pydantic 모델 속성 접근
        speaker = dialogue.speaker if hasattr(dialogue, 'speaker') else "Unknown"
        content = dialogue.content if hasattr(dialogue, 'content') else ""
        emotion = dialogue.emotion if hasattr(dialogue, 'emotion') else "neutral"

        emoji = emotion_emoji.get(emotion, "💭")

        # 대사 출력
        print(f"{emoji} {speaker}: {content}")

        # 마지막 대사가 아니면 딜레이
        if i < len(dialogues) - 1:
            time.sleep(delay)


def display_dialogues_with_typing_effect(dialogues: List[Dialogue], delay: float = 2.0, typing_speed: float = 0.03):
    """
    타이핑 효과와 함께 대사 출력

    Args:
        dialogues: 대사 리스트
        delay: 각 대사 사이의 딜레이 (초)
        typing_speed: 각 글자의 타이핑 속도 (초)
    """
    emotion_emoji = {
        "happy": "😊",
        "sad": "😢",
        "angry": "😠",
        "worried": "😰",
        "determined": "💪",
        "neutral": "😐",
        "excited": "🤩"
    }

    for i, dialogue in enumerate(dialogues):
        speaker = dialogue.speaker if hasattr(dialogue, 'speaker') else "Unknown"
        content = dialogue.content if hasattr(dialogue, 'content') else ""
        emotion = dialogue.emotion if hasattr(dialogue, 'emotion') else "neutral"

        emoji = emotion_emoji.get(emotion, "💭")

        # 이름 먼저 출력
        print(f"{emoji} {speaker}: ", end='', flush=True)

        # 타이핑 효과
        for char in content:
            print(char, end='', flush=True)
            time.sleep(typing_speed)

        print()  # 줄바꿈

        # 마지막 대사가 아니면 딜레이
        if i < len(dialogues) - 1:
            time.sleep(delay)
