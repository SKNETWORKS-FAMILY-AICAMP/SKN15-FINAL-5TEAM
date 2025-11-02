# 15. 데이터베이스 구조 완성 및 Migration 적용

**작성일**: 2025-10-30
**작업 목적**: 장기기억 시스템과 사용자 인증을 위한 DB 테이블 구조 완성

---

## 📋 문제 상황

### 발견된 심각한 문제:
1. **Users 테이블 미생성**: 사용자 인증 시스템 코드는 있지만 DB 테이블이 없음
2. **Password Reset Tokens 테이블 미생성**: 비밀번호 재설정 기능을 위한 테이블 누락
3. **Migration 파일만 존재**: `003_users_table.sql`, `004_password_reset_tokens.sql`, `005_conversation_summary.sql` 파일은 있지만 DB에 적용되지 않음

### 영향:
- ❌ 사용자 로그인/회원가입 불가능
- ❌ 비밀번호 재설정 불가능
- ❌ 세션과 사용자 연결 불가능
- ⚠️ 장기기억 데이터가 저장되지 않을 수 있음

---

## 🔧 해결 작업

### 1️⃣ 데이터베이스 현황 분석

```bash
# 기존 테이블 확인
docker exec -i kime-postgres psql -U kime -d kimedb -c "\dt statedb.*"
```

**기존 테이블 (Migration 적용 전)**:
- `affinity_records` - 친밀도 기록
- `dialogues` - 대화 기록
- `game_events` - 게임 이벤트
- `mission_records` - 미션 기록
- `session_snapshots` - 세션 스냅샷
- `sessions` - 세션 메타데이터
- `stage_progression` - 스테이지 진행
- `user_inputs` - 사용자 입력

**누락된 테이블**:
- ❌ `users` - 사용자 계정 정보
- ❌ `password_reset_tokens` - 비밀번호 재설정 토큰

---

### 2️⃣ Migration 파일 적용

#### ✅ 003_users_table.sql 적용

```bash
docker exec -i kime-postgres psql -U kime -d kimedb \
  < database/migrations/003_users_table.sql
```

**생성된 구조**:

```sql
CREATE TABLE statedb.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    provider VARCHAR(50) DEFAULT 'email',
    display_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);
```

**인덱스**:
- `idx_users_username` - username 검색
- `idx_users_email` - email 검색
- `idx_users_provider` - provider 필터링
- `idx_users_active` - 활성 사용자 필터링
- `idx_users_created` - 생성일 정렬

**추가된 외래키**:
```sql
ALTER TABLE statedb.sessions
ADD COLUMN user_id UUID REFERENCES statedb.users(user_id) ON DELETE SET NULL;
```

**테스트 계정 생성**:
| Username | Password | Display Name |
|----------|----------|--------------|
| tanjiro  | 123      | 탄지로       |
| zenitsu  | 123      | 젠이츠       |
| inosuke  | 123      | 이노스케     |
| giyu     | 123      | 기유         |
| rengoku  | 123      | 렌고쿠       |
| tengen   | 123      | 텐겐         |

---

#### ✅ 004_password_reset_tokens.sql 적용

```bash
docker exec -i kime-postgres psql -U kime -d kimedb \
  < database/migrations/004_password_reset_tokens.sql
```

**생성된 구조**:

```sql
CREATE TABLE statedb.password_reset_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    used_at TIMESTAMP
);
```

**인덱스**:
- `idx_reset_tokens_token` - 토큰 검색 (UNIQUE)
- `idx_reset_tokens_user` - 사용자별 토큰 조회
- `idx_reset_tokens_expires` - 만료된 토큰 정리

**자동 정리 함수**:
```sql
CREATE OR REPLACE FUNCTION clean_expired_reset_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM statedb.password_reset_tokens
    WHERE expires_at < NOW() OR used_at IS NOT NULL;
END;
$$ LANGUAGE plpgsql;
```

---

#### ✅ 005_conversation_summary.sql 확인

**이미 적용된 필드** (이전 작업에서 완료):
```sql
ALTER TABLE statedb.sessions
ADD COLUMN conversation_summary TEXT DEFAULT '',
ADD COLUMN summary_updated_at TIMESTAMP,
ADD COLUMN summary_turn_count INT DEFAULT 0;
```

---

### 3️⃣ 최종 데이터베이스 구조

```bash
# 모든 테이블 확인
docker exec -i kime-postgres psql -U kime -d kimedb -c "\dt statedb.*"
```

**완성된 테이블 목록** (총 10개):
```
statedb.affinity_records       - 친밀도 기록
statedb.dialogues              - 대화 기록
statedb.game_events            - 게임 이벤트
statedb.mission_records        - 미션 기록
statedb.password_reset_tokens  - ✨ 비밀번호 재설정 토큰 (신규)
statedb.session_snapshots      - 세션 스냅샷
statedb.sessions               - 세션 메타데이터
statedb.stage_progression      - 스테이지 진행
statedb.user_inputs            - 사용자 입력
statedb.users                  - ✨ 사용자 계정 (신규)
```

---

### 4️⃣ sessions 테이블 구조 (최종)

```sql
\d statedb.sessions
```

**핵심 컬럼**:

| 컬럼명 | 타입 | 설명 | 카테고리 |
|--------|------|------|----------|
| session_id | UUID | 세션 ID (PK) | 기본 |
| scenario_id | VARCHAR | 시나리오 ID | 기본 |
| user_name | VARCHAR | 사용자 이름 | 기본 |
| **user_id** | **UUID** | **사용자 ID (FK)** | **🆕 인증** |
| current_stage | VARCHAR | 현재 스테이지 | 진행 |
| turn_count | INTEGER | 총 턴 수 | 진행 |
| stage_turn | INTEGER | 스테이지 턴 수 | 진행 |
| **conversation_summary** | **TEXT** | **대화 요약** | **🧠 장기기억** |
| **summary_turn_count** | **INTEGER** | **요약 턴 카운트** | **🧠 장기기억** |
| **summary_updated_at** | **TIMESTAMP** | **요약 업데이트 시간** | **🧠 장기기억** |
| is_active | BOOLEAN | 활성 상태 | 상태 |
| created_at | TIMESTAMP | 생성 시간 | 메타 |
| updated_at | TIMESTAMP | 업데이트 시간 | 메타 |

**외래키 관계**:
```
sessions.user_id → users.user_id (ON DELETE SET NULL)
```

**인덱스**:
- `sessions_pkey` - session_id (PRIMARY KEY)
- `idx_sessions_active` - is_active (활성 세션 필터)
- `idx_sessions_created` - created_at (생성일 정렬)
- `idx_sessions_scenario` - scenario_id (시나리오별 조회)
- `idx_sessions_user` - user_id (사용자별 세션 조회)

---

## 📊 데이터베이스 ERD (관계도)

```
┌─────────────────┐
│     users       │
│─────────────────│
│ user_id (PK)    │◄──┐
│ username        │   │
│ email           │   │
│ password_hash   │   │
│ provider        │   │
│ is_active       │   │
└─────────────────┘   │
         △            │
         │            │
         │ (FK)       │ (FK)
         │            │
┌─────────────────┐   │
│   sessions      │───┘
│─────────────────│
│ session_id (PK) │
│ user_id (FK)    │◄────────────┐
│ scenario_id     │             │
│ user_name       │             │
│ turn_count      │             │
│ conversation_   │             │
│   summary       │ 🧠          │
│ summary_turn_   │             │
│   count         │ 🧠          │
└─────────────────┘             │
         △                      │
         │                      │
         │ (FK)                 │ (FK)
         ├──────────────────────┤
         │                      │
┌─────────────────┐  ┌──────────────────┐
│ session_        │  │ password_reset_  │
│   snapshots     │  │   tokens         │
│─────────────────│  │──────────────────│
│ snapshot_id(PK) │  │ token_id (PK)    │
│ session_id (FK) │  │ user_id (FK)     │
│ state_data      │  │ token            │
│ created_at      │  │ expires_at       │
└─────────────────┘  │ used_at          │
                     └──────────────────┘
```

---

## 🧪 검증 및 테스트

### 1. 사용자 계정 확인

```sql
SELECT
    username,
    email,
    provider,
    display_name,
    is_active
FROM statedb.users;
```

**결과**:
```
username | email | provider | display_name | is_active
---------|-------|----------|--------------|----------
tanjiro  |       | email    | 탄지로       | t
zenitsu  |       | email    | 젠이츠       | t
inosuke  |       | email    | 이노스케     | t
giyu     |       | email    | 기유         | t
rengoku  |       | email    | 렌고쿠       | t
tengen   |       | email    | 텐겐         | t
```
✅ 6개의 테스트 계정 정상 생성

---

### 2. sessions 테이블 구조 확인

```sql
\d statedb.sessions
```

**확인 사항**:
- ✅ `user_id` 컬럼 존재
- ✅ `conversation_summary` 컬럼 존재
- ✅ `summary_turn_count` 컬럼 존재
- ✅ `summary_updated_at` 컬럼 존재
- ✅ `users` 테이블로의 외래키 설정

---

### 3. password_reset_tokens 테이블 확인

```sql
\d statedb.password_reset_tokens
```

**확인 사항**:
- ✅ 테이블 존재
- ✅ `user_id` 외래키 설정
- ✅ `token` UNIQUE 제약조건
- ✅ 인덱스 정상 생성
- ✅ 자동 정리 함수 생성

---

## 🔍 DBeaver 접속 정보

이제 DBeaver에서 완성된 데이터베이스 구조를 확인할 수 있습니다:

```
Host: localhost
Port: 5433
Database: kimedb
Username: kime
Password: dev123
```

**확인할 스키마**: `statedb`

**주요 테이블**:
1. `users` - 사용자 계정 (6개 테스트 계정 포함)
2. `password_reset_tokens` - 비밀번호 재설정
3. `sessions` - 세션 + 장기기억 + 사용자 연결

---

## 📈 기능별 테이블 매핑

### 🔐 사용자 인증 시스템
```
users                    → 계정 정보
password_reset_tokens    → 비밀번호 재설정
sessions.user_id         → 세션-사용자 연결
```

### 🧠 장기기억 시스템
```
sessions.conversation_summary    → 대화 요약 저장
sessions.summary_turn_count      → 요약된 턴 수
sessions.summary_updated_at      → 요약 업데이트 시간
```

### 💾 세션 관리
```
sessions                 → 세션 메타데이터
session_snapshots        → 전체 상태 스냅샷
user_inputs             → 사용자 입력 기록
dialogues               → 대화 기록
```

### ❤️ 게임 데이터
```
affinity_records        → 친밀도 기록
mission_records         → 미션 진행
stage_progression       → 스테이지 진행
game_events            → 게임 이벤트
```

---

## 🎯 다음 단계

### 1. API 서버 연동 확인
- [ ] 사용자 등록 API 테스트
- [ ] 로그인 API 테스트
- [ ] 세션-사용자 연결 테스트
- [ ] 장기기억 자동 저장 테스트

### 2. 데이터 저장 검증
- [ ] 10턴 이상 대화 후 요약 생성 확인
- [ ] DBeaver에서 `conversation_summary` 데이터 확인
- [ ] 사용자 로그인 후 `user_id` 연결 확인

### 3. 성능 최적화
- [ ] 인덱스 사용률 분석
- [ ] 쿼리 성능 모니터링
- [ ] 만료된 토큰 자동 정리 스케줄링

---

## 📚 관련 파일

### Migration 파일
- `backend/database/migrations/001_initial_schema.sql` - 초기 스키마
- `backend/database/migrations/002_logdb_training_logs.sql` - 학습 로그
- `backend/database/migrations/003_users_table.sql` - **사용자 테이블**
- `backend/database/migrations/004_password_reset_tokens.sql` - **비밀번호 재설정**
- `backend/database/migrations/005_conversation_summary.sql` - **장기기억**

### 관련 코드
- `backend/src/database/db_manager.py` - DB 매니저
- `backend/src/utils/conversation_summarizer.py` - 대화 요약
- `backend/src/core/graph_state.py` - 상태 정의
- `backend/api_server.py` - API 서버

---

## ✅ 작업 완료 요약

### 해결된 문제
1. ✅ **users 테이블 생성** - 사용자 인증 기반 마련
2. ✅ **password_reset_tokens 테이블 생성** - 비밀번호 재설정 기능
3. ✅ **sessions.user_id 외래키** - 세션과 사용자 연결
4. ✅ **장기기억 필드 확인** - conversation_summary 등 정상 존재
5. ✅ **테스트 계정 생성** - 6개 계정 즉시 사용 가능

### 현재 상태
- 🗄️ **PostgreSQL**: 10개 테이블, 완전한 스키마
- 🔐 **인증**: 사용자 계정 시스템 준비 완료
- 🧠 **장기기억**: DB 구조 완성
- ✅ **모든 Migration 적용 완료**

---

**작성자**: Claude (AI Assistant)
**검토 필요 사항**: 실제 사용자 로그인 및 장기기억 데이터 저장 테스트
