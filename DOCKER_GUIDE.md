# Docker 배포 가이드

KIME Chat 프로젝트의 Docker 기반 배포 가이드입니다.

## 📋 목차

1. [시스템 구성](#시스템-구성)
2. [사전 요구사항](#사전-요구사항)
3. [환경 변수 설정](#환경-변수-설정)
4. [빠른 시작](#빠른-시작)
5. [개별 서비스 관리](#개별-서비스-관리)
6. [프로덕션 배포](#프로덕션-배포)
7. [트러블슈팅](#트러블슈팅)

---

## 🏗️ 시스템 구성

```
┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend   │
│  (Vite)     │     │  (FastAPI)  │
│  Port: 5173 │     │  Port: 8000 │
└─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌──────────┐
              │ Postgres │  │  Redis   │
              │ + Vector │  │  Cache   │
              │ Port:5432│  │ Port:6379│
              └──────────┘  └──────────┘
```

### 서비스 구성

| 서비스 | 이미지 | 포트 | 역할 |
|--------|--------|------|------|
| **frontend** | node:20-alpine | 5173 | React + Vite UI |
| **backend** | python:3.11-slim | 8000 | FastAPI 서버 |
| **postgres** | ankane/pgvector | 5432 | 메인 DB + 벡터 검색 |
| **redis** | redis:7-alpine | 6379 | 캐시 + 세션 |

---

## 📦 사전 요구사항

### 필수 소프트웨어

- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+

### 설치 확인

```bash
docker --version
docker-compose --version
```

---

## ⚙️ 환경 변수 설정

### 1. .env 파일 생성

```bash
cp .env.example .env
```

### 2. 필수 환경 변수

`.env` 파일에 다음 값들을 설정하세요:

```env
# Database
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=your-strong-password-here
DB_PORT=5432

# Redis
REDIS_PASSWORD=your-redis-password-here
REDIS_PORT=6379

# OpenAI (필수!)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx

# JWT Security
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# App Configuration
FRONTEND_URL=http://localhost:5173
BACKEND_PORT=8000
FRONTEND_PORT=5173
VITE_API_BASE_URL=http://localhost:8000
ENVIRONMENT=development
```

⚠️ **보안 주의사항**
- 프로덕션 환경에서는 반드시 강력한 비밀번호 사용
- `.env` 파일을 Git에 커밋하지 마세요 (이미 .gitignore에 포함됨)

---

## 🚀 빠른 시작

### 개발 환경 (전체 스택 실행)

```bash
# 1. 모든 서비스 시작
docker-compose up -d

# 2. 로그 확인
docker-compose logs -f

# 3. 서비스 상태 확인
docker-compose ps
```

**접속 URL:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 서비스 종료

```bash
# 서비스만 중지 (데이터 보존)
docker-compose stop

# 서비스 삭제 (데이터 보존)
docker-compose down

# 서비스 + 볼륨 삭제 (데이터 삭제)
docker-compose down -v
```

---

## 🔧 개별 서비스 관리

### 특정 서비스만 시작

```bash
# 데이터베이스만
docker-compose up -d postgres redis

# 백엔드만 (DB 의존성 자동 시작)
docker-compose up -d backend

# 프론트엔드만
docker-compose up -d frontend
```

### 서비스 재시작

```bash
# 백엔드 재시작
docker-compose restart backend

# 모든 서비스 재시작
docker-compose restart
```

### 로그 확인

```bash
# 전체 로그
docker-compose logs

# 특정 서비스 로그 (실시간)
docker-compose logs -f backend

# 최근 100줄만
docker-compose logs --tail=100 backend
```

### 컨테이너 접속

```bash
# 백엔드 컨테이너 접속
docker-compose exec backend /bin/bash

# PostgreSQL 접속
docker-compose exec postgres psql -U kime -d kimedb

# Redis CLI 접속
docker-compose exec redis redis-cli -a your-redis-password
```

---

## 🏭 프로덕션 배포

### 1. 프로덕션 빌드

```bash
# 프로덕션 이미지 빌드
docker-compose build --no-cache

# 백그라운드 실행
docker-compose up -d
```

### 2. Health Check 확인

```bash
# 백엔드 헬스체크
curl http://localhost:8000/health

# 프론트엔드 헬스체크
curl http://localhost:5173/health
```

### 3. 리소스 모니터링

```bash
# 컨테이너 리소스 사용량
docker stats

# 특정 서비스만
docker stats kime-backend kime-postgres
```

### 4. 백업

```bash
# PostgreSQL 백업
docker-compose exec postgres pg_dump -U kime kimedb > backup_$(date +%Y%m%d).sql

# Redis 백업
docker-compose exec redis redis-cli -a your-password SAVE
```

---

## 🔍 트러블슈팅

### 문제 1: 포트 충돌

**증상**: `port is already allocated` 에러

**해결**:
```bash
# 사용 중인 포트 확인
sudo lsof -i :5173
sudo lsof -i :8000
sudo lsof -i :5432

# .env에서 포트 변경
BACKEND_PORT=8001
FRONTEND_PORT=5174
```

### 문제 2: 데이터베이스 연결 실패

**증상**: `connection refused` 또는 `could not connect to server`

**해결**:
```bash
# 1. PostgreSQL 컨테이너 상태 확인
docker-compose ps postgres

# 2. PostgreSQL 로그 확인
docker-compose logs postgres

# 3. 헬스체크 확인
docker-compose exec postgres pg_isready -U kime

# 4. 데이터베이스 재시작
docker-compose restart postgres
```

### 문제 3: 백엔드가 시작되지 않음

**증상**: 백엔드 컨테이너가 계속 재시작됨

**해결**:
```bash
# 1. 상세 로그 확인
docker-compose logs --tail=100 backend

# 2. 환경 변수 확인
docker-compose exec backend env | grep -E "DB_|REDIS_|OPENAI_"

# 3. 의존성 재설치
docker-compose build --no-cache backend
docker-compose up -d backend
```

### 문제 4: Redis 연결 오류

**증상**: `NOAUTH Authentication required`

**해결**:
```bash
# Redis 비밀번호 확인
docker-compose exec redis redis-cli -a your-password ping

# .env 파일의 REDIS_PASSWORD 확인
```

### 문제 5: 프론트엔드 빌드 실패

**증상**: `npm install` 또는 `npm run build` 실패

**해결**:
```bash
# 1. node_modules 삭제 후 재빌드
docker-compose down frontend
docker volume rm myproject_frontend_node_modules
docker-compose build --no-cache frontend
docker-compose up -d frontend

# 2. 로컬에서 빌드 테스트
cd front
npm install
npm run build
```

### 문제 6: 볼륨 권한 오류

**증상**: `Permission denied` 에러

**해결**:
```bash
# 볼륨 권한 확인
docker-compose exec backend ls -la /app

# 볼륨 재생성
docker-compose down -v
docker-compose up -d
```

---

## 📊 유용한 명령어

### 컨테이너 정리

```bash
# 사용하지 않는 컨테이너 삭제
docker container prune

# 사용하지 않는 이미지 삭제
docker image prune -a

# 사용하지 않는 볼륨 삭제
docker volume prune

# 모두 삭제 (주의!)
docker system prune -a --volumes
```

### 디버깅

```bash
# 컨테이너 프로세스 확인
docker-compose top

# 컨테이너 내부 쉘 접속
docker-compose exec backend sh

# 파일 복사 (컨테이너 → 호스트)
docker cp kime-backend:/app/logs/error.log ./error.log

# 파일 복사 (호스트 → 컨테이너)
docker cp ./config.json kime-backend:/app/config.json
```

---

## 📚 추가 리소스

- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [PostgreSQL + pgvector](https://github.com/pgvector/pgvector)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
- [Vite 프로덕션 빌드](https://vitejs.dev/guide/build.html)

---

**문제가 계속되면 GitHub Issues에 보고해주세요!**
