# 지식 그래프 및 로깅 시스템 가이드

이 문서는 KIME 챗봇 프로젝트의 **지식 그래프 시스템**과 **통합 로깅 시스템**에 대한 종합 가이드입니다.

---

## 목차

1. [지식 그래프 시스템](#1-지식-그래프-시스템)
   - [엔티티 추출](#11-엔티티-추출-entity-extraction)
   - [관계 분석](#12-관계-분석-relationship-analysis)
   - [언급 추적](#13-언급-추적-entity-mention-tracking)
2. [로깅 시스템](#2-로깅-시스템)
   - [시스템 로그](#21-시스템-로그)
   - [에러 로그](#22-에러-로그)
   - [성능 메트릭](#23-성능-메트릭)
   - [AI 학습 로그](#24-ai-학습-로그)
3. [사용 예제](#3-사용-예제)
4. [데이터베이스 스키마](#4-데이터베이스-스키마)

---

## 1. 지식 그래프 시스템

지식 그래프 시스템은 대화에서 **엔티티를 자동 추출**하고, **엔티티 간 관계를 분석**하며, **언급을 추적**하는 기능을 제공합니다.

### 1.1 엔티티 추출 (Entity Extraction)

#### 개요
대화 텍스트에서 캐릭터, 장소, 이벤트, 아이템, 스킬 등을 자동으로 추출합니다.

#### 추출 방법
- **Rule-based (60%)**: 알려진 엔티티 패턴 매칭 (빠르고 정확함)
- **LLM-based (40%)**: 새로운 엔티티 발견 (느리지만 포괄적)

#### 엔티티 타입
- `character`: 캐릭터 (예: 탄지로, 렌고쿠, 시노부)
- `location`: 장소 (예: 나비저택, 무한열차, 무한성)
- `event`: 이벤트 (예: 전투, 훈련, 만남)
- `item`: 아이템 (예: 일륜도, 약초)
- `skill`: 스킬 (예: 물의 호흡, 불꽃의 호흡)

#### 코드 위치
```
backend/app/features/chat/services/extractors/entity_extractor.py
backend/app/features/chat/models/entity.py
```

#### 사용 예제
```python
from app.features.chat.services.extractors.entity_extractor import EntityExtractor
from app.core.llm.client import LLMClient

# 초기화
llm_client = LLMClient()
extractor = EntityExtractor(llm_client=llm_client, enable_llm=True)

# 엔티티 추출
text = "탄지로가 나비저택에서 시노부와 함께 물의 호흡을 연습했다."
entities = await extractor.extract_entities(text)

for entity in entities:
    print(f"{entity.entity_type}: {entity.entity_name} (confidence: {entity.confidence})")
```

**출력 예시:**
```
character: 탄지로 (confidence: 0.95)
location: 나비저택 (confidence: 0.95)
character: 시노부 (confidence: 0.95)
skill: 물의 호흡 (confidence: 0.95)
```

---

### 1.2 관계 분석 (Relationship Analysis)

#### 개요
엔티티 간의 관계를 자동으로 분석하고 추출합니다.

#### 관계 타입
- `TRAINS_WITH`: 함께 훈련
- `HAS_AFFINITY`: 친밀도/관계
- `LOCATED_IN`: 위치
- `USES_SKILL`: 스킬 사용
- `OCCURRED_IN`: 이벤트 발생
- `BELONGS_TO`: 소유
- `BATTLES_WITH`: 전투
- `PROTECTS`: 보호
- `INTERACTS_WITH`: 상호작용

#### 추출 방법
- **Co-occurrence (60%)**: 함께 등장하는 엔티티
- **Rule-based (20%)**: 키워드 패턴 기반
- **LLM-based (20%)**: 복잡한 컨텍스트 이해

#### 코드 위치
```
backend/app/features/chat/services/extractors/relationship_extractor.py
```

#### 사용 예제
```python
from app.features.chat.services.extractors.relationship_extractor import RelationshipExtractor

# 초기화
extractor = RelationshipExtractor(llm_client=llm_client, enable_llm=True)

# 관계 추출
text = "탄지로가 나비저택에서 시노부와 함께 물의 호흡을 연습했다."
entities = [...]  # 앞에서 추출한 엔티티 리스트

relationships = await extractor.extract_relationships(
    text=text,
    entities=entities,
    session_id="session-123",
    turn_number=5
)

for rel in relationships:
    print(f"{rel.source_entity_name} --[{rel.relationship_type}]--> {rel.target_entity_name} (strength: {rel.strength})")
```

**출력 예시:**
```
탄지로 --[TRAINS_WITH]--> 시노부 (strength: 0.85)
탄지로 --[LOCATED_IN]--> 나비저택 (strength: 0.90)
탄지로 --[USES_SKILL]--> 물의 호흡 (strength: 0.92)
```

---

### 1.3 언급 추적 (Entity Mention Tracking)

#### 개요
대화 턴별로 엔티티가 언급된 기록을 추적합니다.

#### 추적 정보
- 세션 ID
- 턴 번호
- 언급 텍스트
- 주변 컨텍스트
- 감정 점수 (선택적)

#### 데이터베이스 모델
```
backend/app/features/chat/models/entity_mention.py
```

#### 사용 예제 (통합 서비스)
```python
from app.features.chat.services.knowledge_graph_service import KnowledgeGraphService

# 초기화
kg_service = KnowledgeGraphService(db=db, llm_client=llm_client)

# 대화 턴 처리 (엔티티 추출 + 관계 분석 + 언급 추적 통합)
result = await kg_service.process_dialogue_turn(
    text="탄지로가 나비저택에서 시노부와 훈련했다.",
    session_id="session-123",
    turn_number=5,
    speaker="narr",
    context={"scenario_id": "butterfly_mansion"}
)

print(result)
# {
#     "entities_extracted": 3,
#     "entities_new": 0,
#     "relationships_extracted": 2,
#     "mentions_recorded": 3
# }
```

---

## 2. 로깅 시스템

통합 로깅 시스템은 **시스템 로그**, **에러 로그**, **성능 메트릭**, **AI 학습 로그**를 제공합니다.

### 2.1 시스템 로그

#### 개요
일반적인 시스템 동작 로그를 기록합니다.

#### 로그 레벨
- `DEBUG`: 디버깅 정보
- `INFO`: 일반 정보
- `WARNING`: 경고
- `ERROR`: 에러
- `CRITICAL`: 심각한 에러

#### 코드 위치
```
backend/app/features/logging/models.py (Log 모델)
backend/app/features/logging/repository.py (LoggingRepository)
backend/app/features/logging/service.py (LoggingService)
```

#### 사용 예제
```python
from app.features.logging.service import LoggingService

# 초기화
logging_service = LoggingService(db=db)

# INFO 로그
await logging_service.log_info(
    message="User started new session",
    session_id="session-123",
    user_id="user-456"
)

# WARNING 로그
await logging_service.log_warning(
    message="High latency detected",
    session_id="session-123",
    latency_ms=2500
)

# ERROR 로그
await logging_service.log_error(
    message="Failed to load scenario",
    session_id="session-123",
    scenario_id="missing-scenario"
)
```

---

### 2.2 에러 로그

#### 개요
예외 및 에러를 자동으로 기록합니다.

#### 저장 정보
- 에러 타입 (`ValueError`, `HTTPException` 등)
- 에러 메시지
- 스택 트레이스
- 컨텍스트 데이터

#### 사용 예제
```python
# Exception 자동 로깅
try:
    # 어떤 작업
    result = await risky_operation()
except Exception as e:
    await logging_service.log_exception(
        exception=e,
        session_id="session-123",
        operation="risky_operation"
    )
    raise

# 최근 에러 조회
recent_errors = await logging_service.get_recent_errors(limit=20)
for error in recent_errors:
    print(f"{error.error_type}: {error.error_message}")
```

---

### 2.3 성능 메트릭

#### 개요
시스템 성능을 측정하고 모니터링합니다.

#### 메트릭 타입
- **레이턴시 메트릭**: LLM 호출 시간, DB 쿼리 시간 등
- **카운트 메트릭**: API 호출 수, 세션 생성 수 등
- **통계**: 평균, 최소, 최대, 개수

#### 사용 예제
```python
import time

# 레이턴시 기록
start = time.perf_counter()
result = await llm_client.call(...)
latency_ms = (time.perf_counter() - start) * 1000

await logging_service.record_latency(
    operation_name="llm_call",
    latency_ms=latency_ms,
    model="gpt-4",
    agent="dialogue_agent"
)

# 카운트 기록
await logging_service.record_count(
    metric_name="api_calls",
    count=1,
    endpoint="/api/chat"
)

# 성능 통계 조회 (최근 1시간)
stats = await logging_service.get_performance_stats(
    metric_name="llm_call_latency",
    hours=1
)
print(f"Average: {stats['avg']}ms, Max: {stats['max']}ms")
```

#### 데코레이터 사용
```python
# 함수 실행 시간 자동 측정
@logging_service.measure_time("create_dialogue", component="chat")
async def create_dialogue(session_id, text):
    # 작업 수행
    ...
```

---

### 2.4 AI 학습 로그

#### 개요
LLM 호출 및 AI 에이전트 동작을 기록하여 학습 데이터로 활용합니다.

#### 저장 정보
- 세션 ID, 턴 번호
- 에이전트 이름
- 사용자 입력
- LLM 입력 컨텍스트
- LLM 출력
- 레이턴시, 토큰 수
- 결과 (success/failure)

#### 사용 예제
```python
# LLM 호출 로그
await logging_service.log_llm_call(
    session_id="session-123",
    turn_count=5,
    agent_name="dialogue_agent",
    context={
        "system_prompt": "You are a helpful assistant",
        "user_input": "안녕하세요"
    },
    model_output={
        "response": "안녕하세요! 무엇을 도와드릴까요?",
        "emotion": "friendly"
    },
    latency_ms=1250,
    llm_model="gpt-4-turbo",
    token_count=85,
    outcome="success"
)

# 에이전트 성능 분석
performance = await logging_service.get_agent_performance(
    agent_name="dialogue_agent",
    limit=100
)
print(f"Total calls: {performance['total_calls']}")
print(f"Avg latency: {performance['avg_latency_ms']}ms")
print(f"Error rate: {performance['error_rate']*100}%")
```

---

## 3. 사용 예제

### 3.1 전체 통합 예제

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.llm.client import LLMClient
from app.features.chat.services.knowledge_graph_service import KnowledgeGraphService
from app.features.logging.service import LoggingService

async def process_user_message(
    db: AsyncSession,
    session_id: str,
    turn_number: int,
    user_input: str
):
    """사용자 메시지 처리 (지식 그래프 + 로깅 통합)"""

    # 초기화
    llm_client = LLMClient()
    kg_service = KnowledgeGraphService(db, llm_client)
    logging_service = LoggingService(db)

    try:
        # 1. 시스템 로그
        await logging_service.log_info(
            message="Processing user message",
            session_id=session_id,
            turn=turn_number
        )

        # 2. LLM 호출 (성능 측정 포함)
        start = time.perf_counter()
        llm_response = await llm_client.call(
            system_prompt="You are a helpful assistant",
            user_prompt=user_input
        )
        latency_ms = (time.perf_counter() - start) * 1000

        # 3. AI 학습 로그
        await logging_service.log_llm_call(
            session_id=session_id,
            turn_count=turn_number,
            agent_name="main_agent",
            context={"user_input": user_input},
            model_output={"response": llm_response},
            latency_ms=int(latency_ms),
            llm_model="gpt-4"
        )

        # 4. 지식 그래프 업데이트 (엔티티 추출 + 관계 분석)
        kg_result = await kg_service.process_dialogue_turn(
            text=llm_response,
            session_id=session_id,
            turn_number=turn_number,
            speaker="assistant"
        )

        # 5. 성능 메트릭 기록
        await logging_service.record_latency(
            operation_name="full_turn",
            latency_ms=latency_ms,
            session_id=session_id
        )

        return {
            "response": llm_response,
            "knowledge_graph": kg_result,
            "latency_ms": latency_ms
        }

    except Exception as e:
        # 6. 에러 로깅
        await logging_service.log_exception(
            exception=e,
            session_id=session_id,
            turn=turn_number
        )
        raise
```

### 3.2 세션 분석 예제

```python
async def analyze_session(db: AsyncSession, session_id: str):
    """세션 전체 분석"""

    kg_service = KnowledgeGraphService(db)
    logging_service = LoggingService(db)

    # 1. 지식 그래프 조회
    knowledge_graph = await kg_service.get_session_knowledge_graph(session_id)
    print(f"Total entities: {knowledge_graph['stats']['total_entities']}")
    print(f"Total relationships: {knowledge_graph['stats']['total_relationships']}")

    # 2. 세션 로깅 분석
    analytics = await logging_service.get_session_analytics(session_id)
    print(f"Total logs: {analytics['total_logs']}")
    print(f"Total errors: {analytics['total_errors']}")
    print(f"Avg LLM latency: {analytics['avg_llm_latency_ms']}ms")

    return {
        "knowledge_graph": knowledge_graph,
        "analytics": analytics
    }
```

---

## 4. 데이터베이스 스키마

### 4.1 지식 그래프 테이블

#### `knowledge.entities` - 엔티티
```sql
CREATE TABLE knowledge.entities (
    entity_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,  -- character, location, event, item, skill
    entity_name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255),
    description TEXT,
    properties JSONB DEFAULT '{}',
    embedding VECTOR(1536),  -- OpenAI embedding
    importance_score FLOAT DEFAULT 0.5,
    mention_count INTEGER DEFAULT 0,
    first_seen_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_entity_type CHECK (entity_type IN ('character', 'location', 'event', 'item', 'skill')),
    CONSTRAINT valid_importance CHECK (importance_score >= 0.0 AND importance_score <= 1.0)
);
```

#### `knowledge.entity_mentions` - 엔티티 언급
```sql
CREATE TABLE knowledge.entity_mentions (
    mention_id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES knowledge.entities(entity_id) ON DELETE CASCADE,
    session_id UUID REFERENCES conversation.sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    mention_text TEXT,
    context_window TEXT,
    sentiment_score FLOAT,
    mentioned_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_sentiment CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0)
);
```

### 4.2 로깅 테이블

#### `observability.logs` - 시스템 로그
```sql
CREATE TABLE observability.logs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID,
    log_level VARCHAR(20) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    stage_name VARCHAR(100),
    agent_name VARCHAR(100),
    message TEXT NOT NULL,
    context_data JSON,
    duration_ms FLOAT,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

#### `observability.error_logs` - 에러 로그
```sql
CREATE TABLE observability.error_logs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context_data JSON,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

#### `observability.performance_metrics` - 성능 메트릭
```sql
CREATE TABLE observability.performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit VARCHAR(50),
    tags JSON,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

#### `ml.training_logs` - AI 학습 로그
```sql
CREATE TABLE ml.training_logs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    turn_count INTEGER NOT NULL,
    scenario_id VARCHAR(50),
    current_stage VARCHAR(100),
    agent_name VARCHAR(50) NOT NULL,
    user_input TEXT,
    context JSON NOT NULL,
    model_output JSON NOT NULL,
    latency_ms INTEGER,
    token_count INTEGER,
    llm_model VARCHAR(100),
    outcome VARCHAR(20),  -- success, failure, timeout
    outcome_reason TEXT,
    feedback_score FLOAT,
    is_error BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_feedback CHECK (feedback_score >= 0.0 AND feedback_score <= 1.0)
);
```

---

## 5. 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
│  (Chat Controller, API Endpoints)                          │
└────────────────────┬───────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
┌─────────▼──────────┐  ┌──────▼────────────┐
│  Knowledge Graph    │  │  Logging Service  │
│  Service            │  │                   │
│ ┌─────────────────┐ │  │ ┌───────────────┐ │
│ │ Entity Extractor│ │  │ │ System Logs   │ │
│ └─────────────────┘ │  │ └───────────────┘ │
│ ┌─────────────────┐ │  │ ┌───────────────┐ │
│ │ Relationship    │ │  │ │ Error Logs    │ │
│ │ Extractor       │ │  │ └───────────────┘ │
│ └─────────────────┘ │  │ ┌───────────────┐ │
│ ┌─────────────────┐ │  │ │ Performance   │ │
│ │ Entity Repo     │ │  │ │ Metrics       │ │
│ └─────────────────┘ │  │ └───────────────┘ │
└─────────────────────┘  │ ┌───────────────┐ │
                         │ │ AI Training   │ │
                         │ │ Logs          │ │
                         │ └───────────────┘ │
                         └───────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
          ┌─────────▼────────┐      ┌───────▼─────────┐
          │  knowledge        │      │  observability  │
          │  schema           │      │  & ml schemas   │
          │                   │      │                 │
          │ - entities        │      │ - logs          │
          │ - entity_mentions │      │ - error_logs    │
          │ - relationships   │      │ - metrics       │
          └───────────────────┘      │ - training_logs │
                                     └─────────────────┘
```

---

## 6. 주요 기능 요약

### 지식 그래프
✅ **엔티티 추출**: Rule-based + LLM Hybrid 방식으로 5가지 타입 엔티티 자동 추출
✅ **관계 분석**: Co-occurrence + Rule + LLM으로 9가지 관계 타입 자동 분석
✅ **언급 추적**: 턴별 엔티티 언급 기록 및 컨텍스트 저장
✅ **통합 서비스**: KnowledgeGraphService로 모든 기능 통합 제공

### 로깅 시스템
✅ **시스템 로그**: DEBUG/INFO/WARNING/ERROR/CRITICAL 레벨 지원
✅ **에러 로그**: Exception 자동 캡처 및 스택 트레이스 저장
✅ **성능 메트릭**: 레이턴시, 카운트 측정 및 통계 분석
✅ **AI 학습 로그**: LLM 호출 기록 및 학습 데이터 수집
✅ **통합 분석**: 세션별 전체 로그 분석 기능

---

## 7. 다음 단계

### 구현 완료 ✅
- [x] 엔티티 추출 로직 (Rule-based + LLM)
- [x] 관계 분석 로직 (Co-occurrence + Rule + LLM)
- [x] 언급 추적 시스템
- [x] 시스템 로그
- [x] 에러 로그
- [x] 성능 메트릭
- [x] AI 학습 로그
- [x] 통합 서비스 레이어

### 향후 개선 사항
- [ ] 지식 그래프 시각화 API
- [ ] 실시간 메트릭 대시보드
- [ ] 자동 알림 시스템 (에러 임계값 초과 시)
- [ ] 엔티티 임베딩 기반 유사도 검색
- [ ] AI 학습 데이터 자동 라벨링

---

**문의**: 태민 (Taemin)
**마지막 업데이트**: 2025-11-14
