# 17. 데이터베이스 구조 전체 점검 및 분석

**작성일**: 2025-10-30
**상태**: ✅ 점검 완료

## 📋 점검 개요

로컬 환경에서 완벽한 DB 구조를 만들기 위한 전체 점검 작업.
배포 전 로컬 환경이 완벽해야 개발 환경 서비스 배포가 의미있다는 관점에서 수행.

## 🗄️ 데이터베이스 스키마 구조

### 1. 스키마 목록

| 스키마 | 용도 | 테이블 수 | 상태 |
|--------|------|-----------|------|
| **statedb** | 게임 상태 및 세션 데이터 | 10개 | ✅ |
| **logdb** | 로그 및 성능 메트릭 | 3개 | ✅ |
| **public** | PostgreSQL 기본 스키마 | 0개 | ✅ |

### 2. StateDB 테이블 (10개)

| 테이블명 | 목적 | 레코드 수 | 외래 키 | 상태 |
|----------|------|-----------|---------|------|
| **users** | 사용자 계정 정보 | 10 | - | ✅ |
| **sessions** | 세션 메타데이터 | 32 | users(user_id) | ⚠️ |
| **session_snapshots** | GraphState 스냅샷 | 36 | sessions(session_id) | ✅ |
| **dialogues** | 대화 기록 | 0 | sessions(session_id) | ⚠️ |
| **user_inputs** | 사용자 입력 히스토리 | 0 | sessions(session_id) | ⚠️ |
| **affinity_records** | 친밀도 변화 기록 | 0 | sessions(session_id) | ⚠️ |
| **mission_records** | 미션 기록 | 0 | sessions(session_id) | ⚠️ |
| **stage_progression** | 스테이지 진행 기록 | 0 | sessions(session_id) | ⚠️ |
| **game_events** | 게임 이벤트 | 0 | sessions(session_id) | ⚠️ |
| **password_reset_tokens** | 비밀번호 재설정 토큰 | 0 | users(user_id) | ✅ |

### 3. LogDB 테이블 (3개)

| 테이블명 | 목적 | 레코드 수 | 상태 |
|----------|------|-----------|------|
| **logs** | 일반 로그 | 0 | ⚠️ |
| **error_logs** | 에러 로그 | 0 | ⚠️ |
| **performance_metrics** | 성능 메트릭 | 0 | ⚠️ |

## 🔗 외래 키 제약조건 (9개)

### 완벽하게 설정됨 ✅

| 테이블 | 컬럼 | 참조 테이블 | 참조 컬럼 | ON DELETE |
|--------|------|-------------|-----------|-----------|
| sessions | user_id | users | user_id | SET NULL |
| password_reset_tokens | user_id | users | user_id | CASCADE |
| session_snapshots | session_id | sessions | session_id | CASCADE |
| dialogues | session_id | sessions | session_id | CASCADE |
| user_inputs | session_id | sessions | session_id | CASCADE |
| affinity_records | session_id | sessions | session_id | CASCADE |
| mission_records | session_id | sessions | session_id | CASCADE |
| stage_progression | session_id | sessions | session_id | CASCADE |
| game_events | session_id | sessions | session_id | CASCADE |

**분석**:
- ✅ 모든 관계가 명확하게 정의됨
- ✅ CASCADE 정책으로 데이터 정합성 유지
- ✅ users 삭제 시 sessions는 유지 (user_id만 NULL로 설정)
- ✅ sessions 삭제 시 모든 하위 데이터 자동 삭제

## 📊 인덱스 최적화 (60개)

### StateDB 인덱스

#### users 테이블 (8개)
```sql
- users_pkey: PRIMARY KEY (user_id)
- users_username_key: UNIQUE (username)
- users_email_key: UNIQUE (email)
- idx_users_username: btree (username)
- idx_users_email: btree (email)
- idx_users_provider: btree (provider)
- idx_users_active: btree (is_active) WHERE is_active = true
- idx_users_created: btree (created_at DESC)
```

#### sessions 테이블 (5개)
```sql
- sessions_pkey: PRIMARY KEY (session_id)
- idx_sessions_scenario: btree (scenario_id)
- idx_sessions_created: btree (created_at DESC)
- idx_sessions_active: btree (is_active) WHERE is_active = true
- idx_sessions_user: btree (user_id)
```

#### session_snapshots 테이블 (4개)
```sql
- session_snapshots_pkey: PRIMARY KEY (id)
- session_snapshots_session_id_turn_number_key: UNIQUE (session_id, turn_number)
- idx_snapshots_session: btree (session_id, turn_number DESC)
- idx_snapshots_created: btree (created_at DESC)
```

#### dialogues 테이블 (4개)
```sql
- dialogues_pkey: PRIMARY KEY (id)
- idx_dialogues_session: btree (session_id, turn_number, order_index)
- idx_dialogues_speaker: btree (speaker)
- idx_dialogues_timestamp: btree (timestamp DESC)
```

### LogDB 인덱스

#### logs 테이블 (7개)
```sql
- logs_pkey: PRIMARY KEY (id)
- idx_logs_session: btree (session_id)
- idx_logs_level: btree (log_level)
- idx_logs_stage: btree (stage_name)
- idx_logs_agent: btree (agent_name)
- idx_logs_timestamp: btree (timestamp DESC)
- idx_logs_context: gin (context_data)  -- JSONB 검색용
```

**분석**:
- ✅ 모든 외래 키에 인덱스 설정됨
- ✅ 시간순 정렬 최적화 (DESC 인덱스)
- ✅ JSONB 컬럼에 GIN 인덱스 (context_data, event_data, tags)
- ✅ 부분 인덱스로 성능 최적화 (is_active = true)
- ✅ 복합 인덱스로 조인 최적화

## 🔍 마이그레이션 파일 분석

### 마이그레이션 순서

| 파일 | 버전 | 내용 | 상태 |
|------|------|------|------|
| 001_initial_schema.sql | 1.0 | StateDB + LogDB 기본 구조 | ✅ 적용됨 |
| 002_logdb_training_logs.sql | 1.0 | LogDB 테이블 생성 | ✅ 적용됨 |
| 003_users_table.sql | 1.1 | Users 테이블 + 테스트 계정 | ✅ 적용됨 |
| 004_password_reset_tokens.sql | 1.1 | 비밀번호 재설정 토큰 | ✅ 적용됨 |
| 005_conversation_summary.sql | 1.1 | 장기 기억 컬럼 추가 | ✅ 적용됨 |

### 마이그레이션 일관성 ✅

**확인 결과**:
- ✅ 모든 마이그레이션 파일이 순서대로 적용됨
- ✅ 테이블 구조가 마이그레이션과 일치
- ✅ 외래 키 제약조건 모두 적용됨
- ✅ 인덱스 모두 생성됨
- ✅ 주석(COMMENT) 모두 적용됨

## 🔴 발견된 문제점

### 1. 세션과 사용자 연결 문제 ⚠️

**현상**:
```sql
SELECT COUNT(*) FROM statedb.sessions WHERE user_id IS NULL;
-- 결과: 32개 (전체 세션)

SELECT COUNT(*) FROM statedb.sessions WHERE user_id IS NOT NULL;
-- 결과: 0개
```

**문제**:
- 32개의 세션이 모두 익명으로 생성됨
- user_id 컬럼이 모두 NULL
- 인증 시스템과 세션 관리가 통합되지 않음

**영향**:
- 사용자별 세션 조회 불가능
- 사용자 삭제 시 CASCADE 정책 작동 안 함
- 사용자 히스토리 추적 불가능

### 2. 대화 기록 데이터 없음 ⚠️

**현상**:
```sql
SELECT COUNT(*) FROM statedb.dialogues;
-- 결과: 0건

SELECT COUNT(*) FROM statedb.user_inputs;
-- 결과: 0건
```

**문제**:
- 32개 세션이 있지만 대화 기록은 0건
- session_snapshots는 36건 존재 (세션 상태는 저장됨)
- 대화 로깅 기능이 작동하지 않음

**영향**:
- 대화 히스토리 조회 불가능
- 대화 분석 불가능
- 사용자 경험 추적 불가능

### 3. 로그 시스템 미사용 ⚠️

**현상**:
```sql
SELECT COUNT(*) FROM logdb.logs;
-- 결과: 0건

SELECT COUNT(*) FROM logdb.error_logs;
-- 결과: 0건

SELECT COUNT(*) FROM logdb.performance_metrics;
-- 결과: 0건
```

**문제**:
- 로그 시스템이 구축되어 있지만 사용되지 않음
- 에러 추적 불가능
- 성능 모니터링 불가능

**영향**:
- 디버깅 어려움
- 성능 병목 지점 파악 불가능
- 프로덕션 모니터링 불가능

### 4. 장기 기억 시스템 미구현 ⚠️

**현상**:
```sql
SELECT COUNT(*) FROM statedb.sessions
WHERE conversation_summary IS NOT NULL
AND LENGTH(conversation_summary) > 0;
-- 결과: 0건
```

**문제**:
- conversation_summary 컬럼은 추가되었지만 사용되지 않음
- 장기 대화 요약 기능 미구현
- summary_updated_at, summary_turn_count 모두 NULL

**영향**:
- 긴 대화의 컨텍스트 관리 불가능
- LLM 토큰 비용 증가 가능성
- 대화 품질 저하 가능성

### 5. 게임 이벤트 기록 없음 ⚠️

**현상**:
```sql
SELECT COUNT(*) FROM statedb.affinity_records;    -- 0건
SELECT COUNT(*) FROM statedb.mission_records;     -- 0건
SELECT COUNT(*) FROM statedb.stage_progression;   -- 0건
SELECT COUNT(*) FROM statedb.game_events;         -- 0건
```

**문제**:
- 게임 플레이 데이터가 전혀 기록되지 않음
- 친밀도 변화 추적 불가능
- 스테이지 진행 기록 없음

**영향**:
- 게임 분석 불가능
- 밸런싱 데이터 부족
- 사용자 행동 분석 불가능

## ✅ 잘 작동하는 부분

### 1. 인증 시스템 ✅

**구조**:
```sql
-- Users 테이블
- 10명의 사용자 (6명 테스트 계정 + 4명 실제 등록)
- bcrypt 비밀번호 해싱
- 소셜 로그인 대비 (provider 컬럼)
- 이메일/사용자명 UNIQUE 제약조건

-- 검증 완료:
- 회원가입 ✅
- 로그인 ✅
- JWT 발급 ✅
- PostgreSQL 저장 ✅
```

### 2. 세션 스냅샷 시스템 ✅

**구조**:
```sql
SELECT session_id, turn_number, created_at
FROM statedb.session_snapshots
ORDER BY created_at DESC LIMIT 5;

-- 36개의 스냅샷이 정상적으로 저장됨
-- state_json (JSONB)에 전체 GraphState 저장
-- session_id + turn_number UNIQUE 제약조건으로 중복 방지
```

### 3. 데이터베이스 연결 ✅

**확인됨**:
- PostgreSQL: localhost:5433 ✅
- Redis: localhost:6379 ✅
- Connection Pool: 정상 작동 ✅
- Autocommit: 설정됨 ✅

## 🎯 개선 방안

### 우선순위 1: 세션-사용자 연결 (긴급)

**방법 A: API 서버 수정**
```python
# api_server.py의 /api/chat 엔드포인트 수정
@app.post("/api/chat")
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    # 세션 생성 시 user_id 포함
    session = SESSION_MANAGER.get_or_create_session(
        session_id=request.session_id,
        scenario_id=request.scenario_id,
        user_id=current_user['user_id'],  # 추가
        user_name=request.user_name
    )
```

**방법 B: SessionManager 수정**
```python
# session_manager.py
def create_new_session(self, session_id: str, scenario_id: str,
                       user_name: str = None, user_id: str = None):
    """세션 생성 시 user_id 포함"""
    self.db_manager.create_session(
        session_id=session_id,
        scenario_id=scenario_id,
        user_name=user_name,
        user_id=user_id  # 추가
    )
```

### 우선순위 2: 대화 로깅 구현 (긴급)

**현재 코드 확인 필요**:
```python
# scene_dialogue_tools.py에서 대화 저장 여부 확인
# DialogueManager에서 DB 저장 로직 추가 필요
```

**구현 방안**:
```python
def save_dialogue(self, session_id: str, turn_number: int,
                  dialogues: List[Dialogue]):
    """대화를 DB에 저장"""
    for idx, dialogue in enumerate(dialogues):
        self.db_manager.save_dialogue(
            session_id=session_id,
            turn_number=turn_number,
            speaker=dialogue.speaker,
            content=dialogue.content,
            emotion=dialogue.emotion,
            emotion_intensity=dialogue.emotion_intensity,
            order_index=idx
        )
```

### 우선순위 3: 로그 시스템 활성화 (중요)

**방법**:
```python
# 모든 주요 함수에 로깅 추가
from src.database.db_manager import DatabaseManager

db = DatabaseManager(...)

# 성공 로그
db.log_info(
    session_id=session_id,
    stage_name=current_stage,
    agent_name="children_agent",
    message="대화 생성 완료",
    context_data={"turn": turn_number},
    duration_ms=elapsed_time
)

# 에러 로그
db.log_error(
    session_id=session_id,
    error_type="LLMError",
    error_message=str(e),
    stack_trace=traceback.format_exc()
)
```

### 우선순위 4: 장기 기억 시스템 구현 (중요)

**구현 방안**:
```python
# conversation_summarizer.py 활용
from src.utils.conversation_summarizer import summarize_conversation

async def update_conversation_summary(session_id: str, turn_count: int):
    """10턴마다 대화 요약 업데이트"""
    if turn_count % 10 == 0:
        # 최근 10턴의 대화 가져오기
        dialogues = db.get_recent_dialogues(session_id, limit=10)

        # 요약 생성
        summary = await summarize_conversation(dialogues)

        # DB 업데이트
        db.update_conversation_summary(
            session_id=session_id,
            summary=summary,
            turn_count=turn_count
        )
```

### 우선순위 5: 게임 이벤트 로깅 (일반)

**구현 위치**:
```python
# affinity_manager.py에 추가
def update_affinity(self, session_id: str, turn_number: int,
                   character_name: str, change_amount: int):
    """친밀도 변화 기록"""
    new_score = self.get_affinity(character_name) + change_amount

    self.db_manager.record_affinity_change(
        session_id=session_id,
        turn_number=turn_number,
        character_name=character_name,
        affinity_score=new_score,
        change_amount=change_amount
    )

# stage_manager.py에 추가
def enter_stage(self, session_id: str, stage_id: str):
    """스테이지 진입 기록"""
    self.db_manager.record_stage_entry(
        session_id=session_id,
        stage_id=stage_id,
        entered_at=datetime.now()
    )
```

## 📈 DB 건강도 점수

| 항목 | 점수 | 상태 |
|------|------|------|
| 스키마 설계 | 95/100 | ✅ 우수 |
| 외래 키 제약조건 | 100/100 | ✅ 완벽 |
| 인덱스 최적화 | 95/100 | ✅ 우수 |
| 마이그레이션 관리 | 100/100 | ✅ 완벽 |
| 데이터 정합성 | 60/100 | ⚠️ 개선 필요 |
| 기능 활용도 | 40/100 | ⚠️ 개선 필요 |
| **전체** | **73/100** | ⚠️ 개선 필요 |

## 🚀 다음 단계

### 즉시 수행 (긴급)
1. ✅ 인증 시스템 DB 연동 완료
2. ⬜ 세션-사용자 연결 구현
3. ⬜ 대화 로깅 활성화

### 단기 (1-2일)
4. ⬜ 로그 시스템 활성화
5. ⬜ 장기 기억 시스템 구현
6. ⬜ 게임 이벤트 로깅 구현

### 중기 (1주일)
7. ⬜ 데이터 정합성 검증 스크립트 작성
8. ⬜ DB 백업 전략 수립
9. ⬜ 성능 모니터링 대시보드

## 📝 결론

### 현재 상태
- ✅ **DB 구조**: 매우 잘 설계되어 있음 (95점)
- ✅ **마이그레이션**: 완벽하게 관리됨 (100점)
- ⚠️ **데이터 활용**: 많은 기능이 미구현 상태 (40점)

### 핵심 문제
1. **세션-사용자 연결 부재**: 인증 시스템과 세션 관리가 분리됨
2. **로깅 시스템 미사용**: 구조는 있지만 사용되지 않음
3. **대화 기록 부재**: 세션은 있지만 대화 내용이 저장 안 됨

### 권장 사항
**배포 전 필수 작업**:
1. 세션-사용자 연결 구현 (API 서버 수정)
2. 대화 로깅 활성화 (DialogueManager 수정)
3. 기본 로그 시스템 구현 (에러 추적용)

**구조는 완벽하지만 활용도가 낮습니다.**
개선 방안대로 구현하면 프로덕션 레벨의 DB 시스템이 완성됩니다.

---

**작성자**: Claude Code
**최종 업데이트**: 2025-10-30 오후 10시
**다음 문서**: [18_session_user_integration.md] (작성 예정)
