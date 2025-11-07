# KIME-Chat 백엔드 아키텍처 및 실제 작동 방식 (Code-Based)

이 문서는 KIME-Chat 프로젝트 백엔드 시스템의 실제 코드 실행 흐름을 기반으로 아키텍처와 데이터 흐름을 상세히 설명합니다.

## I. 개요 (Overview)

백엔드 시스템은 **FastAPI**를 기반으로 구축된 비동기 웹 애플리케이션입니다. 핵심 기능은 프론트엔드로부터 들어온 채팅 요청을 **LangGraph**로 구축된 상태 기반(Stateful) 워크플로우를 통해 처리하고, 그 결과를 **SSE(Server-Sent Events)** 스트리밍 방식으로 실시간 전송하는 것입니다.

주요 특징은 사용자의 입력과 대화의 맥락을 `GraphState`라는 상태 객체로 관리하며, 이 상태가 `guardrail`, `router`, `parent_agent` 등 여러 에이전트 노드를 거치면서 점진적으로 업데이트되고 최종 응답이 만들어지는 구조입니다.

## II. 프로젝트 구조 (Project Structure)

백엔드의 소스 코드는 `backend/src` 내부에 있으며, 계층형 아키텍처(Layered Architecture)를 따릅니다.

```
backend/src/
│
├── api/              # 1. API 계층: 외부와의 통신 담당
│   ├── routes/       #    - chat_routes.py: 채팅 엔드포인트 정의
│   └── server.py     #    - FastAPI 앱 초기화
│
├── core/             # 2. 코어 로직 계층: 핵심 처리 흐름 정의
│   ├── workflow.py   #    - LangGraph 워크플로우(그래프) 정의
│   ├── graph_state.py#    - 그래프의 각 노드를 오가는 상태 객체
│   └── utils/        #    - 시나리오 로더, 경로 해석 등 유틸리티
│
├── domain/           # 3. 도메인 계층: 실제 작업 수행 에이전트
│   ├── agents/       #    - guardrail, router, parent 등 각 노드의 실제 로직
│   └── services/     #    - dialogue 생성, 메모리 추출 등 세부 서비스
│
└── infrastructure/   # 4. 인프라 계층: 외부 시스템 연동
    ├── database/     #    - DB Manager (대화/로그 저장, 메모리 로드)
    └── llm/          #    - (LLM Provider 연동 - 현재는 agents에서 직접 처리)
```

## III. 실제 실행 흐름 (Step-by-Step Execution Flow)

사용자가 메시지를 보내면, 백엔드는 다음 순서로 작업을 처리합니다. (주로 `chat_routes.py`의 `/stream` 엔드포인트 기준)

**1. 요청 수신 및 상태 준비**

*   FastAPI는 `/api/chat/stream` 경로로 들어온 요청을 `chat_routes.py`의 `chat_stream` 함수로 전달합니다.
*   `require_auth` 의존성을 통해 사용자 인증(JWT)을 먼저 확인합니다.
*   `session_id`가 없으면 새로 생성하고, 있으면 기존 세션을 사용합니다.
*   `session_manager.load_or_create`를 통해 세션 정보를 불러옵니다. (이전 대화 내용, 현재 스테이지 등)
*   **새로운 세션일 경우:**
    *   `load_scenario` 유틸을 사용해 `scenario_id`에 맞는 시나리오 파일을 읽습니다.
    *   `create_initial_graph_state`를 호출하여 LangGraph 워크플로우를 위한 초기 상태(`GraphState`) 객체를 만듭니다.
    *   `db_manager.get_user_memory_context`를 호출하여 사용자의 장기 기억(캐릭터 관계, 선호도 등)이 DB에 있다면 불러와 상태에 추가합니다.
*   사용자의 입력(`user_input`)을 상태 객체에 추가하여 워크플로우를 실행할 준비를 마칩니다.

**2. LangGraph 워크플로우 실행 (`workflow.invoke`)**

*   준비된 `state` 객체를 `workflow.invoke(state)` 함수의 인자로 전달하여 워크플로우를 단 한 번 호출합니다. 이 한 번의 호출이 아래의 모든 에이전트 실행을 트리거합니다.

**3. 에이전트 그래프 실행 순서 (`workflow.py`)**

`state` 객체는 아래 정의된 순서대로 그래프의 각 노드를 이동하며 처리됩니다.

*   **A. `guardrail` 노드 (입력 필터링):**
    *   가장 먼저 실행되는 노드입니다.
    *   사용자 입력을 검사하여 안전 가이드라인 위반 여부, 명령어 여부 등을 판단합니다.
    *   결과에 따라 입력을 차단(`blocked`)하거나, 바로 응답을 생성(`dialogue_agent`)하거나, 다음 단계인 `router`로 보낼지 결정합니다.

*   **B. `router` 노드 (흐름 제어):**
    *   `guardrail`을 통과한 입력을 받아, 대화의 전체적인 방향을 결정합니다.
    *   예를 들어, "시나리오의 다음 단계로 넘어가야 하는가?" 또는 "단순한 일상 대화인가?" 등을 판단하여 `state`에 다음 목적지(`next_node`)를 지정합니다.

*   **C. `parent_agent` 노드 (상위 목표 설정):**
    *   `router`의 결정을 바탕으로, 이번 턴의 상위 목표를 설정합니다.
    *   예를 들어, "사용자에게 렌고쿠의 상태에 대한 힌트를 제공한다"와 같은 추상적인 지침을 생성하여 `state`에 추가합니다.

*   **D. `children_agent` 노드 (역할 분담):**
    *   `parent_agent`가 설정한 상위 목표를 받아, 각 캐릭터(자식) 에이전트가 수행해야 할 구체적인 역할과 지침을 분배합니다.

*   **E. `dialogue_agent` 노드 (대화 생성):**
    *   `children_agent`로부터 받은 지침에 따라, 각 캐릭터의 실제 대사를 생성합니다.
    *   이 과정에서 캐릭터의 성격, 말투, 현재 대화 맥락 등을 모두 고려하여 최종적인 대화문(`dialogues`)을 만들어 `state`에 저장합니다.
    *   대화 생성이 완료되면, `parent_after_dialogue` 함수를 호출하여 다음 스테이지로 넘어갈지 여부 등 후처리를 진행합니다.

**4. 응답 스트리밍 및 후처리**

*   `workflow.invoke()` 실행이 완료되면, `chat_routes.py`는 결과물이 담긴 `state` 객체를 돌려받습니다.
*   **이미지 결정:** `ImageManager`를 사용하여 생성된 대화 내용에 가장 적합한 배경 이미지를 선택하고, 이미지 파일명을 `state`에 추가합니다.
*   **SSE 스트리밍:** `generate_events` 함수를 통해 `state`에 담긴 최종 결과물들을 조각내어 프론트엔드로 실시간 전송합니다.
    *   `event: metadata`: 세션 ID, 현재 스테이지, 친밀도 등 메타 정보 전송
    *   `event: dialogue`: 생성된 대화(dialogue)를 하나씩 순차적으로 전송
    *   `event: complete`: 모든 전송이 끝났음을 알림
*   **백그라운드 작업 (중요):** 사용자에게 응답 스트림을 보내는 동시에, `background_tasks.add_task`를 사용하여 시간이 오래 걸리는 작업들을 후순위로 처리합니다.
    *   `db_manager.save_dialogues`: 생성된 대화 내용을 DB에 저장
    *   `update_conversation_summary`: 대화 요약본 업데이트
    *   `extract_and_save_memories`: 대화에서 장기 기억을 추출하여 DB에 저장 (이 부분에서 Vector DB가 사용될 수 있음)
    *   `track_affinity_change`: 친밀도 변화량 기록

이러한 구조 덕분에 사용자는 응답을 빠르게 받으면서도, 서버는 뒷단에서 꾸준히 데이터를 저장하고 학습할 수 있습니다.

## IV. 주요 기술 스택 (Key Technologies)

*   **웹 프레임워크:** `FastAPI`
*   **LLM 오케스트레이션:** `LangChain`, `LangGraph`
*   **데이터베이스:** `PostgreSQL` (with `pgvector`), `SQLAlchemy` (ORM)
*   **캐싱:** `Redis`
*   **데이터 유효성 검사:** `Pydantic`
*   **인증:** `JWT (JSON Web Tokens)`
*   **비동기 처리:** `asyncio`
