# 목표: 리팩토링된 구조의 완전한 통합 및 시스템 활성화

Master Blueprint 1단계에 따라 개편된 src 패키지 구조가 정상적으로 동작하도록, 모든 파이썬 파일의 내부 로직을 수정한다. 구체적으로 모든 import 경로를 수정하고, 새로운 GraphState를 적용하며, 중앙화된 configs 설정 파일을 사용하도록 코드를 전면 리팩토링하여 play.py가 오류 없이 실행되도록 만든다.

# 작업 지시사항

## 단계 1: 핵심 파일 이름 변경 및 이동

루트 폴더에 남아있는 langgraph_workflow.py 파일의 이름을 **workflow.py**로 변경하고, src/core/ 폴더로 이동시킨다.

루트 폴더에 남아있는 agent_state_enhanced.py 파일의 이름을 **graph_state.py**로 변경하고, src/core/ 폴더로 이동시킨다.

기존 parent_agent_enhanced.py, children_agent_enhanced.py, router_agent_enhanced.py 파일들의 이름에서 _enhanced를 제거하여 각각 parent_agent.py, children_agent.py, router_agent.py 로 변경하고 src/agents/ 폴더로 이동시킨다.

scene_tools_enhanced.py 와 state_tools_enhanced.py 파일들의 이름에서 _enhanced를 제거하여 scene_tools.py, state_tools.py 로 변경하고 src/tools/ 폴더로 이동시킨다.

나머지 유틸리티성 .py 파일들 (llm_client.py, output_utils.py, scenario_loader.py 등)은 src/utils/ 폴더로 이동시킨다.

## 단계 2: GraphState 표준 적용

src/core/graph_state.py 파일을 열고, 클래스 이름을 AgentState에서 **GraphState**로 변경한다.

GraphState 클래스 내부의 모든 변수명을 Master Blueprint의 GraphState 정의에 명시된 표준 변수명으로 전부 교체한다. (예: history -> messageHistory, affinity_scores -> affinityScores 등)

## 단계 3: 절대 경로 import 적용 및 코드 전면 수정

이제 src 폴더 내의 모든 .py 파일을 열고, 아래 규칙에 따라 코드를 수정한다. 이는 프로젝트 전체에서 가장 중요한 작업이다.

import 경로 수정: 모든 import 구문을 src를 최상위 패키지로 하는 절대 경로로 변경한다.

수정 전: from parent_agent import create_parent_agent

수정 후: from src.agents.parent_agent import create_parent_agent

수정 전: from agent_state_enhanced import AgentState

수정 후: from src.core.graph_state import GraphState

GraphState 참조 수정: 모든 파일에서 AgentState를 참조하던 코드를 GraphState로 변경하고, 변경된 표준 변수명으로 값을 읽고 쓰도록 수정한다.

수정 전: current_scene = state.get("current_scene_id")

수정 후: current_scene = state.get("currentSceneId")

설정 로더(config_loader) 적용: src/utils/config_loader.py를 구현하고, 모든 파일에서 하드코딩된 설정값(LLM 모델 이름, DB 경로 등)과 프롬프트를 이 로더를 통해 동적으로 불러오도록 수정한다.

src/agents/*.py 수정 예시:

수정 전: SYSTEM_PROMPT = "당신은..."

수정 후:

Python

from src.utils.config_loader import get_prompt
SYSTEM_PROMPT = get_prompt('parent')
src/tools/state_tools.py 수정 예시:

수정 전: db_path = "data/game_state.db"

수정 후:

Python

from src.utils.config_loader import get_setting
db_path = get_setting('database.path')
## 단계 4: 실행 시작점(play.py) 수정

루트 폴더의 play.py 파일을 수정하여, 새로운 src 패키지 구조에서 워크플로우를 정상적으로 실행할 수 있도록 만든다.

import 경로 수정: play.py 내부의 모든 import 구문을 src 패키지를 기준으로 수정한다.

수정 전: from langgraph_workflow import create_workflow

수정 후: from src.core.workflow import create_workflow

초기 상태 객체 수정: 게임 시작 시 생성하는 초기 상태 객체를 GraphState의 새로운 변수명 규칙에 맞게 수정한다.