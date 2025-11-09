🎯 완전한 tm_work → dw_work 마이그레이션 계획

## 📊 현황 요약
- **소스**: tm_work 브랜치 (backend/src, 85개 파일)
- **타겟**: dw_work 브랜치 (backend/app, 37개 파일 - 4-Layer 아키텍처)
- **병합 대상**: tm-merge-all-logic (dw_work와 동일 커밋)
- **지침**: merge_strategy.md + 4-Layer 규칙

## 🚦 핵심 규칙 (절대 준수)
1. **의존성 규칙**: Controller → UseCase → Agent/Service → Repository
2. **DB 접근 금지**: Controller, UseCase, Service는 DB 직접 접근 절대 금지
3. **SQL 제거**: 모든 순수 SQL을 SQLAlchemy ORM으로 변환

---

## 🔴 중대 주의사항: DB 스키마 통합

### 스키마 변경 사항
**기존 구조** (tm_work):
- `statedb` 스키마: 37개 테이블 (세션, 사용자, 시나리오, 친밀도 등)
- `logdb` 스키마: 3개 테이블 (로그, 에러, 성능 메트릭)
- `public` 스키마: 2개 테이블 (학습 로그, 피드백)

**새 구조** (dw_work):
- **모든 테이블 → `public` 스키마로 통합** (총 42개 테이블)

### 영향받는 파일
- **SQL 마이그레이션**: 18개 파일에서 스키마 참조 제거 필요
- **Python 코드**:
  - `db_manager.py`: 138개 라인 수정 (`statedb.`, `logdb.` 제거)
  - `db_manager_comments.py`: 12개 라인 수정

### 필수 작업
⚠️ **모든 코드에서 `statedb.`, `logdb.` 참조를 제거해야 함**

정규식 치환:
```
statedb\. → (빈 문자열)
logdb\. → (빈 문자열)
```

예시:
```python
# ❌ 잘못된 코드 (tm_work 스타일)
INSERT INTO statedb.users (...)
SELECT * FROM logdb.logs WHERE ...

# ✅ 올바른 코드 (dw_work 스타일)
INSERT INTO users (...)
SELECT * FROM logs WHERE ...
```

---

## 📋 PHASE 0: DB 스키마 사전 준비 ⭐ 최우선 (1일)

### 0-1. 백업 (필수)
```bash
# PostgreSQL 덤프
pg_dump -U kime -d kimedb > backup_before_schema_migration.sql

# Git 커밋
git add .
git commit -m "backup: Before schema consolidation"
```

### 0-2. 스키마 통합 마이그레이션 스크립트 작성

**파일**: `backend/migrations/versions/000_schema_consolidation.py`

```python
"""Schema consolidation: Move all tables to public schema

Revision ID: 000_schema_consolidation
Revises:
Create Date: 2025-01-XX
"""

def upgrade():
    # 1. statedb 테이블들을 public으로 이동 (37개)
    tables = [
        'sessions', 'user_inputs', 'dialogues', 'affinity_records',
        'stage_progression', 'game_events', 'mission_records',
        'session_snapshots', 'users', 'password_reset_tokens',
        'user_credits', 'credit_transactions', 'user_settings',
        'user_memories', 'rank_definitions', 'user_progression',
        'user_equipment', 'xp_transactions', 'scenarios',
        'scenario_statistics', 'user_scenario_progress',
        'scenario_views', 'scenario_comments', 'comment_likes',
        'scenario_likes', 'image_assets', 'scenario_stage_images',
        'image_mapping_rules', 'scenario_default_images',
        'user_unlocked_images', 'user_character_affinity',
        'entities', 'entity_relationships', 'entity_mentions'
    ]

    for table in tables:
        op.execute(f"ALTER TABLE IF EXISTS statedb.{table} SET SCHEMA public")

    # 2. logdb 테이블들을 public으로 이동 (3개)
    log_tables = ['logs', 'error_logs', 'performance_metrics']
    for table in log_tables:
        op.execute(f"ALTER TABLE IF EXISTS logdb.{table} SET SCHEMA public")

    # 3. 함수들을 public으로 이동
    functions = [
        'get_scenario_comments', 'get_comment_replies',
        'upsert_character_affinity', 'update_affinity_level',
        'get_top_affinity_characters', 'get_best_image_for_stage',
        'get_user_unlocked_images'
    ]
    for func in functions:
        op.execute(f"ALTER FUNCTION IF EXISTS statedb.{func} SET SCHEMA public")

    # 4. 뷰들을 public으로 이동
    views = ['v_scenario_cards', 'v_user_progression_summary']
    for view in views:
        op.execute(f"ALTER VIEW IF EXISTS statedb.{view} SET SCHEMA public")

    # 5. 스키마 삭제
    op.execute("DROP SCHEMA IF EXISTS statedb CASCADE")
    op.execute("DROP SCHEMA IF EXISTS logdb CASCADE")

def downgrade():
    # 롤백: 스키마 재생성 및 테이블 복원
    op.execute("CREATE SCHEMA IF NOT EXISTS statedb")
    op.execute("CREATE SCHEMA IF NOT EXISTS logdb")
    # ... (역순 작업)
```

### 0-3. Python 코드 스키마 참조 제거

**파일 1**: `backend/src/database/db_manager.py` (138개 라인 수정)

```bash
# VSCode 또는 sed를 사용한 일괄 치환
sed -i 's/statedb\.//g' backend/src/database/db_manager.py
sed -i 's/logdb\.//g' backend/src/database/db_manager.py
```

**주요 수정 위치**:
- Line 130, 151, 179: users 테이블
- Line 361, 394, 420: sessions 테이블
- Line 541: user_inputs 테이블
- Line 598: dialogues 테이블
- Line 697: affinity_records 테이블
- Line 960, 987, 1012: logs, error_logs, performance_metrics

**파일 2**: `backend/src/database/db_manager_comments.py` (12개 라인 수정)

```bash
sed -i 's/statedb\.//g' backend/src/database/db_manager_comments.py
```

**주요 수정 위치**:
- Line 45, 71: 함수 호출
- Line 103, 124, 153, 183: scenario_comments
- Line 214, 221, 228, 235: comment_likes

### 0-4. SQL 마이그레이션 파일 수정 (선택사항)

⚠️ **주의**: 이미 실행된 마이그레이션 파일은 수정하지 않는 것이 안전합니다.
대신 새로운 스키마 통합 마이그레이션(000_schema_consolidation.py)을 실행하세요.

### 0-5. 테스트 및 검증

```bash
# 1. 로컬 DB에서 마이그레이션 실행
cd backend
alembic upgrade head

# 2. 테이블 확인
psql -U kime -d kimedb -c "\dt public.*"

# 3. 기능 테스트
python -m pytest tests/test_db_schema.py

# 4. API 서버 실행 확인
python api_server.py
```

**테스트 체크리스트**:
- [ ] 모든 테이블이 public 스키마에 존재
- [ ] FK 제약조건 정상 작동
- [ ] 트리거 함수 정상 작동
- [ ] 사용자 로그인/가입 정상
- [ ] 세션 저장/로드 정상
- [ ] 대화 저장 정상
- [ ] 친밀도 업데이트 정상

---
## 📋 PHASE 1: DB 스키마 병합 (1-2일)

### ⚠️ 스키마 주의사항
- **중요**: SQLAlchemy 모델에서 `__table_args__` 스키마 지정을 **제거**하거나 생략하세요
- public 스키마가 기본값이므로 명시적으로 지정할 필요 없음

### 1-1. SQLAlchemy Models 생성

**타겟**: `app/features/chat/models.py`에 추가

UserCharacterAffinity 모델 (018_user_character_affinity.sql 기반)

```python
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, CheckConstraint

class UserCharacterAffinity(Base):
    __tablename__ = 'user_character_affinity'
    # ✅ 스키마 지정 제거 - public이 기본
    __table_args__ = (
        CheckConstraint('total_affinity_score >= 0 AND total_affinity_score <= 1000'),
        CheckConstraint('affinity_level >= 1 AND affinity_level <= 10'),
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String, nullable=False)
    character_name = Column(String(255), nullable=False)
    total_affinity_score = Column(Integer, nullable=False, default=0)
    affinity_level = Column(Integer, nullable=False, default=1)
    total_interactions = Column(Integer, nullable=False, default=0)
    last_interaction_at = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

**타겟**: `app/features/scenarios/models.py` (신규 생성)

ScenarioComment, ScenarioLike, CommentLike 모델 (019, 020 SQL 기반)

```python
from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, DateTime, UUID, UniqueConstraint

class ScenarioComment(Base):
    __tablename__ = 'scenario_comments'
    # ✅ 스키마 지정 제거

    id = Column(BigInteger, primary_key=True)
    scenario_id = Column(String(50), nullable=False)
    user_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(BigInteger)
    like_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class ScenarioLike(Base):
    __tablename__ = 'scenario_likes'
    __table_args__ = (UniqueConstraint('scenario_id', 'user_id'),)

    like_id = Column(UUID, primary_key=True)
    scenario_id = Column(String(50), nullable=False)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime)

class CommentLike(Base):
    __tablename__ = 'comment_likes'
    __table_args__ = (UniqueConstraint('comment_id', 'user_id'),)

    id = Column(BigInteger, primary_key=True)
    comment_id = Column(BigInteger, nullable=False)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime)
```

### 1-2. Alembic 마이그레이션

```bash
# 1. env.py에 새 모델 import 추가
# backend/migrations/env.py
from app.features.chat.models import UserCharacterAffinity
from app.features.scenarios.models import ScenarioComment, ScenarioLike, CommentLike

# 2. 마이그레이션 생성
cd backend
alembic revision --autogenerate -m "Add affinity, comments, likes from tm_work"

# 3. 생성된 마이그레이션 파일 확인 및 수정 (스키마 참조 제거 확인)

# 4. 마이그레이션 실행
alembic upgrade head
```
## 📦 PHASE 2: Repository Layer 구현 (Layer 4) (2-3일)

### ⚠️ 스키마 주의사항
- **SQLAlchemy ORM 사용 시**: 모델 클래스를 사용하므로 스키마 자동 처리 → 문제 없음
- **Raw SQL 사용 시**: 테이블명에 스키마 prefix 절대 금지
  ```python
  # ❌ 잘못된 예
  query = text("SELECT * FROM statedb.users WHERE ...")

  # ✅ 올바른 예
  query = text("SELECT * FROM users WHERE ...")
  ```

### 2-1. ChatRepository 확장

**파일**: `app/features/chat/repository.py`

**추가 메서드** (db_manager.py에서 마이그레이션):

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from .models import UserCharacterAffinity, AffinityRecord, Entity, Relationship, Memory

class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_affinity(self, session_id: str, affinity_data: dict) -> None:
        """세션별 친밀도 저장"""
        stmt = insert(AffinityRecord).values(
            session_id=session_id,
            **affinity_data
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def load_latest_affinity(self, session_id: str) -> dict:
        """최신 친밀도 로드"""
        stmt = select(AffinityRecord).where(
            AffinityRecord.session_id == session_id
        ).order_by(AffinityRecord.created_at.desc()).limit(1)

        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        return record.to_dict() if record else {}

    async def upsert_character_affinity(
        self, user_id: str, character_name: str, score_delta: int
    ) -> UserCharacterAffinity:
        """글로벌 친밀도 UPSERT"""
        # SQLAlchemy의 on_conflict_do_update 사용
        # ...

    async def save_entities(self, entities: list[dict]) -> None:
        """엔티티 저장"""
        # ...

    async def save_relationships(self, relationships: list[dict]) -> None:
        """관계 저장"""
        # ...

    async def save_memory(self, user_id: str, memory_data: dict) -> None:
        """장기 기억 저장"""
        # ...

    async def get_user_memories(self, user_id: str, limit: int = 10) -> list:
        """메모리 조회"""
        # ...
```
2-2. ScenarioRepository 생성 (신규)
파일: app/features/scenarios/repository.py 메서드 (db_manager_comments.py에서 마이그레이션):
get_scenario_comments() - 댓글 목록 (정렬, 페이징)
get_comment_replies() - 대댓글 조회
create_comment() - 댓글 생성
update_comment() - 댓글 수정
delete_comment() - 소프트 삭제
toggle_comment_like() - 댓글 추천
toggle_scenario_like() - 시나리오 좋아요
2-3. SessionRepository 생성 (Hybrid)
파일: app/core/db/session_repository.py 메서드 (session_manager.py에서 마이그레이션):
save_session() - Redis + PostgreSQL 하이브리드 저장
load_session() - hot(Redis) → cold(PostgreSQL) 폴백
delete_session() - 세션 삭제
get_recent_sessions() - 최근 세션 목록
🎯 PHASE 3: Service Layer 구현 (Layer 3) (3-4일)
3-1. AffinityService 추가
파일: app/features/chat/services/affinity_service.py 마이그레이션: src/services/affinity_service.py → 그대로 복사 + Repository 주입
update_affinity() - LLM 기반 친밀도 계산
_classify_interaction_with_llm() - 상호작용 분류
3-2. DialogueService 확장
파일: app/features/chat/services/dialogue_service.py (신규) 통합 서비스 (6개 서비스 통합):
dialogue_validation_service.py → validate_dialogue()
dialogue_correction_service.py → correct_dialogue()
dialogue_formatter_service.py → format_dialogue()
dialogue_event_detector_service.py → detect_events()
dialogue_image_service.py → select_image()
3-3. MissionService 추가
파일: app/features/chat/services/mission_service.py (신규) 통합 서비스 (3개 서비스 통합):
mission_logic_service.py → check_mission_completion()
mission_feedback_service.py → generate_feedback()
mission_record_service.py → record_mission_result()
3-4. ContextService 추가
파일: app/features/chat/services/context_service.py (신규) 통합 서비스 (2개 서비스 통합):
context_builder_service.py → build_children_context()
beats_generator_service.py → generate_beats()
3-5. RouterService 확장
파일: app/features/chat/agent/guards/router.py 확장 통합 서비스 (3개 서비스 통합):
topic_classification_service.py → 토픽 분류 로직
intent_detection_service.py → 의도 탐지 로직
router_response_service.py → 응답 전략 로직
3-6. MemoryService 추가
파일: app/features/chat/services/memory_service.py (신규) 통합 유틸 (3개 유틸 통합):
entity_extractor.py → extract_entities()
relationship_extractor.py → extract_relationships()
memory_extractor.py → extract_memories()
🤖 PHASE 4: Agent Layer 확장 (Layer 3) (2-3일)
4-1. DialogueAgent 추가
파일: app/features/chat/agent/dialogue.py (신규) 마이그레이션: src/agents/dialogue_agent.py
validate_and_correct() - DialogueService 호출
4-2. ChildrenAgent 통합 확인
파일: app/features/chat/agent/children.py (신규 또는 llm_service 확인) 마이그레이션: src/agents/children_agent.py
이미 llm_service에 통합되어 있는지 확인
없으면 별도 Agent로 생성
4-3. StageHandlers 추가
디렉토리: app/features/chat/agent/stage_handlers/ (신규) 마이그레이션: src/agents/stage_handlers/* (5개 파일 전체)
mission_stage.py - 미션 스테이지
free_intent_stage.py - 자유 의도 스테이지
router_stage.py - 라우터 스테이지
scene_stage.py - 씬 스테이지
open_narrative_stage.py - 오픈 내러티브 스테이지
4-4. ParentAgent 확장
파일: app/features/chat/agent/parent.py 확장 추가 기능:
StageHandlers 통합
DialogueAgent 파이프라인에 추가
AffinityService 통합
MemoryService 통합
🌐 PHASE 5: UseCase Layer 확장 (Layer 2) (2-3일)
5-1. ChatUseCase 확장
파일: app/features/chat/usecase.py 확장 추가 메서드:
process_affinity() - AffinityService + Repository 호출
save_memories() - MemoryService + Repository 호출
handle_mission() - MissionService 호출
5-2. ScenarioUseCase 생성 (신규)
파일: app/features/scenarios/usecase.py 메서드 (scenario_router.py 로직 분리):
list_scenarios() - 시나리오 목록
get_scenario_detail() - 상세 조회
toggle_like() - 좋아요 토글
create_comment() - 댓글 작성
update_comment() - 댓글 수정
delete_comment() - 댓글 삭제
toggle_comment_like() - 댓글 추천
5-3. UserUseCase 생성 (신규)
파일: app/features/users/usecase.py 메서드 (user_router.py 로직 분리):
get_user_profile() - 프로필 조회
update_user_profile() - 프로필 수정
get_user_stats() - 통계 조회
5-4. SessionUseCase 생성 (신규)
파일: app/features/sessions/usecase.py 메서드 (session_router.py 로직 분리):
list_user_sessions() - 세션 목록
get_session_detail() - 세션 상세
delete_session() - 세션 삭제
5-5. GalleryUseCase 생성 (신규)
파일: app/features/galleries/usecase.py 메서드 (gallery_router.py 로직 분리):
list_user_images() - 이미지 목록
save_generated_image() - 생성 이미지 저장
🎮 PHASE 6: Controller Layer 구현 (Layer 1) (2-3일)
6-1. ScenarioController 생성
파일: app/features/scenarios/controller.py 엔드포인트 (scenario_router.py 마이그레이션):
GET /scenarios - 목록 조회
GET /scenarios/{id} - 상세 조회
POST /scenarios/{id}/like - 좋아요
GET /scenarios/{id}/comments - 댓글 목록
POST /scenarios/{id}/comments - 댓글 작성
PUT /scenarios/{id}/comments/{comment_id} - 댓글 수정
DELETE /scenarios/{id}/comments/{comment_id} - 댓글 삭제
POST /scenarios/{id}/comments/{comment_id}/like - 댓글 추천
6-2. UserController 생성
파일: app/features/users/controller.py 엔드포인트 (user_router.py 마이그레이션):
GET /users/me - 내 프로필
PUT /users/me - 프로필 수정
GET /users/me/stats - 통계
6-3. SessionController 생성
파일: app/features/sessions/controller.py 엔드포인트 (session_router.py 마이그레이션):
GET /sessions - 세션 목록
GET /sessions/{id} - 세션 상세
DELETE /sessions/{id} - 세션 삭제
6-4. GalleryController 생성
파일: app/features/galleries/controller.py 엔드포인트 (gallery_router.py 마이그레이션):
GET /gallery - 이미지 목록
🛠️ PHASE 7: Core & Utils 정리 (2-3일)
7-1. Core 레이어 통합
파일: app/core/ 마이그레이션:
src/core/workflow.py → app/features/chat/workflow.py
src/core/graph_state.py → app/features/chat/graph_state.py
src/core/prompt_builder.py → app/core/llm/prompts.py 통합
src/core/story_orchestrator.py → app/features/chat/services/story_service.py
src/core/scenes_repo.py → app/features/scenarios/services/scene_service.py
7-2. Utils 정리
디렉토리: app/shared/utils/ (신규) 마이그레이션 (22개 파일):
llm_client.py → app/core/llm/client.py (이미 있음, 통합)
logger.py → app/core/logging.py (이미 있음)
config_loader.py → app/core/config.py 통합
scenario_loader.py → app/features/scenarios/services/loader.py
characters_repo.py → app/features/scenarios/services/characters.py
world_loader.py → app/features/scenarios/services/world.py
embedding_matcher.py → app/core/embeddings.py 통합
나머지 utils → app/shared/utils/로 이동
7-3. Tools 정리
디렉토리: app/shared/tools/ (신규) 마이그레이션 (7개 파일):
scene_tools.py, state_tools.py, fallback_tools.py, image_manager.py, loop_tools.py, training_logger.py
모두 app/shared/tools/로 이동 또는 적절한 Service에 통합
🧪 PHASE 8: 테스트 & 검증 (1-2일)
8-1. 단위 테스트 작성
Repository 테스트 (DB Mock)
Service 테스트 (Repository Mock)
UseCase 테스트 (의존성 주입)
Agent 테스트
8-2. 통합 테스트
E2E 채팅 플로우
시나리오 댓글 플로우
친밀도 업데이트 플로우
8-3. 기능 검증 체크리스트
 ParentAgent 파이프라인 정상 실행
 모든 StageHandler 작동
 친밀도 시스템 작동
 댓글/좋아요 시스템 작동
 세션 Hybrid 저장 작동
 장기 기억 저장/조회 작동
 SSE 스트리밍 정상
 OAuth 로그인 정상
---

## 📊 업데이트된 작업량 요약

| Phase | 작업 내용 | 파일 수 | 예상 기간 |
|-------|----------|--------|----------|
| **0** | **DB 스키마 통합** | SQL 18개 + Python 2개 | **1일** ⭐ |
| 1 | DB 모델 생성 | 3개 모델 + Alembic | 1-2일 |
| 2 | Repository | 3개 Repository | 2-3일 |
| 3 | Service | 6개 Service | 3-4일 |
| 4 | Agent | 5개 Handler + 2개 Agent | 2-3일 |
| 5 | UseCase | 5개 UseCase | 2-3일 |
| 6 | Controller | 4개 Controller | 2-3일 |
| 7 | Core/Utils | 30개 파일 정리 | 2-3일 |
| 8 | 테스트 | 전체 검증 | 1-2일 |
| **총합** | | **85개 파일** | **16-24일 (3.5-5주)** |

---

## 📋 스키마 통합 완전 체크리스트

### A. 백업 및 준비
- [ ] PostgreSQL 전체 덤프 생성
- [ ] Git 커밋 (롤백 포인트 확보)
- [ ] 로컬 개발 환경 확인

### B. 마이그레이션 스크립트 실행
- [ ] 000_schema_consolidation.py 작성
- [ ] Alembic 마이그레이션 실행
- [ ] 모든 테이블이 public 스키마로 이동 확인
- [ ] 함수/뷰 이동 확인
- [ ] statedb, logdb 스키마 삭제 확인

### C. Python 코드 수정
- [ ] backend/src/database/db_manager.py (138개 라인)
  - [ ] `statedb.` → `` 치환
  - [ ] `logdb.` → `` 치환
  - [ ] 전체 파일 검색하여 남은 스키마 참조 확인
- [ ] backend/src/database/db_manager_comments.py (12개 라인)
  - [ ] `statedb.` → `` 치환
  - [ ] 전체 파일 검색하여 남은 스키마 참조 확인

### D. SQLAlchemy 모델 확인
- [ ] app/features/*/models.py에서 `__table_args__` 스키마 제거
- [ ] dw_work 브랜치의 모든 모델 파일 검토

### E. 기능 테스트 (중요!)
- [ ] **인증**: 사용자 로그인/회원가입
- [ ] **세션**: 세션 생성/저장/로드
- [ ] **대화**: 대화 저장/조회
- [ ] **친밀도**: 친밀도 업데이트/조회
- [ ] **크레딧**: 크레딧 차감/조회
- [ ] **시나리오**: 시나리오 목록/상세
- [ ] **댓글**: 댓글 작성/조회/수정/삭제
- [ ] **좋아요**: 시나리오/댓글 좋아요
- [ ] **Graph RAG**: 엔티티/관계 저장/조회
- [ ] **이미지**: 이미지 매핑/조회

### F. 통합 테스트
- [ ] E2E 채팅 플로우 (시작~종료)
- [ ] 시나리오 댓글 전체 플로우
- [ ] 사용자 진행도 업데이트 플로우
- [ ] API 서버 재시작 후 정상 작동

### G. 성능 테스트
- [ ] 응답 시간 측정 (스키마 통합 전후 비교)
- [ ] 쿼리 실행 계획 확인 (EXPLAIN ANALYZE)
- [ ] 인덱스 정상 작동 확인

### H. 배포 준비
- [ ] 스테이징 환경 테스트
- [ ] 롤백 스크립트 준비
- [ ] 배포 문서 작성

---

## ✅ 성공 기준

1. **기능 완전성**: tm_work의 모든 85개 파일 기능이 dw_work에 통합됨
2. **아키텍처 준수**: 모든 코드가 4-Layer 규칙 준수
3. **DB 접근 제거**: Controller, UseCase, Service에서 DB 직접 접근 0건
4. **스키마 통합 완료**: 모든 테이블이 public 스키마에 존재, statedb/logdb 제거
5. **코드 정리**: 모든 코드에서 `statedb.`, `logdb.` 참조 완전 제거
6. **테스트 커버리지**: 주요 기능 80% 이상
7. **성능 유지**: 응답 시간 tm_work와 동등 이상
8. **하위 호환성**: 기존 API 엔드포인트 모두 작동

---

## 🎯 마이그레이션 진행 순서 (요약)

```
PHASE 0: DB 스키마 통합 (1일) ⭐ 최우선
  ↓
PHASE 1: DB 모델 생성 (1-2일)
  ↓
PHASE 2: Repository 구현 (2-3일)
  ↓
PHASE 3: Service 구현 (3-4일)
  ↓
PHASE 4: Agent 확장 (2-3일)
  ↓
PHASE 5: UseCase 확장 (2-3일)
  ↓
PHASE 6: Controller 생성 (2-3일)
  ↓
PHASE 7: Core/Utils 정리 (2-3일)
  ↓
PHASE 8: 전체 테스트 (1-2일)
```

**이 계획대로 진행하면 tm_work의 모든 기능을 누락 없이 dw_work의 깨끗한 아키텍처로 완전히 통합할 수 있으며, DB 스키마 통합으로 인한 코드 꼬임을 방지할 수 있습니다.**