"""
Scenario Service - 시나리오 및 캐릭터 데이터 로드
YAML/JSON 파일에서 시나리오, 캐릭터, world 설정을 로드하고 관리
"""
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from app.core.logging import get_parent_logger
from app.core.config import get_settings

logger = get_parent_logger("ScenarioService")
settings = get_settings()


class ScenarioService:
    """
    시나리오 및 캐릭터 데이터 로드 서비스

    책임:
    - 시나리오 JSON 파일 로드
    - 캐릭터 JSON 파일 로드
    - World YAML 파일 로드
    - 데이터 캐싱
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        ScenarioService 초기화

        Args:
            data_dir: 데이터 디렉토리 경로 (None이면 settings에서 로드)
        """
        if data_dir is None:
            data_dir = settings.DATA_DIR
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

    def get_beats_for_stage(self, scenario_id: str, stage_id: str, language: str = "ko") -> Optional[List[Dict[str, Any]]]:
        """
        특정 스테이지의 Beats 가져오기

        Args:
            scenario_id: 시나리오 ID
            stage_id: 스테이지 ID (예: "rengoku_dialogue", "enmu_appear")
            language: 언어 코드 (기본: "ko")

        Returns:
            Beats 리스트 또는 None
        """
        scenario = self.load_scenario(scenario_id)
        if not scenario:
            logger.warning("get_beats_for_stage", f"Scenario not found: {scenario_id}")
            return None

        # i18n 섹션에서 beats 찾기
        i18n = scenario.get("i18n", {})
        lang_data = i18n.get(language, {})

        # beats_{stage_id} 형태로 찾기
        beats_key = f"beats_{stage_id}"
        beats = lang_data.get(beats_key)

        if beats:
            logger.info("get_beats_for_stage", f"Beats found for {scenario_id}/{stage_id}: {len(beats)} beats")
            return beats
        else:
            logger.warning("get_beats_for_stage", f"Beats not found for {scenario_id}/{stage_id}")
            return None

    def get_available_beat_stages(self, scenario_id: str, language: str = "ko") -> List[str]:
        """
        시나리오에서 사용 가능한 beat stage 목록

        Args:
            scenario_id: 시나리오 ID
            language: 언어 코드

        Returns:
            Stage ID 리스트 (beats_ 접두사 제거됨)
        """
        scenario = self.load_scenario(scenario_id)
        if not scenario:
            return []

        i18n = scenario.get("i18n", {})
        lang_data = i18n.get(language, {})

        # beats_로 시작하는 모든 키 찾기
        beat_stages = []
        for key in lang_data.keys():
            if key.startswith("beats_"):
                stage_id = key.replace("beats_", "")
                beat_stages.append(stage_id)

        logger.info("get_available_beat_stages", f"Beat stages in {scenario_id}: {beat_stages}")
        return beat_stages

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 모든 시나리오 목록 조회

        Returns:
            시나리오 메타데이터 리스트
            [
                {
                    "scenario_id": str,
                    "title": str,
                    "description": str,
                    "difficulty": str,
                    "tags": list,
                    ...
                }
            ]
        """
        logger.info("list_scenarios", f"Listing scenarios from {self.scenarios_dir}")

        scenarios = []

        # scenarios 디렉토리가 없으면 빈 리스트 반환
        if not self.scenarios_dir.exists():
            logger.warning("list_scenarios", f"Scenarios directory not found: {self.scenarios_dir}")
            return scenarios

        # 모든 .json 파일 탐색
        for scenario_file in self.scenarios_dir.glob("*.json"):
            try:
                scenario_id = scenario_file.stem  # 파일명에서 확장자 제거

                # 시나리오 로드
                scenario_data = self.load_scenario(scenario_id)
                if not scenario_data:
                    continue

                # 메타데이터 추출
                metadata = {
                    "scenario_id": scenario_id,
                    "title": scenario_data.get("title", scenario_id),
                    "description": scenario_data.get("description", ""),
                    "version": scenario_data.get("version", "1.0"),
                    "difficulty": scenario_data.get("difficulty", "medium"),
                    "tags": scenario_data.get("tags", []),
                    "world_id": scenario_data.get("world_id", ""),
                    "character_refs": list(scenario_data.get("character_refs", {}).keys()),
                }

                scenarios.append(metadata)

            except Exception as e:
                logger.error("list_scenarios", f"Failed to load scenario {scenario_file}: {e}")
                continue

        logger.info("list_scenarios", f"Found {len(scenarios)} scenarios")
        return scenarios

    def clear_cache(self):
        """캐시 초기화"""
        self._scenario_cache.clear()
        self._character_cache.clear()
        self._world_cache.clear()
        logger.info("clear_cache", "All caches cleared")
