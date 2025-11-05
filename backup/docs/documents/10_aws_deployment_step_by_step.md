# AWS 배포 완전 초보자 가이드

**작성일**: 2025-10-30
**대상**: AWS를 처음 사용하는 개발자
**예상 소요 시간**: 약 12시간
**예상 비용**: ₩252,261 / 27일 (아키텍처 문서 참조)

---

## 📋 목차

1. [사전 준비사항](#사전-준비사항)
2. [Phase 1: AWS 계정 및 초기 보안 설정 (1시간)](#phase-1-aws-계정-및-초기-보안-설정)
3. [Phase 2: VPC 및 네트워크 구성 (1시간)](#phase-2-vpc-및-네트워크-구성)
4. [Phase 3: RDS PostgreSQL 설정 (1.5시간)](#phase-3-rds-postgresql-설정)
5. [Phase 4: ElastiCache Redis 설정 (1시간)](#phase-4-elasticache-redis-설정)
6. [Phase 5: EC2 인스턴스 설정 (2시간)](#phase-5-ec2-인스턴스-설정)
7. [Phase 6: S3 + CloudFront 설정 (1.5시간)](#phase-6-s3--cloudfront-설정)
8. [Phase 7: Application Load Balancer 설정 (1.5시간)](#phase-7-application-load-balancer-설정)
9. [Phase 8: 보안 그룹 최종 점검 (1시간)](#phase-8-보안-그룹-최종-점검)
10. [Phase 9: 애플리케이션 배포 (1시간)](#phase-9-애플리케이션-배포)
11. [Phase 10: 테스트 및 모니터링 설정 (0.5시간)](#phase-10-테스트-및-모니터링-설정)
12. [Troubleshooting](#troubleshooting)

---

## 사전 준비사항

### 1. AWS 계정 생성
1. https://aws.amazon.com/ko/ 접속
2. "AWS 계정 생성" 클릭
3. 이메일, 비밀번호, AWS 계정 이름 입력
4. 결제 정보 등록 (신용카드 또는 체크카드)
5. 전화번호 인증 완료
6. Support Plan 선택 (Basic - 무료 선택)

**⚠️ 중요**:
- 루트 계정 이메일/비밀번호는 **절대 잊어버리지 마세요**
- 비밀번호는 반드시 암호 관리자(1Password, LastPass 등)에 저장하세요

### 2. 필요한 도구 설치

#### macOS/Linux:
```bash
# AWS CLI 설치
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# 설치 확인
aws --version
# 출력 예: aws-cli/2.13.0 Python/3.11.4 Darwin/23.0.0 source/x86_64 prompt/off

# SSH 키 생성 (아직 없는 경우)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
# Enter 키를 3번 눌러 기본값 사용
```

#### Windows:
1. https://aws.amazon.com/cli/ 에서 Windows용 설치 파일 다운로드
2. 설치 후 PowerShell 또는 CMD에서 `aws --version` 확인

### 3. 로컬 프로젝트 준비
```bash
cd /Users/jtm427/Desktop/workspace

# 현재 프로젝트 상태 확인
git status

# 배포할 브랜치 확인
git branch
# 현재: remake 브랜치

# 배포용 환경변수 파일 준비
cp backend/.env.example backend/.env.production
# .env.production 파일을 텍스트 에디터로 열어 나중에 수정할 예정
```

---

## Phase 1: AWS 계정 및 초기 보안 설정

### 1.1 AWS Management Console 접속
1. https://console.aws.amazon.com 접속
2. 루트 사용자 이메일로 로그인
3. **리전 선택**: 우측 상단에서 **"아시아 태평양 (서울) ap-northeast-2"** 선택

**⚠️ 중요**: 모든 리소스는 반드시 **서울 리전 (ap-northeast-2)**에 생성하세요!

### 1.2 MFA (다중 인증) 설정 - 필수!
1. 우측 상단 계정명 클릭 → "보안 자격 증명" 클릭
2. "멀티 팩터 인증(MFA)" 섹션에서 "MFA 활성화" 클릭
3. "가상 MFA 디바이스" 선택
4. 스마트폰에 **Google Authenticator** 앱 설치
5. QR 코드 스캔 후 연속된 2개의 MFA 코드 입력
6. "MFA 할당" 클릭

**✅ 확인**: "MFA 디바이스" 항목에 "arn:aws:iam::..." 표시됨

### 1.3 IAM 사용자 생성 (루트 계정 대신 사용)
루트 계정은 절대 일상적으로 사용하지 마세요. IAM 사용자를 생성합니다.

1. **IAM 서비스로 이동**
   - 상단 검색창에 "IAM" 입력 → "IAM" 클릭

2. **사용자 생성**
   - 좌측 메뉴에서 "사용자" 클릭
   - "사용자 추가" 버튼 클릭

3. **사용자 세부 정보**
   - 사용자 이름: `admin-user` (또는 원하는 이름)
   - "AWS Management Console에 대한 사용자 액세스 권한 제공" 체크
   - "IAM 사용자를 생성하고 싶음" 선택
   - 콘솔 암호: "사용자 지정 암호" 선택 후 강력한 암호 입력
   - "사용자는 다음 로그인 시 새 암호를 생성해야 합니다" 체크 해제 (선택 사항)
   - "다음" 클릭

4. **권한 설정**
   - "직접 정책 연결" 선택
   - 검색창에 "AdministratorAccess" 입력 → 체크
   - "다음" 클릭

5. **검토 및 생성**
   - "사용자 생성" 클릭
   - **중요**: "콘솔 로그인 URL" 복사 및 저장
   - 예: `https://123456789012.signin.aws.amazon.com/console`

6. **IAM 사용자로 로그인**
   - 로그아웃 후 복사한 URL로 접속
   - IAM 사용자 이름과 암호로 로그인
   - **이제부터 이 계정으로만 작업합니다**

### 1.4 AWS CLI 설정
```bash
# IAM 사용자용 액세스 키 생성
# AWS Console → IAM → 사용자 → admin-user → "보안 자격 증명" 탭
# → "액세스 키 만들기" → "명령줄 인터페이스(CLI)" 선택
# → "액세스 키 만들기" 클릭
# → Access Key ID와 Secret Access Key 복사

# 로컬에서 AWS CLI 설정
aws configure

# 입력 내용:
# AWS Access Key ID: AKIA.................... (복사한 값)
# AWS Secret Access Key: .................... (복사한 값)
# Default region name: ap-northeast-2
# Default output format: json

# 설정 확인
aws sts get-caller-identity
# 출력 예:
# {
#     "UserId": "AIDA...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/admin-user"
# }
```

**✅ Phase 1 완료 체크리스트**:
- [ ] AWS 계정 생성 완료
- [ ] 루트 계정 MFA 활성화
- [ ] IAM 관리자 사용자 생성
- [ ] IAM 사용자로 로그인
- [ ] AWS CLI 설정 완료
- [ ] 리전이 **ap-northeast-2 (서울)**인지 확인

---

## Phase 2: VPC 및 네트워크 구성

### 2.1 VPC 생성
1. **VPC 서비스로 이동**
   - 상단 검색창에 "VPC" 입력 → "VPC" 클릭

2. **VPC 생성**
   - "VPC 생성" 버튼 클릭
   - **생성할 리소스**: "VPC 등" 선택 (VPC, 서브넷, 라우팅 테이블을 자동으로 생성)

3. **VPC 설정**
   - 이름 태그: `kime-vpc`
   - IPv4 CIDR 블록: `10.0.0.0/16`
   - IPv6 CIDR 블록: "IPv6 CIDR 블록 없음"
   - 테넌시: "기본값"

4. **서브넷 설정**
   - 가용 영역(AZ) 수: **2** (고가용성)
   - 퍼블릭 서브넷 수: **2**
   - 프라이빗 서브넷 수: **2**
   - NAT 게이트웨이: **1개의 AZ에** (비용 절감)
   - VPC 엔드포인트: "S3 게이트웨이" 선택 (무료)

5. **생성 클릭**

**⏱️ 대기**: VPC 생성에 약 2-3분 소요

**✅ 확인**:
- VPC ID가 생성됨 (예: vpc-0a1b2c3d4e5f6g7h8)
- 서브넷 4개 생성 확인:
  - `kime-vpc-public-ap-northeast-2a` (10.0.0.0/24)
  - `kime-vpc-public-ap-northeast-2c` (10.0.1.0/24)
  - `kime-vpc-private-ap-northeast-2a` (10.0.128.0/24)
  - `kime-vpc-private-ap-northeast-2c` (10.0.129.0/24)

### 2.2 보안 그룹 생성 (기본 틀)

#### 2.2.1 ALB 보안 그룹
```bash
# CLI로 생성 (또는 Console에서)
aws ec2 create-security-group \
  --group-name kime-alb-sg \
  --description "Security group for Application Load Balancer" \
  --vpc-id vpc-XXXXXXXX  # 위에서 생성된 VPC ID로 교체

# 인바운드 규칙 추가
# HTTP (80)
aws ec2 authorize-security-group-ingress \
  --group-id sg-XXXXXXXX \  # 생성된 보안 그룹 ID
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# HTTPS (443)
aws ec2 authorize-security-group-ingress \
  --group-id sg-XXXXXXXX \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

**또는 AWS Console에서**:
1. EC2 → 보안 그룹 → "보안 그룹 생성"
2. 보안 그룹 이름: `kime-alb-sg`
3. 설명: `Security group for Application Load Balancer`
4. VPC: `kime-vpc` 선택
5. 인바운드 규칙 추가:
   - 유형: HTTP, 소스: 0.0.0.0/0
   - 유형: HTTPS, 소스: 0.0.0.0/0
6. "보안 그룹 생성" 클릭

#### 2.2.2 EC2 보안 그룹 (Frontend/Backend)
```bash
# Frontend EC2 보안 그룹
aws ec2 create-security-group \
  --group-name kime-frontend-sg \
  --description "Security group for Frontend EC2" \
  --vpc-id vpc-XXXXXXXX

# Backend EC2 보안 그룹
aws ec2 create-security-group \
  --group-name kime-backend-sg \
  --description "Security group for Backend EC2" \
  --vpc-id vpc-XXXXXXXX
```

**Console에서**:
1. `kime-frontend-sg` 생성:
   - VPC: `kime-vpc`
   - 인바운드 규칙:
     - 유형: HTTP (80), 소스: `kime-alb-sg` 보안 그룹
     - 유형: SSH (22), 소스: "내 IP" (개발 중에만)

2. `kime-backend-sg` 생성:
   - VPC: `kime-vpc`
   - 인바운드 규칙:
     - 유형: Custom TCP (8000), 소스: `kime-alb-sg` 보안 그룹
     - 유형: SSH (22), 소스: "내 IP"

#### 2.2.3 RDS 보안 그룹
```bash
aws ec2 create-security-group \
  --group-name kime-rds-sg \
  --description "Security group for RDS PostgreSQL" \
  --vpc-id vpc-XXXXXXXX
```

**Console에서**:
- 이름: `kime-rds-sg`
- VPC: `kime-vpc`
- 인바운드 규칙:
  - 유형: PostgreSQL (5432), 소스: `kime-backend-sg` 보안 그룹

#### 2.2.4 Redis 보안 그룹
```bash
aws ec2 create-security-group \
  --group-name kime-redis-sg \
  --description "Security group for ElastiCache Redis" \
  --vpc-id vpc-XXXXXXXX
```

**Console에서**:
- 이름: `kime-redis-sg`
- VPC: `kime-vpc`
- 인바운드 규칙:
  - 유형: Custom TCP (6379), 소스: `kime-backend-sg` 보안 그룹

**✅ Phase 2 완료 체크리스트**:
- [ ] VPC 생성 (`kime-vpc`, 10.0.0.0/16)
- [ ] 서브넷 4개 생성 (퍼블릭 2, 프라이빗 2)
- [ ] NAT Gateway 생성
- [ ] 보안 그룹 5개 생성 (ALB, Frontend, Backend, RDS, Redis)

---

## Phase 3: RDS PostgreSQL 설정

### 3.1 서브넷 그룹 생성
1. **RDS 서비스로 이동**
   - 상단 검색창에 "RDS" 입력 → "RDS" 클릭

2. **서브넷 그룹 생성**
   - 좌측 메뉴에서 "서브넷 그룹" 클릭
   - "DB 서브넷 그룹 생성" 클릭

3. **서브넷 그룹 세부 정보**
   - 이름: `kime-rds-subnet-group`
   - 설명: `Subnet group for Kime RDS`
   - VPC: `kime-vpc` 선택

4. **서브넷 추가**
   - 가용 영역: `ap-northeast-2a`, `ap-northeast-2c` 선택
   - 서브넷: 프라이빗 서브넷 2개 선택
     - `kime-vpc-private-ap-northeast-2a`
     - `kime-vpc-private-ap-northeast-2c`
   - "생성" 클릭

### 3.2 RDS 인스턴스 생성
1. **데이터베이스 생성**
   - RDS 대시보드에서 "데이터베이스 생성" 클릭

2. **엔진 옵션**
   - 엔진 유형: **PostgreSQL**
   - 버전: **PostgreSQL 15.x** (최신 안정화 버전)

3. **템플릿**
   - **프리 티어** (개발/테스트용) 또는 **프로덕션** 선택
   - 프로덕션 선택 시 비용 고려

4. **설정**
   - DB 인스턴스 식별자: `kime-db`
   - 마스터 사용자 이름: `postgres`
   - 마스터 암호: 강력한 암호 생성 (반드시 저장!)
   - 암호 확인: 동일하게 입력

**⚠️ 중요**:
- 마스터 암호는 **반드시 암호 관리자에 저장**하세요
- 예시: `K1m3Ch@t_DB_P@ssw0rd!2025`

5. **인스턴스 구성**
   - DB 인스턴스 클래스: `db.t3.micro` (프리 티어) 또는 `db.t3.small`
   - 스토리지 유형: **범용 SSD (gp3)**
   - 할당된 스토리지: **20 GiB** (시작용)
   - 스토리지 자동 조정 활성화: 체크
   - 최대 스토리지 임계값: **100 GiB**

6. **연결**
   - Virtual Private Cloud (VPC): `kime-vpc` 선택
   - DB 서브넷 그룹: `kime-rds-subnet-group` 선택
   - 퍼블릭 액세스: **아니요** (보안상 중요!)
   - VPC 보안 그룹: `kime-rds-sg` 선택
   - 가용 영역: "기본 설정 없음" (자동 선택)
   - 포트: **5432** (기본값)

7. **추가 구성**
   - 초기 데이터베이스 이름: `kime_statedb`
   - DB 파라미터 그룹: 기본값
   - 백업:
     - 자동 백업 활성화: 체크
     - 백업 보존 기간: **7일**
     - 백업 기간: 02:00-03:00 (한국 시간 기준 새벽)
   - 암호화: **활성화** (필수!)
     - AWS KMS 키: "기본값(aws/rds)" 선택
   - 성능 개선 도우미: 활성화 (선택 사항)
   - 로그 내보내기: "PostgreSQL 로그" 체크
   - 삭제 방지: **활성화** (실수로 삭제 방지)

8. **월별 추정 요금 확인**
   - 하단의 월별 추정 요금 확인
   - 예상: ~$15-30/월 (db.t3.micro 기준)

9. **데이터베이스 생성 클릭**

**⏱️ 대기**: RDS 인스턴스 생성에 약 10-15분 소요

### 3.3 RDS 엔드포인트 확인 및 저장
1. RDS → 데이터베이스 → `kime-db` 클릭
2. "연결 & 보안" 탭에서 **엔드포인트** 복사
   - 예: `kime-db.c9akj7l6z8y0.ap-northeast-2.rds.amazonaws.com`
3. 포트: `5432` 확인

**📝 저장**:
```bash
# 로컬에 저장 (나중에 환경변수로 사용)
RDS_ENDPOINT=kime-db.c9akj7l6z8y0.ap-northeast-2.rds.amazonaws.com
RDS_PORT=5432
RDS_USER=postgres
RDS_PASSWORD=K1m3Ch@t_DB_P@ssw0rd!2025  # 실제 암호로 교체
RDS_DBNAME=kime_statedb
```

### 3.4 데이터베이스 초기 설정 (Bastion Host에서)

**참고**: 프라이빗 서브넷의 RDS에 접속하려면 EC2 인스턴스(Bastion Host)가 필요합니다.
지금은 Phase 5에서 EC2를 생성할 예정이므로, **이 단계는 Phase 5 이후에 진행**합니다.

**✅ Phase 3 완료 체크리스트**:
- [ ] RDS 서브넷 그룹 생성 (`kime-rds-subnet-group`)
- [ ] RDS PostgreSQL 인스턴스 생성 (`kime-db`)
- [ ] 엔드포인트 및 자격 증명 저장
- [ ] 자동 백업 활성화 (7일)
- [ ] 암호화 활성화
- [ ] 삭제 방지 활성화

---

## Phase 4: ElastiCache Redis 설정

### 4.1 서브넷 그룹 생성
1. **ElastiCache 서비스로 이동**
   - 상단 검색창에 "ElastiCache" 입력 → "ElastiCache" 클릭

2. **서브넷 그룹 생성**
   - 좌측 메뉴에서 "서브넷 그룹" 클릭
   - "서브넷 그룹 생성" 클릭

3. **서브넷 그룹 세부 정보**
   - 이름: `kime-redis-subnet-group`
   - 설명: `Subnet group for Kime Redis`
   - VPC ID: `kime-vpc` 선택

4. **서브넷 선택**
   - 가용 영역: `ap-northeast-2a`, `ap-northeast-2c` 선택
   - 서브넷: 프라이빗 서브넷 2개 선택
   - "생성" 클릭

### 4.2 Redis 클러스터 생성
1. **Redis 클러스터 생성**
   - ElastiCache 대시보드에서 "Redis 클러스터" → "클러스터 생성" 클릭

2. **클러스터 모드**
   - **클러스터 모드 비활성화됨** 선택 (단순한 설정)

3. **클러스터 정보**
   - 이름: `kime-redis`
   - 설명: `Redis cache for Kime Chat`
   - 엔진 버전: **Redis 7.x** (최신 안정화 버전)
   - 포트: **6379** (기본값)
   - 파라미터 그룹: `default.redis7`
   - 노드 유형: **cache.t3.micro** (또는 cache.t4g.micro)
   - 복제본 수: **1** (고가용성을 위해 권장)

4. **서브넷 그룹 설정**
   - 서브넷 그룹: `kime-redis-subnet-group` 선택

5. **보안**
   - 보안 그룹: `kime-redis-sg` 선택
   - 전송 중 암호화: **활성화**
   - 저장 중 암호화: **활성화**
   - AUTH 토큰: 설정 (강력한 토큰 생성)
     - 예: `K1m3Ch@t_R3d1s_T0k3n!2025`
     - **반드시 저장**하세요!

6. **백업**
   - 자동 백업 활성화: 체크
   - 백업 보존 기간: **1일** (Redis는 캐시이므로 짧게)

7. **로그**
   - 느린 로그 형식: TEXT
   - 로그 대상: CloudWatch Logs

8. **유지 관리**
   - 유지 관리 기간: "기본 설정 없음"

9. **생성 클릭**

**⏱️ 대기**: Redis 클러스터 생성에 약 5-10분 소요

### 4.3 Redis 엔드포인트 확인 및 저장
1. ElastiCache → Redis 클러스터 → `kime-redis` 클릭
2. **기본 엔드포인트** 복사
   - 예: `kime-redis.abc123.ng.0001.apn2.cache.amazonaws.com`
3. **읽기 엔드포인트** 복사 (복제본이 있는 경우)

**📝 저장**:
```bash
REDIS_ENDPOINT=kime-redis.abc123.ng.0001.apn2.cache.amazonaws.com
REDIS_PORT=6379
REDIS_AUTH_TOKEN=K1m3Ch@t_R3d1s_T0k3n!2025  # 실제 토큰으로 교체
```

**✅ Phase 4 완료 체크리스트**:
- [ ] Redis 서브넷 그룹 생성 (`kime-redis-subnet-group`)
- [ ] Redis 클러스터 생성 (`kime-redis`)
- [ ] 엔드포인트 및 AUTH 토큰 저장
- [ ] 전송 중 암호화 활성화
- [ ] 저장 중 암호화 활성화
- [ ] 자동 백업 활성화

---

## Phase 5: EC2 인스턴스 설정

### 5.1 SSH 키 페어 생성
1. **EC2 서비스로 이동**
   - 상단 검색창에 "EC2" 입력 → "EC2" 클릭

2. **키 페어 생성**
   - 좌측 메뉴에서 "네트워크 및 보안" → "키 페어" 클릭
   - "키 페어 생성" 클릭

3. **키 페어 세부 정보**
   - 이름: `kime-keypair`
   - 키 페어 유형: **RSA**
   - 프라이빗 키 파일 형식: **pem** (macOS/Linux) 또는 **ppk** (Windows/PuTTY)
   - "키 페어 생성" 클릭

4. **키 파일 저장**
   - `kime-keypair.pem` 파일이 자동 다운로드됨
   - 안전한 위치로 이동:
   ```bash
   # macOS/Linux
   mv ~/Downloads/kime-keypair.pem ~/.ssh/
   chmod 400 ~/.ssh/kime-keypair.pem
   ```

**⚠️ 중요**: 이 키 파일을 잃어버리면 EC2에 접속할 수 없습니다!

### 5.2 Backend EC2 인스턴스 생성 (1번)

1. **인스턴스 시작**
   - EC2 대시보드에서 "인스턴스 시작" 클릭

2. **이름 및 태그**
   - 이름: `kime-backend-1`
   - 태그 추가:
     - Key: `Environment`, Value: `production`
     - Key: `Type`, Value: `backend`

3. **애플리케이션 및 OS 이미지 (AMI)**
   - **Ubuntu Server 22.04 LTS** 선택
   - 아키텍처: **64비트 (x86)**

4. **인스턴스 유형**
   - **t3.medium** 선택 (2 vCPU, 4 GiB RAM)
   - 또는 예산에 맞게 t3.small 선택

5. **키 페어**
   - `kime-keypair` 선택

6. **네트워크 설정**
   - VPC: `kime-vpc` 선택
   - 서브넷: **프라이빗 서브넷 선택** (`kime-vpc-private-ap-northeast-2a`)
   - 퍼블릭 IP 자동 할당: **비활성화**
   - 방화벽(보안 그룹): "기존 보안 그룹 선택"
     - `kime-backend-sg` 선택

7. **스토리지 구성**
   - 볼륨 1: **30 GiB** gp3
   - 암호화: **활성화**

8. **고급 세부 정보**
   - IAM 인스턴스 프로파일: 나중에 설정 (Phase 8)
   - 사용자 데이터 (User Data): 아래 스크립트 입력

```bash
#!/bin/bash
# Backend 초기 설정 스크립트

# 시스템 업데이트
apt-get update -y
apt-get upgrade -y

# 필수 패키지 설치
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    nginx \
    postgresql-client \
    redis-tools \
    htop \
    curl \
    wget

# Python 심볼릭 링크
update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# pip 업그레이드
python -m pip install --upgrade pip

# 애플리케이션 디렉토리 생성
mkdir -p /home/ubuntu/kime-backend
chown -R ubuntu:ubuntu /home/ubuntu/kime-backend

# CloudWatch 에이전트 설치 (모니터링용)
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb

# 로그 디렉토리 생성
mkdir -p /var/log/kime
chown -R ubuntu:ubuntu /var/log/kime

echo "Backend EC2 setup completed at $(date)" > /var/log/kime/setup.log
```

9. **인스턴스 시작 클릭**

**⏱️ 대기**: 인스턴스 시작에 약 2-3분 소요

### 5.3 Backend EC2 인스턴스 #2 생성
위와 동일한 방법으로 생성:
- 이름: `kime-backend-2`
- 서브넷: `kime-vpc-private-ap-northeast-2c` (다른 AZ)
- 나머지 설정 동일

### 5.4 Frontend EC2 인스턴스 생성 (1번, 2번)

Backend와 유사하지만 차이점:

1. **이름**: `kime-frontend-1`
2. **인스턴스 유형**: **t3.small** (1 vCPU, 2 GiB RAM)
3. **서브넷**: **퍼블릭 서브넷** (`kime-vpc-public-ap-northeast-2a`)
4. **퍼블릭 IP 자동 할당**: **활성화**
5. **보안 그룹**: `kime-frontend-sg`
6. **사용자 데이터**:

```bash
#!/bin/bash
# Frontend 초기 설정 스크립트

apt-get update -y
apt-get upgrade -y

# Node.js 20.x 설치
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# 필수 패키지
apt-get install -y \
    git \
    nginx \
    build-essential \
    htop \
    curl \
    wget

# 애플리케이션 디렉토리
mkdir -p /home/ubuntu/kime-frontend
chown -R ubuntu:ubuntu /home/ubuntu/kime-frontend

# Nginx 설정 디렉토리
mkdir -p /etc/nginx/sites-available
mkdir -p /etc/nginx/sites-enabled

# CloudWatch 에이전트
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb

echo "Frontend EC2 setup completed at $(date)" > /var/log/setup.log
```

7. **Frontend #2 생성**: `kime-frontend-2` (서브넷: `kime-vpc-public-ap-northeast-2c`)

### 5.5 Bastion Host 생성 (RDS/Redis 접속용)

1. **이름**: `kime-bastion`
2. **인스턴스 유형**: **t3.micro** (최소 사양)
3. **서브넷**: **퍼블릭 서브넷** (`kime-vpc-public-ap-northeast-2a`)
4. **퍼블릭 IP**: **활성화**
5. **보안 그룹**: 새로운 보안 그룹 생성
   - 이름: `kime-bastion-sg`
   - 인바운드 규칙: SSH (22) - **내 IP만** (보안!)
6. **사용자 데이터**:

```bash
#!/bin/bash
apt-get update -y
apt-get install -y postgresql-client redis-tools
```

### 5.6 EC2 인스턴스 접속 테스트

**Bastion Host에 접속**:
```bash
# Bastion의 퍼블릭 IP 확인 (EC2 콘솔에서)
BASTION_IP=13.124.XXX.XXX

# SSH 접속
ssh -i ~/.ssh/kime-keypair.pem ubuntu@$BASTION_IP

# 접속 성공 후
ubuntu@kime-bastion:~$
```

**Backend 인스턴스에 접속 (Bastion을 통해)**:
```bash
# Bastion에서
BACKEND_PRIVATE_IP=10.0.128.XXX  # EC2 콘솔에서 확인

ssh -i ~/.ssh/kime-keypair.pem ubuntu@$BACKEND_PRIVATE_IP
# 또는 로컬에서 SSH 터널링:
ssh -i ~/.ssh/kime-keypair.pem \
    -J ubuntu@$BASTION_IP \
    ubuntu@$BACKEND_PRIVATE_IP
```

### 5.7 RDS 초기 설정 (Bastion에서)

```bash
# Bastion Host에 접속한 상태에서
RDS_ENDPOINT=kime-db.c9akj7l6z8y0.ap-northeast-2.rds.amazonaws.com

# PostgreSQL 접속
psql -h $RDS_ENDPOINT -U postgres -d kime_statedb

# 암호 입력: K1m3Ch@t_DB_P@ssw0rd!2025

# 연결 성공 확인
postgres=# \l
# 데이터베이스 목록 표시됨

# 추가 데이터베이스 생성 (LogDB용)
postgres=# CREATE DATABASE kime_logdb;
postgres=# \l
# kime_statedb, kime_logdb 확인

# 종료
postgres=# \q
```

**✅ Phase 5 완료 체크리스트**:
- [ ] SSH 키 페어 생성 및 저장
- [ ] Backend EC2 2개 생성 (프라이빗 서브넷)
- [ ] Frontend EC2 2개 생성 (퍼블릭 서브넷)
- [ ] Bastion Host 생성
- [ ] Bastion을 통해 Backend 접속 확인
- [ ] RDS 접속 확인 및 LogDB 생성

---

## Phase 6: S3 + CloudFront 설정

### 6.1 S3 버킷 생성

1. **S3 서비스로 이동**
   - 상단 검색창에 "S3" 입력 → "S3" 클릭

2. **버킷 만들기**
   - "버킷 만들기" 클릭

3. **버킷 구성**
   - 버킷 이름: `kime-assets-2025` (전 세계 고유해야 함)
   - AWS 리전: **아시아 태평양(서울) ap-northeast-2**

4. **객체 소유권**
   - "ACL 비활성화됨(권장)" 선택

5. **퍼블릭 액세스 차단 설정**
   - **모든 퍼블릭 액세스 차단** 체크 (CloudFront를 통해서만 접근)

6. **버킷 버전 관리**
   - "비활성화" (정적 자산은 버전 관리 불필요)

7. **기본 암호화**
   - "Amazon S3 관리형 키로 서버 측 암호화(SSE-S3)" 선택

8. **버킷 만들기 클릭**

### 6.2 S3 버킷 정책 설정 (CloudFront 전용)

나중에 CloudFront 생성 후 설정합니다 (Phase 6.4에서).

### 6.3 정적 자산 업로드

```bash
# 로컬에서 S3로 업로드
cd /Users/jtm427/Desktop/workspace

# AWS CLI로 업로드
aws s3 sync front/public/images/ s3://kime-assets-2025/images/ \
  --exclude "*.DS_Store"

# 확인
aws s3 ls s3://kime-assets-2025/images/
```

### 6.4 CloudFront 배포 생성

1. **CloudFront 서비스로 이동**
   - 상단 검색창에 "CloudFront" 입력 → "CloudFront" 클릭

2. **배포 생성**
   - "배포 생성" 클릭

3. **원본 설정**
   - 원본 도메인: S3 버킷 선택 (`kime-assets-2025.s3.ap-northeast-2.amazonaws.com`)
   - 원본 경로: 비워둠
   - 이름: `S3-kime-assets`
   - **원본 액세스**: "Origin access control settings (recommended)" 선택
     - "Create control setting" 클릭 → 기본값 → "생성"

4. **기본 캐시 동작**
   - 뷰어 프로토콜 정책: **Redirect HTTP to HTTPS**
   - 허용된 HTTP 메서드: **GET, HEAD**
   - 캐시 정책: **CachingOptimized**
   - 원본 요청 정책: 없음

5. **설정**
   - 가격 분류: **Use all edge locations (best performance)**
   - AWS WAF 웹 ACL: "Do not enable security protections" (나중에 필요시 추가)
   - 대체 도메인 이름 (CNAME): 비워둠 (커스텀 도메인 없는 경우)
   - SSL 인증서: "Default CloudFront Certificate"
   - 기본 루트 객체: `index.html`

6. **배포 생성 클릭**

**⏱️ 대기**: CloudFront 배포 완료까지 약 10-15분 소요

### 6.5 S3 버킷 정책 업데이트 (CloudFront 접근 허용)

1. CloudFront 배포 생성 완료 후, **정책 복사 알림** 표시
2. S3 → `kime-assets-2025` → "권한" 탭 → "버킷 정책"
3. 다음 정책 추가:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowCloudFrontServicePrincipal",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::kime-assets-2025/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/EXXXXXXXXXXXXX"
                }
            }
        }
    ]
}
```

**⚠️ 주의**: `AWS:SourceArn`의 Distribution ID는 CloudFront 콘솔에서 복사하세요!

### 6.6 CloudFront 배포 URL 확인

1. CloudFront → 배포 → 생성한 배포 클릭
2. **배포 도메인 이름** 복사
   - 예: `d1234567890abc.cloudfront.net`
3. 브라우저에서 접속 테스트:
   - `https://d1234567890abc.cloudfront.net/images/your-image.png`

**📝 저장**:
```bash
CLOUDFRONT_DOMAIN=d1234567890abc.cloudfront.net
```

**✅ Phase 6 완료 체크리스트**:
- [ ] S3 버킷 생성 (`kime-assets-2025`)
- [ ] 정적 자산 업로드
- [ ] CloudFront 배포 생성
- [ ] S3 버킷 정책 설정 (CloudFront 접근 허용)
- [ ] CloudFront URL 접속 확인

---

## Phase 7: Application Load Balancer 설정

### 7.1 대상 그룹 생성 (Backend)

1. **EC2 서비스 → 대상 그룹**
   - 좌측 메뉴에서 "로드 밸런싱" → "대상 그룹" 클릭
   - "대상 그룹 생성" 클릭

2. **대상 유형 선택**
   - **인스턴스** 선택

3. **대상 그룹 구성**
   - 대상 그룹 이름: `kime-backend-tg`
   - 프로토콜: **HTTP**
   - 포트: **8000**
   - VPC: `kime-vpc` 선택
   - 프로토콜 버전: **HTTP1**

4. **상태 검사**
   - 상태 검사 프로토콜: **HTTP**
   - 상태 검사 경로: `/health` (Backend에서 구현 필요)
   - 정상 임계값: **2**
   - 비정상 임계값: **2**
   - 제한 시간: **5초**
   - 간격: **30초**
   - 성공 코드: **200**

5. **다음 클릭**

6. **대상 등록**
   - `kime-backend-1`, `kime-backend-2` 선택
   - 포트: **8000** 확인
   - "아래에 보류 중인 것으로 포함" 클릭

7. **대상 그룹 생성 클릭**

### 7.2 대상 그룹 생성 (Frontend)

동일한 방법으로:
- 이름: `kime-frontend-tg`
- 프로토콜: **HTTP**
- 포트: **80**
- 상태 검사 경로: `/` (또는 `/index.html`)
- 대상: `kime-frontend-1`, `kime-frontend-2`

### 7.3 Application Load Balancer 생성

1. **로드 밸런서 생성**
   - EC2 → 로드 밸런서 → "로드 밸런서 생성" 클릭
   - **Application Load Balancer** 선택 → "생성"

2. **로드 밸런서 구성**
   - 이름: `kime-alb`
   - 체계: **인터넷 경계** (외부 트래픽 수신)
   - IP 주소 유형: **IPv4**

3. **네트워크 매핑**
   - VPC: `kime-vpc` 선택
   - 매핑: **ap-northeast-2a**, **ap-northeast-2c** 선택
   - 서브넷:
     - ap-northeast-2a: **퍼블릭 서브넷** 선택
     - ap-northeast-2c: **퍼블릭 서브넷** 선택

4. **보안 그룹**
   - `kime-alb-sg` 선택

5. **리스너 및 라우팅**
   - 리스너 1:
     - 프로토콜: **HTTP**
     - 포트: **80**
     - 기본 작업: "대상 그룹으로 전달"
       - 대상 그룹: `kime-frontend-tg` 선택

6. **로드 밸런서 생성 클릭**

**⏱️ 대기**: ALB 생성 및 활성화에 약 3-5분 소요

### 7.4 리스너 규칙 추가 (경로 기반 라우팅)

1. **리스너 편집**
   - 로드 밸런서 → `kime-alb` → "리스너" 탭
   - HTTP:80 리스너 선택 → "규칙 관리"

2. **규칙 추가**
   - "규칙 추가" 클릭
   - 우선순위: **1**

3. **조건 추가**
   - "조건 추가" → "경로"
   - 경로 패턴: `/api/*`

4. **작업 추가**
   - "작업 추가" → "대상 그룹으로 전달"
   - 대상 그룹: `kime-backend-tg` 선택

5. **저장**

**결과**:
- `/api/*` 요청 → Backend (포트 8000)
- 그 외 모든 요청 → Frontend (포트 80)

### 7.5 HTTPS 리스너 추가 (선택 사항 - SSL 인증서 있는 경우)

**참고**: 커스텀 도메인이 없으면 HTTP만 사용합니다.
도메인이 있다면:

1. **ACM에서 SSL 인증서 발급**
   - AWS Certificate Manager → "인증서 요청"
   - 도메인 이름 입력: `yourdomain.com`, `*.yourdomain.com`
   - DNS 검증 완료

2. **HTTPS 리스너 추가**
   - ALB → 리스너 추가
   - 프로토콜: **HTTPS**
   - 포트: **443**
   - 기본 SSL 인증서: ACM에서 발급한 인증서 선택
   - 기본 작업: `kime-frontend-tg`

3. **HTTP → HTTPS 리디렉션 규칙**
   - HTTP:80 리스너의 기본 작업을 "리디렉션"으로 변경
   - 프로토콜: HTTPS, 포트: 443

### 7.6 ALB DNS 이름 확인

1. 로드 밸런서 → `kime-alb` → "설명" 탭
2. **DNS 이름** 복사
   - 예: `kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com`
3. 브라우저에서 접속 테스트:
   - `http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com`

**📝 저장**:
```bash
ALB_DNS=kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com
```

**✅ Phase 7 완료 체크리스트**:
- [ ] Backend 대상 그룹 생성 (`kime-backend-tg`)
- [ ] Frontend 대상 그룹 생성 (`kime-frontend-tg`)
- [ ] Application Load Balancer 생성 (`kime-alb`)
- [ ] 경로 기반 라우팅 규칙 설정 (`/api/*` → Backend)
- [ ] ALB DNS 이름 확인 및 접속 테스트

---

## Phase 8: 보안 그룹 최종 점검

### 8.1 보안 그룹 규칙 검토

#### ALB 보안 그룹 (`kime-alb-sg`)
```
인바운드:
- HTTP (80) from 0.0.0.0/0
- HTTPS (443) from 0.0.0.0/0

아웃바운드:
- All traffic to 0.0.0.0/0
```

#### Frontend 보안 그룹 (`kime-frontend-sg`)
```
인바운드:
- HTTP (80) from kime-alb-sg
- SSH (22) from 내 IP (임시, 나중에 삭제)

아웃바운드:
- All traffic to 0.0.0.0/0
```

#### Backend 보안 그룹 (`kime-backend-sg`)
```
인바운드:
- Custom TCP (8000) from kime-alb-sg
- SSH (22) from kime-bastion-sg
- PostgreSQL (5432) from kime-rds-sg (역방향 확인)
- Redis (6379) from kime-redis-sg (역방향 확인)

아웃바운드:
- All traffic to 0.0.0.0/0
```

#### RDS 보안 그룹 (`kime-rds-sg`)
```
인바운드:
- PostgreSQL (5432) from kime-backend-sg
- PostgreSQL (5432) from kime-bastion-sg

아웃바운드:
- (기본값 유지)
```

#### Redis 보안 그룹 (`kime-redis-sg`)
```
인바운드:
- Custom TCP (6379) from kime-backend-sg
- Custom TCP (6379) from kime-bastion-sg

아웃바운드:
- (기본값 유지)
```

#### Bastion 보안 그룹 (`kime-bastion-sg`)
```
인바운드:
- SSH (22) from 내 IP만!

아웃바운드:
- All traffic to 0.0.0.0/0
```

### 8.2 IAM 역할 생성 (EC2용)

#### Backend EC2 IAM 역할
```bash
# CLI로 신뢰 정책 생성
cat > /tmp/ec2-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# IAM 역할 생성
aws iam create-role \
  --role-name KimeBackendEC2Role \
  --assume-role-policy-document file:///tmp/ec2-trust-policy.json

# S3 읽기 권한 추가
aws iam attach-role-policy \
  --role-name KimeBackendEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# CloudWatch 로그 권한 추가
aws iam attach-role-policy \
  --role-name KimeBackendEC2Role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy

# 인스턴스 프로파일 생성
aws iam create-instance-profile \
  --instance-profile-name KimeBackendEC2Profile

# 역할을 프로파일에 추가
aws iam add-role-to-instance-profile \
  --instance-profile-name KimeBackendEC2Profile \
  --role-name KimeBackendEC2Role
```

**또는 AWS Console에서**:
1. IAM → 역할 → "역할 만들기"
2. 신뢰할 수 있는 엔터티: **AWS 서비스** → **EC2**
3. 권한 정책:
   - `AmazonS3ReadOnlyAccess`
   - `CloudWatchAgentServerPolicy`
4. 역할 이름: `KimeBackendEC2Role`
5. 생성 후 EC2 인스턴스에 연결:
   - EC2 → `kime-backend-1` → 작업 → 보안 → "IAM 역할 수정"
   - `KimeBackendEC2Role` 선택

#### Frontend EC2 IAM 역할
동일한 방법으로:
- 역할 이름: `KimeFrontendEC2Role`
- 권한: `AmazonS3ReadOnlyAccess`, `CloudWatchAgentServerPolicy`

### 8.3 SSH 접근 제한 (프로덕션 모드)

**⚠️ 중요**: 배포가 완료되면 SSH 접근을 Bastion Host로만 제한하세요!

```bash
# Frontend/Backend 보안 그룹에서 SSH 규칙 삭제
# EC2 → 보안 그룹 → kime-frontend-sg → 인바운드 규칙 편집
# SSH (22) from 0.0.0.0/0 → 삭제
# SSH (22) from kime-bastion-sg → 추가
```

**✅ Phase 8 완료 체크리스트**:
- [ ] 모든 보안 그룹 규칙 검토 완료
- [ ] Backend/Frontend IAM 역할 생성 및 연결
- [ ] SSH 접근을 Bastion으로 제한 (프로덕션 시)

---

## Phase 9: 애플리케이션 배포

### 9.1 환경변수 설정

#### Backend 환경변수 (`/home/ubuntu/kime-backend/.env`)
```bash
# Backend EC2에 접속 (Bastion을 통해)
ssh -i ~/.ssh/kime-keypair.pem \
    -J ubuntu@$BASTION_IP \
    ubuntu@$BACKEND_PRIVATE_IP

# .env 파일 생성
cat > /home/ubuntu/kime-backend/.env <<EOF
# Database
DATABASE_URL=postgresql://postgres:K1m3Ch@t_DB_P@ssw0rd!2025@kime-db.c9akj7l6z8y0.ap-northeast-2.rds.amazonaws.com:5432/kime_statedb
LOGDB_URL=postgresql://postgres:K1m3Ch@t_DB_P@ssw0rd!2025@kime-db.c9akj7l6z8y0.ap-northeast-2.rds.amazonaws.com:5432/kime_logdb

# Redis
REDIS_HOST=kime-redis.abc123.ng.0001.apn2.cache.amazonaws.com
REDIS_PORT=6379
REDIS_PASSWORD=K1m3Ch@t_R3d1s_T0k3n!2025
REDIS_DB=0
REDIS_SSL=true

# LLM API Keys (실제 키로 교체)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS=http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com

# S3/CloudFront
CDN_URL=https://d1234567890abc.cloudfront.net
S3_BUCKET=kime-assets-2025
EOF

chmod 600 /home/ubuntu/kime-backend/.env
```

#### Frontend 환경변수 (`/home/ubuntu/kime-frontend/.env.production`)
```bash
# Frontend EC2에 접속
ssh -i ~/.ssh/kime-keypair.pem ubuntu@$FRONTEND_PUBLIC_IP

cat > /home/ubuntu/kime-frontend/.env.production <<EOF
# API Endpoint
VITE_API_URL=http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com/api

# CDN
VITE_CDN_URL=https://d1234567890abc.cloudfront.net

# Environment
VITE_ENV=production
EOF
```

### 9.2 Backend 배포

```bash
# Backend EC2에서
cd /home/ubuntu/kime-backend

# Git clone (또는 로컬에서 rsync)
git clone https://github.com/yourusername/kime-chat.git .
# 또는
# 로컬에서: rsync -avz -e "ssh -i ~/.ssh/kime-keypair.pem -J ubuntu@$BASTION_IP" \
#             backend/ ubuntu@$BACKEND_PRIVATE_IP:/home/ubuntu/kime-backend/

# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 마이그레이션 (Alembic 사용 시)
# alembic upgrade head

# Systemd 서비스 생성
sudo tee /etc/systemd/system/kime-backend.service > /dev/null <<EOF
[Unit]
Description=Kime Chat Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/kime-backend
Environment="PATH=/home/ubuntu/kime-backend/venv/bin"
ExecStart=/home/ubuntu/kime-backend/venv/bin/python api_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable kime-backend
sudo systemctl start kime-backend

# 상태 확인
sudo systemctl status kime-backend

# 로그 확인
sudo journalctl -u kime-backend -f
```

**Health Check 엔드포인트 추가 (api_server.py)**:
```python
@app.get("/health")
async def health_check():
    """ALB Health Check Endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

### 9.3 Frontend 빌드 및 배포

```bash
# 로컬에서 빌드
cd /Users/jtm427/Desktop/workspace/front

# 환경변수 설정
export VITE_API_URL=http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com/api
export VITE_CDN_URL=https://d1234567890abc.cloudfront.net

# 프로덕션 빌드
npm run build

# Frontend EC2로 전송
rsync -avz -e "ssh -i ~/.ssh/kime-keypair.pem" \
    dist/ ubuntu@$FRONTEND_PUBLIC_IP:/home/ubuntu/kime-frontend/dist/

# Frontend EC2에서 Nginx 설정
ssh -i ~/.ssh/kime-keypair.pem ubuntu@$FRONTEND_PUBLIC_IP

sudo tee /etc/nginx/sites-available/kime <<EOF
server {
    listen 80;
    server_name _;

    root /home/ubuntu/kime-frontend/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Gzip 압축
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
EOF

# Nginx 활성화
sudo ln -s /etc/nginx/sites-available/kime /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 9.4 배포 확인

```bash
# Backend Health Check
curl http://<BACKEND_PRIVATE_IP>:8000/health
# 출력: {"status":"healthy","timestamp":"2025-10-30T..."}

# Frontend 접속 (ALB를 통해)
curl http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com/
# HTML 출력 확인

# API 요청 테스트
curl -X POST http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "train",
    "user_input": "시작",
    "user_name": "테스트"
  }'
```

**✅ Phase 9 완료 체크리스트**:
- [ ] Backend 환경변수 설정
- [ ] Frontend 환경변수 설정
- [ ] Backend 배포 및 Systemd 서비스 등록
- [ ] Frontend 빌드 및 Nginx 설정
- [ ] Health Check 엔드포인트 동작 확인
- [ ] ALB를 통한 Frontend/Backend 접속 확인

---

## Phase 10: 테스트 및 모니터링 설정

### 10.1 CloudWatch 대시보드 생성

1. **CloudWatch 서비스로 이동**
   - 상단 검색창에 "CloudWatch" 입력 → "CloudWatch" 클릭

2. **대시보드 생성**
   - 좌측 메뉴에서 "대시보드" → "대시보드 생성"
   - 이름: `Kime-Production-Dashboard`

3. **위젯 추가**
   - **ALB 메트릭**:
     - RequestCount
     - TargetResponseTime
     - HTTPCode_Target_2XX_Count
     - HTTPCode_Target_4XX_Count
     - HTTPCode_Target_5XX_Count
     - HealthyHostCount
     - UnHealthyHostCount

   - **EC2 메트릭**:
     - CPUUtilization (Backend, Frontend 각각)
     - NetworkIn/NetworkOut
     - DiskReadOps/DiskWriteOps

   - **RDS 메트릭**:
     - CPUUtilization
     - DatabaseConnections
     - ReadLatency/WriteLatency
     - FreeStorageSpace

   - **ElastiCache 메트릭**:
     - CPUUtilization
     - CurrConnections
     - NetworkBytesIn/NetworkBytesOut
     - CacheHits/CacheMisses

### 10.2 CloudWatch 알람 설정

```bash
# EC2 CPU 사용률 알람
aws cloudwatch put-metric-alarm \
  --alarm-name kime-backend-high-cpu \
  --alarm-description "Backend CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=InstanceId,Value=i-XXXXXXXXX

# RDS 연결 수 알람
aws cloudwatch put-metric-alarm \
  --alarm-name kime-rds-high-connections \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=DBInstanceIdentifier,Value=kime-db

# ALB 5XX 에러 알람
aws cloudwatch put-metric-alarm \
  --alarm-name kime-alb-5xx-errors \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=LoadBalancer,Value=app/kime-alb/...
```

### 10.3 로그 수집 설정 (CloudWatch Logs)

```bash
# Backend EC2에서 CloudWatch Agent 설정
cat > /tmp/cloudwatch-config.json <<EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/kime/*.log",
            "log_group_name": "/aws/ec2/kime-backend",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%d %H:%M:%S"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "Kime/Backend",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"}
        ],
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DISK_USED", "unit": "Percent"}
        ]
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}
        ]
      }
    }
  }
}
EOF

# CloudWatch Agent 시작
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:///tmp/cloudwatch-config.json
```

### 10.4 종합 테스트

```bash
# 부하 테스트 (로컬에서)
# Apache Bench 사용
ab -n 1000 -c 10 http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com/

# 또는 wrk 사용
wrk -t4 -c100 -d30s http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com/

# API 성능 테스트
time curl -X POST http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "train",
    "user_input": "시작",
    "user_name": "성능테스트"
  }' --max-time 120
```

**✅ Phase 10 완료 체크리스트**:
- [ ] CloudWatch 대시보드 생성
- [ ] CloudWatch 알람 설정 (CPU, RDS, ALB)
- [ ] CloudWatch Logs 수집 설정
- [ ] 부하 테스트 실행 및 결과 확인

---

## Troubleshooting

### 문제 1: EC2 인스턴스에 SSH 접속 불가

**증상**: `ssh: connect to host X.X.X.X port 22: Connection timed out`

**원인**:
- 보안 그룹에서 SSH 포트가 열려있지 않음
- 잘못된 서브넷 (프라이빗 서브넷의 경우 Bastion 필요)

**해결**:
```bash
# 보안 그룹 확인
aws ec2 describe-security-groups --group-ids sg-XXXXXXXX

# Bastion을 통해 접속
ssh -i ~/.ssh/kime-keypair.pem \
    -J ubuntu@<BASTION_PUBLIC_IP> \
    ubuntu@<PRIVATE_IP>
```

### 문제 2: RDS 접속 불가

**증상**: `psql: could not connect to server: Connection timed out`

**원인**:
- RDS 보안 그룹에서 Backend EC2의 접근을 허용하지 않음
- 서브넷 그룹이 올바르지 않음

**해결**:
```bash
# Bastion에서 테스트
psql -h <RDS_ENDPOINT> -U postgres -d kime_statedb

# 연결 실패 시 보안 그룹 규칙 추가
aws ec2 authorize-security-group-ingress \
  --group-id <RDS_SG_ID> \
  --protocol tcp \
  --port 5432 \
  --source-group <BACKEND_SG_ID>
```

### 문제 3: ALB Health Check 실패

**증상**: Target Group에서 "unhealthy" 상태

**원인**:
- Backend 서비스가 실행되지 않음
- Health Check 경로가 잘못됨 (`/health` 엔드포인트 없음)

**해결**:
```bash
# Backend EC2에서 서비스 상태 확인
sudo systemctl status kime-backend

# 로그 확인
sudo journalctl -u kime-backend -n 100

# Health Check 엔드포인트 수동 테스트
curl http://localhost:8000/health

# 서비스 재시작
sudo systemctl restart kime-backend
```

### 문제 4: CloudFront에서 S3 접근 거부

**증상**: `403 Forbidden` 에러

**원인**:
- S3 버킷 정책에서 CloudFront 접근을 허용하지 않음
- OAC (Origin Access Control) 설정 누락

**해결**:
1. S3 버킷 정책에 CloudFront Distribution ARN 추가 (Phase 6.5 참조)
2. CloudFront 배포에서 OAC 설정 확인

### 문제 5: 환경변수 로드 실패

**증상**: Backend에서 `KeyError: 'DATABASE_URL'`

**원인**:
- `.env` 파일이 올바른 위치에 없음
- Systemd 서비스에서 환경변수를 로드하지 않음

**해결**:
```bash
# .env 파일 위치 확인
ls -la /home/ubuntu/kime-backend/.env

# Systemd 서비스 수정 (EnvironmentFile 추가)
sudo tee -a /etc/systemd/system/kime-backend.service > /dev/null <<EOF
[Service]
EnvironmentFile=/home/ubuntu/kime-backend/.env
EOF

sudo systemctl daemon-reload
sudo systemctl restart kime-backend
```

### 문제 6: Redis 연결 실패

**증상**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**원인**:
- Redis AUTH 토큰이 잘못됨
- SSL/TLS 설정 누락

**해결**:
```python
# backend 코드에서 Redis 연결 확인
import redis

r = redis.Redis(
    host='<REDIS_ENDPOINT>',
    port=6379,
    password='<AUTH_TOKEN>',
    ssl=True,  # 중요!
    ssl_cert_reqs=None
)
r.ping()  # True 반환되어야 함
```

### 문제 7: 대상 그룹에 트래픽 분산 안 됨

**증상**: 한 인스턴스만 요청을 처리함

**원인**:
- 스티키 세션 (Session Affinity) 활성화
- 한 인스턴스만 healthy 상태

**해결**:
```bash
# 대상 그룹 상태 확인
aws elbv2 describe-target-health --target-group-arn <TG_ARN>

# 스티키 세션 비활성화 (필요 시)
# ALB → 대상 그룹 → 속성 → 스티키 세션 비활성화
```

---

## 다음 단계

**배포 완료 후**:
1. **도메인 연결** (선택 사항):
   - Route 53에서 도메인 구매 또는 외부 도메인 연결
   - ALB에 ALIAS 레코드 추가
   - ACM에서 SSL 인증서 발급 후 HTTPS 리스너 추가

2. **Auto Scaling 설정**:
   - EC2 Auto Scaling Group 생성
   - 트래픽에 따라 자동으로 인스턴스 증감

3. **CI/CD 파이프라인 구축**:
   - GitHub Actions 또는 AWS CodePipeline
   - 자동 빌드 및 배포

4. **백업 및 재해 복구**:
   - RDS 스냅샷 자동화
   - S3 버전 관리 활성화
   - 다른 리전으로 크로스 리전 복제

5. **보안 강화**:
   - AWS WAF 설정 (DDoS, SQL Injection 방어)
   - Secrets Manager로 민감 정보 관리
   - GuardDuty 활성화 (위협 탐지)

6. **비용 최적화**:
   - Cost Explorer로 비용 분석
   - Savings Plans 또는 Reserved Instances 구매
   - 사용하지 않는 리소스 정리

---

## 참고 자료

- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS EC2 사용 설명서](https://docs.aws.amazon.com/ec2/)
- [AWS RDS 모범 사례](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [AWS ALB 설명서](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
- [AWS CloudFront 개발자 가이드](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/)

---

**작성자**: Claude Code
**마지막 업데이트**: 2025-10-30
**버전**: 1.0
