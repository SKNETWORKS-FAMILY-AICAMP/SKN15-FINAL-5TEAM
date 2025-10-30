# AWS 배포 가이드

## 📋 최종 아키텍처

### 5-서버 구성
1. **Frontend EC2 × 2** (t3.medium)
2. **Backend EC2 × 2** (t3.medium)
3. **PostgreSQL RDS** (db.t3.small, Single-AZ)
4. **Redis ElastiCache** (cache.t3.micro)
5. **S3 + CloudFront** (이미지 CDN)
6. **Application Load Balancer** (트래픽 분산)

### 고가용성 구성
- Frontend 2대: 사용자 요청 분산
- Backend 2대: API 처리 부하 분산
- ALB Health Check: 장애 인스턴스 자동 제외
- Multi-AZ 미사용: 비용 절감 (Single-AZ)

---

## 💰 비용 계획

### 예산: ₩300,000 (27일 운영)

| 리소스 | 인스턴스 타입 | 월 비용 | 27일 비용 |
|--------|-------------|---------|----------|
| Frontend EC2 × 2 | t3.medium | $60.16 | $54.14 |
| Backend EC2 × 2 | t3.medium | $60.16 | $54.14 |
| RDS PostgreSQL | db.t3.small | $48.18 | $43.36 |
| ElastiCache Redis | cache.t3.micro | $12.41 | $11.17 |
| S3 + CloudFront | 저장 10GB + 전송 50GB | $5.00 | $4.50 |
| ALB | - | $24.84 | $22.36 |
| **총계** | - | **$210.75** | **$189.67** |

**한화:** ₩252,270 (환율 1,330 기준)

---

## ⏱ 12시간 배포 타임라인

### Phase 1: 네트워크 및 보안 (1.5시간)
- [ ] VPC 생성 (ap-northeast-2, 서울 리전)
- [ ] Public Subnet × 2 (가용 영역 2a, 2c)
- [ ] Private Subnet × 2 (데이터베이스용)
- [ ] Internet Gateway 생성 및 연결
- [ ] Security Groups 설정
  - Frontend: 80, 443, 22
  - Backend: 8000, 22
  - RDS: 5432 (Backend에서만)
  - Redis: 6379 (Backend에서만)

### Phase 2: 데이터베이스 구축 (2시간)
- [ ] RDS PostgreSQL 생성
  - 엔진: PostgreSQL 15
  - 인스턴스: db.t3.small
  - Multi-AZ: 비활성화 (비용 절감)
  - 스토리지: 20GB gp3
  - 백업: 7일 보관
- [ ] ElastiCache Redis 생성
  - 엔진: Redis 7
  - 노드: cache.t3.micro
  - 복제본: 0개 (비용 절감)
- [ ] 데이터베이스 마이그레이션 실행
  ```bash
  psql -h [RDS_ENDPOINT] -U kime -d kimedb -f backend/database/migrations/001_initial_schema.sql
  ```

### Phase 3: S3 + CloudFront (1.5시간)
- [ ] S3 버킷 생성: `kime-images-bucket`
- [ ] 버킷 정책 설정 (CloudFront에서만 접근)
- [ ] 이미지 업로드
  ```bash
  aws s3 sync front/public/images/ s3://kime-images-bucket/
  ```
- [ ] CloudFront 배포 생성
  - Origin: S3 버킷
  - Caching: Optimized
  - HTTPS 강제
- [ ] CloudFront URL 확인 및 기록
  예: `https://d1a2b3c4d5e6f7.cloudfront.net`

### Phase 4: 백엔드 배포 (2.5시간)
- [ ] EC2 인스턴스 × 2 생성 (t3.medium)
- [ ] Python 환경 설정
  ```bash
  sudo yum update -y
  sudo yum install -y python3.11 git
  pip3 install --upgrade pip
  ```
- [ ] 코드 배포
  ```bash
  git clone [REPO_URL]
  cd workspace/backend
  pip3 install -r requirements.txt
  ```
- [ ] 환경 변수 설정 (.env.production)
  ```bash
  DB_HOST=[RDS_ENDPOINT]
  DB_PORT=5432
  DB_NAME=kimedb
  REDIS_HOST=[REDIS_ENDPOINT]
  REDIS_PORT=6379
  ```
- [ ] 서비스 시작 (systemd)
- [ ] Health Check 확인

### Phase 5: 프론트엔드 배포 (2시간)
- [ ] EC2 인스턴스 × 2 생성 (t3.medium)
- [ ] Nginx 설치
  ```bash
  sudo yum install -y nginx
  ```
- [ ] 프론트엔드 빌드 및 배포
  ```bash
  # 로컬에서 빌드
  cd front
  npm install
  npm run build

  # EC2로 전송
  scp -r dist/* ec2-user@[EC2_IP]:/usr/share/nginx/html/
  ```
- [ ] Nginx 설정 (리버스 프록시)
- [ ] Nginx 시작

### Phase 6: ALB 설정 (1.5시간)
- [ ] Target Group 생성
  - Frontend TG: 포트 80
  - Backend TG: 포트 8000
- [ ] Health Check 설정
  - Frontend: GET / → 200 OK
  - Backend: GET /health → 200 OK
- [ ] ALB 생성
- [ ] Listener 규칙 설정
  - `/api/*` → Backend TG
  - `/*` → Frontend TG

### Phase 7: 테스트 및 모니터링 (1시간)
- [ ] E2E 테스트
  - 홈페이지 접속
  - 시나리오 선택
  - 대화 시작
  - 이미지 로딩 확인
- [ ] CloudWatch 알람 설정
  - CPU > 80%
  - 메모리 > 80%
  - RDS 연결 수
- [ ] 로그 확인

---

## 🔑 핵심 엔드포인트 기록

배포 완료 후 다음 정보를 기록하세요:

```bash
# RDS
RDS_ENDPOINT=kime-db.xxxxx.ap-northeast-2.rds.amazonaws.com
RDS_PORT=5432

# Redis
REDIS_ENDPOINT=kime-redis.xxxxx.cache.amazonaws.com
REDIS_PORT=6379

# CloudFront
CDN_URL=https://d1a2b3c4d5e6f7.cloudfront.net

# ALB
ALB_DNS=kime-alb-xxxxx.ap-northeast-2.elb.amazonaws.com
```

이 정보를 `front/.env.production`에 업데이트하세요!

---

## 📊 성능 목표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 응답 시간 | < 2초 | CloudWatch |
| 이미지 로딩 | < 500ms | CloudFront |
| 동시 접속 | 100명 | Load Test |
| 가용성 | 99% | ALB Health Check |

---

## 다음 단계

1. ⏳ 12시간 배포 실행
2. ⏳ 운영 모니터링 (27일)
3. ⏳ 사용자 피드백 수집

**관련 문서:**
- [02_image_cdn_migration.md](02_image_cdn_migration.md)
- [04_environment_variables.md](04_environment_variables.md)

---
작성일: 2025-10-30
예상 배포일: 2025-10-31
