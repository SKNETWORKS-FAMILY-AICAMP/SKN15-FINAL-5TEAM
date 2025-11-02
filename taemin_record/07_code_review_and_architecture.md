# 코드 리뷰 및 아키텍처 분석

**날짜**: 2025-10-30
**주제**: LangGraph 워크플로우 및 핵심 코드 구조 분석
**목적**: 시스템의 동작 원리를 이해하고 향후 유지보수 및 확장을 위한 가이드 제공

---

## 📋 목차

1. [전체 아키텍처 개요](#전체-아키텍처-개요)
2. [GraphState 분석](#graphstate-분석)
3. [LangGraph 워크플로우 분석](#langgraph-워크플로우-분석)
4. [주요 Agent 흐름](#주요-agent-흐름)
5. [데이터 흐름 다이어그램](#데이터-흐름-다이어그램)
6. [핵심 설계 패턴](#핵심-설계-패턴)

---

## 전체 아키텍처 개요

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                    KIME Chat System                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [FastAPI]  api_server.py                                    │
│      ↓                                                        │
│  [SessionManager]  하이브리드 세션 관리                      │
│      ├─ Redis (캐시, TTL 1시간)                              │
│      └─ PostgreSQL (영구 저장)                               │
│      ↓                                                        │
│  [LangGraph Workflow]  workflow.py                           │
│      ├─ Guardrail Agent (입력 검증)                          │
│      ├─ Router Agent (의도 분류)                             │
│      ├─ Parent Agent (대화 생성)                             │
│      ├─ Children Agent (대화 가공)                           │
│      └─ Dialogue Agent (출력 포매팅)                         │
│      ↓                                                        │
│  [GraphState]  graph_state.py                                │
│      - 50+ 필드로 구성된 중앙 상태 저장소                     │
│      - LangGraph의 모든 노드가 공유                          │
│      ↓                                                        │
│  [Scenario Loader]  scenario_loader.py                       │
│      - JSON 기반 시나리오 로딩                                │
│      - 스테이지별 분기 처리                                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 파일 구조

```
backend/
├── api_server.py                    # FastAPI 엔드포인트
├── src/
│   ├── core/
│   │   ├── graph_state.py          # ⭐ 중앙 상태 저장소 (50+ 필드)
│   │   ├── workflow.py             # ⭐ LangGraph 워크플로우
│   │   ├── scenes_repo.py          # 시나리오 관리
│   │   └── story_orchestrator.py   # 스토리 오케스트레이터
│   ├── agents/
│   │   ├── guardrail_agent.py      # 입력 검증
│   │   ├── router_agent.py         # 의도 분류
│   │   ├── parent_agent.py         # 대화 생성 (LLM)
│   │   ├── children_agent.py       # 대화 가공
│   │   └── dialogue_agent.py       # 출력 포매팅
│   ├── database/
│   │   ├── session_manager.py      # 하이브리드 세션 관리
│   │   ├── db_manager.py           # PostgreSQL 매니저
│   │   └── cache_manager.py        # Redis 캐시 매니저
│   └── utils/
│       └── scenario_loader.py      # JSON 시나리오 로더
```

---

## GraphState 분석

### 파일 위치
[backend/src/core/graph_state.py](backend/src/core/graph_state.py)

### 역할
**중앙 상태 저장소 (Centralized State Store)**

LangGraph의 모든 노드(Guardrail, Router, Parent, Children, Dialogue)가 공유하는 단일 데이터 구조입니다.

### 핵심 특징

1. **TypedDict 기반**
   - Python 3.8+ 타입 힌팅
   - IDE 자동완성 지원
   - 런타임 타입 체크는 없음 (선택적)

2. **50+ 필드 구성**
   - 세션 관리: `session_id`, `turn_count`, `user_name`
   - 시나리오 관리: `scenario_id`, `current_stage`, `stage_history`
   - 게임 로직: `affinity_scores`, `mission_result`, `final_ending`
   - 출력: `output`, `agent_responses`, `dialogues`

3. **Annotated 메시지**
   ```python
   messages: Annotated[List[BaseMessage], lambda x, y: x + y]
   ```
   - LangGraph의 메시지 누적 전략
   - 새 메시지가 기존 메시지에 추가됨

### 주요 필드 분류

#### 1. LangGraph 핵심 (2개)
```python
messages: Annotated[List[BaseMessage], lambda x, y: x + y]  # 메시지 히스토리
next_node: str  # 다음 노드 지정 (라우팅)
```

#### 2. 세션 및 진행 상태 (5개)
```python
session_id: str                # 세션 고유 ID
current_node_name: str         # 현재 노드 이름
current_scene_id: str          # 현재 씬 ID
turn_count: int                # 전체 턴 수
is_timeout: bool               # 타임아웃 여부
```

#### 3. 사용자 상호작용 (6개)
```python
user_input: str                # 현재 사용자 입력
user_inputs: List[str]         # 입력 히스토리
user_name: str                 # 사용자 이름
agent_responses: List[Dict]    # AI 응답 목록
active_character: str          # 현재 대화 캐릭터
available_choices: List[Dict]  # 선택지
```

#### 4. 게임 로직 (9개)
```python
affinity_scores: Dict[str, int]      # 캐릭터별 친밀도
is_persuasion_successful: bool       # 설득 성공 여부
mission_result: str                  # 미션 결과
system_flags: List[str]              # 시스템 플래그
allies_recruited: List[str]          # 동료 규합 목록
recruit_attempts: Dict[str, int]     # 설득 시도 횟수
recruit_failures: List[str]          # 설득 실패 목록
recruit_order: List[str]             # 설득 시도 순서
final_ending: str                    # 최종 엔딩
```

#### 5. 시나리오 관리 (8개)
```python
scenario_id: str                     # 시나리오 ID
scenario_data: Dict[str, Any]        # 전체 시나리오 JSON
scenario: Dict[str, Any]             # parent_agent용 별칭
current_stage: str                   # 현재 스테이지 ID
stage_history: List[str]             # 스테이지 기록
stage_states: Dict[str, Dict]        # 스테이지별 상태
stage_turn: int                      # 스테이지 내 턴 수
```

#### 6. 출력 및 메타데이터 (7개)
```python
output: Dict[str, Any]               # 최종 출력
message_history: List[Dict]          # 메시지 히스토리
routing_result: Dict[str, Any]       # 라우팅 결과
meta: Dict[str, Any]                 # 메타데이터
scene: Dict[str, Any]                # 씬 상태
temp_data: Dict[str, Any]            # 임시 데이터
error_message: str                   # 에러 메시지
```

#### 7. 대화 배치 모드 (4개)
```python
has_more_dialogues: bool             # 추가 대화 필요 여부
dialogue_batch_index: int            # 배치 인덱스
dialogues_generated_count: int       # 생성된 대화 수
stage_dialogue_counts: Dict[str, int] # 스테이지별 대화 수
```

#### 8. 이미지 관리 (3개)
```python
current_image: str                   # 현재 이미지
image_transition_history: List[Dict] # 이미지 전환 이력
event_flags: List[str]               # 이벤트 플래그
```

### 초기화 함수

```python
def create_initial_graph_state(
    session_id: str,
    user_input: str,
    user_name: str = "User",
    scenario_id: str = "default"
) -> GraphState:
    """
    새 세션의 초기 GraphState 생성

    모든 필드를 기본값으로 초기화:
    - messages: []
    - turn_count: 0
    - affinity_scores: {"inosuke": 300, "zenitsu": 400, "tanjiro": 500}
    - stage_history: []
    - output: {"dialogues": [], "images": []}
    """
```

---

## LangGraph 워크플로우 분석

### 파일 위치
[backend/src/core/workflow.py](backend/src/core/workflow.py)

### 역할
**AI 에이전트 워크플로우 오케스트레이션**

LangGraph를 사용하여 여러 AI 에이전트를 순차적/조건적으로 실행합니다.

### 워크플로우 구조

```
시작
  ↓
[Guardrail Agent] ─────→ (입력 검증)
  ↓                      ↓
  ↓                   차단/재입력
  ↓                      ↓
[Router Agent] ─────────→ END
  ↓
  ├─ on_topic ──────────→ [Parent Agent]
  │                           ↓
  │                      [Children Agent]
  │                           ↓
  │                      [Dialogue Agent]
  │                           ↓
  └─ off_topic ─────────→   END
```

### 노드 설명

#### 1. Guardrail Agent
**역할**: 입력 검증 및 필터링

```python
def _guardrail_node(self, state: GraphState) -> GraphState:
    """
    - 유해 콘텐츠 차단
    - 빈 입력 처리
    - 시나리오 이탈 감지

    출력:
    - next_node: "router" | "blocked" | "wait_user_input"
    """
```

**처리 시간**: 평균 600ms

**주요 로직**:
- OpenAI Moderation API 호출
- 입력 길이 체크
- 시나리오 관련성 검증

#### 2. Router Agent
**역할**: 사용자 의도 분류

```python
def _router_node(self, state: GraphState) -> GraphState:
    """
    LLM으로 사용자 입력의 의도를 분류

    출력:
    - on_topic: 시나리오 진행 의도
    - off_topic: 시나리오 이탈
    - warning_handler: 경고 처리

    다음 노드:
    - parent_agent (on_topic)
    - END (off_topic)
    """
```

**처리 시간**: 평균 3,600ms (LLM 호출)

**주요 로직**:
- GPT-4o-mini로 의도 분류
- 임베딩 기반 유사도 검색
- Intent mapping (자유 입력 → 시나리오 액션)

#### 3. Parent Agent
**역할**: 대화 생성 (메인 LLM)

```python
def _parent_node(self, state: GraphState) -> GraphState:
    """
    시나리오와 컨텍스트를 기반으로 대화 생성

    - 스테이지 타입별 처리:
      - open_narrative: 자유 서술형
      - scene: 비트 기반 대화
      - choice: 선택지 제공
      - mission: 미션 진행

    - StoryOrchestrator 호출
    - 대화 beats 생성
    """
```

**처리 시간**: 평균 11,500ms (LLM 호출)

**주요 로직**:
- GPT-4-turbo로 대화 생성
- 시나리오 beats 처리
- 캐릭터 프로필 적용

#### 4. Children Agent
**역할**: 대화 가공 및 보정

```python
def _children_node(self, state: GraphState) -> GraphState:
    """
    Parent가 생성한 대화를 가공

    - 사용자 이름 치환 ({user} → 실제 이름)
    - 대화 순서 조정
    - Fallback 대화 적용
    """
```

**처리 시간**: 평균 0.07ms (LLM 없음)

**주요 로직**:
- 텍스트 치환
- 순서 조정
- 검증

#### 5. Dialogue Agent
**역할**: 출력 포매팅

```python
def _dialogue_node(self, state: GraphState) -> GraphState:
    """
    최종 출력 형식으로 변환

    - JSON 응답 구성
    - 이미지 매핑 (LLM 기반)
    - 시스템 메시지 추가

    출력 형식:
    {
      "dialogues": [...],
      "images": [...],
      "system_messages": [...]
    }
    """
```

**처리 시간**: 평균 0.01ms

**주요 로직**:
- 대화 → JSON 변환
- 이미지 선택 (GPT-4o-mini)
- 메타데이터 추가

### 조건부 라우팅

#### 1. Guardrail 이후
```python
def _route_after_guardrail(self, state: GraphState) -> str:
    """
    next_node 값에 따라 분기:
    - "blocked" → END (차단)
    - "wait_user_input" → END (재입력)
    - "dialogue_agent" → dialogue_agent (직접 이동)
    - 기본값 → "router"
    """
```

#### 2. Router 이후
```python
def _route_after_router(self, state: GraphState) -> str:
    """
    routing_result에 따라 분기:
    - "on_topic" → parent_agent
    - "off_topic" → warning_handler → END
    - "context_needed" → parent_agent (컨텍스트 요청)
    """
```

### 워크플로우 컴파일

```python
def _build_graph(self) -> StateGraph:
    """
    LangGraph 워크플로우 구축

    1. StateGraph(GraphState) 생성
    2. 노드 추가 (5개)
    3. 엣지 추가 (조건부 포함)
    4. 시작점 설정 (guardrail)
    5. 컴파일 → 실행 가능한 그래프 반환
    """
    workflow = StateGraph(GraphState)

    # 노드 추가
    workflow.add_node("guardrail", self._guardrail_node)
    workflow.add_node("router", self._router_node)
    workflow.add_node("parent_agent", self._parent_node)
    workflow.add_node("children_agent", self._children_node)
    workflow.add_node("dialogue_agent", self._dialogue_node)

    # 시작점
    workflow.set_entry_point("guardrail")

    # 조건부 라우팅
    workflow.add_conditional_edges("guardrail", self._route_after_guardrail, {...})
    workflow.add_conditional_edges("router", self._route_after_router, {...})

    # 순차 엣지
    workflow.add_edge("parent_agent", "children_agent")
    workflow.add_edge("children_agent", "dialogue_agent")
    workflow.add_edge("dialogue_agent", END)

    return workflow.compile()
```

---

## 주요 Agent 흐름

### 1. 전체 API 호출 흐름

```
HTTP POST /api/chat
  ↓
[api_server.py]
  ├─ SessionManager.load_or_create() → Redis/PostgreSQL
  ├─ Workflow.invoke(state)
  │   ↓
  │   [Guardrail] (600ms)
  │   ↓
  │   [Router] (3,600ms)
  │   ↓
  │   [Parent] (11,500ms)
  │   ↓
  │   [Children] (0.07ms)
  │   ↓
  │   [Dialogue] (0.01ms)
  │   ↓
  │   return updated_state
  ↓
  └─ SessionManager.save() → Redis + PostgreSQL
  ↓
JSON Response (24초)
```

### 2. 대화 생성 상세 흐름

```
[Parent Agent]
  ↓
1. 현재 스테이지 확인 (state.current_stage)
  ↓
2. 시나리오 데이터 로드 (scenario_data.stages[current_stage])
  ↓
3. 스테이지 타입 분기
  ├─ open_narrative → StoryOrchestrator.generate_narrative()
  ├─ scene → beats 기반 대화 생성
  ├─ choice → 선택지 제공
  └─ mission → 미션 진행
  ↓
4. LLM 호출 (GPT-4-turbo)
  - 시스템 프롬프트: 캐릭터 설정, 씬 컨텍스트
  - 사용자 프롬프트: 현재 상황, 사용자 입력
  ↓
5. 대화 beats 생성
  [
    {"goal": "...", "speaker_hint": ["rengoku"], "fx": "flame_warm"},
    {"goal": "...", "speaker_hint": ["narr"], "fx": "wind_howl"}
  ]
  ↓
6. Children Agent로 전달
  - agent_inputs["children"] = {...}
  - children_ctx에 백업
```

### 3. 이미지 선택 흐름

```
[Dialogue Agent]
  ↓
1. ImageManager.load(scenario_id)
  - JSON 이미지 매핑 파일 로드
  - 21개 이미지 메타데이터
  ↓
2. 등장 캐릭터 필터링
  - dialogues에서 speaker 추출
  - 아직 등장하지 않은 캐릭터의 이미지 제외
  ↓
3. LLM 기반 이미지 선택 (GPT-4o-mini)
  - 대화 내용 분석
  - 가장 적합한 이미지 선택
  - 선택 이유 반환
  ↓
4. image_index 설정
  - dialogues[i]["image_index"] = "2"
  - current_image = "2"
```

---

## 데이터 흐름 다이어그램

### 세션 생성 (첫 요청)

```
POST /api/chat {"user_input": "시작", "user_name": "테스트"}
  ↓
session_id = UUID 생성
  ↓
create_initial_graph_state()
  ├─ messages: []
  ├─ turn_count: 0
  ├─ affinity_scores: {...}
  ├─ scenario_id: "cutscene5_llm_driven"
  └─ output: {}
  ↓
Workflow.invoke(state)
  ↓
  [Guardrail] ✅ 통과
  ↓
  [Router] LLM → "on_topic"
  ↓
  [Parent] LLM → 5개 대화 생성
  ↓
  [Children] 사용자 이름 치환
  ↓
  [Dialogue] JSON 포매팅
  ↓
updated_state
  ├─ turn_count: 2
  ├─ output: {"dialogues": [5개], "images": []}
  └─ current_stage: "TRAIN_PRELUDE"
  ↓
SessionManager.save()
  ├─ statedb.sessions (메타데이터)
  ├─ statedb.session_snapshots (전체 JSON)
  └─ Redis (캐시, TTL 1시간)
  ↓
HTTP 200 OK
{
  "session_id": "...",
  "dialogues": [...],
  "turn_count": 2
}
```

### 대화 이어가기 (후속 요청)

```
POST /api/chat {"session_id": "...", "user_input": "승객을 살펴봅니다"}
  ↓
SessionManager.load_or_create(session_id)
  ├─ 1️⃣ Redis 조회 (2ms) → HIT ✅
  │   return cached_state
  │
  └─ (캐시 MISS 시)
      2️⃣ PostgreSQL 조회 (50ms)
      3️⃣ Redis에 warming
  ↓
state (기존 데이터 로드)
  ├─ turn_count: 2
  ├─ affinity_scores: {...}
  ├─ current_stage: "TRAIN_PRELUDE"
  └─ message_history: [...]
  ↓
state["user_input"] = "승객을 살펴봅니다"
  ↓
Workflow.invoke(state)
  ↓
  [Guardrail] ✅ 통과
  ↓
  [Router] LLM → "on_topic"
  ↓
  [Parent] LLM → 5개 새 대화 생성
  ↓
  [Children] 가공
  ↓
  [Dialogue] 포매팅
  ↓
updated_state
  ├─ turn_count: 4 (증가)
  ├─ output: {"dialogues": [5개], ...}
  └─ current_stage: "TRAIN_PRELUDE"
  ↓
SessionManager.save()
  ├─ UPDATE sessions SET turn_count=4
  ├─ INSERT session_snapshots (turn_number=4)
  └─ Redis SETEX (TTL 3600)
  ↓
HTTP 200 OK
{
  "session_id": "...",
  "dialogues": [...],
  "turn_count": 4
}
```

### 세션 복구 (캐시 미스)

```
POST /api/chat {"session_id": "...", ...}
  ↓
SessionManager.load_or_create(session_id)
  ↓
1️⃣ Redis 조회
   redis.get("session:graphstate:{id}")
   → None (캐시 만료/삭제)
  ↓
2️⃣ PostgreSQL 조회
   SELECT * FROM session_snapshots
   WHERE session_id = '...'
   ORDER BY turn_number DESC
   LIMIT 1
   → state_json (JSONB, 46KB)
  ↓
3️⃣ Redis warming
   redis.setex("session:graphstate:{id}", 3600, json.dumps(state))
  ↓
return state (복구 완료)
  ↓
Workflow.invoke(state) → 정상 진행
```

---

## 핵심 설계 패턴

### 1. State Machine Pattern
**적용 위치**: LangGraph 워크플로우

```
State (GraphState)
  ↓
Event (user_input, routing_result)
  ↓
Transition (Guardrail → Router → Parent → ...)
  ↓
New State (updated GraphState)
```

**장점**:
- 명확한 상태 전환
- 디버깅 용이 (어느 노드에서 멈췄는지 명확)
- 테스트 가능 (각 노드 독립 테스트)

### 2. Repository Pattern
**적용 위치**: SessionManager, DatabaseManager

```python
# 인터페이스
class SessionManagerInterface:
    def load(session_id) -> State
    def save(session_id, state)
    def delete(session_id)

# 구현체
class HybridSessionManager(SessionManagerInterface):
    def load():
        # 1. Redis 시도
        # 2. PostgreSQL 폴백

    def save():
        # 1. PostgreSQL 저장
        # 2. Redis 캐싱
```

**장점**:
- 데이터 소스 추상화
- 캐싱 전략 변경 용이
- 테스트 시 Mock 사용 가능

### 3. Strategy Pattern
**적용 위치**: Parent Agent (스테이지 타입별 처리)

```python
def run_parent_agent(state):
    stage_type = state["current_stage"]["type"]

    if stage_type == "open_narrative":
        return handle_open_narrative(state)
    elif stage_type == "scene":
        return handle_scene(state)
    elif stage_type == "choice":
        return handle_choice(state)
    elif stage_type == "mission":
        return handle_mission(state)
```

**장점**:
- 스테이지 타입 추가 용이
- 각 전략 독립적으로 수정 가능
- 코드 가독성 향상

### 4. Chain of Responsibility Pattern
**적용 위치**: Agent 체인 (Guardrail → Router → Parent → ...)

```
Request (user_input)
  ↓
[Guardrail] → 통과/차단 결정
  ↓
[Router] → 의도 분류
  ↓
[Parent] → 대화 생성
  ↓
[Children] → 가공
  ↓
[Dialogue] → 포매팅
  ↓
Response
```

**장점**:
- 각 Agent가 독립적으로 판단
- 중간에 종료 가능 (차단, 경고 등)
- Agent 순서 변경 용이

### 5. Facade Pattern
**적용 위치**: api_server.py

```python
# 복잡한 내부 구조를 단순한 API로 감싸기
@app.post("/api/chat")
def chat(request: ChatRequest):
    # 1. 세션 로드 (Redis + PostgreSQL)
    # 2. 워크플로우 실행 (5개 Agent)
    # 3. 세션 저장 (PostgreSQL + Redis)
    # 4. JSON 응답 반환

    return {"dialogues": [...], ...}
```

**장점**:
- 클라이언트는 내부 복잡도를 알 필요 없음
- 단일 엔드포인트로 모든 작업 처리
- 내부 구조 변경 시 API 변경 불필요

### 6. Cache-Aside Pattern
**적용 위치**: HybridSessionManager

```python
def load(session_id):
    # 1. 캐시 조회
    data = cache.get(session_id)
    if data:
        return data

    # 2. DB 조회
    data = db.query(session_id)

    # 3. 캐시 업데이트
    cache.set(session_id, data, ttl=3600)

    return data

def save(session_id, data):
    # Write-through
    db.save(session_id, data)  # 먼저 DB 저장
    cache.set(session_id, data)  # 그 다음 캐시
```

**장점**:
- 캐시 미스 시 자동 복구
- DB 부하 감소 (캐시 히트율 높음)
- 데이터 일관성 유지

---

## 성능 최적화 포인트

### 1. LLM 호출 최적화
**현재 병목**: Parent Agent (11,500ms)

**개선 방안**:
- 모델 변경: GPT-4-turbo → GPT-4o-mini (3~5배 빠름)
- 배치 처리: 여러 대화를 한 번에 생성
- 스트리밍: 대화를 하나씩 순차적으로 반환

### 2. 캐시 전략 개선
**현재**: 전체 GraphState 캐싱 (46KB)

**개선 방안**:
- 부분 캐싱: 자주 변하지 않는 데이터만 캐싱
- 압축: gzip 압축 적용 (50% 크기 감소)
- TTL 조정: 활성 세션은 1시간, 비활성 세션은 10분

### 3. 데이터베이스 최적화
**현재**: 모든 턴마다 스냅샷 저장

**개선 방안**:
- 선택적 저장: 중요한 턴만 저장 (스테이지 전환, 엔딩 등)
- 인덱스 추가: `session_id + turn_number` 복합 인덱스
- 파티셔닝: 날짜별 테이블 분할

---

## 핵심 학습 포인트

### 1. LangGraph의 강점
- **명확한 워크플로우**: 노드 기반 시각화
- **조건부 분기**: 라우팅 로직 명확
- **상태 관리**: GraphState 하나로 모든 데이터 공유
- **디버깅 용이**: 각 노드 독립 실행 가능

### 2. 하이브리드 아키텍처의 가치
- **성능**: Redis 캐시 히트 시 25배 빠름
- **안정성**: PostgreSQL 영구 저장으로 복구 가능
- **확장성**: Redis만 스케일 아웃하면 전체 성능 향상

### 3. TypedDict의 장점
- **타입 안전성**: IDE 자동완성 지원
- **문서화**: 필드 설명이 코드 안에 존재
- **유연성**: 런타임 타입 체크 선택 가능

### 4. Agent 기반 설계의 유연성
- **독립성**: 각 Agent 독립 개발/테스트
- **확장성**: 새 Agent 추가 용이
- **재사용성**: 다른 시나리오에도 동일 Agent 사용

---

## 다음 단계

### 1. 성능 개선
- [ ] GPT-4o-mini로 모델 변경 (Parent Agent)
- [ ] 대화 배치 생성 구현
- [ ] 캐시 압축 적용

### 2. 기능 확장
- [ ] 멀티 시나리오 동시 진행
- [ ] 사용자별 프로필 저장
- [ ] 대화 히스토리 검색 기능

### 3. 모니터링 강화
- [ ] 각 Agent별 성능 메트릭 수집
- [ ] LLM 토큰 사용량 추적
- [ ] 캐시 히트율 대시보드

---

**작성일**: 2025-10-30
**검토 대상**: workflow.py, graph_state.py, api_server.py, session_manager.py
**다음 문서**: [08_aws_production_deployment.md](08_aws_production_deployment.md) (배포 후 작성 예정)
