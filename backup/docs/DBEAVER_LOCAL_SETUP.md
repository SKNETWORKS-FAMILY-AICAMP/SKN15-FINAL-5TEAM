# DBeaver 로컬 PostgreSQL 연결 가이드

## 📊 로컬 DB 정보 (확인 완료!)

### Docker PostgreSQL Container
```
Container Name: kime-postgres
Image:         pgvector/pgvector:pg15
Status:        Up 2 days (healthy) ✅
Port Mapping:  0.0.0.0:5433 -> 5432
```

### 연결 정보
```
Host:     localhost
Port:     5433
Database: kimedb
Username: kime
Password: dev123
```

---

## 🔧 DBeaver 연결 설정 (단계별)

### Step 1: 새 데이터베이스 연결 만들기

1. DBeaver 실행
2. 좌측 상단 **"새 데이터베이스 연결"** 버튼 클릭 (플러그 🔌 아이콘)
3. **PostgreSQL** 선택
4. **다음** 클릭

---

### Step 2: 연결 정보 입력

**Main 탭에서 입력**:
```
Server Host:    localhost
Port:           5433
Database:       kimedb
Username:       kime
Password:       dev123
```

**중요 설정**:
- [x] **Show all databases** 체크 해제 (kimedb만 보기)
- [x] **Save password** 체크 (비밀번호 저장)

---

### Step 3: SSL 설정 (로컬은 불필요)

**PostgreSQL 탭 → SSL**:
```
SSL mode:       disable
```

로컬 Docker 컨테이너는 SSL이 필요 없습니다.

---

### Step 4: 연결 테스트

1. 좌측 하단 **"Test Connection"** 버튼 클릭
2. ✅ **"Connected"** 메시지 확인
3. **완료** 클릭

---

## 📊 연결 후 확인할 데이터

### 데이터베이스 구조

```
kime-postgres (localhost:5433)
 └── Databases
      └── kimedb
           └── Schemas
                ├── statedb          ← 메인 애플리케이션 데이터
                │    └── Tables
                │         ├── users
                │         ├── chat_sessions
                │         ├── dialogues
                │         ├── user_memories
                │         ├── user_progression
                │         ├── user_equipment
                │         ├── scenarios
                │         ├── scenes
                │         └── scene_dialogues
                └── logdb            ← 로깅 데이터
                     └── Tables
                          └── training_logs
```

---

## 🔍 유용한 쿼리

### 1. 전체 사용자 목록
```sql
SELECT user_id, username, display_name, email, created_at
FROM statedb.users
ORDER BY created_at DESC;
```

### 2. 최근 대화 세션
```sql
SELECT
    s.session_id,
    u.username,
    s.scenario_id,
    s.current_scene,
    s.created_at,
    COUNT(d.dialogue_id) as message_count
FROM statedb.chat_sessions s
LEFT JOIN statedb.users u ON s.user_id = u.user_id
LEFT JOIN statedb.dialogues d ON s.session_id = d.session_id
GROUP BY s.session_id, u.username, s.scenario_id, s.current_scene, s.created_at
ORDER BY s.created_at DESC
LIMIT 20;
```

### 3. 사용자 장기 기억 확인
```sql
SELECT
    u.username,
    um.memory_key,
    um.memory_value,
    um.memory_type,
    um.created_at
FROM statedb.user_memories um
LEFT JOIN statedb.users u ON um.user_id = u.user_id
ORDER BY um.created_at DESC
LIMIT 50;
```

### 4. 사용자 진행도 확인
```sql
SELECT
    u.username,
    u.display_name,
    up.rank_code,
    up.level,
    up.experience_points,
    up.total_messages,
    up.total_sessions,
    ue.sword_status,
    ue.uniform_status,
    ue.crow_status
FROM statedb.users u
LEFT JOIN statedb.user_progression up ON u.user_id = up.user_id
LEFT JOIN statedb.user_equipment ue ON u.user_id = ue.user_id
ORDER BY up.experience_points DESC;
```

### 5. 시나리오 목록
```sql
SELECT
    scenario_id,
    title_ko,
    description_ko,
    difficulty,
    estimated_duration_minutes,
    is_active
FROM statedb.scenarios
ORDER BY display_order;
```

### 6. 대화 메시지 내용 보기
```sql
SELECT
    d.timestamp,
    u.username,
    d.role,
    d.content,
    d.token_count
FROM statedb.dialogues d
LEFT JOIN statedb.chat_sessions s ON d.session_id = s.session_id
LEFT JOIN statedb.users u ON s.user_id = u.user_id
ORDER BY d.timestamp DESC
LIMIT 50;
```

---

## ❌ 트러블슈팅

### 문제 1: "Connection refused" 오류

**원인**: PostgreSQL 컨테이너가 실행되지 않음

**확인**:
```bash
docker ps | grep postgres
```

**해결**:
```bash
# Docker 컨테이너 시작
docker start kime-postgres

# 또는 docker-compose로 시작
cd /Users/jtm427/Desktop/workspace
docker-compose up -d postgres
```

---

### 문제 2: "Authentication failed" 오류

**원인**: 잘못된 비밀번호

**해결**:
```
Username: kime
Password: dev123
```

정확히 입력하세요 (대소문자 구분)

---

### 문제 3: "Database does not exist" 오류

**원인**: 데이터베이스가 생성되지 않음

**해결**:
```bash
# 컨테이너 접속
docker exec -it kime-postgres psql -U kime

# 데이터베이스 목록 확인
\l

# kimedb가 없으면 생성
CREATE DATABASE kimedb;
```

---

### 문제 4: "Connection timeout" 오류

**원인**: 포트가 잘못됨

**확인**:
```bash
lsof -i:5433
```

**해결**:
- DBeaver에서 Port를 **5433**으로 정확히 입력
- 5432가 아닙니다! (5432는 컨테이너 내부 포트)

---

## 🆚 로컬 vs RDS 비교

### 로컬 PostgreSQL (5433)
```
Host:     localhost
Port:     5433
Database: kimedb
Username: kime
Password: dev123
SSL:      disable

용도: 개발 및 테스트
장점: 빠른 속도, 무료
단점: 로컬에서만 접근 가능
```

### AWS RDS (5432)
```
Host:     kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com
Port:     5432
Database: kimedb
Username: kime
Password: jnhzlsyihvxwfhvz
SSL:      require

용도: 프로덕션 배포
장점: 외부 접근, 고가용성, 백업
단점: 비용 발생, 보안 그룹 설정 필요
```

---

## 📋 빠른 체크리스트

DBeaver 로컬 연결 전 확인:
- [x] Docker 실행 중
- [x] kime-postgres 컨테이너 실행 중 (Up 2 days)
- [x] Port 5433 열림
- [ ] DBeaver PostgreSQL 드라이버 설치됨
- [ ] 연결 정보 정확히 입력
- [ ] SSL mode: disable 설정
- [ ] Test Connection 성공

---

## 🎯 연결 테스트 (터미널에서)

DBeaver 연결 전에 터미널에서 먼저 테스트해보세요:

```bash
# psql로 직접 연결
PGPASSWORD=dev123 psql -h localhost -p 5433 -U kime -d kimedb

# 연결 성공 시
kimedb=> \dt statedb.*

# 사용자 목록 확인
kimedb=> SELECT username FROM statedb.users;

# 종료
kimedb=> \q
```

**성공 메시지**:
```
psql (15.x)
Type "help" for help.

kimedb=>
```

---

## 📖 데모 쿼리 파일 사용

프로젝트에 준비된 쿼리 파일 사용:

**위치**: [backend/demo_queries/](backend/demo_queries/)

**DBeaver에서 실행**:
1. SQL Editor 열기 (SQL 아이콘)
2. 파일 → 열기 → 쿼리 파일 선택
3. 실행 (Ctrl + Enter 또는 ▶️ 버튼)

**사용 가능한 쿼리**:
- `01_session_check.sql` - 세션 확인
- `02_dialogues_check.sql` - 대화 기록
- `03_training_logs_check.sql` - 학습 로그
- `09_user_memories.sql` - 사용자 기억
- `07_overall_stats.sql` - 전체 통계

---

## 🚀 다음 단계

### 로컬 DB 연결 성공 후
1. RDS 연결도 추가 (프로덕션 모니터링용)
2. 두 연결을 동시에 관리
3. 로컬 개발 → RDS 배포 워크플로우 구축

---

**작성일**: 2025-11-03
**로컬 DB**: localhost:5433 (kime-postgres)
**컨테이너 상태**: Up 2 days (healthy) ✅
