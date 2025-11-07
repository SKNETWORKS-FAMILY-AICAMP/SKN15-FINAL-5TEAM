"""
캐릭터 저장소 서비스

API: list_characters(), get_character(id), default_affinity_of(id),
     flags(affinity_visible/applicable), build_character_rulebook(char)
"""

# ============================================================
# 👥 캐릭터 저장소 — 스토리 메타데이터 제공
# ============================================================
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, Any, List, Tuple, Optional

from core.interfaces.repositories.character_repository import ICharacterRepository

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAR_DIR = os.path.join(BASE_DIR, "data", "characters")


class CharacterService:
    """
    캐릭터 데이터 서비스

    의존성 주입을 통해 Repository를 받아 사용
    """

    def __init__(self, character_repository: ICharacterRepository):
        self._repo = character_repository
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load_characters(self) -> Dict[str, Dict[str, Any]]:
        """Load all characters from repository and cache"""
        if self._cache:
            return self._cache

        data: Dict[str, Dict[str, Any]] = {}
        try:
            # Repository를 통해 모든 캐릭터 조회
            characters = self._repo.get_all()
            for char in characters:
                char_id = char.get("id", "").strip().lower()
                if char_id:
                    data[char_id] = char
        except Exception as e:
            print(f"Failed to load characters from repository: {e}")
            # 폴백: 파일에서 로드
            if os.path.isdir(CHAR_DIR):
                for name in os.listdir(CHAR_DIR):
                    if not name.endswith(".json"):
                        continue
                    path = os.path.join(CHAR_DIR, name)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            obj = json.load(f)
                        cid = (obj.get("id") or os.path.splitext(name)[0]).strip().lower()
                        data[cid] = obj
                    except Exception:
                        continue

        self._cache = data
        return data

    def list_characters(self) -> List[str]:
        """모든 캐릭터 ID 목록 반환"""
        return list(self._load_characters().keys())

    def get_character(self, char_id: str) -> Optional[Dict[str, Any]]:
        """캐릭터 정보 조회"""
        return self._load_characters().get(str(char_id).strip().lower())

    def default_affinity_of(self, char_id: str) -> int:
        """캐릭터의 기본 호감도 반환"""
        obj = self.get_character(char_id) or {}
        if "default_affinity" in obj:
            try:
                return int(obj.get("default_affinity") or 0)
            except Exception:
                return 0
        prof = obj.get("profile") or {}
        try:
            return int(prof.get("default_affinity") or 0)
        except Exception:
            return 0

    def affinity_visible(self, char_id: str, base_dir: str = "data/characters") -> bool:
        """호감도 표시 여부"""
        fp = os.path.join(base_dir, f"{char_id}.json")
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            node = (data.get("characters") or {}).get(char_id) or data
            return bool(node.get("affinity_visible", True))
        except Exception:
            return True

    def affinity_applicable(self, char_id: str) -> bool:
        """호감도 적용 여부"""
        obj = self.get_character(char_id) or {}
        return bool(obj.get("affinity_applicable", True))

    def build_character_rulebook(self, char_id: str) -> Dict[str, Any]:
        """캐릭터의 Intent 규칙북 생성"""
        obj = self.get_character(char_id) or {}
        rules = obj.get("intent_rules") or {}
        return {
            "weights": rules.get("weights", {}),
            "patterns": rules.get("patterns", {}),
            "sensitivities": rules.get("sensitivities", {}),
            "overrides": rules.get("overrides", {}),
            "priorities": rules.get("priorities", {}),
        }

    def character_names_aliases(self) -> List[Tuple[str, List[str]]]:
        """
        캐릭터 이름 및 별칭 목록 반환

        Returns:
            List of (char_id, aliases) with primary name included
        """
        out: List[Tuple[str, List[str]]] = []
        for cid, obj in self._load_characters().items():
            names: List[str] = []
            # 기본 이름
            for k in ("name", "name_ko"):
                v = obj.get(k)
                if isinstance(v, str) and v:
                    names.append(v)
            if "characters" in obj and isinstance(obj["characters"], dict):
                inner = obj["characters"].get(cid) or {}
                for k in ("name", "name_ko"):
                    v = inner.get(k)
                    if isinstance(v, str) and v:
                        names.append(v)
                # 별칭
                als = inner.get("aliases") or []
                if isinstance(als, list):
                    for a in als:
                        if isinstance(a, str) and a:
                            names.append(a)
            # 중복 제거
            uniq = []
            for n in names:
                n = n.strip()
                if n and n not in uniq:
                    uniq.append(n)
            if cid not in uniq:
                uniq.append(cid)
            out.append((cid, uniq))
        return out


# ============================================================
# 하위 호환성을 위한 전역 함수 (Deprecated)
# ============================================================
# TODO: 모든 호출자를 CharacterService로 마이그레이션 후 삭제
_global_service: Optional[CharacterService] = None


def _get_global_service() -> CharacterService:
    """전역 서비스 인스턴스 (임시)"""
    global _global_service
    if _global_service is None:
        # 임시: DI Container에서 주입받도록 수정 필요
        from infrastructure.di.container import get_container
        container = get_container()
        _global_service = CharacterService(container.character_repository)
    return _global_service


def list_characters() -> List[str]:
    """DEPRECATED: CharacterService.list_characters() 사용"""
    return _get_global_service().list_characters()


def get_character(char_id: str) -> Optional[Dict[str, Any]]:
    """DEPRECATED: CharacterService.get_character() 사용"""
    return _get_global_service().get_character(char_id)


def default_affinity_of(char_id: str) -> int:
    """DEPRECATED: CharacterService.default_affinity_of() 사용"""
    return _get_global_service().default_affinity_of(char_id)


def affinity_visible(char_id: str, base_dir: str = "data/characters") -> bool:
    """DEPRECATED: CharacterService.affinity_visible() 사용"""
    return _get_global_service().affinity_visible(char_id, base_dir)


def affinity_applicable(char_id: str) -> bool:
    """DEPRECATED: CharacterService.affinity_applicable() 사용"""
    return _get_global_service().affinity_applicable(char_id)


def build_character_rulebook(char_id: str) -> Dict[str, Any]:
    """DEPRECATED: CharacterService.build_character_rulebook() 사용"""
    return _get_global_service().build_character_rulebook(char_id)


def character_names_aliases() -> List[Tuple[str, List[str]]]:
    """DEPRECATED: CharacterService.character_names_aliases() 사용"""
    return _get_global_service().character_names_aliases()
