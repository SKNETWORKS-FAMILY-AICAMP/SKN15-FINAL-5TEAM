# tm_work 브랜치 대비 현재 브랜치 부족한 기능 정리

**비교 기준**: `tm_work` vs `tm-merge-all-logic`
**분석일**: 2025-11-11

---

## 🏗️ 아키텍처 차이

### tm_work (LangGraph 기반)
```
backend/
├── api_server.py           # 단일 FastAPI 서버 파일
├── src/
│   ├── agents/             # LangGraph 에이전트들
│   │   ├── parent_agent.py
│   │   ├── children_agent.py
│   │   ├── dialogue_agent.py
│   │   ├── router_agent.py
│   │   └── guardrail_agent.py
│   ├── core/
│   │   ├── workflow.py     # LangGraph 워크플로우 구성
│   │   ├── graph_state.py  # 그래프 상태 관리
│   │   └── scenes_repo.py  # 시나리오 Scene 저장소
│   ├── database/
│   │   ├── session_manager.py      # Hybrid Session Manager
│   │   ├── db_manager.py           # PostgreSQL 관리
│   │   └── cache_manager.py        # Redis 캐시
│   ├── api/                # API 라우터들
│   │   ├── chat_router.py
│   │   ├── auth_router.py
│   │   ├── user_router.py
│   │   └── scenario_router.py
│   └── utils/
│       ├── conversation_summarizer.py
│       └── scenario_loader.py
└── database/
    └── migrations/         # SQL 마이그레이션 파일들
        ├── 001_initial_schema.sql
        ├── 008_graph_rag_schema.sql
        ├── 009_user_credits.sql
        └── ...
```

### 현재 브랜치 (4-Layer Architecture)
```
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── database.py
│   └── features/           # Feature 기반 모듈
│       ├── auth/
│       │   ├── controller.py
│       │   ├── usecase.py
│       │   └── repository.py
│       ├── chat/
│       ├── users/
│       └── scenarios/
└── migrations/             # Alembic 마이그레이션
```

---

## ❌ 현재 브랜치에 **완전히 누락된 기능**

### 1. **LangGraph 멀티에이전트 시스템** 🚫
tm_work의 핵심 기능이 전혀 없음

- ❌ `src/agents/` 디렉토리 전체 누락
  - **parent_agent.py**: 최상위 에이전트 (전체 워크플로우 조율)
  - **children_agent.py**: 하위 에이전트 (세부 작업 처리)
  - **dialogue_agent.py**: 대화 생성 에이전트
  - **router_agent.py**: 시나리오 라우팅 에이전트
  - **guardrail_agent.py**: 가드레일 검증 에이전트

- ❌ `src/core/workflow.py`: LangGraph 워크플로우 구성 로직
- ❌ `src/core/graph_state.py`: 그래프 상태 관리 (TypedDict 기반)
- ❌ `src/core/scenes_repo.py`: Scene 저장소 (Redis 기반)

**영향**:
- 복잡한 시나리오 분기 처리 불가
- 멀티턴 대화 관리 미흡
- AI 에이전트 간 협업 불가

---

### 2. **HybridSessionManager (Redis + PostgreSQL)** 🚫

tm_work의 세션 관리 시스템 누락

- ❌ `src/database/session_manager.py`:
  - Redis (빠른 세션 상태) + PostgreSQL (영구 저장) 하이브리드
  - 자동 백업 및 복원
  - TTL 기반 세션 관리

- ❌ `src/database/cache_manager.py`:
  - Redis 캐시 추상화
  - 대화 요약 캐싱
  - 임베딩 벡터 캐싱

**현재 상태**:
- SQLAlchemy Repository만 있음 (Redis 캐싱 없음)
- 세션 복원 기능 미흡

---

### 3. **고급 시나리오 시스템** 🚫

#### tm_work의 `mugen_train_full.json`
```json
{
  "stages": [
    {
      "type": "scene",           // 장면 재생 (micro_beat 지원)
      "loop_mode": "micro_beat",
      "llm_beats": true
    },
    {
      "type": "mission",         // 미션 스테이지 (목표 기반)
      "feedback_i18n": {...}
    },
    {
      "type": "router",          // 조건 기반 분기
      "next_by_outcome": {...}
    },
    {
      "type": "free_intent",     // 자유 의도 파싱
      "intent_mapping": {...}
    },
    {
      "type": "open_narrative"   // 개방형 대화
    }
  ],
  "i18n": {
    "ko": {
      "beats_rengoku_dialogue": [...],
      "beats_enmu_appear": [...],
      ...
    }
  }
}
```

**현재 브랜치**: 간단한 JSON 구조만 있음 (stage type 구분 없음)

---

### 4. **대화 요약 자동화** 🚫

- ❌ `src/utils/conversation_summarizer.py`:
  - LLM 기반 대화 요약
  - 임베딩 생성 (`generate_embedding()`)
  - 주기적 요약 업데이트 (`update_conversation_summary()`)

**현재 상태**: 대화 요약 기능 없음

---

### 5. **SQL Migration 시스템** 🚫

tm_work: 20개의 SQL migration 파일
```
backend/database/migrations/
├── 001_initial_schema.sql
├── 002_logdb_training_logs.sql
├── 003_users_table.sql
├── 004_password_reset_tokens.sql
├── 005_conversation_summary.sql
├── 006_user_memories.sql
├── 007_install_pgvector.sql      # ⭐ 벡터 DB (pgvector)
├── 008_graph_rag_schema.sql      # ⭐ Graph RAG
├── 009_user_credits.sql
├── 012_user_progression.sql
├── 013_scenarios_system.sql
├── 016_image_mapping.sql
├── 018_user_character_affinity.sql
├── 019_scenario_comments.sql
└── 020_scenario_likes.sql
```

**현재 브랜치**: Alembic만 있음 (pgvector, Graph RAG 없음)

---

### 6. **실시간 스트리밍 (LangGraph astream)** 🚫

tm_work 커밋 `a2cae87`:
```python
# LangGraph의 astream()을 통한 진정한 실시간 스트리밍
for await (const chunk of sendChatMessage(...)) {
  if (chunk.type === 'dialogue') {
    // 실시간으로 대화 청크 스트리밍
  }
}
```

**현재 상태**: SSE 스트리밍은 있으나 LangGraph 통합 없음

---

### 7. **Graph RAG (지식 그래프 기반 RAG)** 🚫

- ❌ `008_graph_rag_schema.sql`:
  - `entities` 테이블 (엔티티)
  - `entity_relationships` 테이블 (관계)
  - `entity_mentions` 테이블 (멘션)

- ❌ pgvector 확장 설치 (`007_install_pgvector.sql`)

**영향**: 복잡한 대화 맥락 추적 불가

---

### 8. **사용자 진행도 시스템 (RPG-like)** 🚫

- ❌ `012_user_progression.sql`:
  - `user_progression` 테이블 (레벨, XP, 랭크)
  - `xp_transactions` 테이블 (XP 변동 기록)
  - `user_equipment` 테이블 (장비 시스템)
  - `rank_definitions` 테이블 (계급 정의)

**현재 상태**: 단순 user_credits만 있음

---

### 9. **이미지 매핑 시스템** 🚫

- ❌ `016_image_mapping.sql`:
  - `image_mapping_rules` 테이블 (stage → image 매핑)
  - `scenario_stage_images` 테이블 (시나리오별 이미지)
  - `scenario_default_images` 테이블 (기본 이미지)

**현재 상태**: 하드코딩된 이미지 경로만 사용

---

### 10. **시나리오 코멘트/좋아요 시스템** 🚫

- ❌ `019_scenario_comments.sql` + `020_scenario_likes.sql`
- ❌ `src/api/scenario_router.py`의 관련 엔드포인트

**현재 상태**: galleries feature에만 일부 존재

---

## ⚠️ 부분적으로 구현된 기능

### 1. **사용자 메모리 (User Memories)**
- ✅ tm_work: `006_user_memories.sql` + 벡터 임베딩
- ⚠️ 현재: `user_memories` 테이블 있으나 벡터 검색 없음

### 2. **크레딧 시스템**
- ✅ tm_work: `user_credits` + `credit_transactions`
- ⚠️ 현재: `user_credits` 있으나 transaction 로깅 미흡

### 3. **세션 관리**
- ✅ tm_work: Hybrid (Redis + PostgreSQL)
- ⚠️ 현재: PostgreSQL만 (캐싱 없음)

---

## 📊 구조적 차이 요약

| 기능 | tm_work | 현재 브랜치 | 비고 |
|------|---------|-------------|------|
| **아키텍처** | LangGraph 기반 | 4-Layer (CRUD) | 완전히 다름 |
| **AI 에이전트** | ✅ 5개 에이전트 | ❌ 없음 | **핵심 차이** |
| **워크플로우** | ✅ LangGraph | ❌ 단순 API | **핵심 차이** |
| **세션 관리** | ✅ Hybrid (Redis+PG) | ⚠️ PG only | 캐싱 없음 |
| **시나리오** | ✅ 5가지 stage type | ⚠️ 단순 JSON | 분기 처리 미흡 |
| **대화 요약** | ✅ LLM 자동 요약 | ❌ 없음 | - |
| **Graph RAG** | ✅ pgvector + 관계 그래프 | ❌ 없음 | - |
| **사용자 진행도** | ✅ RPG 시스템 | ⚠️ 크레딧만 | XP/레벨 없음 |
| **이미지 매핑** | ✅ DB 기반 매핑 | ❌ 하드코딩 | - |
| **스트리밍** | ✅ LangGraph astream | ⚠️ SSE만 | - |
| **Migration** | ✅ SQL 20개 | ⚠️ Alembic | - |

---

## 🎯 우선순위별 통합 권장사항

### Priority 1 (핵심 기능)
1. **LangGraph 통합** - tm_work의 `src/agents/` + `src/core/workflow.py`
   - 현재 4-layer 구조를 유지하면서 Agent 레이어에 LangGraph 통합
   - `app/features/chat/agent/` 디렉토리에 통합

2. **HybridSessionManager** - Redis 캐싱 추가
   - 현재 Repository 위에 Cache 레이어 추가
   - `app/core/cache/` 생성

3. **고급 시나리오 시스템** - `mugen_train_full.json` 구조 적용
   - 5가지 stage type 지원
   - 현재 scenario_service.py에 통합

### Priority 2 (성능 개선)
4. **대화 요약 자동화** - `conversation_summarizer.py` 통합
5. **pgvector + Graph RAG** - 벡터 검색 및 지식 그래프

### Priority 3 (사용자 경험)
6. **사용자 진행도 시스템** - XP/레벨/랭크 추가
7. **이미지 매핑 시스템** - DB 기반 동적 매핑
8. **시나리오 코멘트/좋아요** - 소셜 기능

---

## 🔄 통합 전략

### Option A: LangGraph를 현재 구조에 통합
```
app/features/chat/
├── controller.py       # [Layer 1] HTTP 엔드포인트
├── usecase.py          # [Layer 2] 비즈니스 로직
├── agent/              # [Layer 3] LangGraph 에이전트 (tm_work 통합)
│   ├── workflow.py
│   ├── parent_agent.py
│   ├── children_agent.py
│   └── dialogue_agent.py
└── repository.py       # [Layer 4] DB 접근
```

### Option B: tm_work 구조를 4-layer로 리팩토링
- api_server.py를 feature별 controller로 분리
- HybridSessionManager를 Repository 패턴으로 래핑

---

## 📝 결론

**가장 중요한 차이점**:
1. ⭐ **LangGraph 멀티에이전트 시스템** (tm_work의 핵심)
2. ⭐ **HybridSessionManager** (Redis 캐싱)
3. ⭐ **고급 시나리오 시스템** (5가지 stage type)

**현재 브랜치의 장점**:
- ✅ 깔끔한 4-layer 아키텍처
- ✅ 완전한 Repository 패턴
- ✅ 체계적인 로깅 시스템

**tm_work의 장점**:
- ✅ 강력한 AI 에이전트 시스템
- ✅ 복잡한 시나리오 분기 처리
- ✅ 실시간 스트리밍 (LangGraph astream)

**권장 방향**:
현재 4-layer 구조를 유지하면서 tm_work의 LangGraph 에이전트를 Agent 레이어에 통합하는 하이브리드 접근 방식을 추천합니다.
