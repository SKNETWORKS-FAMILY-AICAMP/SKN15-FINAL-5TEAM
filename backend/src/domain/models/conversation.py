# ============================================================
# 💬 대화 모델 — 턴·대사 자료구조
# ============================================================
# //.
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class Dialogue:
    speaker: str
    content: str
    emotion: Optional[str] = None
    fx: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker": self.speaker,
            "text": self.content,
            "emotion": self.emotion,
            "fx": self.fx,
        }

@dataclass
class ConversationTurn:
    turn_number: int
    user_input: str
    agent_responses: List[Dialogue]
