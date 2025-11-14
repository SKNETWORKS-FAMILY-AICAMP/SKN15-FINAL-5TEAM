# 지식 그래프 시스템 통합 가이드

## 📚 목차
1. [시스템 개요](#시스템-개요)
2. [아키텍처](#아키텍처)
3. [설치 및 설정](#설치-및-설정)
4. [에이전트 통합 방법](#에이전트-통합-방법)
5. [GraphRAG 활용 방법](#graphrag-활용-방법)
6. [테스트 및 검증](#테스트-및-검증)

---

## 시스템 개요

### 목적
모든 에이전트의 의사결정 데이터를 수집하고 지식 그래프를 구축하여:
- **단기 목표**: LLM 판단에 과거 유사 사례 제공 → 정확도 향상
- **중기 목표**: 자주 발생하는 패턴을 GraphRAG로 처리 → LLM 호출 30-50% 감소
- **장기 목표**: 대부분의 의사결정을 GraphRAG로 처리 → 비용 70% 절감, 응답속도 3배 향상

### 핵심 개념

**문제 상황:**
```
사용자: "렌고쿠와 싸운다"
사용자: "이노스케와 싸운다"

→ "싸운다"라는 동사만으로는 어느 캐릭터를 선택할지 판단 불가
```

**해결 방법:**
```python
# 지식 그래프에 저장된 패턴:
{
    "싸운다" + "렌고쿠" + "무한열차_보스전" + "친밀도=50": {
        "분기": "rengoku_battle_accept",
        "성공률": 85%,
        "발생": 120회
    },
    "싸운다" + "이노스케" + "나비저택" + "친밀도=30": {
        "분기": "inosuke_training",
        "성공률": 70%,
        "발생": 45회
    }
}

→ 컨텍스트와 결합하여 정확한 분기 선택 가능
```

---

## 아키텍처

### 데이터베이스 스키마

#### 1. `ml.decision_logs` - 의사결정 로그
```sql
CREATE TABLE ml.decision_logs (
    decision_id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    turn_number INTEGER,
    agent_name VARCHAR(50) NOT NULL,        -- parent_agent, children_agent, etc.
    decision_type VARCHAR(50) NOT NULL,     -- stage_selection, dialogue_generation, etc.

    -- 입력
    user_input TEXT,
    extracted_keywords JSONB,               -- {verbs: [], targets: [], modifiers: []}
    context_state JSONB,                    -- {stage, affinity, turn_count, etc.}

    -- LLM 호출 정보
    llm_prompt TEXT,
    llm_parameters JSONB,
    llm_model VARCHAR(100),

    -- 출력
    decision_output JSONB NOT NULL,         -- 실제 선택된 분기/결과
    reasoning TEXT,
    confidence FLOAT,

    -- 성능
    execution_time_ms INTEGER,

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### 2. `knowledge.graph_nodes` - 지식 그래프 노드
```sql
CREATE TABLE knowledge.graph_nodes (
    node_id BIGSERIAL PRIMARY KEY,
    node_type VARCHAR(50) NOT NULL,         -- verb, character, stage, context
    node_value TEXT NOT NULL,
    normalized_value VARCHAR(200),
    properties JSONB,
    frequency INTEGER DEFAULT 1,            -- 출현 빈도
    success_rate FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### 3. `knowledge.graph_edges` - 지식 그래프 관계
```sql
CREATE TABLE knowledge.graph_edges (
    edge_id BIGSERIAL PRIMARY KEY,
    source_node_id BIGINT REFERENCES knowledge.graph_nodes(node_id),
    target_node_id BIGINT REFERENCES knowledge.graph_nodes(node_id),
    edge_type VARCHAR(50) NOT NULL,         -- ACTION_WITH, IN_STAGE, LED_TO_BRANCH

    -- 통계
    occurrence_count INTEGER DEFAULT 1,     -- 발생 횟수
    success_count INTEGER DEFAULT 0,        -- 성공 횟수
    avg_confidence FLOAT,
    weight FLOAT DEFAULT 1.0,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 서비스 구조

```
backend/app/features/ml/
├── __init__.py
├── models.py                     # DecisionLog, GraphNode, GraphEdge
├── repository.py                 # DB 접근 레이어
└── services/
    ├── decision_collector.py     # 의사결정 수집
    ├── keyword_extractor.py      # LLM 키워드 추출
    ├── graph_builder.py          # 그래프 구축
    └── graph_rag.py              # GraphRAG 예측
```

---

## 설치 및 설정

### 1. 환경 변수 (선택사항)

```bash
# .env
ENABLE_DECISION_COLLECTION=true  # 의사결정 수집 활성화 (기본: true)
GRAPHRAG_CONFIDENCE_THRESHOLD=0.75  # GraphRAG 확신도 임계값 (기본: 0.75)
```

### 2. 데이터베이스 마이그레이션

이미 생성되어 있습니다:
- `ml.decision_logs`
- `knowledge.graph_nodes`
- `knowledge.graph_edges`

---

## 에이전트 통합 방법

### 1. ParentAgent에 DecisionCollector 추가

**위치:** `backend/app/features/chat/agent/parent.py`

#### Step 1: Import 추가

```python
from app.features.ml.services import DecisionCollector, KeywordExtractor
from sqlalchemy.ext.asyncio import AsyncSession
import time
```

#### Step 2: __init__ 수정

```python
class ParentAgent:
    def __init__(
        self,
        db: Optional[AsyncSession] = None,  # 추가
        # ... 기존 파라미터들
    ):
        # ... 기존 코드

        # ML 서비스 초기화
        if db:
            self.decision_collector = DecisionCollector(db)
            self.keyword_extractor = KeywordExtractor()
        else:
            self.decision_collector = None
            self.keyword_extractor = None
```

#### Step 3: _execute_stage_handler 수정

```python
async def _execute_stage_handler(
    self,
    handler: Any,
    scenario: Dict[str, Any],
    stage_def: Dict[str, Any],
    state: Dict[str, Any],
    user_message: str,
) -> Dict[str, Any]:
    """StageHandler 실행 및 의사결정 수집"""

    start_time = time.time()

    # 기존 로직 실행
    children_ctx, stage_complete, next_stage = await handler.handle(
        scenario=scenario,
        stage_def=stage_def,
        state=state,
        user_input=user_message,
    )

    # 🔥 의사결정 데이터 수집
    if self.decision_collector and self.keyword_extractor:
        try:
            # 키워드 추출
            keywords = await self.keyword_extractor.extract(
                text=user_message,
                context={
                    "stage": state.get("current_stage"),
                    "scenario_id": state.get("scenario_id"),
                    "characters": list(scenario.get("character_refs", {}).keys()),
                }
            )

            # 의사결정 로그 저장
            await self.decision_collector.collect_with_timing(
                session_id=state["session_id"],
                agent_name="parent_agent",
                decision_type="stage_selection",
                decision_output={
                    "handler_type": stage_def.get("type"),
                    "stage_tag": stage_def.get("tag"),
                    "stage_complete": stage_complete,
                    "next_stage": next_stage,
                    "beats_count": len(children_ctx.get("beats", [])),
                },
                start_time=start_time,
                turn_number=state.get("turn_count"),
                user_input=user_message,
                extracted_keywords=keywords,
                context_state={
                    "current_stage": state.get("current_stage"),
                    "scenario_id": state.get("scenario_id"),
                    "turn_count": state.get("turn_count"),
                    "affinity": state.get("affinity", {}),
                },
            )
        except Exception as e:
            logger.warning("_execute_stage_handler", f"Failed to collect decision data: {e}")

    return children_ctx, stage_complete, next_stage
```

### 2. ChildrenAgent에 DecisionCollector 추가

**위치:** `backend/app/features/chat/agent/children.py`

#### Step 1: __init__ 수정

```python
class ChildrenAgent:
    def __init__(
        self,
        db: Optional[AsyncSession] = None,  # 추가
        # ... 기존 파라미터들
    ):
        # ... 기존 코드

        # ML 서비스 초기화
        if db:
            self.decision_collector = DecisionCollector(db)
            self.keyword_extractor = KeywordExtractor()
        else:
            self.decision_collector = None
            self.keyword_extractor = None
```

#### Step 2: _generate_dialogues 수정

```python
async def _generate_dialogues(
    self,
    beats: List[Dict[str, Any]],
    # ... 기존 파라미터들
) -> List[ChatMessage]:
    """대화 생성 및 의사결정 수집"""

    start_time = time.time()

    # 기존 LLM 호출 로직
    prompt = await self.prompt_service.build_beat_dialogue_prompt(...)
    response = await self.llm_service.call_json(
        system_prompt=prompt["system"],
        user_prompt=prompt["user"],
        temperature=0.8,
        max_tokens=2000,
    )

    dialogues = self._normalize_response(response)

    # 🔥 의사결정 데이터 수집
    if self.decision_collector and self.keyword_extractor:
        try:
            keywords = await self.keyword_extractor.extract(
                text=user_input,
                context={"stage": current_stage, "characters": speaker_pool}
            )

            await self.decision_collector.collect_with_timing(
                session_id=session_id,
                agent_name="children_agent",
                decision_type="dialogue_generation",
                decision_output={
                    "dialogue_count": len(dialogues),
                    "speakers": [d.speaker for d in dialogues],
                    "loop_mode": loop_mode,
                },
                start_time=start_time,
                turn_number=current_turn,
                user_input=user_input,
                extracted_keywords=keywords,
                llm_prompt=prompt["user"],
                llm_parameters={"temperature": 0.8, "max_tokens": 2000},
                llm_model="gpt-4",
            )
        except Exception as e:
            logger.warning("_generate_dialogues", f"Failed to collect decision: {e}")

    return dialogues
```

### 3. RouterStageHandler에 DecisionCollector 추가

**위치:** `backend/app/features/chat/agent/stage_handlers/router_stage.py`

```python
async def handle(
    self,
    scenario: Dict[str, Any],
    stage_def: Dict[str, Any],
    state: Dict[str, Any],
    user_input: str,
) -> tuple:
    """라우팅 핸들러 및 의사결정 수집"""

    start_time = time.time()

    # 기존 라우팅 로직
    routing_result = await self.router_service.route_to_next_stage(...)

    # 🔥 의사결정 데이터 수집
    if hasattr(self, 'decision_collector') and self.decision_collector:
        try:
            keywords = await self.keyword_extractor.extract(user_input, {"stage": state.get("current_stage")})

            await self.decision_collector.collect_with_timing(
                session_id=state["session_id"],
                agent_name="router_handler",
                decision_type="routing",
                decision_output={
                    "selected_branch": routing_result["next_stage"],
                    "confidence": routing_result.get("confidence"),
                    "available_branches": list(stage_def.get("routes", {}).keys()),
                },
                start_time=start_time,
                turn_number=state.get("turn_count"),
                user_input=user_input,
                extracted_keywords=keywords,
                context_state=state,
            )
        except Exception as e:
            logger.warning("handle", f"Failed to collect routing decision: {e}")

    return children_ctx, stage_complete, next_stage
```

### 4. UseCase에서 DB Session 전달

**위치:** `backend/app/features/chat/usecase.py`

```python
async def create_dialogue(
    self,
    user_id: str,
    scenario_id: str,
    user_input: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """대화 생성 (트랜잭션 관리)"""

    async with self.db.begin():  # 트랜잭션 시작
        # ... 기존 로직

        # ParentAgent 생성 시 DB 세션 전달
        parent_agent = ParentAgent(
            db=self.db,  # 🔥 DB 세션 전달
            state_service=StateService(),
            # ... 기타 서비스들
        )

        # Agent 실행
        result = await parent_agent.run(
            user_message=user_input,
            session_state=session_state,
            scenario_id=scenario_id,
        )

        # ... 기존 로직
```

---

## GraphRAG 활용 방법

### 1. RouterAgent에서 GraphRAG 우선 조회

**위치:** `backend/app/features/chat/agent/guards/router.py`

```python
from app.features.ml.services import GraphRAG

class RouterAgent:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.graph_rag = GraphRAG(db)
        # ... 기존 코드

    async def route_to_next_stage(
        self,
        user_input: str,
        context_state: Dict[str, Any],
        available_routes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """라우팅 결정 (GraphRAG 우선, LLM 백업)"""

        # 1. GraphRAG로 예측 시도
        prediction = await self.graph_rag.predict_decision(
            user_input=user_input,
            context_state=context_state,
            decision_type="routing",
            threshold=0.75,  # 75% 이상 확신 시 LLM 생략
        )

        if not prediction["use_llm"]:
            # GraphRAG만으로 결정
            logger.info("route_to_next_stage", "Using GraphRAG prediction", prediction=prediction)
            return {
                "next_stage": prediction["decision"]["action"],
                "confidence": prediction["confidence"],
                "reasoning": prediction["reasoning"],
                "method": "graph_rag",
            }

        # 2. LLM 호출 (GraphRAG 신뢰도 낮음)
        logger.info("route_to_next_stage", "Using LLM with GraphRAG context")

        # GraphRAG 컨텍스트 생성
        graph_context = await self.graph_rag.get_context_for_llm(
            user_input=user_input,
            context_state=context_state,
            top_k=3,
        )

        # LLM 프롬프트에 컨텍스트 추가
        prompt = f"""
{graph_context}

**현재 상황:**
사용자 입력: {user_input}
현재 스테이지: {context_state.get('current_stage')}

어느 분기로 가야 할까요?
"""

        # LLM 호출
        llm_response = await self.llm_service.call_json(...)

        return {
            "next_stage": llm_response["branch"],
            "confidence": llm_response.get("confidence", 0.5),
            "reasoning": llm_response.get("reasoning", ""),
            "method": "llm_with_graph_context",
            "graph_context": prediction["similar_cases"],
        }
```

### 2. 주기적 그래프 재구축

**위치:** 새로운 파일 `backend/app/core/tasks/graph_builder_task.py`

```python
from app.features.ml.services import GraphBuilder
from app.core.db import get_async_session

async def rebuild_knowledge_graph():
    """지식 그래프 재구축 (크론 작업)"""

    async with get_async_session() as db:
        builder = GraphBuilder(db)

        # 최근 24시간 의사결정으로 그래프 업데이트
        result = await builder.build_from_recent_decisions(
            hours=24,
            limit=1000,
        )

        print(f"Graph rebuilt: {result['nodes_created']} nodes, {result['edges_created']} edges")
```

**크론 설정:**
```bash
# 매일 새벽 3시에 그래프 재구축
0 3 * * * cd /app && python -m app.core.tasks.graph_builder_task
```

---

## 테스트 및 검증

### 1. 데이터 수집 테스트

```python
import asyncio
from app.core.db import get_async_session
from app.features.ml.services import DecisionCollector
from uuid import uuid4

async def test_decision_collection():
    async with get_async_session() as db:
        collector = DecisionCollector(db)

        decision_id = await collector.collect(
            session_id=uuid4(),
            agent_name="test_agent",
            decision_type="test_decision",
            decision_output={"result": "success"},
            turn_number=1,
            user_input="렌고쿠와 싸운다",
            extracted_keywords={
                "verbs": ["싸운다"],
                "targets": ["렌고쿠"],
            },
            context_state={
                "stage": "mugen_train_boss",
                "affinity": {"렌고쿠": 50},
            },
            confidence=0.85,
        )

        print(f"Decision collected: {decision_id}")

asyncio.run(test_decision_collection())
```

### 2. 키워드 추출 테스트

```python
async def test_keyword_extraction():
    extractor = KeywordExtractor()

    keywords = await extractor.extract(
        text="렌고쿠와 강하게 싸운다",
        context={"stage": "mugen_train"},
    )

    print(f"Extracted keywords: {keywords}")
    # 예상 출력:
    # {
    #     "verbs": ["싸운다"],
    #     "targets": ["렌고쿠"],
    #     "modifiers": ["강하게"],
    #     "emotions": [],
    #     "locations": ["무한열차"]
    # }

asyncio.run(test_keyword_extraction())
```

### 3. 그래프 구축 테스트

```python
async def test_graph_building():
    async with get_async_session() as db:
        builder = GraphBuilder(db)

        result = await builder.build_from_recent_decisions(
            hours=24,
            limit=100,
        )

        print(f"Graph building result: {result}")

        # 통계 확인
        stats = await builder.get_graph_statistics()
        print(f"Graph statistics: {stats}")

asyncio.run(test_graph_building())
```

### 4. GraphRAG 예측 테스트

```python
async def test_graphrag_prediction():
    async with get_async_session() as db:
        graph_rag = GraphRAG(db)

        prediction = await graph_rag.predict_decision(
            user_input="렌고쿠와 싸운다",
            context_state={
                "stage": "mugen_train_boss",
                "affinity": {"렌고쿠": 50},
                "turn_count": 10,
            },
            threshold=0.75,
        )

        print(f"Prediction: {prediction}")
        # 예상 출력:
        # {
        #     "use_llm": False,  # 확신도 높아서 LLM 생략
        #     "decision": {"action": "싸운다", "target": "렌고쿠"},
        #     "confidence": 0.85,
        #     "reasoning": "과거 120회 중 80%의 성공률...",
        #     "similar_cases": [...]
        # }

asyncio.run(test_graphrag_prediction())
```

---

## 예상 효과

### 단기 (1-2주)
- ✅ 의사결정 로그 수집 시작
- ✅ 지식 그래프 구축 시작
- ✅ LLM에 과거 유사 사례 제공 → **판단 정확도 10-15% 향상**

### 중기 (1-2개월)
- ✅ 자주 발생하는 패턴 학습 완료
- ✅ GraphRAG로 일부 의사결정 처리 → **LLM 호출 30-50% 감소**
- ✅ 응답 속도 향상 (GraphRAG는 LLM보다 10배 빠름)

### 장기 (3-6개월)
- ✅ 대부분의 의사결정을 GraphRAG로 처리
- ✅ **비용 70% 절감** (LLM 호출 최소화)
- ✅ **응답 속도 3배 향상**
- ✅ **정확도 20-30% 향상** (패턴 학습 완료)

---

## 문의

문의사항이 있으시면 개발팀에 연락해주세요.
