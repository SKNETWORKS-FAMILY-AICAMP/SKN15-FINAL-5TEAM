# 트러블슈팅 가이드

## 📋 목차
1. [PostgreSQL 연결 에러](#postgresql-연결-에러)
2. [Foreign Key 제약 조건 위반](#foreign-key-제약-조건-위반)
3. [TypeScript import.meta.env 에러](#typescript-importmetaenv-에러)
4. [환경 변수 미적용](#환경-변수-미적용)
5. [이미지 로딩 실패](#이미지-로딩-실패)

---

## PostgreSQL 연결 에러

### 문제 상황

**에러 메시지:**
```
psycopg2.OperationalError: FATAL: role "kime" does not exist
```

**발생 시점:** Docker PostgreSQL 실행 후 Python에서 연결 시도

### 원인 분석

1. **로컬 PostgreSQL과 포트 충돌**
   - 로컬에 PostgreSQL이 이미 5432 포트 사용 중
   - Docker PostgreSQL도 5432 포트 사용
   - 연결 시 로컬 PostgreSQL에 연결됨 (Docker 아님!)

2. **확인 방법**
   ```bash
   # 5432 포트 사용 프로세스 확인
   lsof -i :5432

   # 출력 예시:
   # postgres  1234 user  5u  IPv6  0t0  TCP localhost:5432 (LISTEN)
   # → 로컬 PostgreSQL이 포트 점유!
   ```

### 해결 방법

#### 방법 1: Docker 포트 변경 (채택)

**docker-compose.yml 수정:**
```yaml
postgres:
  ports:
    - "5433:5432"  # 로컬 5433 → 컨테이너 5432
```

**.env.local 수정:**
```bash
DB_HOST=127.0.0.1  # ⚠️ localhost 아님!
DB_PORT=5433       # ⚠️ 5433으로 변경
```

**재시작:**
```bash
docker-compose down
docker-compose up -d
```

#### 방법 2: 로컬 PostgreSQL 중지 (비추천)
```bash
# macOS
brew services stop postgresql

# 주의: 다른 프로젝트에 영향
```

### 추가 팁

**localhost vs 127.0.0.1**
- `localhost`: IPv6로 해석될 수 있음 (`::1`)
- `127.0.0.1`: 명시적 IPv4
- **권장:** 127.0.0.1 사용

---

## Foreign Key 제약 조건 위반

### 문제 상황

**에러 메시지:**
```
psycopg2.errors.ForeignKeyViolation:
insert or update on table "session_snapshots"
violates foreign key constraint "session_snapshots_session_id_fkey"
DETAIL: Key (session_id)=(abc123) is not present in table "sessions".
```

**발생 시점:** 세션 저장 시

### 원인 분석

**잘못된 저장 순서:**
```python
# ❌ 문제가 있는 코드
def save(self, session_id, state):
    # 1. 스냅샷 먼저 저장 (오류!)
    self.db.save_snapshot(session_id, turn_count, state)

    # 2. 세션 메타데이터 저장
    self.db.save_session(session_meta)
```

**문제:**
- `session_snapshots` 테이블은 `sessions` 테이블을 외래 키로 참조
- `sessions` 레코드가 없으면 `session_snapshots` 저장 불가!

### 해결 방법

**올바른 저장 순서:**
```python
# ✅ 올바른 코드
def save(self, session_id, state):
    # 1. 세션 메타데이터 먼저 저장 (부모 테이블)
    self.db.save_session({
        "session_id": session_id,
        "scenario_id": state.get("scenario_id"),
        "status": "active"
    })

    # 2. 스냅샷 저장 (자식 테이블)
    self.db.save_snapshot(session_id, turn_count, state)

    # 3. 캐시 업데이트
    self.cache.set_session(session_id, state)
```

### 일반 원칙

**외래 키 제약 조건이 있는 경우:**
1. 부모 테이블 레코드 먼저 생성
2. 자식 테이블 레코드 생성
3. 삭제는 반대 순서 (자식 → 부모)

**CASCADE 옵션:**
```sql
ON DELETE CASCADE  -- 부모 삭제 시 자식도 자동 삭제
```

---

## TypeScript import.meta.env 에러

### 문제 상황

**에러 메시지:**
```
Property 'env' does not exist on type 'ImportMeta'. TS(2339)
```

**발생 위치:**
```typescript
const CDN_URL = import.meta.env.VITE_CDN_URL;
                              // ^^^ 여기서 에러
```

### 원인 분석

TypeScript가 Vite의 `import.meta.env` 타입을 모름

### 해결 방법

**vite-env.d.ts 파일 생성:**

`front/src/vite-env.d.ts`:
```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_CDN_URL: string
  readonly VITE_ENVIRONMENT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

**파일 위치:** `src` 폴더 바로 아래

**확인 방법:**
```bash
ls front/src/vite-env.d.ts  # 파일 존재 확인
```

**VSCode 재시작:**
- `Cmd+Shift+P` → "Reload Window"
- 또는 VSCode 완전 재시작

---

## 환경 변수 미적용

### 문제 상황

**증상:**
- 환경 변수 설정했는데 기본값만 사용됨
- 이미지가 로컬 경로로만 로드됨

```typescript
const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';
console.log(CDN_URL);  // '/images'만 출력 (환경 변수 미적용)
```

### 원인 분석

1. **환경 변수 파일 위치 오류**
   - ❌ `front/src/.env`
   - ✅ `front/.env`

2. **개발 서버 미재시작**
   - 환경 변수 변경 후 재시작 필요

3. **파일명 오류**
   - ❌ `.env.txt`
   - ✅ `.env` (확장자 없음)

4. **VITE_ 접두사 누락**
   - ❌ `CDN_URL=...`
   - ✅ `VITE_CDN_URL=...`

### 해결 방법

#### 1. 파일 위치 확인
```bash
# 올바른 위치
ls -la front/.env
ls -la front/.env.production
```

#### 2. 파일 내용 확인
```bash
# .env 파일 읽기
cat front/.env

# 출력 예시:
# VITE_CDN_URL=/images
```

#### 3. 개발 서버 재시작
```bash
# Ctrl+C로 중지 후
npm run dev
```

#### 4. 브라우저에서 확인
```typescript
// 콘솔에서 직접 확인
console.log('All env vars:', import.meta.env);
console.log('CDN URL:', import.meta.env.VITE_CDN_URL);
```

---

## 이미지 로딩 실패

### 문제 상황

**증상:**
- 브라우저에서 이미지가 표시되지 않음
- Network 탭에서 404 에러

```
GET http://localhost:3000/images/프로필_탄지로.png 404 (Not Found)
```

### 원인별 해결 방법

#### 원인 1: 이미지 파일 위치 오류

**확인:**
```bash
ls front/public/images/프로필_탄지로.png
```

**해결:**
- 이미지를 `front/public/images/` 폴더에 배치
- Vite는 `public` 폴더를 루트로 서빙

#### 원인 2: 경로 오타

**문제:**
```typescript
// ❌ 오타
const path = `${CDN_URL}/프로필_탄지료.png`;  // 료 (X)

// ✅ 정확한 이름
const path = `${CDN_URL}/프로필_탄지로.png`;  // 로 (O)
```

**해결:**
- 파일명 대소문자 정확히 확인
- 한글 자음/모음 정확히 확인

#### 원인 3: 잘못된 CDN URL (프로덕션)

**문제:**
```bash
# .env.production
VITE_CDN_URL=https://d1a2b3c4d5e6f7.cloudfront.net/images
                                                       # ^^^ 불필요
```

**해결:**
```bash
# 올바른 설정
VITE_CDN_URL=https://d1a2b3c4d5e6f7.cloudfront.net
```

코드에서 이미 `/프로필_탄지로.png`가 포함되므로, CDN URL에는 `/images` 제외!

#### 원인 4: CORS 에러 (프로덕션)

**증상:**
```
Access to image at 'https://cloudfront...' blocked by CORS policy
```

**해결:**
S3 버킷 CORS 설정:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": []
  }
]
```

---

## 일반 디버깅 팁

### 1. 로그 확인

**프론트엔드:**
```typescript
console.log('Environment:', import.meta.env.VITE_ENVIRONMENT);
console.log('API URL:', import.meta.env.VITE_API_URL);
console.log('CDN URL:', import.meta.env.VITE_CDN_URL);
console.log('Image path:', imagePath);
```

**백엔드:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.debug(f"DB Host: {os.getenv('DB_HOST')}")
logger.debug(f"Session ID: {session_id}")
```

### 2. 네트워크 확인

**브라우저 개발자 도구:**
1. F12 → Network 탭
2. 이미지 요청 확인
3. Status Code 확인 (200, 404, 500 등)
4. Response Headers 확인

### 3. Docker 상태 확인

```bash
# 컨테이너 상태
docker-compose ps

# 로그 확인
docker-compose logs postgres
docker-compose logs redis

# 컨테이너 내부 접속
docker exec -it kime_postgres psql -U kime -d kimedb
```

### 4. 데이터베이스 직접 확인

```bash
# PostgreSQL 접속
psql -h 127.0.0.1 -p 5433 -U kime -d kimedb

# 테이블 확인
\dt statedb.*
\dt logdb.*

# 데이터 확인
SELECT * FROM statedb.sessions LIMIT 5;
```

### 5. 환경 초기화

**모든 것을 다시 시작:**
```bash
# 1. Docker 중지 및 데이터 삭제
cd backend/database
docker-compose down -v

# 2. Docker 재시작
docker-compose up -d

# 3. 프론트엔드 재시작
cd ../../front
rm -rf node_modules dist
npm install
npm run dev

# 4. 백엔드 재시작
cd ../backend
pip install -r requirements.txt
python api_server.py
```

---

## 문의하기 전 체크리스트

- [ ] 에러 메시지 전체 복사 (스택 트레이스 포함)
- [ ] 어떤 작업 중 발생했는지 기록
- [ ] 최근 변경한 코드/설정 확인
- [ ] 재시작 시도 (개발 서버, Docker 등)
- [ ] 브라우저 개발자 도구 확인
- [ ] 환경 변수 파일 존재 및 내용 확인

---

## 관련 문서
- [01_database_setup.md](01_database_setup.md) - 데이터베이스 에러
- [02_image_cdn_migration.md](02_image_cdn_migration.md) - 이미지 경로 에러
- [04_environment_variables.md](04_environment_variables.md) - 환경 변수 에러

---
작성일: 2025-10-30
마지막 업데이트: 실전 에러 발생 시 계속 추가
