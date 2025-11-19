"""
SSE (Server-Sent Events) Helper
채팅 응답을 SSE 형식으로 스트리밍
"""
import json
from typing import Any, AsyncGenerator, Optional


async def sse_generator(
    session_id: str,
    dialogues: list,
    turn_count: int,
    current_stage: str,
    affinity_scores: dict,
    is_ended: bool,
    has_more: bool,
    current_image: str = None,
    output: dict = None,
    memory_events: list = None,
    stage_turn: int = 0,
    user_language: str = "ko"
) -> AsyncGenerator[str, None]:
    """
    SSE 형식으로 채팅 응답 스트리밍

    프론트엔드가 기대하는 형식:
    - data: {"type": "metadata", "session_id": "...", ...}
    - data: {"type": "dialogue", "dialogue": {...}, "index": 0}
    - data: {"type": "done", ...}

    다국어 지원:
    - user_language가 "ko"가 아니면 각 dialogue를 번역하여 전송
    """
    # 번역 서비스 초기화 (필요한 경우)
    translator = None
    if user_language != "ko":
        from app.features.chat.services import TranslationService
        translator = TranslationService()

    # 1. metadata 전송
    metadata = {
        "type": "metadata",
        "session_id": session_id,
        "has_more": has_more,
        "current_image": current_image,
        "turn_count": turn_count,
        "stage_turn": stage_turn,
        "current_stage": current_stage
    }
    yield f"data: {json.dumps(metadata)}\n\n"

    # 2. 각 dialogue 순차 전송 (번역 포함)
    for index, dialogue in enumerate(dialogues):
        # 번역 처리
        dialogue_text = dialogue.text
        if translator:
            dialogue_text = await translator.translate_dialogue(
                text=dialogue.text,
                to_lang=user_language,
                speaker=dialogue.speaker,
                emotion=dialogue.emotion if hasattr(dialogue, 'emotion') else "neutral"
            )

        dialogue_data = {
            "type": "dialogue",
            "index": index,
            "dialogue": {
                "speaker": dialogue.speaker,
                "text": dialogue_text,  # 번역된 텍스트
                "emotion": dialogue.emotion if hasattr(dialogue, 'emotion') else "neutral",
                "timestamp": None,
                "fx": None,
                "image_index": None,
                "affinity_level": None,
                "emotion_intensity": None
            }
        }
        yield f"data: {json.dumps(dialogue_data)}\n\n"

    # 3. done 전송 (최종 상태)
    done_data = {
        "type": "done",
        "turn_count": turn_count,
        "stage_turn": stage_turn,
        "current_stage": current_stage,
        "affinity_scores": affinity_scores or {},
        "is_ended": is_ended,
        "output": output or {},
        "memory_events": [
            {
                "event_type": event.event_type,
                "character_name": event.character_name,
                "memory_type": event.memory_type,
                "memory_content": event.memory_content,
                "importance": event.importance,
                "count": event.count
            } for event in (memory_events or [])
        ] if memory_events else []
    }
    yield f"data: {json.dumps(done_data)}\n\n"
