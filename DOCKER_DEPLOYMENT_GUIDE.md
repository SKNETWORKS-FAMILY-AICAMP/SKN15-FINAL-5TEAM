# Docker 배포 가이드 - KIME Chat

## 목차
1. [개요](#개요)
2. [사전 요구사항](#사전-요구사항)
3. [프로젝트 구조](#프로젝트-구조)
4. [환경 설정](#환경-설정)
5. [빌드 및 실행](#빌드-및-실행)
6. [개별 서비스 실행](#개별-서비스-실행)
7. [모니터링 및 로그](#모니터링-및-로그)
8. [트러블슈팅](#트러블슈팅)
9. [프로덕션 배포](#프로덕션-배포)
10. [유지보수](#유지보수)

---

## 개요

이 프로젝트는 Docker를 사용하여 마이크로서비스 아키텍처로 구성되어 있습니다:

- **Frontend**: React + Vite + Nginx
- **Backend**: FastAPI + LangGraph + Python
- **Database**: PostgreSQL + pgvector (벡터 검색)
- **Cache**: Redis (세션 및 캐시)

각 서비스는 독립적인 Docker 이미지로 빌드되며, `docker-compose`로 통합 관리됩니다.

---

## 사전 요구사항

### 1. Docker 설치
```bash
# Docker 버전 확인 (20.10 이상 권장)
docker --version

# Docker Compose 버전 확인 (2.0 이상 권장)
docker-compose --version
```

**설치 방법**:
- Mac: [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)
- Linux: `sudo apt-get install docker docker-compose`
- Windows: [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)

### 2. 환경 변수 설정
```bash
# 루트 디렉토리에서 실행
cp .env.example .env

# .env 파일을 에디터로 열어 필수 값 입력
vi .env  # 또는 nano, code 등 사용
```

**필수 설정 항목**:
- `OPENAI_API_KEY`: OpenAI API 키 (필수)
- `JWT_SECRET_KEY`: JWT 토큰 서명 키 (최소 32자)
- `DB_PASSWORD`: PostgreSQL 비밀번호
- `REDIS_PASSWORD`: Redis 비밀번호

---

## 프로젝트 구조

```
workspace/
├── docker-compose.yml          # 전체 스택 오케스트레이션
├── .env.example                # 환경변수 템플릿
├── .env                        # 실제 환경변수 (Git 제외)
├── .dockerignore               # Docker 빌드 제외 파일
│
├── backend/
│   ├── Dockerfile              # Backend 이미지 (Multi-stage)
│   ├── .dockerignore           # Backend 빌드 제외
│   ├── requirements.txt        # Python 의존성
│   ├── api_server.py           # FastAPI 진입점
│   └── src/                    # 소스 코드
│
└── front/
    ├── Dockerfile              # Frontend 이미지 (Multi-stage)
    ├── nginx.conf              # Nginx 설정
    ├── .dockerignore           # Frontend 빌드 제외
    ├── package.json            # Node 의존성
    └── src/                    # React 소스 코드
```

---

## 환경 설정

### `.env` 파일 예시

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=secure_password_123

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password_123

# OpenAI
OPENAI_API_KEY=sk-your-api-key-here

# JWT
JWT_SECRET_KEY=your-long-secret-key-min-32-chars
JWT_ALGORITHM=HS256

# Application
DEBUG=false
USE_LLM=true
VITE_API_URL=http://localhost:8000
```

---

## 빌드 및 실행

### 1. 전체 스택 실행 (권장)

```bash
# 모든 서비스 빌드 및 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만 보기
docker-compose logs -f backend
```

### 2. 실행 후 접속

- **Frontend**: http://localhost:80
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 3. 서비스 확인

```bash
# 실행 중인 컨테이너 확인
docker-compose ps

# 헬스체크 확인
curl http://localhost:8000/health
curl http://localhost:80/health
```

### 4. 종료 및 정리

```bash
# 서비스 중지
docker-compose down

# 볼륨까지 삭제 (데이터베이스 데이터 포함)
docker-compose down -v

# 이미지까지 삭제
docker-compose down --rmi all
```

---

## 개별 서비스 실행

각 서비스를 독립적으로 실행할 수도 있습니다.

### Backend만 실행

```bash
cd backend

# 이미지 빌드
docker build -t kime-backend:latest .

# 컨테이너 실행
docker run -d \
  --name kime-backend \
  -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  -e DB_NAME=kimedb \
  -e DB_USER=kime \
  -e DB_PASSWORD=dev123 \
  -e OPENAI_API_KEY=your-key \
  -e JWT_SECRET_KEY=your-secret \
  kime-backend:latest

# 로그 확인
docker logs -f kime-backend
```

### Frontend만 실행

```bash
cd front

# 이미지 빌드
docker build -t kime-frontend:latest .

# 컨테이너 실행
docker run -d \
  --name kime-frontend \
  -p 80:80 \
  kime-frontend:latest

# 로그 확인
docker logs -f kime-frontend
```

### PostgreSQL만 실행

```bash
docker run -d \
  --name kime-postgres \
  -p 5432:5432 \
  -e POSTGRES_DB=kimedb \
  -e POSTGRES_USER=kime \
  -e POSTGRES_PASSWORD=dev123 \
  -v postgres_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg15
```

### Redis만 실행

```bash
docker run -d \
  --name kime-redis \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --requirepass dev123
```

---

## 모니터링 및 로그

### 실시간 로그 확인

```bash
# 모든 서비스 로그
docker-compose logs -f

# 특정 서비스만
docker-compose logs -f backend
docker-compose logs -f frontend

# 최근 N줄만 보기
docker-compose logs --tail=100 backend
```

### 컨테이너 리소스 사용량

```bash
# CPU, 메모리 사용량 실시간 모니터링
docker stats

# 특정 컨테이너만
docker stats kime-backend kime-frontend
```

### 컨테이너 접속 (디버깅)

```bash
# Backend 컨테이너 접속
docker exec -it kime-backend /bin/bash

# Frontend 컨테이너 접속
docker exec -it kime-frontend /bin/sh

# PostgreSQL 접속
docker exec -it kime-postgres psql -U kime -d kimedb

# Redis CLI 접속
docker exec -it kime-redis redis-cli -a dev123
```

---

## 트러블슈팅

### 1. 포트 충돌

**문제**: "Bind for 0.0.0.0:8000 failed: port is already allocated"

**해결**:
```bash
# 포트 사용 프로세스 확인
lsof -i :8000

# 프로세스 종료
kill -9 <PID>

# 또는 docker-compose.yml에서 포트 변경
ports:
  - "8001:8000"  # 호스트:컨테이너
```

### 2. 데이터베이스 연결 실패

**문제**: "connection to server failed"

**해결**:
```bash
# PostgreSQL 컨테이너 상태 확인
docker-compose ps postgres

# 헬스체크 확인
docker inspect kime-postgres | grep Health -A 10

# 로그 확인
docker-compose logs postgres

# 컨테이너 재시작
docker-compose restart postgres
```

### 3. Frontend 빌드 실패

**문제**: "npm install failed"

**해결**:
```bash
# node_modules 삭제 후 재빌드
cd front
rm -rf node_modules
docker-compose build --no-cache frontend
```

### 4. Backend 의존성 오류

**문제**: "ModuleNotFoundError"

**해결**:
```bash
# 캐시 없이 재빌드
docker-compose build --no-cache backend

# requirements.txt 확인
cat backend/requirements.txt

# 컨테이너 내부에서 확인
docker exec -it kime-backend pip list
```

### 5. 이미지 크기 최적화

**현재 이미지 크기 확인**:
```bash
docker images | grep kime
```

**최적화 방법**:
- Multi-stage build 사용 (이미 적용됨)
- `.dockerignore`에 불필요한 파일 추가
- Alpine 베이스 이미지 사용 (Frontend에 적용됨)

---

## 프로덕션 배포

### 1. AWS ECS/Fargate 배포

```bash
# 1. ECR에 이미지 푸시
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com

# 2. 이미지 태그
docker tag kime-backend:latest <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/kime-backend:latest

# 3. 푸시
docker push <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/kime-backend:latest
```

### 2. Docker Hub 배포

```bash
# 1. Docker Hub 로그인
docker login

# 2. 이미지 태그
docker tag kime-backend:latest your-username/kime-backend:1.0.0

# 3. 푸시
docker push your-username/kime-backend:1.0.0
```

### 3. 환경별 설정

**docker-compose.prod.yml** (프로덕션용):
```yaml
version: '3.8'
services:
  backend:
    image: <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/kime-backend:latest
    environment:
      DEBUG: false
      DB_HOST: your-rds-endpoint.amazonaws.com
      REDIS_HOST: your-elasticache-endpoint.amazonaws.com
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
```

**실행**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 유지보수

### 정기 점검 항목

```bash
# 1. 디스크 사용량 확인
docker system df

# 2. 사용하지 않는 이미지/컨테이너 정리
docker system prune -a

# 3. 볼륨 백업 (PostgreSQL)
docker run --rm \
  -v kime-postgres-data:/source \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/postgres-backup-$(date +%Y%m%d).tar.gz -C /source .

# 4. 로그 로테이션 설정 (docker-compose.yml에 추가)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 업데이트 프로세스

```bash
# 1. 최신 코드 pull
git pull origin main

# 2. 이미지 재빌드
docker-compose build

# 3. 무중단 배포 (Blue-Green)
docker-compose up -d --no-deps --build backend

# 4. 헬스체크 확인
curl http://localhost:8000/health

# 5. 문제 없으면 기존 컨테이너 제거
docker-compose down --remove-orphans
```

---

## 보안 고려사항

### 1. 환경 변수 보안
- `.env` 파일을 절대 Git에 커밋하지 마세요
- AWS Secrets Manager 또는 HashiCorp Vault 사용 권장

### 2. 네트워크 격리
```yaml
# docker-compose.yml
networks:
  frontend:
  backend:
    internal: true  # 외부 접근 차단
```

### 3. Non-root 사용자
- 모든 Dockerfile에서 non-root 사용자로 실행 (이미 적용됨)

### 4. 이미지 스캔
```bash
# Trivy로 보안 취약점 스캔
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image kime-backend:latest
```

---

## 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Dockerfile 최적화 가이드](https://docs.docker.com/develop/dev-best-practices/)
- [pgvector 문서](https://github.com/pgvector/pgvector)

---

## 문의 및 지원

문제가 발생하면 다음 정보와 함께 이슈를 제출해주세요:
1. Docker 버전 (`docker --version`)
2. OS 정보 (`uname -a` 또는 `ver`)
3. 에러 로그 (`docker-compose logs`)
4. docker-compose.yml 설정 (민감 정보 제외)
