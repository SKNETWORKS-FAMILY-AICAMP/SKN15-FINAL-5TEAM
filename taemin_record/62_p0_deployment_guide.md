# P0 - 배포 전 필수 작업 가이드

**예상 소요 시간**: 1.5-2시간
**우선순위**: 🚨 Critical

이 작업들을 완료하면 바로 서비스를 사용할 수 있습니다!

---

## ✅ 완료된 작업 (로컬 준비)

### ✅ P0-1: RDS 마이그레이션 스크립트 준비
- **파일**: [backend/scripts/run_migrations.sh](backend/scripts/run_migrations.sh)
- **상태**: 준비 완료

### ✅ P0-2: Frontend 환경변수 설정
- **파일**: [front/.env.production](front/.env.production)
- **설정값**: ALB DNS 설정 완료
- **상태**: 준비 완료

### ✅ P0-4: CORS 설정
- **파일**: [backend/api_server.py](backend/api_server.py#L86-L92)
- **설정값**: ALB DNS 이미 추가됨
- **상태**: 완료

### ✅ P0-3: Frontend 빌드
- **디렉토리**: [front/dist/](front/dist/)
- **빌드 결과**:
  - index.html (565B)
  - assets/index-zTGyuh8a.css (49.23 kB)
  - assets/index-xtd3mz-K.js (323.02 kB)
  - images/ (30개 파일)
- **상태**: 빌드 완료 ✅

---

## 🔵 실행할 작업 (수동 실행 필요)

### 1️⃣ RDS 마이그레이션 실행 (30-60분)

**RDS 정보**:
- Host: `kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com`
- Port: `5432`
- Database: `kimedb`
- User: `kime`
- Password: `dev123`

**실행 명령어**:
```bash
cd backend/scripts
./run_migrations.sh production
```

**실행 후 확인**:
```bash
# 테이블 확인
PGPASSWORD=dev123 psql -h kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com \
  -p 5432 -U kime -d kimedb -c "\dt statedb.*"
```

**예상 결과**: 11개의 마이그레이션 파일이 순서대로 실행되고, 16개 테이블이 생성됨

---

### 2️⃣ 시나리오 데이터 시딩 (5-10분)

**실행 명령어**:
```bash
cd backend
python database/scripts/seed_scenarios.py
```

**예상 결과**: 시나리오 데이터가 RDS에 저장됨

---

### 3️⃣ Frontend 빌드 (15분)

**실행 명령어**:
```bash
cd front
npm install
npm run build
```

**확인**:
```bash
ls -la dist/
# dist/ 디렉토리에 index.html, assets/ 등이 생성되었는지 확인
```

---

### 4️⃣ Backend 배포 (30분)

**Option A: Backend EC2에 직접 배포**

Backend-1 (EC2 인스턴스):
```bash
# 로컬에서 실행
cd backend
./deploy_to_aws.sh backend-1
```

Backend-2:
```bash
./deploy_to_aws.sh backend-2
```

**Option B: 수동 배포 (deploy_to_aws.sh가 없을 경우)**

```bash
# 1. Backend 파일 압축
tar -czf backend.tar.gz backend/

# 2. EC2로 전송
scp -i ~/.ssh/kime-keypair.pem backend.tar.gz ubuntu@<backend-1-ip>:~/

# 3. EC2에서 압축 해제 및 실행
ssh -i ~/.ssh/kime-keypair.pem ubuntu@<backend-1-ip>
tar -xzf backend.tar.gz
cd backend
pip install -r requirements.txt
python api_server.py
```

---

### 5️⃣ Frontend 배포 (30분)

**Option A: EC2 Nginx 배포**

```bash
# 로컬에서 실행
cd front
scp -i ~/.ssh/kime-keypair.pem -r dist/* ubuntu@54.180.234.223:/var/www/html/
scp -i ~/.ssh/kime-keypair.pem -r dist/* ubuntu@3.39.251.70:/var/www/html/
```

**EC2에서 Nginx 설정 확인**:
```bash
ssh -i ~/.ssh/kime-keypair.pem ubuntu@54.180.234.223
sudo nano /etc/nginx/sites-available/default
```

**Nginx 설정**:
```nginx
server {
    listen 80;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Nginx 재시작**:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

**Option B: S3 + CloudFront (권장, 비용 절감)**

```bash
# S3 버킷 생성 (한 번만)
aws s3 mb s3://kime-frontend-bucket

# 빌드 파일 업로드
aws s3 sync dist/ s3://kime-frontend-bucket/ --acl public-read

# CloudFront 무효화 (캐시 갱신)
aws cloudfront create-invalidation --distribution-id <YOUR-DIST-ID> --paths "/*"
```

---

## 6️⃣ 배포 후 확인 (10분)

### ALB Health Check
```bash
curl http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com/api/health
```

**예상 결과**:
```json
{"status": "healthy", "timestamp": "..."}
```

### Frontend 접속 확인
브라우저에서 접속:
```
http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com
```

### API 테스트
```bash
# 시나리오 목록 조회
curl http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com/api/scenarios

# 회원가입 테스트
curl -X POST http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123","email":"test@example.com"}'
```

---

## 📊 배포 체크리스트

- [ ] RDS 마이그레이션 실행 완료 (AWS EC2에서 실행 필요)
- [ ] 시나리오 데이터 시딩 완료 (RDS 마이그레이션 후)
- [ ] Backend-1 배포 완료
- [ ] Backend-2 배포 완료
- [x] Frontend 빌드 완료 (2025-11-03 완료)
- [ ] Frontend-1 배포 완료
- [ ] Frontend-2 배포 완료
- [ ] ALB Health Check 통과
- [ ] Frontend 페이지 로드 확인
- [ ] 로그인/회원가입 테스트
- [ ] 시나리오 목록 로드 테스트
- [ ] Chat 기능 테스트

---

## 🚨 문제 발생 시

### Backend가 시작되지 않을 때
```bash
# 로그 확인
tail -f backend/logs/api_server.log

# 포트 확인
lsof -i:8000

# 환경변수 확인
cat backend/.env.production
```

### Frontend가 API를 호출하지 못할 때
```bash
# .env.production 확인
cat front/.env.production

# CORS 에러 확인 (브라우저 콘솔)
# → backend/api_server.py의 allow_origins 확인
```

### RDS 연결 실패 시
```bash
# 보안 그룹 확인
# → RDS 보안 그룹에서 EC2 보안 그룹 허용 확인

# 직접 연결 테스트
PGPASSWORD=dev123 psql -h kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com \
  -p 5432 -U kime -d kimedb -c "SELECT 1;"
```

---

## 다음 단계: P1 (High Priority)

P0 완료 후 1주일 내에 진행:
1. JWT Secret 강화 (5분)
2. DB Password 강화 (10분)
3. SSH 접근 제한 (5분)
4. CloudWatch Logs 설정 (30분)
5. Health Check Alerts (20분)

**총 소요시간**: 약 1시간

---

**작성일**: 2025-11-03
**최종 업데이트**: 2025-11-03
**상태**: Frontend 빌드 완료, AWS 배포 대기

## 현재 진행 상황

### ✅ 완료된 작업
1. RDS 마이그레이션 스크립트 준비
2. Frontend 환경변수 설정 (.env.production)
3. Frontend 프로덕션 빌드 완료
4. CORS 설정 확인

### ⏳ 대기 중인 작업 (AWS 접근 필요)
1. RDS 마이그레이션 실행 - EC2에서 실행 필요
2. 시나리오 데이터 시딩 - RDS 마이그레이션 후
3. Backend 배포 (Backend-1, Backend-2)
4. Frontend 배포 (Frontend-1, Frontend-2)
5. 배포 후 검증 테스트
