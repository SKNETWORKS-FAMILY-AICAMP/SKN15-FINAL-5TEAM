# 목표: KIME-Project 아키텍처 전문화 및 변수명 표준 적용

현재 프로젝트를 유지보수와 확장이 용이한 전문적인 구조로 전면 개편한다. Notion에 정의된 변수명 규칙을 시스템 전반에 적용하고, 모든 설정을 중앙에서 관리하며, 체계적인 개발 및 실험 로그 관리 시스템을 도입한다.

단계 1: 프로젝트 구조 개편 (Project Restructuring)
현재 분산된 소스코드와 데이터 파일들을 기능에 따라 명확하게 분리된 Python 표준 패키지 구조로 변경한다.

최종 폴더 구조:

kime_chat_agent/
├── .gitignore
├── README.md
├── requirements.txt
├── play.py                # 게임 실행 시작점
│
├── configs/               # 모든 정적 설정 파일 디렉토리
│   ├── settings.yaml      # 시스템 기본 설정 (LLM, DB 경로 등)
│   ├── prompts.yaml       # 모든 에이전트 프롬프트
│   └── characters.yaml    # 캐릭터 설정 (성격, 역할, 톤)
│
├── data/                  # 동적 데이터 및 시나리오
│   ├── game_state.db      # 게임 상태 DB (런타임)
│   └── scenarios/         # 시나리오별 JSON 파일
│       └── scene5_akaza_encounter.json
│
├── logs/                  # 모든 로그 파일 디렉토리
│   ├── dev/               # 개발 및 디버깅용 로그
│   └── experiments/       # Gemini/Perplexity/Claude/Playtest 워크플로우 로그
│
└── src/                   # ★핵심 소스코드 패키지
    ├── __init__.py
    │
    ├── core/              # 시스템의 심장 (상태와 워크플로우)
    │   ├── __init__.py
    │   ├── graph_state.py # AgentState -> GraphState로 변경 및 표준 변수명 적용
    │   └── workflow.py    # LangGraph 워크플로우 정의
    │
    ├── agents/            # 에이전트 로직
    │   ├── __init__.py
    │   ├── parent_agent.py
    │   ├── children_agent.py
    │   └── router_agent.py
    │
    ├── tools/             # 데이터베이스, 외부 API 연동
    │   ├── __init__.py
    │   ├── scene_tools.py
    │   └── state_tools.py
    │
    └── utils/             # 유틸리티 (설정 로더, 로거 등)
        ├── __init__.py
        └── config_loader.py # 모든 YAML 설정 파일을 읽는 통합 로더
단계 2: 설정 파일 중앙화 (configs/*.yaml)
모든 하드코딩된 설정값, 프롬프트, 캐릭터 정보를 configs/ 폴더의 YAML 파일 3개로 분리하여 관리한다.

configs/settings.yaml (시스템 설정)
YAML

# LLM 클라이언트 설정
llm_client:
  provider: "anthropic"
  default_model: "claude-3-opus-20240229"
  temperature: 0.7
  max_tokens: 4000

# 데이터베이스 경로
database:
  path: "data/game_state.db"

# 로깅 설정
logging:
  level: "INFO" # DEBUG, INFO, WARNING, ERROR
  dev_log_file: "logs/dev/development.log"
configs/prompts.yaml (에이전트 프롬프트)
YAML

agents:
  parent:
    system_prompt: |
      당신은 이 게임의 총괄 디렉터(Parent Agent)입니다.
      사용자의 입력과 현재 게임 상태(`GraphState`)를 종합적으로 분석하여,
      다음 행동 계획(Action Plan)을 수립하는 것이 당신의 유일한 임무입니다.
      당신은 직접 대사를 생성하지 않으며, 오직 '도구 사용'이나 '자식 에이전트에게 지시'만 할 수 있습니다.

  children:
    system_prompt: |
      당신은 디렉터의 지시를 수행하는 전문 배우(Children Agent)입니다.
      주어진 캐릭터 설정(`character_schema`)과 상황(`context`)에 완벽하게 몰입하여,
      캐릭터의 말투, 성격, 감정이 드러나는 생생한 대사(dialogue)를 생성해야 합니다.

  router:
    system_prompt: |
      당신은 사용자의 입력 유형을 분석하여 작업을 분배하는 트래픽 제어 담당자(Router)입니다.
      입력이 시스템 전체의 흐름을 결정해야 하는 전략적 판단이 필요하면 'parent'를,
      단순한 대화나 특정 캐릭터의 응답이 필요하면 'children'을,
      게임을 끝내야 한다면 'end'를 반환하세요. 당신의 답변은 오직 ['parent', 'children', 'end'] 중 하나여야 합니다.
configs/characters.yaml (캐릭터 DB)
YAML

# Notion의 '정적 카탈로그' 아이디어를 구체화
characters:
  tanjiro:
    name: "카마도 탄지로"
    description: "정직하고 배려심 깊음. 동료애가 강함."
    tone:
      low: "조심스럽고 예의바른 어투"
      mid: "단호하지만 따뜻한 어투"
      high: "결연하고 따뜻한 어투"

  inosuke:
    name: "하시비라 이노스케"
    description: "저돌적이고 거칠지만, 인정받고 싶은 욕구가 강하다."
    tone:
      low: "불만 섞인 퉁명스러운 말투"
      mid: "거칠고 자신감 넘치는 말투, '멧돼지 저돌맹진!'"
      high: "흥분하여 소리치는 듯한 전투적인 말투"

  zenitsu:
    name: "아가츠마 젠이츠"
    description: "겁이 매우 많고 소극적이지만, 동료를 지키기 위해 각성한다."
    tone:
      low: "울먹이며 징징대는 약한 소리"
      mid: "평범하게 불평하는 말투"
      high: "[각성 상태] 간결하고 위엄 있는 말투. '벽력일섬'"
단계 3: 코드 리팩토링 및 변수명 표준화
src/ 패키지 내부의 모든 파이썬 코드를 수정하여, 새로운 설정 시스템을 사용하고 Notion에 정의된 변수명 규칙을 전면 적용한다.

1. src/core/graph_state.py (가장 중요한 변경)
agent_state_enhanced.py 파일의 이름을 graph_state.py로 변경하고, 클래스 이름을 AgentState에서 GraphState로 변경한다. 내부 변수들을 Notion 규칙에 따라 모두 수정한다.

Python

# src/core/graph_state.py
from typing import TypedDict, List, Dict, Optional
from langchain_core.messages import BaseMessage
from typing_extensions import Annotated

class GraphState(TypedDict):
    """
    LangGraph의 모든 노드가 공유하는 중앙 데이터 저장소(State).
    Notion에 정의된 변수명 규칙을 따름.
    """
    # LangGraph 핵심
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    next_node: str

    # 세션 및 진행 상태
    session_id: str
    current_node_name: str  # 예: "CUTSCENE_5_INTRO"
    turn_count: int
    
    # 상호작용
    user_inputs: List[str]
    agent_responses: List[Dict] # {"speaker": "Tanjiro", "text": "..."}
    active_character: str
    available_choices: List[Dict] # [{"id": "A", "text": "..."}]

    # 게임 로직
    affinity_scores: Dict[str, int] # {"inosuke": 70}
    is_persuasion_successful: Optional[bool]
    
    # 엔딩
    final_ending: Optional[str]
2. src/utils/config_loader.py (신규 파일)
configs/ 폴더의 모든 .yaml 파일을 읽어오는 유틸리티를 구현한다.

3. 나머지 src/**/*.py 파일 수정
모든 파일: AgentState를 GraphState로 변경하고, 그에 따라 내부 변수 접근 코드를 모두 수정한다 (예: state.get("history") -> state.get("messageHistory"))

에이전트 파일 (src/agents/*.py): 하드코딩된 프롬프트를 config_loader에서 동적으로 불러오도록 수정한다.

도구 파일 (src/tools/*.py): DB 경로 등 하드코딩된 부분을 config_loader에서 불러오도록 수정한다.

단계 4: 로그 관리 시스템 공식화
제안한 4-step 워크플로우를 지원하기 위해 logs/experiments/ 폴더에 다음과 같은 규칙으로 로그를 기록한다. 이는 프로젝트의 히스토리를 관리하는 매우 중요한 자산이 된다.

로그 파일명 규칙: YYYY-MM-DD_[Tool]_[Task_Summary].md

예시:

2025-10-08_Gemini_Analysis_변수명 표준화 방안 분석.md

2025-10-08_Perplexity_Research_YAML을 사용한 동적 캐릭터 설정법.md

2025-10-08_Claude_Implementation_단계1-3 리팩토링 수행.log

2025-10-08_Playtest_Feedback_이노스케 설득 난이도 너무 높음.md