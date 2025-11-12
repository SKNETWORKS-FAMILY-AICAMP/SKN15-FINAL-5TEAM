# 작업 내역 (지난 48시간)

> 2025-01-12 작성
> 브랜치: tm-merge-all-logic

---

## 커밋 히스토리

### 11시간 전 (최근 작업)

#### 1. `8a2858b` - 시나리오 데이터 업데이트
- `data/scenarios/example-advanced.json` 삭제
- `data/scenarios/mugen-train.json` 개선 (+43줄)

#### 2. `23c8dbb` - 프론트엔드 페이지 및 API 서비스 개선
- `front/src/pages/ChatPage.tsx` 리팩토링
- `front/src/pages/HomePage.tsx` 수정
- `front/src/services/api.ts` 대폭 개선 (+763줄)
- `front/src/types/chat.ts` 타입 정의 추가

#### 3. `3acbb22` - 프론트엔드 컨텍스트 및 훅 개선
- `front/src/contexts/AppContext.tsx`
- `front/src/hooks/useBackgroundImage.ts` 간소화
- `front/src/hooks/useScenarioComments.ts`
- `front/src/hooks/useSoundEffects.ts` 간소화

#### 4. `9d82ae2` - 프론트엔드 UI 컴포넌트 개선
- `front/src/components/ChatHeader.tsx` (+179줄)
- `front/src/components/ChatInterface.tsx` 대폭 개선 (+954줄)
- `front/src/components/MyAccountModal.tsx`

#### 5. `1f323c5` - 데이터베이스 마이그레이션 및 데이터 임포트
- `backend/migrations/env.py` 업데이트
- `backend/migrations/versions/20251111_1422_75a366f1b383_add_content_tables_worlds_characters_.py` 신규 마이그레이션
- `backend/scripts/import_content_data.py` 컨텐츠 데이터 임포트 스크립트 (+434줄)

#### 6. `a4623dc` - 백엔드 기능 전반 개선
**파일:**
- `backend/app/features/logging/models.py` 로깅 모델 확장
- `backend/app/features/scenarios/usecase.py`
- `backend/app/features/sessions/controller.py` 세션 컨트롤러 확장
- `backend/app/features/users/controller.py` 사용자 컨트롤러 대폭 확장 (+164줄)
- `backend/app/features/users/repository.py`
- `backend/app/main.py`

#### 7. `c78e040` - 새로운 기능 모듈 추가
**신규 모듈:**
- `backend/app/features/content/` - 컨텐츠 관리 (Worlds, Characters, Items)
  - `models.py` (+181줄)
- `backend/app/features/game/` - 게임 시스템 (장비, 이미지, 랭크, 미션)
  - `controller.py` (+293줄)
  - `models.py` (+148줄)
  - `repository.py` (+279줄)
  - `schemas.py` (+141줄)
  - `usecase.py` (+230줄)
- `backend/app/features/misc/` - 기타 기능 (세션 스냅샷, 통계, 피드백, 크레딧)
  - `controller.py` (+100줄)
  - `models.py` (+81줄)
  - `repository.py` (+137줄)
  - `usecase.py` (+95줄)
- `backend/app/features/progression/` - 진행도 시스템
  - `controller.py` (+330줄)
  - `models.py` (+172줄)
  - `repository.py` (+380줄)
  - `schemas.py` (+175줄)
  - `usecase.py` (+349줄)
- `backend/app/features/images/legacy_models.py` (+104줄)

#### 8. `aebf373` - 채팅 관련 모델 추가 및 개선
**파일:**
- `backend/app/features/chat/models/affinity_record.py` 신규 (+32줄)
- `backend/app/features/chat/models/user_character_affinity.py` 신규 (+36줄)
- `backend/app/features/chat/models/dialogue_turn.py` 개선
- `backend/app/features/chat/models/entity.py` 개선
- `backend/app/features/chat/models/relationship.py` 개선

#### 9. `59ef00a` - 채팅 기능 통합 및 개선
**파일:**
- `backend/app/features/chat/controller.py`
- `backend/app/features/chat/repository.py`
- `backend/app/features/chat/sse_helper.py` 신규 (+64줄) - SSE 헬퍼
- `backend/app/features/chat/usecase.py` (+78줄)
- `backend/app/features/chat/agent/graph_state.py`
- `backend/app/features/chat/agent/stage_handlers/scene_stage.py`

#### 10. `4edbc3b`, `97f8c6f` - 회원가입 시 초기 크레딧 200개 자동 지급
**파일:**
- `backend/app/features/auth/controller.py`
- `backend/app/features/auth/usecase.py` (+58줄)
- `backend/app/features/auth/schemas.py`
- `backend/scripts/grant_initial_credits_to_existing_users.py` 신규 (+153줄)

#### 11. `b9ae6dc` - LangGraph DialogueAgent에 Legacy ParentAgent 통합
**파일:**
- `backend/app/features/chat/agent/nodes/dialogue.py` (+112줄)
- `backend/app/features/chat/agent/workflow.py`

#### 12. `a51e118` - LangGraph ParentAgent 시나리오 로딩 기능 추가
**파일:**
- `backend/app/features/chat/agent/nodes/parent.py` (+30줄)

---

### 24시간 전

#### 13. `cfa3d2e` - 창 3 완료 - progression/memories 통합 + 전체 마이그레이션
**문서:**
- `CHAT_UI_RESTORE_GUIDE.md` 신규 (+522줄)
- `MIGRATION_COMPLETE.md` 신규 (+391줄)
- `MIGRATION_PARALLEL_GUIDE.md` 신규 (+1374줄)
- `MIGRATION_STATUS_REPORT.md` 신규 (+237줄)
- `OPTIMAL_BACKEND_STRUCTURE.md` 신규 (+1370줄)

**LangGraph 워크플로우:**
- `backend/app/features/chat/agent/workflow.py` 신규 (+262줄)
- `backend/app/features/chat/agent/nodes/` 디렉토리 구조 신규
  - `children.py` (+91줄)
  - `dialogue.py` (+46줄)
  - `parent.py` (+33줄)
  - `router.py` (+36줄)
- `backend/app/features/chat/agent/handlers/` 스테이지 핸들러
  - `free_intent.py` (+73줄)
  - `mission.py` (+72줄)
  - `open_narrative.py` (+74줄)
  - `router.py` (+56줄)
  - `scene.py` (+77줄)

**Repository 분리:**
- `backend/app/features/chat/repositories/entity_repository.py` 신규 (+536줄)
- `backend/app/features/chat/repositories/memory_repository.py` 신규 (+233줄)

**서비스 계층:**
- `backend/app/features/chat/services/conversation_summarizer.py` 신규 (+300줄)
- `backend/app/features/chat/services/image_mapping_service.py` 신규 (+86줄)
- `backend/app/features/chat/services/progression_service.py` 신규 (+133줄)

**모델 리팩토링:**
- `backend/app/features/chat/models/` 디렉토리 구조로 변경
  - `dialogue_turn.py`
  - `entity.py`
  - `relationship.py`
  - `user_memory.py`
  - `conversation_summary.py`
  - `entity_mention.py`

**백업:**
- `entities/`, `memories/`, `progression/` 기존 기능 `.backup`으로 이동
- `backend/app/features/users/models/xp_transaction.py` 분리 (+34줄)

---

### 25-26시간 전

#### 14. `2798ea5` - 관리자용 Graph RAG 엔티티 모니터링 API 추가
**파일:**
- `backend/app/features/admin/controller.py` (+79줄)
- `backend/app/features/admin/usecase.py` (+91줄)

#### 15. `bace73b` - 프론트엔드 UI 업데이트 (진행도/기억/설정 통합)
**파일:**
- `front/src/components/BubbleCounter.tsx`
- `front/src/components/ChatInterface.tsx` (+92줄)
- `front/src/contexts/AppContext.tsx` (+30줄)

#### 16. `015c9c1` - 신규 Features 라우터 등록
**파일:**
- `backend/app/main.py` - entities, images 라우터 등록

#### 17. `b0970ed` - Sessions 기능 개선 및 Repository 추가
**파일:**
- `backend/app/features/sessions/repository.py` 신규 (+312줄)
- `backend/app/features/sessions/usecase.py` 대폭 개선 (+229줄)

---

## 오늘 추가 작업 (방금 완료)

### ChatRepository 도메인별 분리
**신규 파일:**
- `backend/app/features/chat/repositories/dialogue_repository.py` (+184줄)
  ```python
  # 기능: 대화 CRUD
  # - save_dialogue() : 대화 저장
  # - save_dialogues_batch() : 대화 배치 저장
  # - count_today() : 오늘 대화 횟수 조회
  # - get_recent_dialogues() : 최근 대화 조회
  # - get_user_dialogue_history() : 사용자 대화 히스토리
  # - delete_session_dialogues() : 세션 대화 삭제
  ```

- `backend/app/features/chat/repositories/session_repository.py` (+156줄)
  ```python
  # 기능: 세션 상태 관리
  # - get_session() : 세션 상태 조회
  # - save_session() : 세션 상태 저장 (upsert)
  # - delete_session() : 세션 삭제 (soft delete)
  ```

- `backend/app/features/chat/repositories/affinity_repository.py` (+206줄)
  ```python
  # 기능: 친밀도 관리
  # - save_affinity_record() : 세션별 친밀도 기록 저장
  # - get_latest_affinity() : 최신 친밀도 조회
  # - upsert_user_character_affinity() : 글로벌 친밀도 UPSERT
  # - get_user_character_affinity() : 사용자 캐릭터 친밀도 조회
  # - get_all_user_affinities() : 모든 친밀도 조회
  ```

- `backend/app/features/chat/repositories/image_repository.py` (+106줄)
  ```python
  # 기능: 이미지 매핑 조회
  # - get_best_image_for_stage() : 스테이지별 최적 이미지 조회 (JSONB 쿼리)
  ```

**수정 파일:**
- `backend/app/features/chat/repositories/__init__.py` - 6개 Repository export
- `backend/app/features/chat/usecase.py` - ChatRepository → 도메인별 Repository로 변경
- `backend/app/features/users/usecase.py` - AffinityRepository, MemoryRepository 사용
- `backend/app/features/sessions/usecase.py` - DialogueRepository 사용
- `backend/app/features/progression/models.py` - XPTransaction 중복 정의 제거 (-39줄)
- `backend/app/features/progression/repository.py` - XPTransaction import 경로 수정

**기타:**
- `TEAM_SETUP_GUIDE.md` 신규 (+325줄)
- `README_VERIFICATION.md` 삭제 (-213줄)

---

## 4계층 아키텍처 구조

```
backend/app/
├── core/                          # 공통 모듈
│   ├── db/                        # 데이터베이스 연결
│   ├── llm/                       # LLM 클라이언트 (OpenAI, Anthropic)
│   ├── cache/                     # 캐시 매니저
│   └── logging/                   # 로깅 유틸
│
├── shared/                        # 공유 모듈
│   ├── exceptions.py              # 커스텀 예외
│   └── dependencies.py            # FastAPI 의존성
│
└── features/                      # 기능별 모듈 (Feature-based Architecture)
    │
    ├── auth/                      # 인증 (회원가입, 로그인)
    │   ├── controller.py          # [Layer 1] API 엔드포인트
    │   ├── usecase.py             # [Layer 2] 비즈니스 로직
    │   ├── repository.py          # [Layer 4] DB 접근
    │   ├── schemas.py             # [Layer 1] DTO
    │   └── models.py              # [Layer 4] ORM 모델
    │
    ├── users/                     # 사용자 프로필 및 통계
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── schemas.py
    │   └── models/
    │       └── xp_transaction.py  # XP 거래 기록
    │
    ├── chat/                      # 대화 시스템 (핵심 기능)
    │   ├── controller.py          # [Layer 1] 채팅 API
    │   ├── usecase.py             # [Layer 2] 대화 생성 로직
    │   │
    │   ├── repositories/          # [Layer 4] Repository (도메인별 분리)
    │   │   ├── __init__.py
    │   │   ├── dialogue_repository.py    # 대화 CRUD
    │   │   ├── session_repository.py     # 세션 상태 관리
    │   │   ├── affinity_repository.py    # 친밀도 관리
    │   │   ├── image_repository.py       # 이미지 매핑 조회
    │   │   ├── entity_repository.py      # Graph RAG 엔티티 관리
    │   │   └── memory_repository.py      # 장기 기억 관리
    │   │
    │   ├── models/                # [Layer 4] ORM 모델
    │   │   ├── dialogue_turn.py          # 대화 턴
    │   │   ├── entity.py                 # 엔티티 (Graph RAG)
    │   │   ├── relationship.py           # 엔티티 관계
    │   │   ├── user_memory.py            # 사용자 기억
    │   │   ├── affinity_record.py        # 친밀도 기록
    │   │   └── user_character_affinity.py # 글로벌 친밀도
    │   │
    │   ├── agent/                 # [Layer 3] LangGraph 워크플로우
    │   │   ├── workflow.py               # LangGraph 그래프 정의
    │   │   ├── graph_state.py            # 상태 관리
    │   │   ├── nodes/                    # 노드 (Parent, Children, Dialogue, Router)
    │   │   └── handlers/                 # 스테이지 핸들러 (Scene, Mission, Router, etc.)
    │   │
    │   ├── services/              # [Layer 3] 서비스 계층
    │   │   ├── affinity_service.py       # 친밀도 계산 로직
    │   │   ├── memory_service.py         # 기억 관리 로직
    │   │   ├── mission_service.py        # 미션 검증 로직
    │   │   ├── scenario_service.py       # 시나리오 로딩
    │   │   ├── conversation_summarizer.py # LLM 기반 대화 요약
    │   │   └── extractors/               # 정보 추출기 (엔티티, 기억 등)
    │   │
    │   └── schemas.py             # [Layer 1] DTO
    │
    ├── scenarios/                 # 시나리오 관리
    │   ├── controller.py          # 시나리오 목록/상세 조회 API
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── models.py              # Scenario, Stage, Choice 모델
    │   └── schemas.py
    │
    ├── sessions/                  # 세션 목록 조회
    │   ├── controller.py
    │   ├── usecase.py
    │   ├── repository.py
    │   └── models.py              # Session 모델
    │
    ├── progression/               # 진행도 시스템
    │   ├── controller.py          # 진행도 조회/업데이트 API
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── models.py              # UserProgression, UserScenarioProgress, StageProgression, UserInput
    │   └── schemas.py
    │
    ├── game/                      # 게임 시스템
    │   ├── controller.py          # 장비, 이미지, 랭크, 미션 API
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── models.py              # UserEquipment, UserUnlockedImage, RankDefinition, GameEvent, MissionRecord
    │   └── schemas.py
    │
    ├── misc/                      # 기타 기능
    │   ├── controller.py          # 세션 스냅샷, 통계, 피드백 API
    │   ├── usecase.py
    │   ├── repository.py
    │   ├── models.py              # SessionSnapshot, ScenarioStatistics, UserFeedback, UserCredits
    │   └── schemas.py
    │
    ├── content/                   # 컨텐츠 관리
    │   └── models.py              # World, Character, Item 모델
    │
    ├── images/                    # 이미지 매핑
    │   ├── controller.py
    │   ├── repository.py
    │   ├── models.py              # ImageMapping (JSONB metadata)
    │   └── legacy_models.py       # 레거시 모델 (ImageAsset 등)
    │
    ├── galleries/                 # 갤러리 (이미지 잠금 해제)
    │   ├── controller.py
    │   ├── repository.py
    │   └── schemas.py
    │
    ├── admin/                     # 관리자 기능
    │   ├── controller.py          # 대화 내역, 엔티티 모니터링, 사용자 관리 API
    │   ├── usecase.py
    │   ├── repository.py
    │   └── schemas.py
    │
    └── logging/                   # 로깅 시스템
        ├── models.py              # Log, ErrorLog, PerformanceMetric, TrainingLog
        └── repository.py
```

---

## 기능별 상세 설명

### 1. **auth** - 인증
```python
# controller.py
POST /api/auth/register           # 회원가입 (초기 크레딧 200개 자동 지급)
POST /api/auth/login              # 로그인
POST /api/auth/refresh            # JWT 토큰 갱신
GET  /api/auth/me                 # 현재 사용자 정보 조회
```

### 2. **users** - 사용자 프로필
```python
# controller.py
GET  /api/users/me                # 사용자 정보 조회
GET  /api/users/me/profile        # 프로필 (진행도, 친밀도, 통계 포함)
GET  /api/users/me/memories       # 사용자 기억 조회
GET  /api/users/me/credits        # 크레딧 조회
POST /api/users/me/credits/consume # 크레딧 소비

# repository.py
# - get_user_by_id() : 사용자 조회
# - create_user() : 사용자 생성
# - create_user_credits() : 초기 크레딧 생성
# - get_user_credits() : 크레딧 조회
# - update_credits() : 크레딧 업데이트
# - save_xp_transaction() : XP 거래 기록 저장
```

### 3. **chat** - 대화 시스템 (핵심)
```python
# controller.py
POST /api/chat                    # 대화 생성 (메인 API)
GET  /api/chat/history/{session_id} # 세션 대화 히스토리
DELETE /api/chat/session/{session_id} # 세션 삭제

# usecase.py - 비즈니스 로직
# - create_dialogue() : 대화 생성 (LangGraph 또는 Legacy Agent)
# - get_recent_dialogues() : 최근 대화 조회
# - delete_session() : 세션 삭제
# - 일일 대화 제한 체크 (MAX_DAILY_CHATS = 1000)

# repositories/dialogue_repository.py
# - save_dialogue() : 대화 저장
# - save_dialogues_batch() : 배치 저장
# - count_today() : 오늘 대화 횟수
# - get_recent_dialogues() : 최근 대화 조회
# - get_user_dialogue_history() : 히스토리 조회
# - delete_session_dialogues() : 세션 대화 삭제

# repositories/session_repository.py
# - get_session() : 세션 상태 조회
# - save_session() : 세션 상태 저장 (upsert)
# - delete_session() : soft delete

# repositories/affinity_repository.py
# - save_affinity_record() : 친밀도 기록 저장
# - get_latest_affinity() : 최신 친밀도 조회
# - upsert_user_character_affinity() : 글로벌 친밀도 업데이트
# - get_user_character_affinity() : 특정 캐릭터 친밀도
# - get_all_user_affinities() : 모든 친밀도 조회

# repositories/image_repository.py
# - get_best_image_for_stage() : JSONB 쿼리로 최적 이미지 선택

# repositories/entity_repository.py (Graph RAG)
# - save_entity() : 엔티티 UPSERT
# - get_entities() : 엔티티 조회
# - search_entities_by_embedding() : 벡터 유사도 검색
# - save_relationship() : 관계 UPSERT
# - get_relationships() : 관계 조회

# repositories/memory_repository.py
# - save_memory() : 장기 기억 저장
# - get_user_memories() : 사용자 기억 조회
# - search_memories_by_embedding() : 벡터 유사도 검색

# agent/workflow.py - LangGraph 워크플로우
# - get_workflow() : StateGraph 생성
# - 노드: parent_node, router_node, children_node, dialogue_node
# - 엣지: 조건부 라우팅 (should_route)

# agent/nodes/parent.py
# - parent_node() : ParentAgent 실행 (시나리오 로딩, 스테이지 관리)

# agent/nodes/dialogue.py
# - dialogue_node() : DialogueAgent 실행 (대사 생성, LLM 호출)

# agent/nodes/children.py
# - children_node() : ChildrenAgent 실행 (후처리)

# agent/nodes/router.py
# - router_node() : RouterAgent 실행 (의도 분류)

# services/affinity_service.py
# - calculate_affinity() : 친밀도 계산 로직

# services/memory_service.py
# - extract_memories() : 기억 추출 로직

# services/conversation_summarizer.py
# - summarize() : LLM 기반 대화 요약
```

### 4. **scenarios** - 시나리오 관리
```python
# controller.py
GET  /api/scenarios               # 시나리오 목록 조회
GET  /api/scenarios/{scenario_id} # 시나리오 상세 조회

# repository.py
# - get_all_scenarios() : 시나리오 목록
# - get_scenario_by_id() : 시나리오 상세 (스테이지 포함)
# - 스테이지 타입: scene, mission, router, free_intent, open_narrative
```

### 5. **sessions** - 세션 관리
```python
# controller.py
GET  /api/sessions/me             # 내 세션 목록
GET  /api/sessions/{session_id}   # 세션 상세 (대화 포함)

# repository.py
# - get_user_sessions() : 사용자 세션 목록
# - get_session_detail() : 세션 상세 조회
```

### 6. **progression** - 진행도 시스템
```python
# controller.py
GET  /api/progression/me          # 내 전체 진행도
GET  /api/progression/me/scenarios/{scenario_id} # 시나리오별 진행도
POST /api/progression/me/xp       # XP 획득
POST /api/progression/me/level-up # 레벨업

# models.py
# - UserProgression : 전체 진행도 (레벨, XP, 랭크, 통계)
# - UserScenarioProgress : 시나리오별 진행도
# - StageProgression : 스테이지 진행 기록
# - UserInput : 사용자 입력 기록

# repository.py
# - save_user_input() : 사용자 입력 저장
# - get_user_progression() : 전체 진행도 조회
# - upsert_user_progression() : 진행도 업데이트
# - get_scenario_progress() : 시나리오 진행도 조회
# - save_stage_progression() : 스테이지 진행 기록
# - save_xp_transaction() : XP 거래 기록 (users.models.XPTransaction 사용)
```

### 7. **game** - 게임 시스템
```python
# controller.py
GET  /api/game/me/equipment       # 내 장비 조회
POST /api/game/me/equipment       # 장비 장착
GET  /api/game/me/images          # 잠금 해제된 이미지
POST /api/game/me/images/unlock   # 이미지 잠금 해제
GET  /api/game/ranks              # 랭크 정의 조회
GET  /api/game/me/missions        # 내 미션 기록

# models.py
# - UserEquipment : 사용자 장비
# - UserUnlockedImage : 잠금 해제된 이미지
# - RankDefinition : 랭크 정의 (novice, bronze, silver, ...)
# - GameEvent : 게임 이벤트 로그
# - MissionRecord : 미션 완료 기록
```

### 8. **misc** - 기타 기능
```python
# controller.py
POST /api/misc/feedback           # 피드백 제출
GET  /api/misc/statistics/{scenario_id} # 시나리오 통계

# models.py
# - SessionSnapshot : 세션 스냅샷 (JSON 저장)
# - ScenarioStatistics : 시나리오 통계
# - UserFeedback : 사용자 피드백
# - UserCredits : 사용자 크레딧
```

### 9. **admin** - 관리자 기능
```python
# controller.py
GET  /api/admin/users             # 사용자 목록
GET  /api/admin/users/{user_id}   # 사용자 상세
GET  /api/admin/dialogues         # 대화 내역 조회
GET  /api/admin/entities          # Graph RAG 엔티티 모니터링
GET  /api/admin/entities/{entity_id}/relationships # 엔티티 관계 조회
```

### 10. **content** - 컨텐츠 관리
```python
# models.py
# - World : 세계관 정의
# - Character : 캐릭터 정보
# - Item : 아이템 정보
```

### 11. **images** - 이미지 매핑
```python
# models.py
# - ImageMapping : 이미지 매핑 (scenario_id, stage_id, JSONB metadata)
# repository.py
# - get_image_mapping() : 이미지 조회 (JSONB 쿼리)
```

### 12. **logging** - 로깅 시스템
```python
# models.py
# - Log : 일반 로그
# - ErrorLog : 에러 로그
# - PerformanceMetric : 성능 메트릭
# - TrainingLog : LLM Fine-tuning 학습 로그
```

---

## 통계

- **총 커밋**: 20개 (지난 48시간)
- **신규 파일**: ~100개 이상
- **수정 파일**: ~50개 이상
- **총 코드 추가**: ~15,000줄 이상
- **주요 기능 모듈**: 12개 (auth, users, chat, scenarios, sessions, progression, game, misc, content, images, admin, logging)
- **4-Layer Architecture 완성도**: 90% 이상

---

## 현재 상태

✅ 백엔드 서버 정상 작동
✅ 모든 Repository import 성공
✅ Health Check 통과
✅ Docker 환경 안정화

---

**작성 완료**
