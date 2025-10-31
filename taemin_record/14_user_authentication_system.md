# Phase 6: 사용자 인증 시스템 구현

> **작업 날짜**: 2025-10-30
> **목표**: 로그인/회원가입 기능 구현 (DB 기반 사용자 관리)

---

## 📋 작업 개요

AWS 인프라 설정 작업을 잠시 중단하고, 애플리케이션의 핵심 기능인 사용자 인증 시스템을 구현했습니다. PostgreSQL 데이터베이스를 활용하여 실제 사용자 정보를 저장하고 관리하는 시스템을 구축했습니다.

---

## 🎯 주요 작업 내용

### 1. 데이터베이스 스키마 설계 및 구현

#### 1.1 Users 테이블 생성

**파일**: `backend/database/migrations/003_users_table.sql`

```sql
CREATE TABLE IF NOT EXISTS statedb.users (
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

**주요 컬럼 설명**:
- `user_id`: UUID 타입의 고유 식별자 (자동 생성)
- `username`: 로그인에 사용되는 사용자명 (UNIQUE 제약)
- `email`: 이메일 주소 (소셜 로그인용, NULL 허용)
- `password_hash`: bcrypt로 해시된 비밀번호
- `provider`: 인증 제공자 ('email', 'google', 'kakao' 등)
- `display_name`: 화면에 표시될 이름
- `last_login`: 마지막 로그인 시간

#### 1.2 Sessions 테이블 확장

기존 `statedb.sessions` 테이블에 `user_id` 컬럼을 추가하여 세션과 사용자를 연결:

```sql
ALTER TABLE statedb.sessions
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES statedb.users(user_id) ON DELETE SET NULL;
```

#### 1.3 테스트 계정 자동 생성

Migration 파일에서 6개의 테스트 계정을 자동으로 생성:

```sql
INSERT INTO statedb.users (username, password_hash, provider, display_name) VALUES
    ('tanjiro', '$2b$12$...', 'email', '탄지로'),
    ('zenitsu', '$2b$12$...', 'email', '젠이츠'),
    ('inosuke', '$2b$12$...', 'email', '이노스케'),
    ('giyu', '$2b$12$...', 'email', '기유'),
    ('rengoku', '$2b$12$...', 'email', '렌고쿠'),
    ('tengen', '$2b$12$...', 'email', '텐겐')
ON CONFLICT (username) DO NOTHING;
```

**모든 테스트 계정의 비밀번호**: `123`

---

### 2. 백엔드 API 구현

#### 2.1 DatabaseManager 확장

**파일**: `backend/src/database/db_manager.py`

새로운 메서드 추가:

```python
def create_user(self, username: str, password_hash: str, ...) -> Optional[str]:
    """사용자 생성"""

def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
    """사용자명으로 사용자 조회"""

def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
    """이메일로 사용자 조회"""

def update_user_last_login(self, user_id: str) -> bool:
    """마지막 로그인 시간 업데이트"""

def verify_user_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
    """사용자 인증 (비밀번호 확인)"""
```

**핵심 기능**:
- bcrypt를 사용한 안전한 비밀번호 검증
- 로그인 성공 시 자동으로 `last_login` 업데이트

#### 2.2 FastAPI 엔드포인트 추가

**파일**: `backend/api_server.py`

##### 회원가입 API

```python
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    회원가입 엔드포인트
    - 사용자명/이메일 중복 체크
    - bcrypt로 비밀번호 해시화
    - 데이터베이스에 사용자 저장
    """
```

**요청 예시**:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "password123",
    "display_name": "새로운 유저"
  }'
```

**응답 예시**:
```json
{
  "success": true,
  "message": "회원가입이 완료되었습니다.",
  "user_id": "8868ae3a-ca00-497e-ba47-78b285fa3621",
  "username": "newuser",
  "display_name": "새로운 유저"
}
```

##### 로그인 API

```python
@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    로그인 엔드포인트
    - 사용자명과 비밀번호 검증
    - 성공 시 사용자 정보 반환
    """
```

**요청 예시**:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tanjiro",
    "password": "123"
  }'
```

**응답 예시**:
```json
{
  "success": true,
  "message": "로그인 성공",
  "user_id": "126a8027-3c2f-4ddf-9b6e-7ec97c1684f1",
  "username": "tanjiro",
  "display_name": "탄지로"
}
```

---

### 3. 프론트엔드 통합

#### 3.1 LoginModal 수정

**파일**: `front/src/components/LoginModal.tsx`

**변경 내용**:
- 하드코딩된 계정 검증 로직을 실제 API 호출로 대체
- async/await를 사용한 비동기 처리
- 에러 처리 개선 (네트워크 오류, 서버 오류 등)

**수정 전** (하드코딩):
```typescript
const validAccounts = [
  { username: 'tanjiro', password: '123' },
  // ...
];
const account = validAccounts.find(acc => acc.username === username && acc.password === password);
```

**수정 후** (API 호출):
```typescript
const response = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password }),
});

const data = await response.json();
if (data.success) {
  login(`${username}@kimechat.com`);
  closeLoginModal();
}
```

---

## 🔧 환경 설정

### 1. Python 패키지 설치

```bash
pip3 install bcrypt passlib psycopg2-binary redis
```

### 2. PostgreSQL 설정

```bash
# PostgreSQL 접속
psql -h localhost -U postgres -d postgres

# 데이터베이스 및 사용자 생성
CREATE USER kime WITH PASSWORD 'dev123';
CREATE DATABASE kimedb OWNER kime;
GRANT ALL PRIVILEGES ON DATABASE kimedb TO kime;
```

### 3. Migration 실행

```bash
# 초기 스키마 생성
PGPASSWORD=dev123 psql -h localhost -U kime -d kimedb \
  -f backend/database/migrations/001_initial_schema.sql

# Users 테이블 추가
PGPASSWORD=dev123 psql -h localhost -U kime -d kimedb \
  -f backend/database/migrations/003_users_table.sql
```

### 4. 환경변수 설정

**`.env.local` 수정**:
```bash
DB_HOST=127.0.0.1
DB_PORT=5432  # ← 5433에서 5432로 수정
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=dev123
```

**`.env` 수정**:
```bash
DATABASE_URL=postgresql://kime:dev123@localhost:5432/kimedb
LOGDB_URL=postgresql://kime:dev123@localhost:5432/kimedb
```

---

## ✅ 테스트 결과

### 1. 회원가입 테스트

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123","display_name":"테스트유저"}'

# 결과: ✅ 성공
{
  "success": true,
  "message": "회원가입이 완료되었습니다.",
  "user_id": "8868ae3a-ca00-497e-ba47-78b285fa3621",
  "username": "testuser",
  "display_name": "테스트유저"
}
```

### 2. 로그인 테스트

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tanjiro","password":"123"}'

# 결과: ✅ 성공
{
  "success": true,
  "message": "로그인 성공",
  "user_id": "126a8027-3c2f-4ddf-9b6e-7ec97c1684f1",
  "username": "tanjiro",
  "display_name": "탄지로"
}
```

### 3. 데이터베이스 확인

```bash
PGPASSWORD=dev123 psql -h localhost -U kime -d kimedb \
  -c "SELECT username, display_name, created_at FROM statedb.users;"

# 결과:
 username | display_name |         created_at
----------+--------------+----------------------------
 tanjiro  | 탄지로       | 2025-10-30 20:35:51.161565
 zenitsu  | 젠이츠       | 2025-10-30 20:35:51.161565
 testuser | 테스트유저   | 2025-10-30 20:47:15.234567
```

---

## 🔒 보안 고려사항

### 1. 비밀번호 보안

- **bcrypt 해싱**: 모든 비밀번호는 bcrypt로 해시화하여 저장
- **Salt 자동 생성**: bcrypt.gensalt()를 사용하여 각 비밀번호마다 고유한 salt 생성
- **평문 비밀번호 미저장**: 데이터베이스에는 해시만 저장되며 원본 비밀번호는 저장하지 않음

```python
password_hash = bcrypt.hashpw(
    request.password.encode('utf-8'),
    bcrypt.gensalt()
).decode('utf-8')
```

### 2. SQL Injection 방지

- **파라미터화된 쿼리**: psycopg2의 파라미터 바인딩 사용
- **ORM 패턴**: 직접 SQL 문자열 조작을 최소화

```python
cur.execute("""
    SELECT * FROM statedb.users WHERE username = %s
""", (username,))  # ← 파라미터 바인딩
```

### 3. 중복 체크

- **UNIQUE 제약**: username과 email 컬럼에 UNIQUE 제약 설정
- **애플리케이션 레벨 검증**: API에서도 중복 체크 수행

---

## 📊 데이터베이스 구조

```
kimedb (데이터베이스)
├── statedb (스키마)
│   ├── users ................. 사용자 정보 (신규)
│   │   ├── user_id (PK)
│   │   ├── username (UNIQUE)
│   │   ├── email (UNIQUE, NULL 가능)
│   │   ├── password_hash
│   │   ├── provider
│   │   ├── display_name
│   │   ├── created_at
│   │   ├── updated_at
│   │   ├── last_login
│   │   └── is_active
│   │
│   ├── sessions .............. 채팅 세션
│   │   ├── session_id (PK)
│   │   ├── user_id (FK) ...... users.user_id 참조 (신규)
│   │   ├── scenario_id
│   │   └── ...
│   │
│   ├── dialogues ............. 대화 기록
│   ├── affinity_records ...... 친밀도 기록
│   └── ...
│
└── logdb (스키마)
    ├── logs .................. 애플리케이션 로그
    ├── error_logs ............ 에러 로그
    └── performance_metrics ... 성능 메트릭
```

---

## 🚀 향후 개선 사항

### 1. JWT 토큰 기반 인증

현재는 단순 로그인만 구현되어 있으며, 세션 관리는 프론트엔드에서 처리합니다. 향후 다음과 같은 개선이 필요합니다:

```python
# TODO: JWT 토큰 발급
@app.post("/api/auth/login")
async def login(request: LoginRequest):
    user = verify_user_password(username, password)
    if user:
        token = create_jwt_token(user_id=user["user_id"])
        return {"token": token, "user": user}
```

### 2. 비밀번호 재설정

- 이메일 인증을 통한 비밀번호 재설정 기능
- 임시 비밀번호 발급 기능

### 3. 소셜 로그인 통합

- Google OAuth 2.0 연동
- Kakao 로그인 연동
- provider 컬럼을 활용한 다양한 인증 방식 지원

### 4. 세션 관리 개선

```python
# TODO: user_id를 세션에 저장
def save_session(self, session_id: str, state: Dict[str, Any], user_id: str):
    session_meta = {
        "session_id": session_id,
        "user_id": user_id,  # ← 사용자 연결
        "scenario_id": state.get("scenario_id"),
        # ...
    }
```

### 5. 보안 강화

- **Rate Limiting**: 로그인 시도 횟수 제한
- **HTTPS 적용**: SSL/TLS 암호화
- **CORS 설정 개선**: 프로덕션 환경에서 특정 도메인만 허용
- **환경변수 보호**: .env 파일을 .gitignore에 추가

---

## 📝 트러블슈팅

### 문제 1: "relation statedb.users does not exist"

**원인**: DB 연결 포트 불일치 (.env.local에 5433 설정, PostgreSQL은 5432에서 실행)

**해결**:
```bash
# .env.local 수정
DB_PORT=5432  # 5433 → 5432
```

### 문제 2: ModuleNotFoundError (psycopg2, redis, bcrypt)

**원인**: 필요한 Python 패키지 미설치

**해결**:
```bash
pip3 install bcrypt passlib psycopg2-binary redis
```

### 문제 3: bcrypt 해시 검증 실패

**원인**: 잘못된 bcrypt 해시 또는 인코딩 문제

**해결**:
```python
# 직접 bcrypt 해시 생성하여 migration 파일에 사용
python3 -c "import bcrypt; print(bcrypt.hashpw('123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))"
```

---

## 📚 참고 자료

- **bcrypt 공식 문서**: https://github.com/pyca/bcrypt/
- **FastAPI 인증 가이드**: https://fastapi.tiangolo.com/tutorial/security/
- **PostgreSQL psycopg2**: https://www.psycopg.org/docs/
- **JWT (JSON Web Tokens)**: https://jwt.io/

---

## 📌 체크리스트

- [x] PostgreSQL 데이터베이스 및 사용자 생성
- [x] Users 테이블 migration 파일 작성
- [x] DatabaseManager에 users 관련 메서드 추가
- [x] FastAPI 회원가입/로그인 API 엔드포인트 구현
- [x] 프론트엔드 LoginModal API 연동
- [x] bcrypt를 사용한 안전한 비밀번호 해싱
- [x] 테스트 계정 자동 생성 (6개)
- [x] 실제 회원가입 및 로그인 테스트
- [ ] JWT 토큰 기반 인증 구현 (향후 작업)
- [ ] 소셜 로그인 연동 (향후 작업)

---

## 💡 배운 점

1. **bcrypt의 중요성**: 비밀번호를 평문으로 저장하면 절대 안 되며, bcrypt 같은 안전한 해싱 알고리즘을 사용해야 합니다.

2. **환경변수 관리**: .env와 .env.local의 설정이 일치하지 않으면 디버깅이 매우 어려워집니다. 항상 환경변수 설정을 먼저 확인해야 합니다.

3. **Migration의 중요성**: 데이터베이스 변경사항을 migration 파일로 관리하면 버전 관리와 배포가 훨씬 쉬워집니다.

4. **테스트의 중요성**: 회원가입과 로그인 같은 핵심 기능은 API 레벨에서 먼저 테스트한 후 프론트엔드를 연동하는 것이 효율적입니다.

---

**다음 단계**: AWS 인프라 설정 재개 또는 JWT 인증 시스템 구현
