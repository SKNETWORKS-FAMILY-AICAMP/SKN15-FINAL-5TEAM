"""
World Definition Loader

세계관 정의 파일(YAML)을 로드하고 캐싱하는 유틸리티.
"""
# ============================================================
# 🌍 월드 로더 — 배경 컨텍스트 로드
# ============================================================
import os
from typing import Dict, Any, Optional
import yaml
from pathlib import Path

import logging
from src.core.utils.logger import log


class WorldLoader:
    """
    World definition loader with caching.

    Usage:
        world = WorldLoader.load("demon_slayer_taisho")
        world_context = world.get("world_context", "")
    """

    _cache: Dict[str, Dict[str, Any]] = {}
    _worlds_dir: Optional[Path] = None

    @classmethod
    def _get_worlds_dir(cls) -> Path:
        """Get the worlds directory path."""
        if cls._worlds_dir is None:
            current_file = Path(__file__)
            backend_dir = current_file.parent.parent.parent
            cls._worlds_dir = backend_dir / "data" / "worlds"
        return cls._worlds_dir

    @classmethod
    def load(cls, world_id: str) -> Dict[str, Any]:
        """
        Load world definition by world_id.

        Args:
            world_id: World identifier (e.g., "demon_slayer_taisho")

        Returns:
            World definition dictionary

        Raises:
            FileNotFoundError: If world file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if world_id in cls._cache:
            log("world_loader", f"✅ Cache hit: {world_id}")
            return cls._cache[world_id]

        #   
        worlds_dir = cls._get_worlds_dir()
        world_file = worlds_dir / f"{world_id}.yaml"

        if not world_file.exists():
            raise FileNotFoundError(
                f"World file not found: {world_file}\n"
                f"Available worlds: {cls.list_available_worlds()}"
            )

        log("world_loader", f"📖 Loading world: {world_id} from {world_file}")

        try:
            with open(world_file, "r", encoding="utf-8") as f:
                world_data = yaml.safe_load(f)

            #   
            required_fields = ["world_id", "title", "world_context"]
            missing = [field for field in required_fields if field not in world_data]
            if missing:
                raise ValueError(f"Missing required fields in {world_id}: {missing}")

            # 캐시  
            cls._cache[world_id] = world_data
            log("world_loader", f"✅ Loaded and cached: {world_id}")
            return world_data

        except yaml.YAMLError as e:
            log("world_loader", f"❌ YAML parsing error in {world_file}: {e}")
            raise

    @classmethod
    def get_world_context(cls, world_id: str) -> str:
        """
        Get world_context string from world definition.

        Args:
            world_id: World identifier

        Returns:
            World context string (empty if not found or error)
        """
        try:
            world = cls.load(world_id)
            return world.get("world_context", "")
        except Exception as e:
            log("world_loader", f"⚠️ Failed to load world context for {world_id}: {e}")
            return ""

    @classmethod
    def list_available_worlds(cls) -> list[str]:
        """
        List all available world IDs.

        Returns:
            List of world_id strings
        """
        worlds_dir = cls._get_worlds_dir()

        if not worlds_dir.exists():
            log("world_loader", f"⚠️ Worlds directory not found: {worlds_dir}")
            return []

        world_files = list(worlds_dir.glob("*.yaml"))
        world_ids = [f.stem for f in world_files]

        log("world_loader", f"📚 Available worlds: {world_ids}")
        return world_ids

    @classmethod
    def clear_cache(cls):
        """Clear the world definition cache."""
        cls._cache.clear()
        log("world_loader", "🗑️ Cache cleared")
