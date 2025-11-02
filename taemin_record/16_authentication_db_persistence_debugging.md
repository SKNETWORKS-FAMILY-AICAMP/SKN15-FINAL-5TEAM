# 16. 인증 시스템 DB 저장 문제 디버깅 (완료)

**작성일**: 2025-10-30
**상태**: ✅ 해결 완료

## 📋 작업 개요

자체 회원가입/로그인 시스템을 구현하고 테스트했으나, **API를 통한 회원가입 시 PostgreSQL에 데이터가 저장되지 않는 심각한 문제** 발견.

## 🔍 문제 상황

### 증상
- ✅ API 응답: 모든 테스트 통과 (success=true, user_id 생성, JWT 토큰 발급)
- ✅ 로그인 테스트: 성공 (사용자를 어딘가에서 찾고 있음)
- ✅ 중복 방지 테스트: 성공 (사용자가 존재한다고 인식)
- ❌ PostgreSQL 조회: 0 rows (실제 DB에 저장 안 됨)

### 테스트 결과
```bash
# API 테스트 - 모두 성공
1️⃣ 회원가입 테스트: ✅ success=true, user_id 생성
2️⃣ 로그인 테스트: ✅ JWT 토큰 발급
3️⃣ 중복 방지 테스트: ✅ 정상 작동
4️⃣ 비밀번호 검증 테스트: ✅ 정상 작동
5️⃣ JWT 인증 테스트: ✅ /api/auth/me 작동

# PostgreSQL 조회 - 실패
SELECT * FROM statedb.users WHERE username LIKE 'testuser%';
-- 결과: 0 rows
```

## 🔧 수행한 디버깅 작업

### 1. 데이터베이스 포트 문제 발견 및 수정 ✅

**문제**: `src/database/db_manager.py`가 잘못된 포트(5432)로 연결 시도
- Docker compose는 PostgreSQL을 **포트 5433**으로 매핑
- 코드는 기본값 **포트 5432**를 사용

**수정**: `src/database/db_manager.py:767`
```python
# Before
port=int(os.getenv("DB_PORT", "5432"))

# After
port=int(os.getenv("DB_PORT", "5433"))
```

### 2. 트랜잭션 Commit 문제 해결 시도 ✅

**문제**: Connection pool에서 트랜잭션이 제대로 commit되지 않는 것으로 의심

**수정 1**: 트랜잭션 상태 확인 및 명시적 commit
```python
@contextmanager
def get_connection(self):
    conn = self.connection_pool.getconn()
    try:
        # 트랜잭션 상태 초기화
        if conn.get_transaction_status() != extensions.TRANSACTION_STATUS_IDLE:
            conn.rollback()

        yield conn

        # 명시적 commit
        if conn.get_transaction_status() == extensions.TRANSACTION_STATUS_INTRANS:
            conn.commit()
    except Exception as e:
        if conn and not conn.closed:
            conn.rollback()
        raise
    finally:
        if conn and not conn.closed:
            self.connection_pool.putconn(conn)
```

**수정 2**: Autocommit 활성화
```python
@contextmanager
def get_connection(self):
    conn = self.connection_pool.getconn()
    try:
        # Autocommit 활성화
        if not conn.autocommit:
            conn.autocommit = True

        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn and not conn.closed:
            self.connection_pool.putconn(conn)
```

### 3. 직접 DB 테스트 - 성공! ✅

**테스트**: `test_direct_insert_verify.py` 작성 및 실행
```python
# DatabaseManager를 직접 사용한 테스트
db = create_database_manager_from_env()
user_id = db.create_user(
    username="directtest_013500409127",
    password_hash=password_hash,
    email="directtest_013500409127@test.com",
    display_name="직접테스트013500409127"
)

# 결과: ✅ PostgreSQL에 실제로 저장됨!
```

**PostgreSQL 확인**:
```sql
SELECT * FROM statedb.users WHERE username = 'directtest_013500409127';
-- 결과: 1 row (성공!)
```

### 4. 백그라운드 프로세스 문제 발견 🔴

**심각한 발견**: 무려 **28개의 백그라운드 API 서버**가 동시에 실행 중!
```bash
ps aux | grep -E "python.*api_server" | wc -l
# 결과: 28개 프로세스
```

**문제점**:
- 일부 서버는 오래된 코드(포트 5432) 사용
- 일부 서버는 새 코드(포트 5433, autocommit) 사용
- 테스트 요청이 무작위로 다른 서버로 전달될 가능성
- 로드 밸런싱이 없어 어느 서버가 요청을 처리하는지 불확실

## 📊 현재 데이터베이스 상태

```sql
SELECT username, created_at FROM statedb.users ORDER BY created_at DESC;
```

**결과**:
- 6명의 마이그레이션 테스트 계정: tanjiro, zenitsu, inosuke, giyu, rengoku, tengen
- 2명의 직접 생성 계정: directtest001, directtest_013500409127
- **0명의 API 생성 계정**: testuser들, curltest들

## 🔍 핵심 발견 사항

### ✅ 작동하는 것
1. **DatabaseManager 직접 사용**: PostgreSQL에 완벽하게 저장됨
2. **포트 5433 연결**: 수정된 코드는 올바른 포트 사용
3. **Autocommit 설정**: 코드에 추가됨
4. **API 엔드포인트**: 모든 로직이 정상 작동 (응답 성공)

### ❌ 작동하지 않는 것
1. **API 서버를 통한 사용자 생성**: PostgreSQL에 저장 안 됨
2. **테스트 계정들**: 모든 testuser, curltest 계정이 DB에 없음

### 🤔 미스터리
- **로그인 테스트가 성공**한다는 것은 `verify_user_password()`가 데이터베이스에서 사용자를 찾았다는 뜻
- **중복 방지 테스트가 성공**한다는 것은 `get_user_by_username()`이 사용자를 찾았다는 뜻
- 하지만 PostgreSQL에는 해당 사용자가 없음
- → **Connection pool 내부나 메모리 캐시에만 존재**할 가능성

## 📁 수정된 파일들

### 1. `backend/src/database/db_manager.py`

**수정 위치**: Line 12, 42-78, 767

**주요 변경사항**:
```python
# Import 추가
from psycopg2 import pool, sql, extensions

# __init__ - Connection pool 생성 (동일)
self.connection_pool = psycopg2.pool.SimpleConnectionPool(...)

# get_connection - Autocommit 활성화
@contextmanager
def get_connection(self):
    conn = self.connection_pool.getconn()
    try:
        if not conn.autocommit:
            conn.autocommit = True
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn and not conn.closed:
            self.connection_pool.putconn(conn)

# create_database_manager_from_env - 포트 수정
def create_database_manager_from_env() -> DatabaseManager:
    return DatabaseManager(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5433")),  # 5432 → 5433
        dbname=os.getenv("DB_NAME", "kimedb"),
        user=os.getenv("DB_USER", "kime"),
        password=os.getenv("DB_PASSWORD", "dev123"),
        min_conn=int(os.getenv("DB_MIN_CONN", "2")),
        max_conn=int(os.getenv("DB_MAX_CONN", "10"))
    )
```

### 2. 테스트 파일 생성

**`backend/test_auth_system.py`**: API 인증 테스트 스크립트
- 5개의 테스트 시나리오
- 회원가입, 로그인, 중복 방지, 비밀번호 검증, JWT 인증

**`backend/test_direct_db.py`**: 직접 DB 연결 테스트
- DatabaseManager 직접 사용
- 사용자 생성 및 조회 검증

**`backend/test_direct_insert_verify.py`**: 직접 삽입 및 즉시 검증
- DatabaseManager로 사용자 생성
- PostgreSQL에서 즉시 조회 확인
- ✅ 성공!

**`backend/test_api_db_connection.py`**: API 서버 DB 연결 정보 확인
- HybridSessionManager의 실제 연결 정보 출력
- 포트 5433 연결 확인

## 🎯 다음 단계 (진행 예정)

### 1. 백그라운드 프로세스 완전 종료 🔴
```bash
# 모든 API 서버 프로세스 종료
ps aux | grep -E "python.*api_server" | awk '{print $2}' | xargs kill -9

# 포트 8000 완전 정리
lsof -ti:8000 | xargs kill -9

# Python 캐시 삭제
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### 2. 단일 서버로 재테스트 🔴
- 완전히 깨끗한 환경에서 단 하나의 API 서버만 실행
- curl로 직접 API 호출
- 즉시 PostgreSQL 확인

### 3. HybridSessionManager 조사 (필요 시) 🔴
- API 서버가 실제로 어떤 DatabaseManager 인스턴스를 사용하는지 확인
- Connection pool 상태 로깅 추가
- 트랜잭션 commit 여부 명시적 로깅

### 4. 환경 변수 확인 🔴
```bash
# API 서버 시작 시 환경 변수 출력
echo "DB_PORT: ${DB_PORT:-5432}"
echo "DB_HOST: ${DB_HOST:-localhost}"
```

## 🔬 추가 디버깅 아이디어

1. **로깅 레벨 변경**: db_manager.py의 logger를 DEBUG 모드로 변경
2. **Connection pool 모니터링**: 각 연결의 상태 추적
3. **Transaction isolation level 확인**: PostgreSQL의 격리 수준 확인
4. **다른 터미널에서 직접 실행**: 백그라운드 프로세스 문제 회피

## 📈 진행 상황

- [x] 문제 발견 및 재현
- [x] 데이터베이스 포트 문제 수정
- [x] 트랜잭션 commit 로직 개선
- [x] Autocommit 활성화
- [x] 직접 DB 테스트 성공
- [x] 백그라운드 프로세스 문제 발견
- [ ] 백그라운드 프로세스 완전 종료
- [ ] 단일 서버로 최종 테스트
- [ ] 문제 해결 확인

## 💡 학습 내용

### PostgreSQL Connection Pool
- `SimpleConnectionPool`: 간단한 연결 풀 구현
- `getconn()`/`putconn()`: 연결 가져오기/반환
- **Autocommit 모드**: 각 SQL 문이 즉시 commit됨
- **Transaction 상태**: IDLE, INTRANS, INERROR, UNKNOWN

### psycopg2 Extensions
```python
from psycopg2 import extensions

# 트랜잭션 상태 확인
conn.get_transaction_status()
# - TRANSACTION_STATUS_IDLE: 트랜잭션 없음
# - TRANSACTION_STATUS_INTRANS: 트랜잭션 진행 중
```

### Autocommit vs Manual Commit
```python
# Manual commit (기존)
conn.commit()  # 명시적으로 commit 필요

# Autocommit (수정)
conn.autocommit = True  # 각 SQL 문이 자동으로 commit
```

## ⚠️ 주의사항

1. **백그라운드 프로세스 관리**: 여러 서버가 동시에 실행되면 예측 불가능한 동작
2. **Python 캐시**: .pyc 파일이 오래된 코드를 캐시할 수 있음
3. **Connection pool 재사용**: 연결이 재사용될 때 상태 초기화 필요
4. **Auto-reload 주의**: Uvicorn의 auto-reload가 제대로 작동하지 않을 수 있음

## 🔗 관련 문서

- [15_database_structure_complete.md](./15_database_structure_complete.md): 데이터베이스 구조 및 마이그레이션
- [Phase 6-8 Authentication System](../documents/architecture/phase6-8_authentication_system.md): 인증 시스템 설계
- PostgreSQL 공식 문서: https://www.postgresql.org/docs/
- psycopg2 공식 문서: https://www.psycopg.org/docs/

---

## 🔬 최종 디버깅 작업 (2025-10-30 오후)

### 5. 시스템 재부팅 및 환경 정리 ✅

**작업 내용**:
- 시스템 완전 재부팅
- Docker 재시작 (PostgreSQL, Redis)
- 28개의 백그라운드 API 서버 프로세스 정리
- Python 캐시 삭제
- 포트 8000 완전 정리

**결과**:
- ✅ PostgreSQL: Healthy (포트 5433)
- ✅ Redis: Healthy (포트 6379)
- ✅ 백그라운드 프로세스: 0개
- ✅ 포트 8000: 정리됨

### 6. PostgreSQL 로그 활성화 및 분석 ✅

**설정 변경**:
```sql
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();
```

**목적**: 모든 SQL 쿼리를 로깅하여 INSERT가 실제로 실행되는지 확인

**발견 사항**:
```bash
# PostgreSQL 로그 분석
docker logs kime-postgres 2>&1 | grep -E "INSERT|SELECT"

# 결과:
✅ SELECT 쿼리들: 있음 (test_api_db_connection.py, DB 조회 등)
✅ INSERT INTO session_snapshots: 있음 (세션 데이터는 저장됨!)
❌ INSERT INTO statedb.users: 전혀 없음! (사용자 데이터는 실행 안 됨!)
```

**결론**: **API 서버가 users 테이블에 INSERT 쿼리를 전혀 보내지 않음**

### 7. db_manager.py에 디버그 로깅 추가 ✅

**수정 위치**: `src/database/db_manager.py:110-130`

**추가된 로깅**:
```python
def create_user(...):
    print(f"🔵 create_user() 호출됨: username={username}")
    try:
        with self.get_connection() as conn:
            print(f"🟢 Connection 획득: autocommit={conn.autocommit}")
            with conn.cursor() as cur:
                print(f"🟡 INSERT 쿼리 실행 중...")
                cur.execute("""INSERT INTO statedb.users...""")
                print(f"🟢 User created: {username} (ID: {user_id})")
```

**테스트 결과**:
```
# curl로 회원가입 테스트 (username: debug_test_001)

🔵 create_user() 호출됨: username=debug_test_001
🟢 Connection 획득: autocommit=True
🟡 INSERT 쿼리 실행 중...
🟢 User created: debug_test_001 (ID: ce8ddf4e-9e73-4a87-bc60-1ad4deae39f6)

# API 응답: ✅ success=true
# PostgreSQL 조회: ❌ 0 rows
# PostgreSQL 로그: ❌ INSERT 쿼리 없음
```

## 💡 최종 발견 사항

### 핵심 문제 원인

**API 서버가 다른 PostgreSQL 인스턴스에 연결하고 있습니다!**

#### 증거 1: test_api_db_connection.py
```python
# HybridSessionManager를 통한 연결 테스트
실제 연결 정보:
  - Host: localhost
  - Port: 5433 ✅
  - Database: kimedb
  - User: kime

statedb.users 테이블 사용자 수: 8명
최근 사용자: directtest_013500409127, directtest001, tanjiro...
```
→ **올바른 PostgreSQL에 연결됨**

#### 증거 2: API 서버 회원가입
```
API 응답: ✅ success=true, user_id 생성
디버그 로그: ✅ create_user() 호출, autocommit=True, INSERT 실행
PostgreSQL 로그: ❌ INSERT 쿼리 도달 안 함
PostgreSQL 조회: ❌ 사용자 없음 (0 rows)
```
→ **다른 PostgreSQL 인스턴스에 INSERT 실행 중**

#### 증거 3: 직접 DB 테스트
```python
# DatabaseManager를 직접 사용
db = create_database_manager_from_env()
user_id = db.create_user(...)

# 결과:
PostgreSQL 로그: ✅ INSERT 쿼리 도달
PostgreSQL 조회: ✅ 사용자 있음 (directtest_013500409127)
```
→ **올바른 PostgreSQL에 저장됨**

### 결론

1. **test_api_db_connection.py (직접 테스트)**: 포트 5433의 올바른 DB 사용 ✅
2. **API 서버 (FastAPI 엔드포인트)**: 다른 PostgreSQL 인스턴스 사용 ❌
3. **직접 DB 매니저 사용**: 포트 5433의 올바른 DB 사용 ✅

**가능한 원인**:
- API 서버가 초기화될 때 환경 변수가 다르게 설정됨
- HybridSessionManager가 생성될 때 다른 설정 사용
- FastAPI의 dependency injection이 다른 인스턴스 생성
- 여러 DatabaseManager 인스턴스가 생성되어 일부는 잘못된 포트 사용

## 📊 최종 데이터베이스 상태

```sql
SELECT count(*) FROM statedb.users;
-- 결과: 8명

SELECT username, created_at FROM statedb.users ORDER BY created_at DESC;
```

| Username | Created At | 저장 방법 |
|----------|-----------|----------|
| directtest_013500409127 | 2025-10-30 16:35:00 | 직접 DB 테스트 ✅ |
| directtest001 | 2025-10-30 15:42:13 | 직접 DB 테스트 ✅ |
| tanjiro, zenitsu... (6명) | 2025-10-30 15:23:30 | 마이그레이션 ✅ |
| testuser*, curltest*, final_test*, debug_test* | - | API 서버 ❌ (0명) |

## 🎯 다음 세션을 위한 해결 방안

### 방안 1: 환경 변수 명시적 설정 (추천)
```bash
# API 서버 시작 시 환경 변수 명시
export DB_PORT=5433
export DB_HOST=localhost
/Users/jtm427/miniconda3/envs/openai/bin/python api_server.py
```

### 방안 2: .env 파일 생성
```bash
# backend/.env
DB_HOST=localhost
DB_PORT=5433
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=dev123
```

### 방안 3: api_server.py 수정
```python
# api_server.py 시작 부분에 추가
import os
os.environ.setdefault('DB_PORT', '5433')

# 또는 직접 설정
_hybrid_manager = HybridSessionManager(
    db_manager=DatabaseManager(
        host='localhost',
        port=5433,  # 명시적으로 5433 지정
        dbname='kimedb',
        user='kime',
        password='dev123'
    ),
    cache_manager=create_cache_manager_from_env()
)
```

### 방안 4: HybridSessionManager 초기화 추적
```python
# session_manager.py의 create_hybrid_session_manager_from_env()에 로깅 추가
def create_hybrid_session_manager_from_env() -> HybridSessionManager:
    db_manager = create_database_manager_from_env()

    # 디버그: 실제 연결 정보 출력
    with db_manager.get_connection() as conn:
        dsn = conn.get_dsn_parameters()
        print(f"🔍 HybridSessionManager DB 연결: {dsn['host']}:{dsn['port']}")

    cache_manager = create_cache_manager_from_env()
    return HybridSessionManager(db_manager, cache_manager)
```

## 📈 진행 상황 (최종)

- [x] 문제 발견 및 재현
- [x] 데이터베이스 포트 문제 수정
- [x] 트랜잭션 commit 로직 개선
- [x] Autocommit 활성화
- [x] 직접 DB 테스트 성공
- [x] 백그라운드 프로세스 문제 발견 및 정리
- [x] 시스템 재부팅 및 환경 정리
- [x] PostgreSQL 로그 분석
- [x] 디버그 로깅 추가 및 분석
- [x] **문제 원인 파악: API 서버가 다른 PostgreSQL 인스턴스 사용**
- [ ] 환경 변수 설정 또는 코드 수정으로 문제 해결 (다음 세션)
- [ ] 최종 테스트 및 검증

## 💭 학습한 교훈

1. **Connection Pool 디버깅**: 연결 풀이 예상과 다른 DB에 연결될 수 있음
2. **PostgreSQL 로그의 중요성**: 실제 쿼리 실행 여부를 확인하는 가장 확실한 방법
3. **디버그 로깅의 가치**: print 문으로도 중요한 정보 확인 가능
4. **환경 변수 관리**: 여러 인스턴스가 생성될 때 환경 변수가 다르게 적용될 수 있음
5. **직접 테스트의 중요성**: API를 거치지 않는 테스트로 문제 범위 좁힐 수 있음

---

## 🎉 최종 해결 (2025-10-30 밤 9시 51분)

### 8. api_server.py 수정 - localhost → 127.0.0.1 ✅✅✅

**문제 원인**: `host='localhost'` 사용 시 DNS 해석 문제 또는 IPv6/IPv4 혼용 문제

**해결 방법**: 명시적으로 IPv4 loopback 주소 `127.0.0.1` 사용

**수정 위치**: `backend/api_server.py:45-47, 198-218`

**변경 내용**:

```python
# Imports 수정
from src.database.session_manager import HybridSessionManager
from src.database.db_manager import DatabaseManager
from src.database.cache_manager import create_cache_manager_from_env

# HybridSessionManager 초기화 수정
try:
    # DatabaseManager를 명시적으로 127.0.0.1:5433으로 생성
    db_manager = DatabaseManager(
        host='127.0.0.1',  # localhost → 127.0.0.1
        port=5433,
        dbname='kimedb',
        user='kime',
        password='dev123',
        min_conn=2,
        max_conn=10
    )
    print(f"✅ DatabaseManager 생성: 127.0.0.1:5433")

    # CacheManager 생성
    cache_manager = create_cache_manager_from_env()

    # HybridSessionManager 생성
    _hybrid_manager = HybridSessionManager(db_manager, cache_manager)
    SESSION_MANAGER = SessionManagerAdapter(_hybrid_manager)
    print("✅ Database-backed SessionManager initialized")
except Exception as e:
    logger.error(f"Failed to initialize SessionManager: {e}")
    sys.exit(1)
```

### 최종 테스트 결과 🎊

#### 테스트 1: 회원가입
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"finaltest001","password":"test1234","email":"finaltest001@test.com","display_name":"최종테스트001"}'

# 결과:
{
  "success": true,
  "message": "회원가입이 완료되었습니다.",
  "user_id": "eeae5eb1-a1ee-47d9-84c0-1947a716926a",
  "username": "finaltest001",
  "display_name": "최종테스트001",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 테스트 2: PostgreSQL 검증
```sql
SELECT user_id, username, email, display_name
FROM statedb.users
WHERE username = 'finaltest001';

-- 결과:
user_id                              | username     | email                 | display_name
-------------------------------------|--------------|------------------------|---------------
eeae5eb1-a1ee-47d9-84c0-1947a716926a | finaltest001 | finaltest001@test.com | 최종테스트001

✅✅✅ PostgreSQL에 저장 성공!
```

#### 테스트 3: 로그인
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"finaltest001","password":"test1234"}'

# 결과:
{
  "success": true,
  "message": "로그인 성공",
  "user_id": "eeae5eb1-a1ee-47d9-84c0-1947a716926a",
  "username": "finaltest001",
  "display_name": "최종테스트001",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

✅ 로그인 성공!
```

#### 테스트 4: 일관성 확인 (두 번째 사용자)
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"finaltest002","password":"test1234","email":"finaltest002@test.com","display_name":"최종테스트002"}'

# PostgreSQL 조회:
SELECT user_id, username, created_at
FROM statedb.users
WHERE username IN ('finaltest001', 'finaltest002')
ORDER BY created_at DESC;

-- 결과:
user_id                              | username     | created_at
-------------------------------------|--------------|----------------------------
52de8d1d-f958-4ffe-8d3d-0f86bfce4229 | finaltest002 | 2025-10-30 21:51:39.291171
eeae5eb1-a1ee-47d9-84c0-1947a716926a | finaltest001 | 2025-10-30 21:51:10.791437

✅✅ 일관성 있게 저장됨!
```

### 문제 해결 요약

| 항목 | 문제 | 해결 |
|-----|------|------|
| **호스트 설정** | `host='localhost'` | `host='127.0.0.1'` |
| **포트 설정** | 기본값 5432 | 명시적 5433 |
| **DatabaseManager 생성** | 환경 변수 의존 | 직접 생성 (hardcoded) |
| **결과** | PostgreSQL 저장 안 됨 ❌ | PostgreSQL 저장 성공 ✅ |

### 왜 localhost가 문제였나?

1. **IPv4 vs IPv6 혼용**:
   - `localhost`는 IPv6 (`::1`) 또는 IPv4 (`127.0.0.1`)로 해석될 수 있음
   - PostgreSQL이 특정 IP에만 바인딩되어 있을 경우 문제 발생

2. **DNS 해석 문제**:
   - 일부 시스템에서 localhost DNS 해석이 올바르게 작동하지 않음
   - 명시적 IP 주소 사용이 더 안정적

3. **Docker 네트워킹**:
   - Docker 환경에서 localhost가 호스트 머신을 가리키지 않을 수 있음
   - 127.0.0.1은 항상 loopback 인터페이스를 명확하게 지정

### 핵심 교훈

1. **네트워크 연결 디버깅**: 호스트 이름보다 IP 주소가 더 명확하고 안정적
2. **Docker 환경**: localhost와 127.0.0.1이 다르게 동작할 수 있음
3. **명시적 설정**: 환경 변수보다 하드코딩이 디버깅에 유리 (프로덕션에서는 환경 변수 사용)
4. **단계적 테스트**: 직접 DB 테스트 → API 테스트로 문제 범위 좁히기

## 📈 최종 진행 상황

- [x] 문제 발견 및 재현
- [x] 데이터베이스 포트 문제 수정
- [x] 트랜잭션 commit 로직 개선
- [x] Autocommit 활성화
- [x] 직접 DB 테스트 성공
- [x] 백그라운드 프로세스 문제 발견 및 정리
- [x] 시스템 재부팅 및 환경 정리
- [x] PostgreSQL 로그 분석
- [x] 디버그 로깅 추가 및 분석
- [x] 문제 원인 파악: API 서버가 다른 PostgreSQL 인스턴스 사용
- [x] **localhost → 127.0.0.1 수정으로 완전 해결 ✅**
- [x] 최종 테스트 및 검증 완료 ✅
- [x] 문서 업데이트 완료 ✅

## 📊 최종 데이터베이스 상태

```sql
SELECT count(*) FROM statedb.users;
-- 결과: 10명 (기존 8명 + 새로 생성 2명)
```

| Username | Created At | 저장 방법 | 상태 |
|----------|-----------|----------|------|
| finaltest002 | 2025-10-30 21:51:39 | API 서버 (127.0.0.1) | ✅ 성공 |
| finaltest001 | 2025-10-30 21:51:10 | API 서버 (127.0.0.1) | ✅ 성공 |
| directtest_013500409127 | 2025-10-30 16:35:00 | 직접 DB 테스트 | ✅ 성공 |
| directtest001 | 2025-10-30 15:42:13 | 직접 DB 테스트 | ✅ 성공 |
| tanjiro, zenitsu... (6명) | 2025-10-30 15:23:30 | 마이그레이션 | ✅ 성공 |

---

**최종 업데이트**: 2025-10-30 밤 9시 51분
**상태**: ✅ 문제 완전 해결
**해결 방법**: `host='localhost'` → `host='127.0.0.1'` 변경
**검증**: 회원가입, 로그인, PostgreSQL 저장 모두 정상 작동 확인
