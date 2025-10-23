# 🐳 Docker 실행 가이드

Kime Chat Agent를 Docker로 실행하는 방법입니다.

## 사전 준비

### 1. Docker 설치 확인
```bash
docker --version
docker-compose --version
```

### 2. 환경 변수 설정
`.env` 파일을 생성하고 API 키를 설정하세요:

```bash
cp .env.example .env
nano .env  # 또는 원하는 에디터 사용
```

`.env` 파일 내용:
```bash
OPENAI_API_KEY=your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
DEBUG=false
USE_LLM=true
```

## 빠른 시작

### 방법 1: Docker Compose (권장)

```bash
# 빌드 및 실행 (한 번에)
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### 방법 2: Docker 직접 실행

```bash
# 1. 이미지 빌드
docker build -t kime-chat-agent .

# 2. 컨테이너 실행
docker run -it \
  --name kime-chat-agent \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  kime-chat-agent

# 3. 컨테이너 중지
docker stop kime-chat-agent

# 4. 컨테이너 삭제
docker rm kime-chat-agent
```

## 주요 명령어

### 컨테이너 관리
```bash
# 실행 중인 컨테이너 확인
docker ps

# 모든 컨테이너 확인
docker ps -a

# 컨테이너 재시작
docker-compose restart

# 컨테이너 접속 (쉘)
docker exec -it kime-chat-agent /bin/bash
```

### 로그 및 디버깅
```bash
# 실시간 로그 확인
docker-compose logs -f kime-chat-agent

# 최근 100줄 로그
docker-compose logs --tail 100 kime-chat-agent

# 컨테이너 내부에서 디버그
docker exec -it kime-chat-agent python -c "import sys; print(sys.path)"
```

### 이미지 관리
```bash
# 이미지 목록
docker images

# 이미지 삭제
docker rmi kime-chat-agent

# 사용하지 않는 이미지 정리
docker image prune
```

## 트러블슈팅

### 1. API 키 오류
```bash
# .env 파일 확인
cat .env

# 환경 변수 재로드
docker-compose down
docker-compose up --build
```

### 2. 포트 충돌
```bash
# 포트 사용 확인
lsof -i :8000

# 다른 포트 사용 (docker-compose.yml 수정)
ports:
  - "8001:8000"
```

### 3. 볼륨 권한 문제
```bash
# 로그 디렉토리 권한 설정
chmod -R 755 logs/
chmod -R 755 data/
```

### 4. 빌드 실패
```bash
# 캐시 없이 재빌드
docker-compose build --no-cache

# 이미지 강제 재생성
docker-compose up --build --force-recreate
```

## 데이터 영구 저장

Docker 볼륨을 통해 다음 디렉토리가 호스트와 동기화됩니다:

- `./logs` → `/app/logs` (로그 파일)
- `./data` → `/app/data` (시나리오 데이터)

컨테이너를 삭제해도 이 데이터는 보존됩니다.

## 프로덕션 배포

### 환경 변수 분리
```bash
# 개발 환경
docker-compose -f docker-compose.yml up

# 프로덕션 환경
docker-compose -f docker-compose.prod.yml up
```

### 리소스 제한
```yaml
# docker-compose.yml에 추가
services:
  kime-chat-agent:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## 팀원 온보딩

새로운 팀원이 프로젝트를 시작할 때:

```bash
# 1. 저장소 클론
git clone <repository-url>
cd kime_chat_agent

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 3. Docker로 즉시 실행
docker-compose up --build

# 완료! 별도의 Python 환경 설정 불필요
```

## 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 가이드](https://docs.docker.com/compose/)
- 프로젝트 README: [README.md](README.md)
