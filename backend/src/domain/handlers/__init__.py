# ============================================================
# 🎯 핸들러 패키지 초기화 — 스테이지결과 재노출
# ============================================================
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class StageResult:
    children_ctx: Dict[str, Any] = field(default_factory=dict)
    stage_complete: bool = False
    next_stage: Optional[str] = None
    scene_tool_response: Optional[Any] = None
    state_tool_response: Optional[Any] = None
