"""
pytest configuration and fixtures
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pytest
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 테스트용 환경변수 설정
os.environ["USE_LLM"] = "false"
os.environ["DEBUG"] = "false"


@pytest.fixture
def sample_state():
    """테스트용 기본 state fixture"""
    from agent_state_enhanced import create_enhanced_initial_state
    return create_enhanced_initial_state("pytest_session")


@pytest.fixture
def sample_scenario():
    """테스트용 기본 시나리오 데이터"""
    from scenario_loader import scenario_loader
    return scenario_loader.load_scenario("cutscene5_akaza_encounter.json")


@pytest.fixture
def mission_data():
    """테스트용 미션 데이터"""
    from scenario_loader import scenario_loader
    scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")
    return scenario["stages"]["recruit_mission"]


@pytest.fixture
def affinity_system():
    """친밀도 시스템 인스턴스"""
    from affinity_system import AffinitySystem
    return AffinitySystem()


@pytest.fixture
def mission_manager(mission_data):
    """MissionManager 인스턴스"""
    from mission_manager import MissionManager
    return MissionManager(mission_data)
