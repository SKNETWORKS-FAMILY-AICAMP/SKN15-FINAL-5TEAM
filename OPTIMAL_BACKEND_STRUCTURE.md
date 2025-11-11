# 최적 백엔드 구조 설계 (Optimal Backend Structure)

> 현재 구조 분석 및 개선안
> 작성일: 2025-11-11
> 기반: 4-Layer Architecture + LangGraph Multi-Agent System

---

## 📋 목차

1. [현재 구조 분석](#1-현재-구조-분석)
2. [핵심 문제점](#2-핵심-문제점)
3. [최적 구조 제안](#3-최적-구조-제안)
4. [상세 설계](#4-상세-설계)
5. [마이그레이션 가이드](#5-마이그레이션-가이드)
6. [아키텍처 원칙](#6-아키텍처-원칙)

---

## 1. 현재 구조 분석

### 1.1 현재 디렉토리 구조

```
backend/app/
├── core/
│   ├── cache/
│   │   ├── cache_manager.py          ✅ Redis 캐싱
│   │   └── hybrid_session_manager.py ✅ Cache-first read + Write-through
│   ├── db/
│   │   ├── models.py                 ✅ Base SQLAlchemy 모델
│   │   └── session_repository.py     ✅ 세션 관리
│   ├── llm/
│   │   └── prompt_service.py         ✅ LLM 프롬프트 관리
│   └── logging/                      ✅ 구조화된 로깅
│
└── features/
    ├── admin/          ✅ 4-layer 완성 (controller, usecase, repository)
    ├── auth/           ✅ 4-layer + models (User, CreditTransaction)
    ├── galleries/      ✅ 4-layer + services (image_generation_service)
    ├── images/         ✅ 4-layer
    ├── scenarios/      ✅ 4-layer + 9개 모델 (Stage, Mission, Router, ImageMapping)
    ├── sessions/       ✅ 4-layer + models
    ├── users/          ✅ 4-layer
    ├── progression/    ⚠️  models, repository만 (XPTransaction)
    ├── memories/       ⚠️  models, repository만
    ├── logging/        ⚠️  models만
    ├── entities/       ❌ 독립 피처 (chat으로 통합 필요)
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   └── schemas.py
    │
    └── chat/           ⚠️  복잡한 구조 (정리 필요)
        ├── controller.py            ✅
        ├── usecase.py               ✅
        ├── repository.py            ✅
        ├── models.py                ✅ (DialogueTurn, ConversationSummary)
        ├── schemas.py               ✅
        │
        ├── agent/                   ⚠️  기존 에이전트 (사용 중?)
        │   ├── parent.py
        │   ├── children.py
        │   ├── dialogue.py
        │   ├── guards/
        │   │   ├── guardrail.py
        │   │   └── router.py
        │   └── stage_handlers/      ✅ 5개 스테이지 핸들러
        │
        ├── agents/                  ⚠️  LangGraph 에이전트 (새로 추가)
        │   ├── graph_state.py       ✅ TypedDict
        │   ├── workflow.py          ✅ StateGraph
        │   ├── parent_agent.py
        │   ├── dialogue_agent.py
        │   ├── router_agent.py
        │   ├── guardrail_agent.py
        │   ├── children_agent.py
        │   ├── context_builder.py
        │   ├── agent_response.py
        │   └── stage_handlers/      ✅ 5개 핸들러
        │
        └── services/                ✅ 매우 완성도 높음
            ├── affinity_service.py
            ├── context_service.py
            ├── conversation_summarizer.py
            ├── dialogue_service.py
            ├── llm_service.py
            ├── memory_service.py
            ├── mission_service.py
            ├── scenario_service.py
            ├── stage_service.py
            ├── state_service.py
            └── extractors/
                ├── entity_extractor.py
                ├── memory_extractor.py
                ├── relationship_extractor.py
                └── conversation_summarizer.py
```

### 1.2 강점 (Strengths)

✅ **4-Layer Architecture 준수**
- Controller → UseCase → Repository → Models 계층 명확
- 의존성 방향이 올바름 (Controller → Repository 직접 접근 없음)

✅ **Redis + PostgreSQL 하이브리드**
- Cache-first read, Write-through write 패턴
- HybridSessionManager로 세션 성능 최적화

✅ **LangGraph 멀티에이전트 시스템**
- StateGraph 기반 워크플로우
- TypedDict로 상태 타입 안전성 확보

✅ **완성도 높은 services/**
- 10개 이상의 도메인 서비스
- extractors/ 서브디렉토리로 관심사 분리

✅ **트랜잭션 로깅 시스템**
- XPTransaction, CreditTransaction 모델로 감사 추적
- JSONB 메타데이터로 유연성 확보

✅ **고급 시나리오 시스템**
- 5가지 스테이지 타입 지원 (scene, mission, router, free_intent, open_narrative)
- 이미지 매핑 우선순위 시스템

---

## 2. 핵심 문제점

### 🔴 문제 1: agent vs agents 디렉토리 중복

**현재 상황:**
- `chat/agent/` - 기존 에이전트 시스템 (Parent → Children → Dialogue)
- `chat/agents/` - LangGraph 멀티에이전트 시스템 (workflow.py, graph_state.py)

**문제점:**
- 두 시스템이 병존하여 혼란
- 어떤 것을 사용해야 하는지 불명확
- 코드 중복 (stage_handlers가 양쪽에 모두 존재)

**영향:**
- 유지보수 복잡도 증가
- 새 개발자 온보딩 어려움
- 향후 확장 시 양쪽 모두 수정해야 하는 위험

---

### 🟡 문제 2: entities 피처 분리

**현재 상황:**
- `features/entities/` - 독립 피처 (controller, usecase, repository, schemas)
- `features/chat/services/extractors/entity_extractor.py` - 엔티티 추출 로직

**문제점:**
- 엔티티는 대화(chat)에서만 사용되는데 분리되어 있음
- chat → entities 의존성 발생
- Graph RAG는 대화의 컨텍스트 기능이므로 chat 내부에 있어야 함

**영향:**
- 불필요한 피처 간 의존성
- 도메인 경계가 모호함
- 순환 참조 위험

---

### 🟡 문제 3: 불완전한 피처들

**progression/**
- models.py, repository.py만 존재
- controller, usecase 없음 (chat에서 직접 repository 사용)
- 4-layer 위반

**memories/**
- models.py, repository.py만 존재
- controller, usecase 없음

**logging/**
- models.py만 존재
- repository조차 없음

**영향:**
- 아키텍처 일관성 저하
- 테스트 어려움
- 비즈니스 로직이 chat.usecase에 섞임

---

### 🟢 문제 4: services/ vs usecase 역할 모호

**현재 상황:**
- `chat/services/` - 10개 이상의 서비스 (affinity, context, dialogue, memory, mission, scenario, stage, state, llm, conversation_summarizer)
- `chat/usecase.py` - ChatUseCase 클래스

**의문점:**
- services는 usecase와 어떻게 다른가?
- 언제 service를 만들고 언제 usecase 메서드를 만드나?

**현재 패턴:**
- usecase - 트랜잭션 단위 (대화 생성, 세션 관리)
- services - 도메인 로직 (affinity 계산, memory 관리, stage 진행)

---

## 3. 최적 구조 제안

### 3.1 핵심 설계 원칙

```
1. 단일 책임 원칙 (SRP)
   - 하나의 디렉토리는 하나의 책임
   - agent vs agents 중복 제거

2. 도메인 응집성 (Domain Cohesion)
   - entities는 chat의 일부 (Graph RAG는 대화 컨텍스트)
   - progression은 users의 일부 (XP는 사용자 속성)

3. 계층 명확성 (Layer Clarity)
   - 모든 피처는 4-layer 준수
   - usecase는 트랜잭션, service는 도메인 로직

4. 확장성 (Scalability)
   - 새 에이전트 추가 용이
   - 새 스테이지 타입 추가 용이

5. 명확한 명명 (Clear Naming)
   - 단수형 사용 (agent, service)
   - 역할 기반 명명 (handlers, extractors, guards)
```

### 3.2 최적 구조 (Optimal Structure)

```
backend/app/
├── core/
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── cache_manager.py           # Redis 기본 연산
│   │   └── hybrid_session_manager.py  # Cache + DB 통합
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                    # Base 클래스
│   │   ├── session.py                 # DB 세션 관리
│   │   └── repository.py              # Base Repository
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py                  # OpenAI/Anthropic 클라이언트
│   │   ├── prompt_service.py          # 프롬프트 템플릿
│   │   └── embedding_service.py       # pgvector 임베딩
│   │
│   └── logging/
│       ├── __init__.py
│       └── logger.py                  # 구조화된 로거
│
└── features/
    │
    ├── admin/                          # ✅ 관리자 기능
    │   ├── __init__.py
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   └── schemas.py
    │
    ├── auth/                           # ✅ 인증 + 크레딧 시스템
    │   ├── __init__.py
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── schemas.py
    │   └── models/
    │       ├── __init__.py
    │       ├── user.py
    │       └── credit_transaction.py   # 크레딧 트랜잭션 로그
    │
    ├── users/                          # ✅ 사용자 프로필 + 진행도
    │   ├── __init__.py
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── schemas.py
    │   └── models/
    │       ├── __init__.py
    │       ├── user_profile.py
    │       ├── xp_transaction.py       # ✨ progression에서 이동
    │       └── user_achievement.py
    │
    ├── scenarios/                      # ✅ 시나리오 + 스테이지 설정
    │   ├── __init__.py
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── schemas.py
    │   └── models/
    │       ├── __init__.py
    │       ├── scenario.py
    │       ├── stage.py
    │       ├── microbeat.py
    │       ├── mission.py
    │       ├── router.py
    │       ├── intent_mapping.py
    │       ├── image_mapping.py        # 이미지 매핑 규칙
    │       ├── stage_image.py
    │       └── default_image.py
    │
    ├── sessions/                       # ✅ 세션 관리
    │   ├── __init__.py
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── schemas.py
    │   └── models/
    │       ├── __init__.py
    │       └── game_session.py
    │
    ├── galleries/                      # ✅ 갤러리 + 이미지 생성
    │   ├── __init__.py
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── schemas.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── gallery.py
    │   │   └── gallery_image.py
    │   └── services/
    │       ├── __init__.py
    │       └── image_generation_service.py
    │
    ├── images/                         # ✅ 이미지 메타데이터
    │   ├── __init__.py
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   └── schemas.py
    │
    ├── logging/                        # ✅ 시스템 로그
    │   ├── __init__.py
    │   ├── repository.py               # ✨ 추가
    │   └── models/
    │       ├── __init__.py
    │       └── system_log.py
    │
    └── chat/                           # 🔥 핵심 피처 (대화 + 멀티에이전트)
        ├── __init__.py
        ├── controller.py               # API 엔드포인트
        ├── usecase.py                  # 비즈니스 로직 (트랜잭션 단위)
        ├── repository.py               # 데이터 접근
        ├── schemas.py                  # Request/Response 스키마
        │
        ├── models/                     # 🆕 models 디렉토리화
        │   ├── __init__.py
        │   ├── dialogue_turn.py
        │   ├── conversation_summary.py
        │   ├── user_memory.py          # ✨ memories에서 이동
        │   ├── entity.py               # ✨ entities에서 이동
        │   ├── relationship.py         # ✨ entities에서 이동
        │   └── entity_mention.py       # ✨ entities에서 이동
        │
        ├── agent/                      # 🔥 LangGraph 멀티에이전트 (단일화)
        │   ├── __init__.py
        │   │
        │   ├── graph_state.py          # TypedDict 상태 정의
        │   ├── workflow.py             # StateGraph 워크플로우
        │   │
        │   ├── nodes/                  # 🆕 노드 (에이전트)
        │   │   ├── __init__.py
        │   │   ├── parent.py           # 세션 검증 + 컨텍스트 준비
        │   │   ├── dialogue.py         # 대화 생성
        │   │   ├── router.py           # 스테이지 라우팅 (router 타입)
        │   │   └── children.py         # 보조 에이전트
        │   │
        │   ├── guards/                 # 🆕 가드 (검증/라우팅)
        │   │   ├── __init__.py
        │   │   ├── guardrail.py        # 입력/출력 안전성 검증
        │   │   └── should_route.py     # 조건부 엣지 함수
        │   │
        │   └── handlers/               # 🆕 스테이지 핸들러 (stage_type별)
        │       ├── __init__.py
        │       ├── base.py             # BaseStageHandler
        │       ├── scene.py            # scene 타입
        │       ├── mission.py          # mission 타입
        │       ├── router.py           # router 타입
        │       ├── free_intent.py      # free_intent 타입
        │       └── open_narrative.py   # open_narrative 타입
        │
        ├── services/                   # ✅ 도메인 서비스 (비즈니스 로직)
        │   ├── __init__.py
        │   ├── affinity_service.py
        │   ├── context_service.py
        │   ├── dialogue_service.py
        │   ├── llm_service.py
        │   ├── memory_service.py
        │   ├── mission_service.py
        │   ├── scenario_service.py
        │   ├── stage_service.py
        │   ├── state_service.py
        │   ├── progression_service.py  # 🆕 XP 계산 로직
        │   ├── image_mapping_service.py # 🆕 이미지 매핑 로직
        │   │
        │   └── extractors/             # 추출 서비스 (LLM 기반)
        │       ├── __init__.py
        │       ├── entity_extractor.py
        │       ├── memory_extractor.py
        │       ├── relationship_extractor.py
        │       └── conversation_summarizer.py
        │
        └── repositories/               # 🆕 저장소 분리 (복잡도 완화)
            ├── __init__.py
            ├── dialogue_repository.py  # DialogueTurn 관련
            ├── entity_repository.py    # ✨ entities에서 이동
            ├── memory_repository.py    # ✨ memories에서 이동
            └── summary_repository.py   # ConversationSummary 관련
```

---

## 4. 상세 설계

### 4.1 chat 피처 구조 (핵심)

#### 4.1.1 계층별 역할

```python
# controller.py - API 엔드포인트
@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """대화 API"""
    return await chat_usecase.process_message(request)

# usecase.py - 비즈니스 로직 (트랜잭션 단위)
class ChatUseCase:
    async def process_message(self, request):
        """
        대화 처리 트랜잭션

        1. 세션 로드 (HybridSessionManager)
        2. 워크플로우 실행 (LangGraph)
        3. 응답 저장 (Repository)
        4. XP 부여 (ProgressionService)
        """
        pass

# services/ - 도메인 서비스 (재사용 가능한 로직)
class AffinityService:
    """호감도 계산 로직"""
    def calculate_affinity_change(self, user_input: str) -> float:
        pass

class ProgressionService:
    """XP 계산 로직"""
    def calculate_message_xp(self, length: int) -> int:
        pass

# repositories/ - 데이터 접근
class DialogueRepository:
    async def save_turn(self, turn: DialogueTurn):
        pass

    async def get_recent_turns(self, session_id: str, limit: int):
        pass

class EntityRepository:
    async def search_by_vector(self, embedding: List[float]):
        pass
```

#### 4.1.2 agent/ 디렉토리 (LangGraph)

**nodes/** - 에이전트 (상태 변환)
```python
# nodes/parent.py
class ParentAgent:
    """
    Parent Agent - 전체 조율

    역할:
    - 세션 검증
    - 시나리오 로드
    - 기본값 설정
    """
    def execute(self, state: GraphState) -> GraphState:
        # 세션 검증
        # 시나리오 로드
        # 기본값 설정
        return state

# nodes/dialogue.py
class DialogueAgent:
    """
    Dialogue Agent - 대화 생성

    역할:
    - 컨텍스트 구성
    - LLM 호출
    - 응답 생성
    """
    def generate_dialogue(self, state: GraphState) -> GraphState:
        # 스테이지 핸들러 선택
        handler = self._get_handler(state["stage_type"])
        # 대화 생성
        response = handler.generate(state)
        return state
```

**guards/** - 검증 및 라우팅
```python
# guards/guardrail.py
class GuardrailAgent:
    """
    Guardrail Agent - 안전성 검증

    역할:
    - 입력 검증 (욕설, 개인정보)
    - 출력 검증 (유해성, 일관성)
    """
    def check_input(self, state: GraphState) -> GraphState:
        pass

    def check_output(self, state: GraphState) -> GraphState:
        pass

# guards/should_route.py
def should_route(state: GraphState) -> str:
    """
    조건부 엣지 함수

    Returns:
        "route" - RouterAgent로 이동
        "dialogue" - DialogueAgent로 이동
        "end" - 종료
    """
    if not state.get("is_safe"):
        return "end"
    if state.get("stage_type") == "router":
        return "route"
    return "dialogue"
```

**handlers/** - 스테이지별 대화 생성
```python
# handlers/base.py
class BaseStageHandler:
    """스테이지 핸들러 베이스"""

    def generate(self, state: GraphState) -> Dict[str, Any]:
        """대화 생성 (추상 메서드)"""
        raise NotImplementedError

# handlers/scene.py
class SceneStageHandler(BaseStageHandler):
    """
    Scene Stage - 마이크로비트 기반 대화

    특징:
    - 미리 정의된 마이크로비트 순서대로 진행
    - LLM으로 자연스럽게 표현
    """
    def generate(self, state: GraphState) -> Dict[str, Any]:
        # 현재 마이크로비트 가져오기
        # LLM으로 대화 생성
        # 다음 마이크로비트로 이동
        pass

# handlers/mission.py
class MissionStageHandler(BaseStageHandler):
    """
    Mission Stage - 목표 달성형 대화

    특징:
    - success_condition 검증
    - 진행도 추적
    """
    def generate(self, state: GraphState) -> Dict[str, Any]:
        # 미션 진행도 확인
        # 대화 생성
        # success_condition 검증
        pass
```

#### 4.1.3 repositories/ 분리 이유

**현재 문제:**
- `chat/repository.py` 파일이 너무 큼 (800+ 줄)
- DialogueTurn, Entity, Memory, Summary 모두 처리

**해결:**
```python
# repositories/dialogue_repository.py
class DialogueRepository:
    """대화 턴 전용"""
    async def save_turn(self, turn: DialogueTurn):
        pass

    async def get_recent_turns(self, session_id: str, limit: int):
        pass

# repositories/entity_repository.py
class EntityRepository:
    """엔티티 Graph RAG 전용"""
    async def search_by_vector(self, embedding: List[float]):
        pass

    async def get_relationships(self, entity_id: str):
        pass

# repositories/memory_repository.py
class MemoryRepository:
    """사용자 메모리 전용"""
    async def save_memory(self, memory: UserMemory):
        pass

    async def search_relevant_memories(self, query: str):
        pass

# repositories/summary_repository.py
class SummaryRepository:
    """대화 요약 전용"""
    async def save_summary(self, summary: ConversationSummary):
        pass

    async def get_latest_summary(self, session_id: str):
        pass
```

**장점:**
- 단일 책임 원칙 (SRP)
- 테스트 용이성
- 병렬 개발 가능

---

### 4.2 users + progression 통합

**현재 문제:**
- progression이 독립 피처인데 controller/usecase 없음
- XP는 사용자의 속성이므로 users에 포함되어야 함

**통합 구조:**
```python
# users/models/xp_transaction.py
class XPTransaction(Base):
    """XP 트랜잭션 로그"""
    transaction_id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.user_id"))
    xp_amount = Column(Integer)
    xp_type = Column(String(50))  # message, scenario_complete, achievement
    xp_balance_after = Column(Integer)
    level_before = Column(Integer)
    level_after = Column(Integer)
    did_level_up = Column(Boolean)

# users/repository.py
class UserRepository:
    async def add_xp(self, user_id: str, amount: int, xp_type: str):
        """XP 추가 + 트랜잭션 로그"""
        pass

    async def get_xp_transactions(self, user_id: str):
        """XP 트랜잭션 조회"""
        pass

# chat/services/progression_service.py
class ProgressionService:
    """XP 계산 로직 (도메인 서비스)"""

    def calculate_message_xp(self, message_length: int) -> int:
        """메시지 길이 기반 XP 계산"""
        base_xp = 5
        if message_length > 50:
            base_xp += 5
        if message_length > 100:
            base_xp += 5
        return base_xp

    def calculate_scenario_complete_xp(self, scenario_difficulty: str) -> int:
        """시나리오 완료 XP"""
        xp_map = {
            "easy": 100,
            "normal": 200,
            "hard": 300,
        }
        return xp_map.get(scenario_difficulty, 100)
```

**역할 분리:**
- `users/` - XP 데이터 저장/조회 (Repository)
- `chat/services/progression_service.py` - XP 계산 로직 (Service)

---

### 4.3 entities → chat/models 통합

**현재 문제:**
- entities가 독립 피처인데 chat에서만 사용
- Graph RAG는 대화의 컨텍스트 기능

**통합 구조:**
```python
# chat/models/entity.py
class Entity(Base):
    """엔티티 (인물, 장소, 사물)"""
    entity_id = Column(UUID, primary_key=True)
    entity_type = Column(String(50))  # person, place, thing, concept
    entity_name = Column(String(255))
    description = Column(Text)
    properties = Column(JSONB)
    embedding = Column(Vector(1536))  # pgvector

# chat/models/relationship.py
class Relationship(Base):
    """엔티티 간 관계"""
    relationship_id = Column(UUID, primary_key=True)
    source_entity_id = Column(UUID, ForeignKey("entities.entity_id"))
    target_entity_id = Column(UUID, ForeignKey("entities.entity_id"))
    relationship_type = Column(String(100))  # knows, located_in, owns
    strength = Column(Float, default=1.0)

# chat/models/entity_mention.py
class EntityMention(Base):
    """엔티티 언급 (대화 턴에서)"""
    mention_id = Column(UUID, primary_key=True)
    entity_id = Column(UUID, ForeignKey("entities.entity_id"))
    dialogue_turn_id = Column(UUID, ForeignKey("dialogue_turns.turn_id"))
    mention_text = Column(Text)
    context = Column(Text)

# chat/repositories/entity_repository.py
class EntityRepository:
    async def search_by_vector(
        self,
        embedding: List[float],
        entity_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Tuple[Entity, float]]:
        """벡터 유사도 검색"""
        pass

    async def get_related_entities(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Tuple[Entity, Relationship]]:
        """관계 그래프 탐색"""
        pass

# chat/services/extractors/entity_extractor.py
class EntityExtractor:
    """LLM 기반 엔티티 추출"""

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """텍스트에서 엔티티 추출"""
        pass
```

**장점:**
- 도메인 응집성 (chat의 일부)
- 순환 참조 제거
- API 엔드포인트 불필요 (내부 사용만)

---

### 4.4 서비스 계층 역할 명확화

#### usecase vs service 구분

| 측면 | UseCase | Service |
|------|---------|---------|
| **범위** | 트랜잭션 단위 | 재사용 가능한 로직 |
| **의존성** | Repository + Service | 다른 Service (선택) |
| **예시** | `process_message()` | `calculate_affinity()` |
| **DB 접근** | ✅ 직접 접근 (Repository) | ❌ 계산/변환만 |
| **트랜잭션** | ✅ 트랜잭션 관리 | ❌ Stateless |

#### 예시

```python
# usecase.py - 트랜잭션 단위
class ChatUseCase:
    def __init__(
        self,
        dialogue_repo: DialogueRepository,
        entity_repo: EntityRepository,
        memory_repo: MemoryRepository,
        affinity_service: AffinityService,
        progression_service: ProgressionService,
        workflow: ChatWorkflow,
    ):
        self.dialogue_repo = dialogue_repo
        self.entity_repo = entity_repo
        self.memory_repo = memory_repo
        self.affinity_service = affinity_service
        self.progression_service = progression_service
        self.workflow = workflow

    async def process_message(self, request: ChatRequest):
        """
        대화 처리 트랜잭션

        1. 세션 로드
        2. 워크플로우 실행
        3. 응답 저장
        4. XP 부여
        5. 엔티티/메모리 추출
        """
        # 1. 세션 로드
        session = await self.session_manager.get_session(request.session_id)

        # 2. 워크플로우 실행
        state = await self.workflow.ainvoke({
            "session_id": request.session_id,
            "user_input": request.user_input,
            ...
        })

        # 3. 응답 저장
        await self.dialogue_repo.save_turn(...)

        # 4. XP 부여
        xp = self.progression_service.calculate_message_xp(len(request.user_input))
        await self.user_repo.add_xp(user_id, xp, "message")

        # 5. 엔티티/메모리 추출
        entities = await self.entity_extractor.extract(state["ai_response"])
        await self.entity_repo.bulk_upsert(entities)

        return state

# services/affinity_service.py - 도메인 로직
class AffinityService:
    """호감도 계산 (Stateless)"""

    def calculate_affinity_change(
        self,
        user_input: str,
        ai_response: str,
        current_affinity: float
    ) -> float:
        """
        호감도 변화 계산

        Args:
            user_input: 사용자 입력
            ai_response: AI 응답
            current_affinity: 현재 호감도

        Returns:
            호감도 변화량 (-1.0 ~ +1.0)
        """
        change = 0.0

        # 긍정 키워드
        positive_keywords = ["고마워", "좋아", "대단해"]
        if any(kw in user_input for kw in positive_keywords):
            change += 0.1

        # 부정 키워드
        negative_keywords = ["싫어", "별로", "귀찮아"]
        if any(kw in user_input for kw in negative_keywords):
            change -= 0.1

        # 현재 호감도에 따라 변화량 조정
        if current_affinity > 0.8:
            change *= 0.5  # 높을 때는 변화 적게

        return change

# services/progression_service.py - 도메인 로직
class ProgressionService:
    """XP 계산 (Stateless)"""

    def calculate_message_xp(self, message_length: int) -> int:
        """메시지 길이 기반 XP"""
        base_xp = 5
        if message_length > 50:
            base_xp += 5
        if message_length > 100:
            base_xp += 5
        return base_xp

    def calculate_level_from_xp(self, xp: int) -> int:
        """XP로부터 레벨 계산"""
        # 레벨 = floor(sqrt(XP / 100))
        import math
        return math.floor(math.sqrt(xp / 100))
```

---

## 5. 마이그레이션 가이드

### 5.1 단계별 작업

#### STEP 1: agent vs agents 통합 (우선순위: 높음)

```bash
# 1. agents/ → agent/ 통합
mkdir -p backend/app/features/chat/agent/nodes
mkdir -p backend/app/features/chat/agent/guards
mkdir -p backend/app/features/chat/agent/handlers

# 2. LangGraph 파일 이동
mv backend/app/features/chat/agents/graph_state.py backend/app/features/chat/agent/
mv backend/app/features/chat/agents/workflow.py backend/app/features/chat/agent/

# 3. 에이전트 → nodes/
mv backend/app/features/chat/agents/parent_agent.py backend/app/features/chat/agent/nodes/parent.py
mv backend/app/features/chat/agents/dialogue_agent.py backend/app/features/chat/agent/nodes/dialogue.py
mv backend/app/features/chat/agents/router_agent.py backend/app/features/chat/agent/nodes/router.py
mv backend/app/features/chat/agents/children_agent.py backend/app/features/chat/agent/nodes/children.py

# 4. 가드 → guards/
mv backend/app/features/chat/agents/guardrail_agent.py backend/app/features/chat/agent/guards/guardrail.py

# 5. 스테이지 핸들러 → handlers/ (중복 제거)
# agents/stage_handlers/와 agent/stage_handlers/ 중 하나 선택
# LangGraph 용으로 통합
mv backend/app/features/chat/agents/stage_handlers/* backend/app/features/chat/agent/handlers/

# 6. 기존 agent/ 디렉토리 정리
rm -rf backend/app/features/chat/agent/guards/  # 옛날 버전
rm -rf backend/app/features/chat/agent/stage_handlers/  # 옛날 버전

# 7. agents/ 삭제
rm -rf backend/app/features/chat/agents/

# 8. import 경로 수정
# 모든 파일에서:
# from app.features.chat.agents.workflow import get_workflow
# → from app.features.chat.agent.workflow import get_workflow
```

**파일 수정 체크리스트:**
- [ ] `chat/usecase.py` - import 경로 수정
- [ ] `chat/agent/workflow.py` - import 경로 수정
- [ ] `chat/agent/nodes/*.py` - import 경로 수정
- [ ] `chat/agent/__init__.py` - export 정리

---

#### STEP 2: entities → chat 통합 (우선순위: 높음)

```bash
# 1. models 이동
mkdir -p backend/app/features/chat/models
mv backend/app/features/entities/schemas.py backend/app/features/chat/models/entity.py

# 2. repository 이동
mkdir -p backend/app/features/chat/repositories
mv backend/app/features/entities/repository.py backend/app/features/chat/repositories/entity_repository.py

# 3. entities/ 삭제
rm -rf backend/app/features/entities/

# 4. import 경로 수정
# from app.features.entities.repository import EntityRepository
# → from app.features.chat.repositories.entity_repository import EntityRepository
```

**파일 수정 체크리스트:**
- [ ] `chat/services/extractors/entity_extractor.py` - import 수정
- [ ] `chat/usecase.py` - EntityRepository import 수정
- [ ] `main.py` - entities 라우터 제거

---

#### STEP 3: progression → users 통합 (우선순위: 중간)

```bash
# 1. models 이동
mkdir -p backend/app/features/users/models
mv backend/app/features/progression/models.py backend/app/features/users/models/xp_transaction.py

# 2. repository 메서드 통합
# progression/repository.py의 메서드를 users/repository.py로 이동

# 3. progression/ 삭제
rm -rf backend/app/features/progression/

# 4. import 경로 수정
# from app.features.progression.repository import ProgressionRepository
# → from app.features.users.repository import UserRepository
```

**파일 수정 체크리스트:**
- [ ] `chat/usecase.py` - XP 관련 import 수정
- [ ] `users/repository.py` - XP 메서드 추가

---

#### STEP 4: chat/repositories 분리 (우선순위: 중간)

```bash
# 1. repositories/ 디렉토리 생성
mkdir -p backend/app/features/chat/repositories

# 2. repository.py 분리
# chat/repository.py를 여러 파일로 분리:
# - dialogue_repository.py (DialogueTurn)
# - entity_repository.py (Entity, Relationship, EntityMention)
# - memory_repository.py (UserMemory)
# - summary_repository.py (ConversationSummary)

# 3. import 경로 수정
# from app.features.chat.repository import ChatRepository
# → from app.features.chat.repositories.dialogue_repository import DialogueRepository
```

**분리 예시:**
```python
# chat/repositories/dialogue_repository.py
class DialogueRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_turn(self, turn: DialogueTurn):
        self.db.add(turn)
        await self.db.flush()

    async def get_recent_turns(self, session_id: str, limit: int = 10):
        result = await self.db.execute(
            select(DialogueTurn)
            .where(DialogueTurn.session_id == session_id)
            .order_by(DialogueTurn.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
```

---

#### STEP 5: memories → chat 통합 (우선순위: 낮음)

```bash
# 1. models 이동
mv backend/app/features/memories/models.py backend/app/features/chat/models/user_memory.py

# 2. repository 이동
mv backend/app/features/memories/repository.py backend/app/features/chat/repositories/memory_repository.py

# 3. memories/ 삭제
rm -rf backend/app/features/memories/

# 4. import 경로 수정
# from app.features.memories.repository import MemoryRepository
# → from app.features.chat.repositories.memory_repository import MemoryRepository
```

---

#### STEP 6: 서비스 추가 (우선순위: 중간)

```bash
# 1. progression_service.py 생성
touch backend/app/features/chat/services/progression_service.py

# 2. image_mapping_service.py 생성
touch backend/app/features/chat/services/image_mapping_service.py
```

**progression_service.py 구현:**
```python
"""
ProgressionService - XP 계산 로직
"""

class ProgressionService:
    """XP 진행도 계산 서비스 (Stateless)"""

    def calculate_message_xp(self, message_length: int) -> int:
        """메시지 길이 기반 XP 계산"""
        base_xp = 5
        if message_length > 50:
            base_xp += 5
        if message_length > 100:
            base_xp += 5
        return base_xp

    def calculate_scenario_complete_xp(self, difficulty: str) -> int:
        """시나리오 완료 XP"""
        xp_map = {"easy": 100, "normal": 200, "hard": 300}
        return xp_map.get(difficulty, 100)

    def calculate_level_from_xp(self, xp: int) -> int:
        """XP로부터 레벨 계산"""
        import math
        return math.floor(math.sqrt(xp / 100))
```

**image_mapping_service.py 구현:**
```python
"""
ImageMappingService - 이미지 매핑 로직
"""
from typing import Optional, Dict, Any

class ImageMappingService:
    """이미지 매핑 우선순위 처리"""

    def __init__(self, scenario_repo):
        self.scenario_repo = scenario_repo

    async def resolve_image(
        self,
        scenario_id: str,
        stage_id: str,
        image_type: str = "background"
    ) -> Optional[str]:
        """
        이미지 URL 결정 (우선순위 기반)

        우선순위:
        1. 스테이지 직접 할당 (ScenarioStageImage)
        2. 매핑 규칙 (ImageMappingRule)
        3. 시나리오 기본 이미지 (ScenarioDefaultImage)

        Args:
            scenario_id: 시나리오 ID
            stage_id: 스테이지 ID
            image_type: 이미지 타입 (background, character_sprite, thumbnail)

        Returns:
            이미지 URL 또는 None
        """
        # 1. 스테이지 직접 할당
        stage_image = await self.scenario_repo.get_stage_image(
            scenario_id, stage_id, image_type
        )
        if stage_image:
            return stage_image.image_url

        # 2. 매핑 규칙
        stage = await self.scenario_repo.get_stage(stage_id)
        if stage:
            mapping = await self.scenario_repo.get_image_mapping(
                scenario_id, stage.stage_type, image_type
            )
            if mapping:
                return mapping.image_url

        # 3. 시나리오 기본 이미지
        default = await self.scenario_repo.get_default_image(
            scenario_id, image_type
        )
        if default:
            return default.image_url

        return None
```

---

### 5.2 마이그레이션 검증

#### 체크리스트

**구조 검증:**
- [ ] agent vs agents 중복 제거 완료
- [ ] entities가 chat/models로 통합
- [ ] progression이 users/models로 통합
- [ ] memories가 chat/models로 통합
- [ ] chat/repositories 분리 완료

**기능 검증:**
- [ ] 대화 API 정상 작동 (`POST /api/chat`)
- [ ] 엔티티 추출 정상 작동
- [ ] XP 부여 정상 작동
- [ ] 호감도 계산 정상 작동
- [ ] 이미지 매핑 정상 작동

**테스트 실행:**
```bash
# 1. 백엔드 시작
cd backend
docker-compose up -d

# 2. 테스트 실행
pytest tests/

# 3. API 테스트
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "scenario_id": "example-advanced",
    "user_input": "안녕하세요",
    "user_name": "테스터"
  }'
```

---

## 6. 아키텍처 원칙

### 6.1 계층 의존성

```
Controller → UseCase → Repository → Models
                ↓
             Service (도메인 로직)
```

**규칙:**
1. Controller는 UseCase만 호출
2. UseCase는 Repository + Service 호출
3. Service는 다른 Service 호출 가능 (순환 참조 금지)
4. Repository는 Models만 접근

---

### 6.2 피처 분리 기준

**독립 피처:**
- `auth` - 인증/인가 (다른 피처에서 사용)
- `users` - 사용자 프로필 + XP
- `scenarios` - 시나리오 설정
- `sessions` - 세션 관리
- `galleries` - 갤러리 + 이미지 생성
- `images` - 이미지 메타데이터

**통합 피처:**
- `chat` - 대화 + 엔티티 + 메모리 + 에이전트
  - entities → chat/models (대화에서만 사용)
  - memories → chat/models (대화에서만 사용)
  - agent/ - 멀티에이전트 시스템

**기준:**
1. 여러 피처에서 사용 → 독립 피처
2. 한 피처에서만 사용 → 통합
3. API 엔드포인트 필요 → 독립 피처 고려

---

### 6.3 서비스 설계 원칙

**UseCase (트랜잭션):**
- DB 트랜잭션 관리
- Repository 직접 접근
- 여러 Service 조합

**Service (도메인 로직):**
- Stateless
- 재사용 가능한 로직
- DB 접근 금지 (계산/변환만)

**Repository (데이터 접근):**
- CRUD 연산
- 복잡한 쿼리
- 캐싱 전략

---

### 6.4 명명 규칙

**디렉토리:**
- 단수형 사용 (`agent`, `service`, `model`)
- 역할 기반 (`handlers`, `extractors`, `guards`)

**파일:**
- snake_case
- 명확한 역할 (`dialogue_service.py`, `entity_extractor.py`)

**클래스:**
- PascalCase
- 접미사로 역할 표시 (`DialogueService`, `EntityExtractor`, `ChatRepository`)

---

## 7. 기대 효과

### 7.1 개선 효과

**가독성:**
- agent vs agents 중복 제거 → 구조 명확
- entities 통합 → 도메인 응집도 향상
- repositories 분리 → 파일 크기 감소

**유지보수성:**
- 4-layer 일관성 → 예측 가능한 구조
- 단일 책임 원칙 → 변경 영향 최소화
- 명확한 명명 → 코드 탐색 용이

**확장성:**
- 새 에이전트 추가 → `agent/nodes/` 에 파일 추가
- 새 스테이지 타입 → `agent/handlers/` 에 핸들러 추가
- 새 서비스 → `services/` 에 파일 추가

**테스트 용이성:**
- Service Stateless → Unit Test 간편
- Repository 분리 → Mock 용이
- 계층 명확 → Integration Test 작성 쉬움

---

### 7.2 성능

**변화 없음:**
- 구조 변경은 런타임 성능에 영향 없음
- Redis 캐싱 유지
- pgvector 벡터 검색 유지

**미래 최적화 가능:**
- Repository 분리 → 캐싱 전략 세분화 가능
- Service 분리 → 병렬 실행 가능

---

## 8. 다음 단계

### 8.1 즉시 적용 (High Priority)

1. **agent vs agents 통합**
   - 가장 혼란스러운 부분
   - 1-2시간 작업

2. **entities → chat 통합**
   - 도메인 응집성 향상
   - 1시간 작업

### 8.2 점진적 적용 (Medium Priority)

3. **progression → users 통합**
   - XP는 사용자 속성
   - 1시간 작업

4. **chat/repositories 분리**
   - 파일 크기 감소
   - 2-3시간 작업

5. **서비스 추가**
   - progression_service.py
   - image_mapping_service.py
   - 1-2시간 작업

### 8.3 장기 개선 (Low Priority)

6. **memories → chat 통합**
   - 필요 시 적용

7. **logging 완성**
   - repository 추가
   - 필요 시 적용

---

## 9. 결론

### 현재 구조의 강점
- ✅ 4-Layer Architecture 대부분 준수
- ✅ LangGraph 멀티에이전트 시스템
- ✅ 완성도 높은 서비스 계층
- ✅ Redis + PostgreSQL 하이브리드

### 개선이 필요한 부분
- ❌ agent vs agents 중복
- ❌ entities 분리 (통합 필요)
- ❌ 불완전한 피처들 (progression, memories, logging)

### 최적 구조의 핵심
1. **단일 agent/ 디렉토리** - nodes/, guards/, handlers/로 구조화
2. **entities는 chat/models/** - Graph RAG는 대화의 일부
3. **progression은 users/models/** - XP는 사용자 속성
4. **chat/repositories 분리** - dialogue, entity, memory, summary
5. **명확한 서비스 역할** - usecase (트랜잭션) vs service (도메인 로직)

---

**작성자:** Claude (Sonnet 4.5)
**검토 필요:** 사용자 승인 후 마이그레이션 진행
**예상 작업 시간:** 8-10시간 (단계별 분산 가능)
