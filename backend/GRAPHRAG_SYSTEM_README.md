# GraphRAG 시스템 - 지식 그래프 기반 의사결정 시스템

## 🎯 시스템 개요

### 핵심 아이디어

**문제:**
```
사용자: "렌고쿠와 싸운다"
사용자: "이노스케와 싸운다"

→ "싸운다"만으로는 렌고쿠 vs 이노스케 중 어느 분기를 선택할지 판단 불가
```

**해결:**
```python
# 지식 그래프에 저장된 패턴:
("싸운다" + "렌고쿠" + "무한열차_보스전" + "친밀도=50") → 분기A (성공률 85%, 발생 120회)
("싸운다" + "이노스케" + "나비저택" + "친밀도=30") → 분기B (성공률 70%, 발생 45회)

→ 컨텍스트와 결합하여 정확한 분기 선택
```

---

## 📂 구현된 파일

### 1. ML Feature (새로 생성)

```
backend/app/features/ml/
├── __init__.py                    # ✅ 생성됨
├── models.py                      # ✅ DecisionLog, GraphNode, GraphEdge
├── repository.py                  # ✅ DB 접근 레이어
└── services/
    ├── __init__.py                # ✅ 생성됨
    ├── decision_collector.py      # ✅ 의사결정 수집
    ├── keyword_extractor.py       # ✅ LLM 키워드 추출
    ├── graph_builder.py           # ✅ 그래프 구축
    └── graph_rag.py               # ✅ GraphRAG 예측
```

### 2. 문서

```
backend/
├── GRAPHRAG_SYSTEM_README.md              # 이 파일
└── KNOWLEDGE_GRAPH_INTEGRATION_GUIDE.md   # ✅ 상세 통합 가이드
```

---

## 🗄️ 데이터베이스 스키마

### 1. `ml.decision_logs` - 의사결정 로그

**용도:** 모든 에이전트의 의사결정을 기록

| 컬럼 | 타입 | 설명 |
|------|------|------|
| decision_id | BIGSERIAL | PK |
| session_id | UUID | 세션 ID |
| agent_name | VARCHAR(50) | parent_agent, children_agent, router_agent 등 |
| decision_type | VARCHAR(50) | stage_selection, dialogue_generation, routing 등 |
| user_input | TEXT | 사용자 입력 |
| extracted_keywords | JSONB | {verbs: [], targets: [], modifiers: []} |
| context_state | JSONB | {stage, affinity, turn_count} |
| llm_prompt | TEXT | LLM 프롬프트 |
| decision_output | JSONB | 의사결정 결과 |
| confidence | FLOAT | 확신도 (0.0 ~ 1.0) |
| execution_time_ms | INTEGER | 실행 시간 |

### 2. `knowledge.graph_nodes` - 그래프 노드

**용도:** 키워드를 노드로 저장 (동사, 캐릭터, 스테이지 등)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| node_id | BIGSERIAL | PK |
| node_type | VARCHAR(50) | verb, character, stage, context |
| node_value | TEXT | "싸운다", "렌고쿠", "무한열차" 등 |
| frequency | INTEGER | 출현 빈도 |
| success_rate | FLOAT | 성공률 |

### 3. `knowledge.graph_edges` - 그래프 엣지

**용도:** 노드 간 관계 저장

| 컬럼 | 타입 | 설명 |
|------|------|------|
| edge_id | BIGSERIAL | PK |
| source_node_id | BIGINT | 소스 노드 |
| target_node_id | BIGINT | 타겟 노드 |
| edge_type | VARCHAR(50) | ACTION_WITH, IN_STAGE, HAS_EMOTION |
| occurrence_count | INTEGER | 발생 횟수 |
| success_count | INTEGER | 성공 횟수 |
| avg_confidence | FLOAT | 평균 확신도 |

**엣지 타입:**
- `ACTION_WITH`: (동사) → (캐릭터) - 예: "싸운다" → "렌고쿠"
- `IN_STAGE`: (동사/캐릭터) → (스테이지) - 예: "싸운다" → "무한열차"
- `HAS_EMOTION`: (동사) → (감정) - 예: "싸운다" → "화난"

---

## 🚀 사용 방법

### 1. DecisionCollector - 의사결정 수집

```python
from app.features.ml.services import DecisionCollector
from sqlalchemy.ext.asyncio import AsyncSession

class ParentAgent:
    def __init__(self, db: AsyncSession):
        self.decision_collector = DecisionCollector(db)

    async def run(self, user_message: str, session_state: dict):
        import time
        start_time = time.time()

        # ... 기존 로직 실행

        # 의사결정 수집
        await self.decision_collector.collect_with_timing(
            session_id=session_state["session_id"],
            agent_name="parent_agent",
            decision_type="stage_selection",
            decision_output={"stage": "intro", "handler": "scene"},
            start_time=start_time,
            user_input=user_message,
        )
```

### 2. KeywordExtractor - 키워드 추출

```python
from app.features.ml.services import KeywordExtractor

extractor = KeywordExtractor()

keywords = await extractor.extract(
    text="렌고쿠와 강하게 싸운다",
    context={"stage": "mugen_train"},
)

# 결과:
# {
#     "verbs": ["싸운다"],
#     "targets": ["렌고쿠"],
#     "modifiers": ["강하게"],
#     "emotions": [],
#     "locations": ["무한열차"]
# }
```

### 3. GraphBuilder - 그래프 구축

```python
from app.features.ml.services import GraphBuilder

builder = GraphBuilder(db)

# 최근 24시간 의사결정으로 그래프 업데이트
result = await builder.build_from_recent_decisions(hours=24, limit=1000)

print(f"Nodes: {result['nodes_created']}, Edges: {result['edges_created']}")
```

### 4. GraphRAG - 예측

```python
from app.features.ml.services import GraphRAG

graph_rag = GraphRAG(db)

prediction = await graph_rag.predict_decision(
    user_input="렌고쿠와 싸운다",
    context_state={"stage": "mugen_train", "affinity": {"렌고쿠": 50}},
    threshold=0.75,  # 75% 확신 시 LLM 생략
)

if not prediction["use_llm"]:
    # GraphRAG만으로 결정
    print(f"Decision: {prediction['decision']}")
    print(f"Reasoning: {prediction['reasoning']}")
else:
    # LLM 호출 필요
    print("LLM with context:", prediction["similar_cases"])
```

---

## 📊 워크플로우

### Phase 1: 데이터 수집

```
[사용자 입력] → [ParentAgent]
                     ↓
           [StageHandler 선택]
                     ↓
           [DecisionCollector.collect()]
                     ↓
           [ml.decision_logs에 저장]
```

### Phase 2: 그래프 구축

```
[ml.decision_logs] → [GraphBuilder]
                           ↓
                    [KeywordExtractor]
                           ↓
                    [knowledge.graph_nodes 생성]
                    [knowledge.graph_edges 생성]
```

### Phase 3: GraphRAG 예측

```
[사용자 입력] → [GraphRAG.predict_decision()]
                        ↓
                 [그래프 검색: 유사 패턴]
                        ↓
                확신도 >= 75%?
                   /        \
                Yes          No
                 ↓            ↓
         [GraphRAG 결정]  [LLM 호출 with 컨텍스트]
```

---

## 🧪 테스트

### 1. 키워드 추출 테스트

```bash
python -c "
import asyncio
from app.features.ml.services import KeywordExtractor

async def test():
    extractor = KeywordExtractor()
    result = await extractor.extract('렌고쿠와 강하게 싸운다')
    print(result)

asyncio.run(test())
"
```

### 2. GraphRAG 테스트

```python
# test_graphrag.py
import asyncio
from app.core.db import get_async_session
from app.features.ml.services import GraphRAG

async def test():
    async with get_async_session() as db:
        graph_rag = GraphRAG(db)

        prediction = await graph_rag.predict_decision(
            user_input="렌고쿠와 싸운다",
            context_state={"stage": "mugen_train", "affinity": {"렌고쿠": 50}},
            threshold=0.75,
        )

        print(f"Use LLM: {prediction['use_llm']}")
        print(f"Confidence: {prediction['confidence']}")

asyncio.run(test())
```

---

## 📈 예상 효과

| 기간 | 목표 | 예상 효과 |
|------|------|----------|
| **단기 (1-2주)** | 데이터 수집 시작 | 판단 정확도 10-15% 향상 |
| **중기 (1-2개월)** | GraphRAG 부분 도입 | LLM 호출 30-50% 감소 |
| **장기 (3-6개월)** | GraphRAG 전면 도입 | 비용 70% 절감, 속도 3배 향상 |

---

## 📚 다음 단계

1. ✅ **ML Feature 구축 완료**
2. ⬜ **에이전트 통합**: [KNOWLEDGE_GRAPH_INTEGRATION_GUIDE.md](./KNOWLEDGE_GRAPH_INTEGRATION_GUIDE.md) 참고
3. ⬜ **테스트 및 검증**
4. ⬜ **프로덕션 배포**

---

## 💬 문의

문의사항이 있으시면 개발팀에 연락해주세요.
