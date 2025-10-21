"""
Config Loader - YAML 설정 파일 통합 로더

모든 설정 파일(settings.yaml, prompts.yaml, characters.yaml)을
중앙에서 로드하고 관리하는 유틸리티
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """YAML 설정 파일 로더"""

    _instance = None
    _configs = {}

    def __new__(cls):
        """싱글톤 패턴으로 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """초기화 - 한 번만 실행"""
        if self._initialized:
            return

        # 프로젝트 루트 경로 찾기
        self.root_dir = self._find_project_root()
        self.configs_dir = self.root_dir / "configs"

        # 모든 설정 파일 로드
        self._load_all_configs()
        self._initialized = True

    def _find_project_root(self) -> Path:
        """프로젝트 루트 디렉토리 찾기"""
        current = Path(__file__).resolve()

        # src/utils에서 2단계 위로 올라가면 루트
        # /path/to/kime_chat_agent/src/utils/config_loader.py
        # → /path/to/kime_chat_agent
        return current.parent.parent.parent

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """YAML 파일 로드"""
        filepath = self.configs_dir / filename

        if not filepath.exists():
            print(f"⚠️ 설정 파일을 찾을 수 없습니다: {filepath}")
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                print(f"✅ 설정 로드 성공: {filename}")
                return data if data else {}
        except Exception as e:
            print(f"❌ 설정 로드 실패 ({filename}): {str(e)}")
            return {}

    def _load_all_configs(self):
        """모든 설정 파일 로드"""
        self._configs['settings'] = self._load_yaml('settings.yaml')
        self._configs['prompts'] = self._load_yaml('prompts.yaml')
        self._configs['characters'] = self._load_yaml('characters.yaml')

    def get_settings(self) -> Dict[str, Any]:
        """시스템 설정 가져오기"""
        return self._configs.get('settings', {})

    def get_prompts(self) -> Dict[str, Any]:
        """프롬프트 설정 가져오기"""
        return self._configs.get('prompts', {})

    def get_characters(self) -> Dict[str, Any]:
        """캐릭터 설정 가져오기"""
        return self._configs.get('characters', {})

    def get_agent_prompt(self, agent_name: str) -> str:
        """특정 에이전트의 시스템 프롬프트 가져오기"""
        prompts = self.get_prompts()
        return prompts.get('agents', {}).get(agent_name, {}).get('system_prompt', '')

    def get_character_data(self, character_id: str) -> Optional[Dict[str, Any]]:
        """특정 캐릭터의 데이터 가져오기"""
        characters = self.get_characters()
        return characters.get('characters', {}).get(character_id)

    def get_llm_config(self) -> Dict[str, Any]:
        """LLM 설정 가져오기"""
        settings = self.get_settings()
        return settings.get('llm_client', {})

    def get_database_path(self) -> str:
        """데이터베이스 경로 가져오기"""
        settings = self.get_settings()
        db_path = settings.get('database', {}).get('path', 'data/game_state.db')

        # 상대 경로를 절대 경로로 변환
        if not os.path.isabs(db_path):
            db_path = str(self.root_dir / db_path)

        return db_path

    def get_logging_config(self) -> Dict[str, Any]:
        """로깅 설정 가져오기"""
        settings = self.get_settings()
        return settings.get('logging', {})

    def reload(self):
        """설정 파일 다시 로드"""
        self._load_all_configs()
        print("🔄 설정 파일 재로드 완료")


# 전역 인스턴스 (싱글톤)
_config_loader = None


def get_config_loader() -> ConfigLoader:
    """ConfigLoader 인스턴스 가져오기 (싱글톤)"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


# 편의 함수들
def get_agent_prompt(agent_name: str) -> str:
    """특정 에이전트의 프롬프트 가져오기"""
    return get_config_loader().get_agent_prompt(agent_name)


def get_character_data(character_id: str) -> Optional[Dict[str, Any]]:
    """특정 캐릭터 데이터 가져오기"""
    return get_config_loader().get_character_data(character_id)


def get_llm_config() -> Dict[str, Any]:
    """LLM 설정 가져오기"""
    return get_config_loader().get_llm_config()


def get_database_path() -> str:
    """데이터베이스 경로 가져오기"""
    return get_config_loader().get_database_path()


if __name__ == "__main__":
    # 테스트 코드
    loader = get_config_loader()

    print("\n=== 설정 로드 테스트 ===")
    print(f"LLM 설정: {loader.get_llm_config()}")
    print(f"DB 경로: {loader.get_database_path()}")
    print(f"\nParent Agent 프롬프트:\n{loader.get_agent_prompt('parent')[:100]}...")
    print(f"\n탄지로 데이터: {loader.get_character_data('tanjiro')}")
