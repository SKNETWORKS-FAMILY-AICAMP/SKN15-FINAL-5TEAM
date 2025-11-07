# ============================================================
# 📖 스토리 모델 — 스테이지· 데이터 구조
# ============================================================
# //.
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Beat:
    """A single unit of action or dialogue in a scene."""
    #    
    goal: Optional[str] = None
    speaker_hint: List[str] = field(default_factory=list)
    fx: Optional[str] = None
    
    text: Optional[str] = None
    speaker: Optional[str] = None
    
    #     
    line: Optional[str] = None
    description: Optional[str] = None
