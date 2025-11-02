# KIME Chat 완전 배포 가이드

**작성일**: 2025-11-03
**목적**: AWS 프로덕션 환경에 KIME Chat 전체 시스템 배포
**소요 시간**: 약 2-3시간

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [Phase 1: 데이터베이스 설정](#phase-1-데이터베이스-설정-30분)
3. [Phase 2: 백엔드 배포](#phase-2-백엔드-배포-60분)
4. [Phase 3: 프론트엔드 배포](#phase-3-프론트엔드-배포-30분)
5. [Phase 4: 검증 및 테스트](#phase-4-검증-및-테스트-30분)
6. [문제 해결](#문제-해결)

---

## 1. 사전 준비

### 1.1 필요한 정보 확인

배포 전에 다음 정보를 확인하세요:

```bash
# AWS 인프라 정보
ALB DNS: kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com
RDS Endpoint: kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com:5432
Redis Endpoint: clustercfg.kime-redis-subnet-group.yp94db.apn2.cache.amazonaws.com:6379

# EC2 인스턴스
Frontend-1: 10.0.10.60 (Bastion Host)
Frontend-2: 10.0.20.108
Backend-1: 10.0.175.166 (Private)
Backend-2: 10.0.176.124 (Private)

# SSH 키
Key file: ~/.ssh/kime-key.pem
```

### 1.2 로컬 환경 확인

```bash
# 1. Git 상태 확인 (모든 변경사항 커밋)
cd /Users/jtm427/Desktop/workspace
git status

# 2. Backend 환경 변수 확인
cat backend/.env.production

# 필수 변수 확인:
# - DB_HOST=kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com
# - DB_PORT=5432
# - DB_NAME=kimedb
# - DB_USER=kime
# - DB_PASSWORD=<실제 비밀번호>
# - REDIS_HOST=clustercfg.kime-redis-subnet-group.yp94db.apn2.cache.amazonaws.com
# - REDIS_PORT=6379
# - OPENAI_API_KEY=<실제 키>

# 3. Frontend 환경 변수 확인
cat front/.env

# 필수 변수 확인:
# - VITE_API_URL=http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com
# - VITE_CDN_URL=/images

# 4. Frontend 빌드 확인
cd front
npm run build

# dist 폴더 생성 확인
ls -la dist/
```

---

## Phase 1: 데이터베이스 설정 (30분)

### Step 1.1: RDS 마이그레이션 실행

**목적**: RDS PostgreSQL에 11개 마이그레이션 SQL 파일 실행

```bash
# 1. backend/scripts 디렉토리로 이동
cd /Users/jtm427/Desktop/workspace/backend/scripts

# 2. 마이그레이션 스크립트 실행 권한 확인
chmod +x run_migrations.sh

# 3. 마이그레이션 실행 (production 환경)
./run_migrations.sh production
```

**예상 출력**:
```
==========================================
RDS Migration Script
Environment: production
==========================================
Loading environment from ../.env.production...

Database Connection Info:
- Host: kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com
- Port: 5432
- Database: kimedb
- User: kime

Testing database connection...
✅ Database connection successful!

==========================================
Running Migrations...
==========================================

📄 Running: 001_initial_schema.sql
   ✅ Success

📄 Running: 002_add_embeddings.sql
   ✅ Success

... (11개 마이그레이션 모두 성공)

==========================================
✅ All migrations completed successfully!
==========================================
```

**문제 발생 시**:
- `psql: command not found` → PostgreSQL 클라이언트 설치 필요
- `connection refused` → RDS 보안 그룹 확인 (포트 5432 허용 여부)
- `authentication failed` → .env.production의 DB_PASSWORD 확인

### Step 1.2: 시나리오 시드 데이터 로드

**목적**: 6개 시나리오 데이터를 RDS에 삽입

```bash
# 1. Python 가상환경 활성화 (있다면)
# source venv/bin/activate

# 2. 시드 스크립트 실행 (production 환경)
python3 seed_scenarios.py production
```

**예상 출력**:
```
🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱
     Scenario Database Seeding Script
🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱🌱

🌍 Environment: PRODUCTION
📄 Loading: /Users/jtm427/Desktop/workspace/backend/.env.production

📡 Connecting to database: kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com:5432/kimedb
✅ Database connection established

==========================================
  Seeding Scenarios
==========================================

✅ Inserted scenario: tanjiro - 편의점 알바생 탄지로
✅ Inserted scenario: train - 무한열차
✅ Inserted scenario: infinity-castle - 무한성
✅ Inserted scenario: ending - 엔딩 이후
✅ Inserted scenario: counseling - 귀칼 상담소 AU
✅ Inserted scenario: idol - 아이돌/밴드 AU

📊 Scenarios: 6 inserted, 0 errors

==========================================
  Seeding Scenario Statistics
==========================================

✅ Inserted statistics: tanjiro (likes: 121, views: 1200)
... (6개 통계 삽입)

📊 Statistics: 6 inserted, 0 errors

==========================================
  Verification
==========================================

✅ Scenarios table: 6 records
✅ Statistics table: 6 records
✅ View (v_scenario_cards): 6 records

✅ ✨ All scenarios seeded successfully!

🎉 Seeding complete! HomePage can now load scenarios from database.
```

### Step 1.3: 데이터 검증

```bash
# RDS에 직접 접속하여 확인
PGPASSWORD=<비밀번호> psql \
  -h kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com \
  -p 5432 \
  -U kime \
  -d kimedb

# PostgreSQL 쉘에서 확인
\dt statedb.*        # 테이블 목록 확인
\dt public.*
\dt logdb.*

SELECT COUNT(*) FROM statedb.scenarios;           # 6 예상
SELECT COUNT(*) FROM statedb.scenario_statistics; # 6 예상
SELECT * FROM statedb.v_scenario_cards;           # 6개 시나리오 전체 정보

\q  # 종료
```

**예상 결과**:
- `statedb` 스키마: 14개 테이블
- `public` 스키마: 2개 테이블 (training_logs, feedback)
- `logdb` 스키마: 3개 테이블 (logs, error_logs, performance_metrics)
- `scenarios`: 6개 레코드
- `scenario_statistics`: 6개 레코드

---

## Phase 2: 백엔드 배포 (60분)

### Step 2.1: 배포 스크립트 확인

**backend/deploy_to_aws.sh 확인**:

```bash
cd /Users/jtm427/Desktop/workspace/backend
cat deploy_to_aws.sh
```

**주요 내용 확인**:
```bash
# Backend-1, Backend-2 IP 주소 확인
BACKEND_1_IP="10.0.175.166"
BACKEND_2_IP="10.0.176.124"

# Bastion Host IP (Frontend-1 통해 접속)
BASTION_IP="10.0.10.60"

# 배포 명령어 확인
# ./deploy_to_aws.sh backend-1  # Backend-1에 배포
# ./deploy_to_aws.sh backend-2  # Backend-2에 배포
```

### Step 2.2: Backend-1 배포

```bash
# 1. 배포 스크립트 실행 권한 확인
chmod +x deploy_to_aws.sh

# 2. Backend-1에 배포
./deploy_to_aws.sh backend-1
```

**배포 과정**:
1. Bastion Host (Frontend-1)를 거쳐 Backend-1에 SSH 접속
2. 기존 backend 디렉토리 백업
3. 새 코드 업로드 (rsync)
4. Python 의존성 설치
5. .env.production 복사
6. API 서버 재시작

**예상 출력**:
```
==========================================
Deploying to backend-1 (10.0.175.166)
==========================================

[1/6] Connecting via bastion host...
✅ SSH connection successful

[2/6] Backing up existing code...
✅ Backup created: /home/ubuntu/backend.backup.2025-11-03_12-30-45

[3/6] Uploading new code...
building file list ... done
./
api_server.py
...
✅ Code uploaded successfully

[4/6] Installing dependencies...
✅ Dependencies installed

[5/6] Setting up environment...
✅ Environment configured

[6/6] Restarting API server...
✅ API server restarted (PID: 12345)

==========================================
✅ Deployment to backend-1 complete!
==========================================

Health Check:
  curl http://10.0.175.166:8000/api/health
  → {"status": "healthy"}
```

### Step 2.3: Backend-2 배포

```bash
# Backend-2에 배포 (동일한 과정)
./deploy_to_aws.sh backend-2
```

### Step 2.4: 백엔드 Health Check

```bash
# ALB를 통한 백엔드 확인
curl http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com/api/health

# 예상 응답:
# {"status": "healthy", "timestamp": "2025-11-03T12:30:45Z"}
```

---

## Phase 3: 프론트엔드 배포 (30분)

### Step 3.1: 프론트엔드 빌드 확인

```bash
cd /Users/jtm427/Desktop/workspace/front

# 최종 빌드
npm run build

# dist 폴더 확인
ls -la dist/

# 예상 파일:
# - index.html
# - assets/index-B2o9aTkz.js (323 kB)
# - assets/index-zTGyuh8a.css (49 kB)
```

### Step 3.2: Frontend-1 배포

```bash
# 1. SSH로 Frontend-1 접속
ssh -i ~/.ssh/kime-key.pem ubuntu@10.0.10.60

# 2. 기존 파일 백업
sudo mkdir -p /var/www/html.backup.$(date +%Y%m%d_%H%M%S)
sudo cp -r /var/www/html/* /var/www/html.backup.$(date +%Y%m%d_%H%M%S)/

# 3. 기존 파일 삭제 (이미지 제외)
sudo rm -rf /var/www/html/*.html
sudo rm -rf /var/www/html/assets

# 4. 새 파일 업로드 (로컬에서 실행)
exit  # SSH 종료 후 로컬에서

# rsync로 dist 파일 복사
rsync -avz -e "ssh -i ~/.ssh/kime-key.pem" \
  /Users/jtm427/Desktop/workspace/front/dist/ \
  ubuntu@10.0.10.60:/tmp/frontend-dist/

# 다시 SSH 접속
ssh -i ~/.ssh/kime-key.pem ubuntu@10.0.10.60

# 5. 파일 이동 및 권한 설정
sudo cp -r /tmp/frontend-dist/* /var/www/html/
sudo chown -R www-data:www-data /var/www/html
sudo chmod -R 755 /var/www/html

# 6. Nginx 설정 확인 (SPA 라우팅)
sudo nano /etc/nginx/sites-available/default
```

**Nginx 설정 확인** (`/etc/nginx/sites-available/default`):
```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.html;

    server_name _;

    # SPA 라우팅 (React Router 지원)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 이미지 캐싱
    location /images/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API 프록시 (선택사항, ALB 사용 시 불필요)
    # location /api/ {
    #     proxy_pass http://backend-private-ip:8000;
    # }
}
```

**Nginx 재시작**:
```bash
# 설정 테스트
sudo nginx -t

# 재시작
sudo systemctl restart nginx

# 상태 확인
sudo systemctl status nginx
```

### Step 3.3: Frontend-2 배포

```bash
# Frontend-2에도 동일하게 배포
# (Frontend-1과 동일한 과정 반복)

ssh -i ~/.ssh/kime-key.pem ubuntu@10.0.20.108
# ... (위와 동일)
```

### Step 3.4: ALB Target Group 확인

```bash
# AWS Console에서 확인:
# EC2 → Load Balancers → kime-alb → Target Groups

# Frontend Target Group:
# - frontend-1 (10.0.10.60:80) → healthy
# - frontend-2 (10.0.20.108:80) → healthy

# Backend Target Group:
# - backend-1 (10.0.175.166:8000) → healthy
# - backend-2 (10.0.176.124:8000) → healthy
```

---

## Phase 4: 검증 및 테스트 (30분)

### Step 4.1: 브라우저 테스트

```
1. 브라우저에서 접속:
   http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com

2. 홈페이지 확인:
   - 6개 시나리오 카드가 표시되는지 확인
   - 이미지가 정상적으로 로드되는지 확인
   - 로딩 스피너가 나타났다가 사라지는지 확인

3. 회원가입 테스트:
   - 우측 상단 "로그인" 클릭
   - "회원가입" 탭 클릭
   - 테스트 계정 생성:
     - 이메일: test@kime.com
     - 비밀번호: test1234
     - 이름: 테스트유저

4. 로그인 테스트:
   - 방금 생성한 계정으로 로그인
   - JWT 토큰이 localStorage에 저장되는지 확인 (F12 → Application → Local Storage)

5. 시나리오 상세 페이지:
   - "무한열차" 카드 클릭
   - 시나리오 정보가 로드되는지 확인
   - 좋아요 버튼 클릭 (즉시 UI 반영되는지 확인)

6. 채팅 테스트:
   - "채팅 시작" 버튼 클릭
   - 세션 복원 모달이 뜨는지 확인 (이전 대화 없으면 안 뜸)
   - "새로 시작" 클릭
   - 메시지 입력: "안녕하세요"
   - AI 응답이 오는지 확인 (10-15초 소요)
```

### Step 4.2: API 엔드포인트 테스트

```bash
# 1. Health Check
curl http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com/api/health

# 예상 응답:
# {"status": "healthy"}

# 2. 시나리오 목록 조회
curl http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com/api/scenarios/list

# 예상 응답:
# [
#   {
#     "scenario_id": "tanjiro",
#     "title": "편의점 알바생 탄지로",
#     ...
#   },
#   ... (6개 시나리오)
# ]

# 3. 회원가입 (cURL)
curl -X POST http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "curl_test@kime.com",
    "password": "test1234",
    "username": "CurlTest",
    "display_name": "Curl 테스트"
  }'

# 예상 응답:
# {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "user_id": "...",
#   "username": "CurlTest"
# }

# 4. 로그인
curl -X POST http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "curl_test@kime.com",
    "password": "test1234"
  }'

# 5. 인증 필요 API (JWT 토큰 사용)
TOKEN="<위에서 받은 access_token>"

curl http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# 예상 응답:
# {
#   "user_id": "...",
#   "username": "CurlTest",
#   "email": "curl_test@kime.com",
#   "display_name": "Curl 테스트"
# }
```

### Step 4.3: 로그 확인

```bash
# Backend 로그 확인 (SSH로 Backend-1 접속)
ssh -i ~/.ssh/kime-key.pem -J ubuntu@10.0.10.60 ubuntu@10.0.175.166

# API 서버 로그 확인
tail -f /home/ubuntu/backend/api_server.log

# 또는 systemd 로그 (서비스로 실행 중이라면)
# sudo journalctl -u kime-api -f

# 에러 로그 확인
# tail -f /home/ubuntu/backend/error.log
```

### Step 4.4: 데이터베이스 확인

```bash
# RDS에 접속하여 실제 데이터 확인
PGPASSWORD=<비밀번호> psql \
  -h kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com \
  -p 5432 \
  -U kime \
  -d kimedb

# 사용자 수 확인
SELECT COUNT(*) FROM statedb.users;

# 세션 수 확인
SELECT COUNT(*) FROM statedb.sessions;

# 최근 대화 확인
SELECT
  session_id,
  turn_number,
  speaker,
  LEFT(content, 50) as content_preview,
  created_at
FROM statedb.dialogues
ORDER BY created_at DESC
LIMIT 10;

# 시나리오 통계 확인
SELECT
  s.title,
  ss.total_views,
  ss.total_likes,
  ss.total_sessions
FROM statedb.scenarios s
JOIN statedb.scenario_statistics ss ON s.scenario_id = ss.scenario_id
ORDER BY ss.total_views DESC;
```

---

## 문제 해결

### Issue 1: CORS 에러

**증상**:
```
Access to XMLHttpRequest at 'http://kime-alb.../api/...' from origin 'http://kime-alb...' has been blocked by CORS policy
```

**해결**:
```bash
# backend/api_server.py 확인
# allow_origins에 ALB DNS가 있는지 확인:
allow_origins=[
    "http://localhost:5173",
    "http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com",  # 이 줄 필요
]

# 수정 후 Backend 재배포
./deploy_to_aws.sh backend-1
./deploy_to_aws.sh backend-2
```

### Issue 2: 404 Not Found (프론트엔드 라우팅)

**증상**: `/character/train` 접속 시 404 에러

**해결**:
```bash
# Nginx 설정에 try_files 추가
location / {
    try_files $uri $uri/ /index.html;  # 이 줄 필요
}

# Nginx 재시작
sudo systemctl restart nginx
```

### Issue 3: API 타임아웃

**증상**: API 요청이 30초 후 타임아웃

**해결**:
```bash
# Nginx에서 프록시 타임아웃 증가
location /api/ {
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;
}

# 또는 ALB 타임아웃 설정 확인 (AWS Console)
# EC2 → Load Balancers → kime-alb → Attributes → Idle timeout: 60s
```

### Issue 4: Database Connection 에러

**증상**: `OperationalError: could not connect to server`

**해결**:
```bash
# 1. RDS 보안 그룹 확인
# - Inbound Rules에 Backend EC2 보안 그룹이 허용되어 있는지 확인
# - Port 5432 (PostgreSQL) 허용 확인

# 2. .env.production 확인
cat backend/.env.production
# DB_HOST가 정확한지 확인
# DB_PASSWORD가 정확한지 확인

# 3. RDS 엔드포인트 직접 테스트
telnet kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com 5432
```

### Issue 5: 환경 변수 미적용

**증상**: 로컬 설정이 프로덕션에 적용됨

**해결**:
```bash
# Backend에서 .env.production이 로드되는지 확인
# api_server.py에서:
load_dotenv(dotenv_path=".env.production", override=True)

# 또는 환경 변수로 직접 전달:
export DB_HOST=kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com
export DB_PORT=5432
python3 api_server.py
```

---

## 체크리스트

### 배포 전 (Pre-Deployment)

- [x] Backend CORS 설정에 ALB DNS 추가
- [ ] RDS 마이그레이션 실행 완료
- [ ] 시나리오 시드 데이터 로드 완료
- [ ] Frontend .env 파일 생성 (VITE_API_URL)
- [ ] Frontend 빌드 성공 (dist 폴더 생성)
- [ ] Backend .env.production 검증

### 배포 중 (Deployment)

- [ ] Backend-1 배포 완료
- [ ] Backend-2 배포 완료
- [ ] Frontend-1 배포 완료
- [ ] Frontend-2 배포 완료
- [ ] Nginx SPA 라우팅 설정

### 배포 후 (Post-Deployment)

- [ ] ALB Health Check 확인 (모든 Target이 healthy)
- [ ] 브라우저 접속 확인 (홈페이지 로드)
- [ ] 회원가입/로그인 테스트
- [ ] 시나리오 카드 클릭 테스트
- [ ] 채팅 기능 테스트
- [ ] API 엔드포인트 테스트 (curl)
- [ ] 데이터베이스 데이터 확인
- [ ] 로그 확인 (에러 없는지)

---

## 다음 단계 (배포 후)

### 1주 내 (P1 - High Priority)

1. **보안 강화**
   - JWT Secret 강화 (랜덤 64자 문자열로 변경)
   - DB 비밀번호 강화
   - SSH 접근 IP 제한 (현재 0.0.0.0/0 → 특정 IP만)

2. **모니터링 설정**
   - CloudWatch Logs 설정 (Backend, Frontend, ALB)
   - CloudWatch Alarms 설정 (CPU, Memory, API 에러율)
   - SNS 알림 설정 (에러 발생 시 이메일/SMS)

### 1-2주 내 (P2 - Medium Priority)

1. **성능 최적화**
   - CloudFront CDN 설정 (이미지 캐싱)
   - DB Connection Pooling 최적화
   - Redis 캐시 전략 개선

2. **품질 보장**
   - E2E 테스트 추가 (Playwright/Cypress)
   - Load Testing (K6, Apache Bench)

---

**작성자**: Taemin
**최종 수정**: 2025-11-03
**다음 업데이트**: 배포 완료 후 실제 이슈 반영
