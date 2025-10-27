from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# -------------------------------
# ✅ Dynamic path fix (서버/로컬 둘 다 동작)
# -------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]  # backend/src → backend
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

# -------------------------------
# ✅ 안전한 logger import
# -------------------------------
try:
    from src.utils import log  # 정상 경로
except Exception:
    # fallback: 로컬 실행 시 상대 import
    sys.path.append(str(BASE_DIR / "src" / "utils"))
    from logger import log


class ScenesRepo:
    """🎬 시나리오(JSON) 로드 및 캐싱 담당 클래스"""

    def __init__(self, base_dir: Optional[str] = None):
        # 기본 시나리오 경로 지정
        self.base_dir = Path(
            base_dir or BASE_DIR / "data" / "scenarios"
        )
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """시나리오 JSON 로드"""
        if scenario_id in self._cache:
            return self._cache[scenario_id]

        file_path = self.base_dir / f"{scenario_id}.json"
        if not file_path.exists():
            log("scenes_repo", f"❌ Scenario file not found: {file_path}")
            return None

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            self._cache[scenario_id] = data
            title = data.get("title", "Untitled")
            version = data.get("version", "?")
            log("scenes_repo", f"✅ Loaded scenario: {title} (ver. {version})")
            return data
        except Exception as e:
            log("scenes_repo", f"⚠️ Failed to load scenario: {e}")
            return None
