# 팀원용 프로젝트 설정 가이드

## 📋 개요

이 프로젝트는 Docker Compose로 완전히 구성되어 있어, 한 번의 명령으로 모든 서비스를 실행할 수 있습니다.

## 🚀 빠른 시작

### 1. 저장소 클론

```bash
git clone <repository-url>
cd workspace
```

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# Database
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=dev123
DB_PORT=5432

# Redis
REDIS_PORT=6379
REDIS_PASSWORD=

# OpenAI (필수!)
OPENAI_API_KEY=your-openai-api-key-here

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# App
FRONTEND_URL=http://localhost:5173
ENVIRONMENT=development
BACKEND_PORT=8000

# Feature Flags
USE_LLM=true
USE_LANGGRAPH=false

# Frontend
VITE_API_URL=http://localhost
```

**⚠️ 주의**: `OPENAI_API_KEY`는 반드시 실제 API 키로 교체해야 합니다!

### 3. Docker로 모든 서비스 실행

```bash
# 모든 서비스 시작 (최초 실행 시 이미지 빌드 포함)
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만 확인
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 4. 접속 확인

- **프론트엔드**: http://localhost
- **백엔드 API**: http://localhost/api
- **백엔드 Health Check**: http://localhost:8000/health
- **PostgreSQL**: localhost:5432 (kimedb / kime / dev123)
- **Redis**: localhost:6379

## 📦 실행 중인 서비스

| 서비스 | 컨테이너명 | 포트 | 설명 |
|--------|-----------|------|------|
| Frontend | frontend | 5173 (내부) | React + Vite |
| Backend | backend | 8000 | FastAPI |
| PostgreSQL | postgresql | 5432 | DB (pgvector 포함) |
| Redis | redis | 6379 | 캐시 |
| Nginx | nginx | 80 | 리버스 프록시 |

## 🔧 자주 사용하는 명령어

### 서비스 관리

```bash
# 모든 서비스 시작
docker-compose up -d

# 모든 서비스 중지
docker-compose down

# 특정 서비스만 재시작
docker-compose restart backend
docker-compose restart frontend

# 서비스 상태 확인
docker-compose ps

# 로그 보기 (실시간)
docker-compose logs -f

# 로그 보기 (최근 50줄)
docker-compose logs --tail=50
```

### 데이터베이스 접근

```bash
# PostgreSQL 접속
docker-compose exec postgres psql -U kime -d kimedb

# SQL 쿼리 실행
docker-compose exec -T postgres psql -U kime -d kimedb -c "SELECT * FROM users LIMIT 5;"
```

### 백엔드 명령 실행

```bash
# 마이그레이션 실행
docker-compose exec backend alembic upgrade head

# Python 스크립트 실행
docker-compose exec backend python scripts/your_script.py

# 백엔드 셸 접속
docker-compose exec backend bash
```

### 완전 초기화 (데이터 삭제)

```bash
# 컨테이너와 볼륨 모두 삭제 (주의: 데이터베이스 데이터 삭제됨!)
docker-compose down -v

# 다시 시작
docker-compose up -d
```

## 🆕 신규 기능: 회원가입 시 초기 크레딧 지급

### 자동 지급
- 신규 회원가입 시 자동으로 **200 버블** 지급
- 트랜잭션 로그 자동 기록

### 수동 지급 (기존 사용자)
기존 사용자들에게 소급 지급하려면:

```bash
docker-compose exec backend python scripts/grant_initial_credits_to_existing_users.py
```

### 테스트 계정 생성

```bash
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "test1234",
    "display_name": "테스트 유저",
    "email": "test@example.com"
  }'
```

회원가입 직후 크레딧 확인:

```bash
docker-compose exec -T postgres psql -U kime -d kimedb -c \
  "SELECT u.username, uc.bubble_count FROM users u
   LEFT JOIN user_credits uc ON u.user_id = uc.user_id
   WHERE u.username = 'testuser';"
```

## 🐛 문제 해결

### ⚠️ 시나리오 로드 실패 오류

**증상**: 채팅 시작 시 "시나리오를 불러올 수 없습니다" 오류 발생

**원인**:
1. `data/scenarios/` 디렉토리에 시나리오 JSON 파일이 없음
2. 잘못된 시나리오 ID 요청
3. JSON 파일 형식 오류

**해결 방법**:

#### 1단계: 시나리오 파일 확인
```bash
# 시나리오 파일 목록 확인
ls -la data/scenarios/

# 시나리오 파일이 없다면 확인
docker-compose exec backend ls -la /app/data/scenarios/
```

#### 2단계: 시나리오 ID 확인
```bash
# 사용 가능한 시나리오 목록 조회
curl -s http://localhost/api/scenarios | jq

# 또는 데이터베이스에서 직접 확인
docker-compose exec -T postgres psql -U kime -d kimedb -c \
  "SELECT scenario_id, scenario_name FROM scenarios;"
```

#### 3단계: 백엔드 로그 확인
```bash
# 시나리오 로딩 관련 에러 확인
docker-compose logs backend --tail=100 | grep -i scenario
docker-compose logs backend --tail=100 | grep -i error
```

#### 4단계: 데이터베이스 시나리오 테이블 확인
```bash
# 시나리오 테이블 존재 확인
docker-compose exec -T postgres psql -U kime -d kimedb -c "\dt scenarios"

# 시나리오 데이터 확인
docker-compose exec -T postgres psql -U kime -d kimedb -c \
  "SELECT scenario_id, scenario_name, is_active FROM scenarios;"
```

#### 5단계: 시나리오 데이터 재임포트 (필요시)
```bash
# 컨텐츠 데이터 임포트 스크립트 실행
docker-compose exec backend python scripts/import_content_data.py

# 성공 확인
docker-compose exec -T postgres psql -U kime -d kimedb -c \
  "SELECT COUNT(*) FROM scenarios;"
```

**프론트엔드 수정이 필요한 경우**:
```bash
# 프론트엔드에서 올바른 scenario_id 사용 확인
# front/src/data/scenarios.json 파일 확인
cat front/src/data/scenarios.json | jq
```

**빠른 해결 (권장)**:
```bash
# 1. 백엔드 재시작
docker-compose restart backend

# 2. 데이터베이스 확인
docker-compose exec -T postgres psql -U kime -d kimedb -c \
  "SELECT scenario_id FROM scenarios LIMIT 5;"

# 3. API 테스트
curl -s http://localhost/api/scenarios | jq
```

---

### 포트 충돌 오류
```bash
# 사용 중인 포트 확인 (macOS/Linux)
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :8000  # Backend
lsof -i :80    # Nginx

# 로컬에서 실행 중인 서비스 종료
brew services stop postgresql
brew services stop redis
```

### 컨테이너가 시작되지 않을 때
```bash
# 로그 확인
docker-compose logs <service-name>

# 컨테이너 재빌드
docker-compose up -d --build <service-name>
```

### 데이터베이스 연결 오류
```bash
# PostgreSQL 컨테이너 상태 확인
docker-compose ps postgres

# PostgreSQL 로그 확인
docker-compose logs postgres

# PostgreSQL 재시작
docker-compose restart postgres

# 데이터베이스 접속 테스트
docker-compose exec postgres psql -U kime -d kimedb -c "SELECT version();"
```

### 프론트엔드가 백엔드에 연결되지 않을 때
```bash
# Nginx 설정 확인
docker-compose exec nginx cat /etc/nginx/nginx.conf

# Nginx 재시작
docker-compose restart nginx

# 백엔드 Health Check
curl http://localhost:8000/health

# Nginx를 통한 백엔드 접근 테스트
curl http://localhost/api/health
```

### OPENAI_API_KEY 오류
```bash
# 환경변수 확인
docker-compose exec backend printenv | grep OPENAI

# .env 파일 확인
cat .env | grep OPENAI

# 환경변수 누락 시 재시작
docker-compose restart backend
```

## 📝 개발 워크플로우

### 1. 코드 변경 사항 적용

**프론트엔드** (React):
- Hot Reload 지원 - 코드 저장 시 자동 반영

**백엔드** (FastAPI):
- 파일 변경 시 자동 재로드
- 모델 변경 시 마이그레이션 필요:
  ```bash
  docker-compose exec backend alembic revision --autogenerate -m "description"
  docker-compose exec backend alembic upgrade head
  ```

### 2. Pull 후 작업

```bash
# 최신 코드 받기
git pull

# 의존성이 변경되었을 수 있으므로 재빌드
docker-compose up -d --build

# 마이그레이션 실행 (DB 스키마 변경 시)
docker-compose exec backend alembic upgrade head
```

### 3. 브랜치 전환 시

```bash
# 브랜치 전환
git checkout <branch-name>

# 서비스 재시작
docker-compose restart backend frontend
```

## 🔐 보안 주의사항

1. **절대로 `.env` 파일을 Git에 커밋하지 마세요!**
   - `.gitignore`에 이미 추가되어 있습니다

2. **OPENAI_API_KEY는 팀 내부에서만 공유**
   - Slack이나 안전한 채널로 공유하세요

3. **운영 환경 배포 시**:
   - `JWT_SECRET_KEY`를 강력한 랜덤 문자열로 변경
   - `DB_PASSWORD`를 강력한 비밀번호로 변경
   - `ENVIRONMENT=production` 설정

## 📚 추가 문서

- [DOCKER_RESTART_GUIDE.md](DOCKER_RESTART_GUIDE.md) - 상세한 Docker 관리 가이드
- [DATA_MIGRATION_COMPLETE.md](DATA_MIGRATION_COMPLETE.md) - 데이터 마이그레이션 내역
- [FINAL_MIGRATION_COMPLETE.md](FINAL_MIGRATION_COMPLETE.md) - 최종 마이그레이션 상태

## 💡 유용한 팁

### VSCode 사용자

1. **Docker Extension** 설치 추천
   - 컨테이너 상태를 GUI로 확인
   - 로그 쉽게 보기

2. **데이터베이스 Extension** 설치 추천
   - PostgreSQL에 직접 연결
   - 연결 정보: `postgresql://kime:dev123@localhost:5432/kimedb`

### 로그 필터링

```bash
# 에러만 보기
docker-compose logs backend | grep ERROR

# 특정 키워드 검색
docker-compose logs backend | grep "register_user"
```

## 🆘 문제가 해결되지 않을 때

1. **완전 초기화 후 재시작**:
   ```bash
   docker-compose down -v
   docker-compose up -d
   docker-compose exec backend alembic upgrade head
   ```

2. **Docker 캐시 삭제**:
   ```bash
   docker system prune -a
   docker-compose up -d --build
   ```

3. **팀원에게 도움 요청**:
   - 에러 로그 전체를 복사해서 공유
   - 실행한 명령어와 환경 정보 제공

---

**질문이 있으시면 언제든지 팀 채널에 문의하세요!** 🙌
