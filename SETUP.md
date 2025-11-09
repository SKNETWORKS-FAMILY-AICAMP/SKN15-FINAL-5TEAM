# KIME Chat - 팀 개발 환경 설정 가이드

## 목차
1. [사전 준비사항](#사전-준비사항)
2. [빠른 시작](#빠른-시작)
3. [환경변수 설정](#환경변수-설정)
4. [데이터베이스 데이터 공유](#데이터베이스-데이터-공유)
5. [개발 서버 실행](#개발-서버-실행)
6. [마이그레이션 확인](#마이그레이션-확인)
7. [문제 해결](#문제-해결)

---

## 사전 준비사항

다음 소프트웨어가 설치되어 있어야 합니다:

- **Docker Desktop** (최신 버전)
  - macOS: https://docs.docker.com/desktop/install/mac-install/
  - Windows: https://docs.docker.com/desktop/install/windows-install/
  - Linux: https://docs.docker.com/desktop/install/linux-install/
- **Git**
- **OpenAI API 키** (필수)

---

## 빠른 시작

### 1️⃣ 저장소 클론

```bash
git clone <repository-url>
cd workspace
```

### 2️⃣ 환경변수 설정

```bash
# .env 파일 생성
cp .env.example .env
```

`.env` 파일을 열어 다음 필수 항목을 수정하세요:

```bash
# OpenAI API 키 (필수!)
OPENAI_API_KEY=sk-your-actual-api-key-here

# JWT 시크릿 (필수! 최소 32자)
JWT_SECRET_KEY=your-very-long-secret-key-here-min-32-chars

# 데이터베이스 비밀번호 (권장)
DB_PASSWORD=your_secure_password

# Redis 비밀번호 (권장)
REDIS_PASSWORD=your_redis_password
```

### 3️⃣ Docker 컨테이너 실행

```bash
# 모든 서비스 시작 (자동 마이그레이션 포함)
docker-compose up -d

# 로그 확인 (선택사항)
docker-compose logs -f
```

### 4️⃣ 서비스 접속

- **프론트엔드**: http://localhost
- **백엔드 API**: http://localhost:8000
- **API 문서 (Swagger)**: http://localhost:8000/docs

---

## 환경변수 설정

### 필수 환경변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 | `sk-proj-...` |
| `JWT_SECRET_KEY` | JWT 인증용 시크릿 (32자 이상) | `your-secret-key-min-32-chars` |

### 선택 환경변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `DB_PASSWORD` | `dev123` | PostgreSQL 비밀번호 |
| `REDIS_PASSWORD` | `dev123` | Redis 비밀번호 |
| `DEBUG` | `false` | 디버그 모드 |
| `USE_LLM` | `true` | LLM 사용 여부 |

### OAuth 소셜 로그인 (선택)

Google 또는 Kakao 로그인을 사용하려면 `.env`에 추가:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Kakao OAuth
KAKAO_CLIENT_ID=your-kakao-client-id
KAKAO_CLIENT_SECRET=your-kakao-client-secret
```

---

## 데이터베이스 데이터 공유

### 데이터 백업 (내보내기)

현재 데이터베이스를 백업하여 팀원과 공유:

```bash
# 백업 파일 생성
./scripts/backup_database.sh

# 생성된 파일: backups/database_backup_YYYYMMDD_HHMMSS.sql
```

### 데이터 복원 (가져오기)

팀원으로부터 받은 백업 파일을 복원:

```bash
# 백업 파일 복원
./scripts/restore_database.sh backups/database_backup_YYYYMMDD_HHMMSS.sql

# 캐시 초기화
docker-compose exec redis redis-cli FLUSHALL

# 백엔드 재시작
docker-compose restart backend
```

---

## 개발 서버 실행

### 전체 서비스 시작

```bash
# 백그라운드 실행
docker-compose up -d

# 포그라운드 실행 (로그 확인)
docker-compose up
```

### 개별 서비스 재시작

```bash
# 백엔드만 재시작
docker-compose restart backend

# 프론트엔드만 재시작
docker-compose restart frontend

# 데이터베이스만 재시작
docker-compose restart postgres
```

### 서비스 중지

```bash
# 모든 서비스 중지
docker-compose down

# 볼륨 포함 완전 삭제 (주의!)
docker-compose down -v
```

---

## 마이그레이션 확인

### 자동 마이그레이션

Docker Compose로 실행하면 PostgreSQL 컨테이너가 시작될 때 자동으로 마이그레이션이 실행됩니다:

```
/docker-entrypoint-initdb.d/
├── 001_initial_schema.sql
├── 002_user_sessions.sql
├── 003_scenarios.sql
├── ...
└── 019_scenario_comments.sql
```

### 마이그레이션 상태 확인

```bash
# PostgreSQL 컨테이너 접속
docker-compose exec postgres psql -U kime -d kimedb

# 테이블 목록 확인
\dt statedb.*

# 시나리오 통계 확인
SELECT * FROM statedb.scenario_statistics;

# 댓글 테이블 확인
SELECT COUNT(*) FROM statedb.scenario_comments;
```

### 수동 마이그레이션 (필요시)

```bash
# 특정 마이그레이션 파일 실행
cat backend/database/migrations/019_scenario_comments.sql | \
  docker-compose exec -T postgres psql -U kime -d kimedb
```

---

## 문제 해결

### 1. 포트 충돌 오류

```
Error: Bind for 0.0.0.0:5432 failed: port is already allocated
```

**해결**: 이미 실행 중인 PostgreSQL이 있는지 확인

```bash
# macOS/Linux
lsof -i :5432

# 프로세스 종료 후 다시 시작
docker-compose up -d
```

### 2. 마이그레이션이 실행되지 않음

```bash
# 1. 볼륨 완전 삭제 후 재시작 (주의: 데이터 손실!)
docker-compose down -v
docker-compose up -d

# 2. 수동으로 마이그레이션 실행
for file in backend/database/migrations/*.sql; do
  echo "Running $file..."
  cat "$file" | docker-compose exec -T postgres psql -U kime -d kimedb
done
```

### 3. OpenAI API 키 오류

```
Error: OPENAI_API_KEY is not set
```

**해결**: `.env` 파일에 올바른 API 키 설정

```bash
# .env 파일 확인
grep OPENAI_API_KEY .env

# 없으면 추가
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# 백엔드 재시작
docker-compose restart backend
```

### 4. Redis 연결 오류

```bash
# Redis 상태 확인
docker-compose exec redis redis-cli ping

# 응답: PONG (정상)

# Redis 캐시 초기화
docker-compose exec redis redis-cli FLUSHALL
```

### 5. 프론트엔드 빌드 오류

```bash
# Node 모듈 재설치
docker-compose exec frontend npm install

# 컨테이너 재빌드
docker-compose up -d --build frontend
```

### 6. 로그 확인

```bash
# 모든 서비스 로그
docker-compose logs -f

# 특정 서비스만
docker-compose logs -f backend
docker-compose logs -f postgres

# 최근 100줄만
docker-compose logs --tail=100 backend
```

---

## 개발 모드 vs 프로덕션 모드

### 개발 모드 (현재)

- 핫 리로드 활성화
- 디버그 로그 출력
- API CORS 허용
- 소스 맵 생성

### 프로덕션 배포 시 변경사항

`.env` 파일 수정:

```bash
DEBUG=false
USE_LLM=true
FRONTEND_URL=https://your-domain.com
VITE_API_URL=https://api.your-domain.com
```

---

## 유용한 명령어

### Docker 관련

```bash
# 컨테이너 상태 확인
docker-compose ps

# 리소스 사용량
docker stats

# 볼륨 목록
docker volume ls

# 미사용 리소스 정리
docker system prune -a
```

### 데이터베이스 관련

```bash
# 데이터베이스 백업
./scripts/backup_database.sh custom_name.sql

# 데이터베이스 복원
./scripts/restore_database.sh backups/custom_name.sql

# PostgreSQL 쉘 접속
docker-compose exec postgres psql -U kime -d kimedb
```

### Git 관련

```bash
# 현재 브랜치 확인
git status

# 변경사항 스태시
git stash

# 최신 코드 받기
git pull origin main
```

---

## 추가 리소스

- **API 문서**: http://localhost:8000/docs (Swagger UI)
- **Redoc**: http://localhost:8000/redoc
- **PostgreSQL 스키마**: [backend/database/migrations/](backend/database/migrations/)
- **프롬프트 설정**: [backend/configs/prompts.yaml](backend/configs/prompts.yaml)

---

## 팀 협업 워크플로우

1. **최신 코드 받기**
   ```bash
   git pull origin main
   ```

2. **환경 업데이트**
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

3. **데이터 동기화** (필요시)
   ```bash
   ./scripts/restore_database.sh backups/latest.sql
   ```

4. **개발 시작**
   - 백엔드: [backend/](backend/) 폴더에서 작업
   - 프론트엔드: [front/](front/) 폴더에서 작업

5. **변경사항 커밋**
   ```bash
   git add .
   git commit -m "feat: 기능 설명"
   git push origin feature/branch-name
   ```

---

## 문의사항

- 기술적 문제: GitHub Issues
- 긴급 문의: 팀 Slack 채널

**Happy Coding! 🚀**
