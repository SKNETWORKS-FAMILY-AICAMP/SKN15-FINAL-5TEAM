"""
Shared Types
공통 타입 정의
"""
from typing import TypedDict, Optional, Dict, Any
from enum import Enum


# ============================================================
# Enum Types
# ============================================================

class EmotionType(str, Enum):
    """캐릭터 감정 타입"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    WORRIED = "worried"


class StageType(str, Enum):
    """스테이지 타입"""
    SCENE = "scene"
    MISSION = "mission"
    NARRATIVE = "narrative"
    ROUTER = "router"
    FREE_INTENT = "free_intent"


# ============================================================
# TypedDict
# ============================================================

class UserContext(TypedDict, total=False):
    """사용자 컨텍스트"""
    user_id: str
    username: str
    session_id: str
    scenario_id: str


class DialogueContext(TypedDict, total=False):
    """대화 생성 컨텍스트"""
    speaker_pool: list[str]
    beats: list[Dict[str, Any]]
    stage_tag: str
    stage_type: str
    user_message: str
    session_state: Dict[str, Any]
