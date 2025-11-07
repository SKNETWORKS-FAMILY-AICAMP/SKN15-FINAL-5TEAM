"""
Scenario Service - 시나리오 및 캐릭터 데이터 로드
YAML/JSON 파일에서 시나리오, 캐릭터, world 설정을 로드하고 관리
"""
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from app.core.logging import get_parent_logger

logger = get_parent_logger("ScenarioService")


class ScenarioService:
    """
    시나리오 및 캐릭터 데이터 로드 서비스

    책임:
    - 시나리오 JSON 파일 로드
    - 캐릭터 JSON 파일 로드
    - World YAML 파일 로드
    - 데이터 캐싱
    """

    def __init__(self, data_dir: str = "/app/data"):
        """
        ScenarioService 초기화

        Args:
            data_dir: 데이터 디렉토리 경로
        """
        self.data_dir = Path(data_dir)
        self.scenarios_dir = self.data_dir / "scenarios"
        self.characters_dir = self.data_dir / "characters"
        self.worlds_dir = self.data_dir / "worlds"

        # 캐시
        self._scenario_cache: Dict[str, Dict[str, Any]] = {}
        self._character_cache: Dict[str, Dict[str, Any]] = {}
        self._world_cache: Dict[str, Dict[str, Any]] = {}

        logger.info("__init__", f"ScenarioService initialized with data_dir={data_dir}")

    def load_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        시나리오 로드

        Args:
            scenario_id: 시나리오 ID

        Returns:
            시나리오 데이터 dict 또는 None
        """
        # 캐시 확인
        if scenario_id in self._scenario_cache:
            logger.info("load_scenario", f"Scenario loaded from cache: {scenario_id}")
            return self._scenario_cache[scenario_id]

        # 파일에서 로드
        scenario_file = self.scenarios_dir / f"{scenario_id}.json"
        if not scenario_file.exists():
            logger.warning("load_scenario", f"Scenario file not found: {scenario_file}")
            return None

        try:
            with open(scenario_file, "r", encoding="utf-8") as f:
                scenario_data = json.load(f)

            # 캐시 저장
            self._scenario_cache[scenario_id] = scenario_data

            logger.info("load_scenario", f"✅ Scenario loaded: {scenario_id}")
            return scenario_data

        except Exception as e:
            logger.error("load_scenario", f"❌ Failed to load scenario {scenario_id}: {e}")
            return None

    def load_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """
        캐릭터 데이터 로드

        Args:
            character_id: 캐릭터 ID

        Returns:
            캐릭터 데이터 dict 또는 None
        """
        # 캐시 확인
        if character_id in self._character_cache:
            logger.info("load_character", f"Character loaded from cache: {character_id}")
            return self._character_cache[character_id]

        # 파일에서 로드
        character_file = self.characters_dir / f"{character_id}.json"
        if not character_file.exists():
            logger.warning("load_character", f"Character file not found: {character_file}")
            return None

        try:
            with open(character_file, "r", encoding="utf-8") as f:
                character_data = json.load(f)

            # characters 키 안의 실제 데이터 추출
            if "characters" in character_data and character_id in character_data["characters"]:
                character_info = character_data["characters"][character_id]
            else:
                logger.warning("load_character", f"Character {character_id} not found in file structure")
                return None

            # 캐시 저장
            self._character_cache[character_id] = character_info

            logger.info("load_character", f"✅ Character loaded: {character_id}")
            return character_info

        except Exception as e:
            logger.error("load_character", f"❌ Failed to load character {character_id}: {e}")
            return None

    def load_world(self, world_id: str) -> Optional[Dict[str, Any]]:
        """
        World 데이터 로드

        Args:
            world_id: World ID

        Returns:
            World 데이터 dict 또는 None
        """
        # 캐시 확인
        if world_id in self._world_cache:
            logger.info("load_world", f"World loaded from cache: {world_id}")
            return self._world_cache[world_id]

        # 파일에서 로드 (YAML)
        world_file = self.worlds_dir / f"{world_id}.yaml"
        if not world_file.exists():
            logger.warning("load_world", f"World file not found: {world_file}")
            return None

        try:
            with open(world_file, "r", encoding="utf-8") as f:
                world_data = yaml.safe_load(f)

            # 캐시 저장
            self._world_cache[world_id] = world_data

            logger.info("load_world", f"✅ World loaded: {world_id}")
            return world_data

        except Exception as e:
            logger.error("load_world", f"❌ Failed to load world {world_id}: {e}")
            return None

    def get_character_personality(self, character_id: str, scenario_id: Optional[str] = None) -> str:
        """
        캐릭터 성격 설명 가져오기

        Args:
            character_id: 캐릭터 ID
            scenario_id: 시나리오 ID (있으면 scenario_specific 정보 포함)

        Returns:
            성격 설명 문자열
        """
        character = self.load_character(character_id)
        if not character:
            return "친근하고 밝은 성격"

        # 기본 personality
        personality = character.get("personality", "")
        description = character.get("description", "")

        # Core values 추가
        core_values = character.get("core_values", [])
        if core_values:
            values_text = " ".join(core_values)
            personality += f". {values_text}"

        # Description 추가
        if description:
            personality += f". {description}"

        logger.info("get_character_personality", f"Personality for {character_id}: {personality[:100]}...")
        return personality

    def get_character_emotion(self, character_id: str, affinity: int = 500) -> str:
        """
        친밀도에 따른 캐릭터 감정 상태 결정

        Args:
            character_id: 캐릭터 ID
            affinity: 친밀도 (0-1000)

        Returns:
            감정 상태 문자열
        """
        character = self.load_character(character_id)
        if not character:
            return "neutral"

        # Tone 설정에서 친밀도별 스타일 확인
        tone_config = character.get("tone", {})

        if affinity < 300:
            tone_info = tone_config.get("low", {})
            style = tone_info.get("style", "조심스럽고 예의바른 어투")
            logger.info("get_character_emotion", f"{character_id} at low affinity ({affinity}): {style}")
            return "polite"
        elif affinity < 700:
            tone_info = tone_config.get("mid", {})
            style = tone_info.get("style", "단호하지만 따뜻한 어투")
            logger.info("get_character_emotion", f"{character_id} at mid affinity ({affinity}): {style}")
            return "friendly"
        else:
            tone_info = tone_config.get("high", {})
            style = tone_info.get("style", "결연하고 따뜻한 어투")
            logger.info("get_character_emotion", f"{character_id} at high affinity ({affinity}): {style}")
            return "warm"

    def get_world_context(self, world_id: str) -> str:
        """
        World 컨텍스트 가져오기 (LLM 프롬프트에 사용)

        Args:
            world_id: World ID

        Returns:
            World 컨텍스트 문자열
        """
        world = self.load_world(world_id)
        if not world:
            return ""

        context = world.get("world_context", "")
        logger.info("get_world_context", f"World context for {world_id}: {len(context)} chars")
        return context

    def get_scenario_characters(self, scenario_id: str) -> List[str]:
        """
        시나리오에 등장하는 캐릭터 ID 목록

        Args:
            scenario_id: 시나리오 ID

        Returns:
            캐릭터 ID 리스트
        """
        scenario = self.load_scenario(scenario_id)
        if not scenario:
            return []

        character_refs = scenario.get("character_refs", {})
        character_ids = list(character_refs.keys())

        logger.info("get_scenario_characters", f"Characters in {scenario_id}: {character_ids}")
        return character_ids

    def clear_cache(self):
        """캐시 초기화"""
        self._scenario_cache.clear()
        self._character_cache.clear()
        self._world_cache.clear()
        logger.info("clear_cache", "All caches cleared")
