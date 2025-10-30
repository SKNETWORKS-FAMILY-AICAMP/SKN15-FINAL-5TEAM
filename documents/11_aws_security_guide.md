# AWS 보안 가이드

**작성일**: 2025-10-30
**대상**: Kime Chat 프로덕션 환경
**버전**: 1.0

---

## 📋 목차

1. [보안 개요](#보안-개요)
2. [IAM 보안](#1-iam-보안)
3. [네트워크 보안](#2-네트워크-보안)
4. [데이터 보안](#3-데이터-보안)
5. [애플리케이션 보안](#4-애플리케이션-보안)
6. [모니터링 및 로깅](#5-모니터링-및-로깅)
7. [규정 준수](#6-규정-준수)
8. [인시던트 대응](#7-인시던트-대응)
9. [보안 체크리스트](#8-보안-체크리스트)

---

## 보안 개요

### 보안 원칙 (AWS Well-Architected Framework)

1. **최소 권한 원칙 (Principle of Least Privilege)**
   - 필요한 최소한의 권한만 부여
   - 정기적으로 권한 검토 및 제거

2. **심층 방어 (Defense in Depth)**
   - 다층 보안 구조 (네트워크, 애플리케이션, 데이터)
   - 한 계층이 뚫려도 다른 계층에서 방어

3. **암호화 기본 적용 (Encryption by Default)**
   - 전송 중 암호화 (TLS/SSL)
   - 저장 중 암호화 (AES-256)

4. **감사 및 모니터링**
   - 모든 활동 로깅
   - 이상 행위 탐지 및 알림

5. **자동화**
   - 보안 설정 자동화
   - 취약점 자동 패치

### 보안 책임 공유 모델

**AWS 책임** (Security OF the Cloud):
- 물리적 보안
- 하드웨어/소프트웨어 인프라
- 네트워크 인프라
- 가상화 계층

**고객 책임** (Security IN the Cloud):
- 게스트 OS 패치 및 업데이트
- 애플리케이션 보안
- 데이터 암호화
- 네트워크 및 방화벽 구성
- IAM 관리

---

## 1. IAM 보안

### 1.1 루트 계정 보호 (최우선)

#### ✅ 필수 조치
```bash
# 1. MFA 활성화 (이미 완료했어야 함)
# AWS Console → IAM → 보안 자격 증명 → MFA 활성화

# 2. 루트 계정 액세스 키 삭제
aws iam list-access-keys --user-name root
# 있다면 즉시 삭제:
aws iam delete-access-key --access-key-id AKIA... --user-name root

# 3. 루트 계정 사용 알림 설정
aws cloudwatch put-metric-alarm \
  --alarm-name root-account-usage \
  --alarm-description "Alert when root account is used" \
  --metric-name RootAccountUsage \
  --namespace AWS/IAM \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold
```

#### ⚠️ 루트 계정 사용 금지
- **절대로** 일상적인 작업에 루트 계정 사용 금지
- IAM 관리자 사용자만 사용
- 루트 계정은 다음 경우에만 사용:
  - 빌링 설정 변경
  - AWS 계정 폐쇄
  - Support Plan 변경

### 1.2 IAM 사용자 및 그룹 관리

#### 사용자 생성 원칙
```bash
# 개인별 IAM 사용자 생성 (공유 계정 금지!)
aws iam create-user --user-name john.doe

# 그룹으로 권한 관리
aws iam create-group --group-name Developers
aws iam attach-group-policy \
  --group-name Developers \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# 사용자를 그룹에 추가
aws iam add-user-to-group \
  --user-name john.doe \
  --group-name Developers
```

#### 권장 그룹 구조
```yaml
그룹 이름: Administrators
권한: AdministratorAccess
대상: 시스템 관리자 (최소 인원)

그룹 이름: Developers
권한: PowerUserAccess (IAM 제외)
대상: 개발자

그룹 이름: ReadOnly
권한: ReadOnlyAccess
대상: 분석가, 감사자

그룹 이름: DatabaseAdmins
권한: RDS Full Access, EC2 Read
대상: DBA
```

### 1.3 IAM 정책 (Policy) 설계

#### 최소 권한 정책 예시 - Backend EC2
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::kime-assets-2025",
        "arn:aws:s3:::kime-assets-2025/*"
      ]
    },
    {
      "Sid": "AllowCloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:ap-northeast-2:*:log-group:/aws/ec2/kime-*"
    },
    {
      "Sid": "AllowSecretsManagerRead",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:ap-northeast-2:*:secret:kime/*"
    }
  ]
}
```

#### 정책 생성 및 적용
```bash
# 정책 파일 생성
cat > backend-ec2-policy.json <<EOF
{위의 정책 내용}
EOF

# 정책 생성
aws iam create-policy \
  --policy-name KimeBackendEC2Policy \
  --policy-document file://backend-ec2-policy.json

# 역할에 연결
aws iam attach-role-policy \
  --role-name KimeBackendEC2Role \
  --policy-arn arn:aws:iam::123456789012:policy/KimeBackendEC2Policy
```

### 1.4 MFA 강제 (Multi-Factor Authentication)

#### 모든 IAM 사용자에게 MFA 강제
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAllExceptMFAManagement",
      "Effect": "Deny",
      "NotAction": [
        "iam:CreateVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:ListMFADevices",
        "iam:ListUsers",
        "iam:ListVirtualMFADevices",
        "iam:ResyncMFADevice",
        "sts:GetSessionToken"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
```

### 1.5 액세스 키 관리

#### ⚠️ 중요 규칙
```bash
# 1. 액세스 키 정기 로테이션 (90일마다)
aws iam list-access-keys --user-name john.doe
# 출력:
# {
#     "AccessKeyMetadata": [
#         {
#             "AccessKeyId": "AKIA...",
#             "CreateDate": "2024-08-01T00:00:00Z",
#             "Status": "Active"
#         }
#     ]
# }

# 90일 이상된 키는 교체
# 새 키 생성
aws iam create-access-key --user-name john.doe

# 애플리케이션에서 새 키로 교체 후 기존 키 삭제
aws iam delete-access-key --user-name john.doe --access-key-id AKIA...

# 2. 사용하지 않는 키 비활성화 (마지막 사용일 확인)
aws iam get-access-key-last-used --access-key-id AKIA...
```

#### 액세스 키 대신 IAM 역할 사용 (권장)
```bash
# EC2 인스턴스: 액세스 키 없이 IAM 역할 사용
# Lambda 함수: 실행 역할 사용
# ECS 태스크: 태스크 역할 사용

# 이점: 자동 로테이션, 유출 위험 감소
```

### 1.6 IAM Access Analyzer 설정

```bash
# IAM Access Analyzer 활성화 (외부 접근 탐지)
aws accessanalyzer create-analyzer \
  --analyzer-name kime-analyzer \
  --type ACCOUNT \
  --region ap-northeast-2

# 발견된 외부 접근 확인
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:ap-northeast-2:123456789012:analyzer/kime-analyzer
```

**✅ IAM 보안 체크리스트**:
- [ ] 루트 계정 MFA 활성화
- [ ] 루트 계정 액세스 키 삭제
- [ ] 모든 IAM 사용자에게 MFA 강제
- [ ] 개인별 IAM 사용자 생성 (공유 금지)
- [ ] 그룹 기반 권한 관리
- [ ] 최소 권한 정책 적용
- [ ] 액세스 키 90일마다 로테이션
- [ ] IAM Access Analyzer 활성화

---

## 2. 네트워크 보안

### 2.1 VPC 보안 설계

#### VPC 구조 (이미 생성 완료)
```
10.0.0.0/16 (kime-vpc)
├── Public Subnet 2a (10.0.0.0/24) - Frontend, ALB, NAT
├── Public Subnet 2c (10.0.1.0/24) - Frontend, ALB, NAT
├── Private Subnet 2a (10.0.128.0/24) - Backend, RDS, Redis
└── Private Subnet 2c (10.0.129.0/24) - Backend, RDS, Redis
```

#### VPC Flow Logs 활성화 (필수)
```bash
# 모든 네트워크 트래픽 로깅
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-XXXXXXXX \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/kime-vpc \
  --deliver-logs-permission-arn arn:aws:iam::123456789012:role/VPCFlowLogsRole

# 로그 보존 기간 설정 (90일)
aws logs put-retention-policy \
  --log-group-name /aws/vpc/kime-vpc \
  --retention-in-days 90
```

**사용 사례**:
- 의심스러운 IP 주소 탐지
- DDoS 공격 분석
- 트래픽 패턴 분석

### 2.2 보안 그룹 (Security Groups) 강화

#### 원칙
1. **기본적으로 모든 인바운드 차단**
2. **필요한 포트만 허용**
3. **소스를 최대한 제한** (0.0.0.0/0 최소화)
4. **아웃바운드도 제한** (필요시)

#### 프로덕션 보안 그룹 규칙

**ALB 보안 그룹** (`kime-alb-sg`):
```bash
# 인바운드
HTTP (80) from 0.0.0.0/0
HTTPS (443) from 0.0.0.0/0

# 아웃바운드 (제한 권장)
HTTP (80) to kime-frontend-sg
Custom TCP (8000) to kime-backend-sg
```

**Frontend 보안 그룹** (`kime-frontend-sg`):
```bash
# 인바운드
HTTP (80) from kime-alb-sg ONLY (0.0.0.0/0 절대 금지!)
SSH (22) from kime-bastion-sg ONLY

# 아웃바운드
HTTPS (443) to 0.0.0.0/0 (npm, apt 업데이트용)
```

**Backend 보안 그룹** (`kime-backend-sg`):
```bash
# 인바운드
Custom TCP (8000) from kime-alb-sg ONLY
SSH (22) from kime-bastion-sg ONLY

# 아웃바운드
PostgreSQL (5432) to kime-rds-sg
Redis (6379) to kime-redis-sg
HTTPS (443) to 0.0.0.0/0 (LLM API, pip 설치용)
```

**RDS 보안 그룹** (`kime-rds-sg`):
```bash
# 인바운드
PostgreSQL (5432) from kime-backend-sg
PostgreSQL (5432) from kime-bastion-sg

# 아웃바운드: 없음 (기본값)
```

**Redis 보안 그룹** (`kime-redis-sg`):
```bash
# 인바운드
Custom TCP (6379) from kime-backend-sg
Custom TCP (6379) from kime-bastion-sg

# 아웃바운드: 없음
```

**Bastion 보안 그룹** (`kime-bastion-sg`):
```bash
# 인바운드
SSH (22) from 특정 IP만! (회사 IP, 집 IP 등)
# 예: 123.45.67.89/32 (단일 IP), 203.0.113.0/24 (서브넷)

# 아웃바운드
SSH (22) to kime-backend-sg, kime-frontend-sg
PostgreSQL (5432) to kime-rds-sg
Redis (6379) to kime-redis-sg
HTTPS (443) to 0.0.0.0/0 (apt 업데이트)
```

#### 보안 그룹 감사
```bash
# 0.0.0.0/0 허용하는 보안 그룹 찾기 (위험!)
aws ec2 describe-security-groups \
  --filters Name=ip-permission.cidr,Values=0.0.0.0/0 \
  --query 'SecurityGroups[?IpPermissions[?FromPort!=`80` && FromPort!=`443`]].[GroupId,GroupName,IpPermissions]'

# 사용하지 않는 보안 그룹 찾기
aws ec2 describe-security-groups \
  --query 'SecurityGroups[?length(NetworkInterfaceIds)==`0`].[GroupId,GroupName]'
```

### 2.3 Network ACLs (선택 사항 - 추가 방어층)

```bash
# 서브넷 단위 방화벽 (보안 그룹보다 상위 계층)
# 예: 특정 국가 IP 차단

aws ec2 create-network-acl-entry \
  --network-acl-id acl-XXXXXXXX \
  --ingress \
  --rule-number 50 \
  --protocol tcp \
  --port-range From=22,To=22 \
  --cidr-block 123.45.67.0/24 \
  --rule-action deny
```

### 2.4 AWS WAF 설정 (Web Application Firewall)

#### ALB에 WAF 연결
```bash
# WAF v2 웹 ACL 생성
aws wafv2 create-web-acl \
  --name kime-waf \
  --scope REGIONAL \
  --region ap-northeast-2 \
  --default-action Allow={} \
  --rules file://waf-rules.json

# ALB에 연결
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:ap-northeast-2:123456789012:regional/webacl/kime-waf/... \
  --resource-arn arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:loadbalancer/app/kime-alb/...
```

#### 권장 WAF 규칙 (`waf-rules.json`):
```json
[
  {
    "Name": "RateLimitRule",
    "Priority": 1,
    "Statement": {
      "RateBasedStatement": {
        "Limit": 2000,
        "AggregateKeyType": "IP"
      }
    },
    "Action": {
      "Block": {}
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "RateLimitRule"
    }
  },
  {
    "Name": "AWSManagedRulesCommonRuleSet",
    "Priority": 2,
    "Statement": {
      "ManagedRuleGroupStatement": {
        "VendorName": "AWS",
        "Name": "AWSManagedRulesCommonRuleSet"
      }
    },
    "OverrideAction": {
      "None": {}
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "CommonRuleSet"
    }
  },
  {
    "Name": "AWSManagedRulesKnownBadInputsRuleSet",
    "Priority": 3,
    "Statement": {
      "ManagedRuleGroupStatement": {
        "VendorName": "AWS",
        "Name": "AWSManagedRulesKnownBadInputsRuleSet"
      }
    },
    "OverrideAction": {
      "None": {}
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "KnownBadInputs"
    }
  }
]
```

**비용**: 약 $5/월 + 요청당 $0.60/백만

### 2.5 DDoS 방어 (AWS Shield)

#### AWS Shield Standard (무료)
- 모든 AWS 고객에게 자동 제공
- Layer 3/4 DDoS 방어 (SYN Flood, UDP Reflection 등)

#### AWS Shield Advanced (선택 사항)
- 비용: $3,000/월
- 추가 DDoS 방어 + 24/7 대응팀
- 소규모 프로젝트에는 불필요

**✅ 네트워크 보안 체크리스트**:
- [ ] VPC Flow Logs 활성화
- [ ] 보안 그룹에서 0.0.0.0/0 최소화
- [ ] SSH 접근을 Bastion으로만 제한
- [ ] RDS/Redis는 프라이빗 서브넷 배치
- [ ] AWS WAF 설정 (Rate Limit, SQL Injection 방어)
- [ ] 정기적으로 보안 그룹 감사

---

## 3. 데이터 보안

### 3.1 암호화 - 저장 중 (Encryption at Rest)

#### RDS 암호화 (이미 활성화)
```bash
# 기존 RDS 인스턴스 암호화 확인
aws rds describe-db-instances \
  --db-instance-identifier kime-db \
  --query 'DBInstances[0].StorageEncrypted'
# 출력: true

# 암호화되지 않은 경우 스냅샷 → 암호화 복원
aws rds create-db-snapshot \
  --db-instance-identifier kime-db \
  --db-snapshot-identifier kime-db-snapshot

aws rds copy-db-snapshot \
  --source-db-snapshot-identifier kime-db-snapshot \
  --target-db-snapshot-identifier kime-db-snapshot-encrypted \
  --kms-key-id arn:aws:kms:ap-northeast-2:123456789012:key/... \
  --copy-tags

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier kime-db-encrypted \
  --db-snapshot-identifier kime-db-snapshot-encrypted
```

#### ElastiCache 암호화 (이미 활성화)
```bash
# 전송 중 + 저장 중 암호화 확인
aws elasticache describe-replication-groups \
  --replication-group-id kime-redis \
  --query 'ReplicationGroups[0].[TransitEncryptionEnabled,AtRestEncryptionEnabled]'
# 출력: [true, true]
```

#### S3 버킷 암호화
```bash
# 서버 측 암호화 (SSE-S3) 활성화
aws s3api put-bucket-encryption \
  --bucket kime-assets-2025 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      },
      "BucketKeyEnabled": true
    }]
  }'

# 버킷 버전 관리 활성화 (선택 사항 - 실수 삭제 방지)
aws s3api put-bucket-versioning \
  --bucket kime-assets-2025 \
  --versioning-configuration Status=Enabled
```

#### EBS 볼륨 암호화
```bash
# 새 볼륨은 기본 암호화 활성화
aws ec2 enable-ebs-encryption-by-default --region ap-northeast-2

# 기존 볼륨 확인
aws ec2 describe-volumes \
  --filters Name=attachment.instance-id,Values=i-XXXXXXXX \
  --query 'Volumes[*].[VolumeId,Encrypted]'

# 암호화되지 않은 볼륨은 스냅샷 → 암호화 복원
```

### 3.2 암호화 - 전송 중 (Encryption in Transit)

#### HTTPS/TLS 강제
```bash
# ALB에서 HTTP → HTTPS 리디렉션 (Phase 7에서 설정)
# Nginx에서 HTTPS만 허용:
server {
    listen 80;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ...
}
```

#### RDS/Redis 연결 암호화
```python
# PostgreSQL (SSL 강제)
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=require"

# Redis (TLS 활성화)
import redis
r = redis.Redis(
    host='...',
    port=6379,
    password='...',
    ssl=True,
    ssl_cert_reqs='required'
)
```

### 3.3 Secrets Manager (민감 정보 관리)

#### 환경변수를 Secrets Manager로 이전
```bash
# Secret 생성
aws secretsmanager create-secret \
  --name kime/production/database \
  --description "RDS credentials for production" \
  --secret-string '{
    "username": "postgres",
    "password": "K1m3Ch@t_DB_P@ssw0rd!2025",
    "host": "kime-db.c9akj7l6z8y0.ap-northeast-2.rds.amazonaws.com",
    "port": 5432,
    "dbname": "kime_statedb"
  }'

aws secretsmanager create-secret \
  --name kime/production/redis \
  --secret-string '{
    "host": "kime-redis.abc123.ng.0001.apn2.cache.amazonaws.com",
    "port": 6379,
    "password": "K1m3Ch@t_R3d1s_T0k3n!2025"
  }'

aws secretsmanager create-secret \
  --name kime/production/llm-api-keys \
  --secret-string '{
    "openai_api_key": "sk-...",
    "anthropic_api_key": "sk-ant-..."
  }'
```

#### Backend 코드에서 Secrets Manager 사용
```python
# backend/src/core/secrets.py
import boto3
import json
from functools import lru_cache

client = boto3.client('secretsmanager', region_name='ap-northeast-2')

@lru_cache(maxsize=10)
def get_secret(secret_name: str) -> dict:
    """Secrets Manager에서 비밀 값 가져오기 (캐싱)"""
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# 사용 예
db_secret = get_secret('kime/production/database')
DATABASE_URL = f"postgresql://{db_secret['username']}:{db_secret['password']}@{db_secret['host']}:{db_secret['port']}/{db_secret['dbname']}"
```

#### IAM 정책 추가 (Backend EC2 역할)
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue"
  ],
  "Resource": "arn:aws:secretsmanager:ap-northeast-2:*:secret:kime/*"
}
```

**비용**: $0.40/secret/month + $0.05/10,000 API calls

### 3.4 백업 및 복구

#### RDS 자동 백업 (이미 활성화)
```bash
# 백업 설정 확인
aws rds describe-db-instances \
  --db-instance-identifier kime-db \
  --query 'DBInstances[0].[BackupRetentionPeriod,PreferredBackupWindow]'
# 출력: [7, "02:00-03:00"]

# 수동 스냅샷 생성
aws rds create-db-snapshot \
  --db-instance-identifier kime-db \
  --db-snapshot-identifier kime-db-manual-$(date +%Y%m%d)

# 크로스 리전 복제 (재해 복구)
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:ap-northeast-2:123456789012:snapshot:kime-db-manual-20251030 \
  --target-db-snapshot-identifier kime-db-dr-20251030 \
  --region ap-northeast-1 \
  --kms-key-id arn:aws:kms:ap-northeast-1:123456789012:key/...
```

#### S3 버전 관리 및 수명 주기
```bash
# 버전 관리 활성화 (실수 삭제 방지)
aws s3api put-bucket-versioning \
  --bucket kime-assets-2025 \
  --versioning-configuration Status=Enabled

# 수명 주기 정책 (오래된 버전 삭제)
cat > lifecycle.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteOldVersions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    },
    {
      "Id": "MoveToGlacier",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket kime-assets-2025 \
  --lifecycle-configuration file://lifecycle.json
```

**✅ 데이터 보안 체크리스트**:
- [ ] RDS 암호화 활성화 (저장 중)
- [ ] ElastiCache 암호화 활성화 (저장 중 + 전송 중)
- [ ] S3 버킷 암호화 활성화
- [ ] EBS 볼륨 암호화 기본 활성화
- [ ] HTTPS/TLS 강제
- [ ] Secrets Manager로 민감 정보 관리
- [ ] RDS 자동 백업 7일 보존
- [ ] 크로스 리전 백업 설정 (재해 복구)

---

## 4. 애플리케이션 보안

### 4.1 OS 보안 강화

#### EC2 인스턴스 보안 설정
```bash
# Backend/Frontend EC2에 접속 후

# 1. 자동 보안 업데이트 활성화
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# 2. Fail2Ban 설치 (SSH 브루트포스 방지)
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 3. SSH 강화 (/etc/ssh/sshd_config)
sudo tee -a /etc/ssh/sshd_config > /dev/null <<EOF
# 보안 강화 설정
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers ubuntu
EOF

sudo systemctl restart sshd

# 4. 방화벽 (ufw) 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.0.0.0/16 to any port 22  # VPC 내부에서만 SSH
sudo ufw allow 8000  # Backend API (보안 그룹에서 이미 제한됨)
sudo ufw enable
```

### 4.2 애플리케이션 의존성 보안

#### Python 패키지 취약점 스캔
```bash
# Backend에서
cd /home/ubuntu/kime-backend

# Safety 설치 (보안 취약점 스캔)
pip install safety

# 의존성 스캔
safety check --json

# 취약점 발견 시 업데이트
pip install --upgrade <패키지명>

# requirements.txt 업데이트
pip freeze > requirements.txt
```

#### Node.js 패키지 취약점 스캔
```bash
# Frontend에서
cd /home/ubuntu/kime-frontend

# npm audit 실행
npm audit

# 자동 수정 (가능한 경우)
npm audit fix

# 강제 수정 (주의!)
npm audit fix --force
```

### 4.3 API 보안

#### Rate Limiting (속도 제한)
```python
# backend/api_server.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/chat")
@limiter.limit("10/minute")  # 분당 10회 제한
async def chat(request: Request, ...):
    ...
```

#### CORS 설정 강화
```python
# backend/api_server.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://kime-alb-1234567890.ap-northeast-2.elb.amazonaws.com",
        "https://yourdomain.com"
    ],  # 특정 도메인만 허용 (와일드카드 금지!)
    allow_credentials=True,
    allow_methods=["POST", "GET"],  # 필요한 메서드만
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600
)
```

#### 입력 검증 (Pydantic)
```python
# backend/src/models/request.py
from pydantic import BaseModel, Field, validator

class ChatRequest(BaseModel):
    scenario_id: str = Field(..., regex="^(train|mugen|final)$")
    user_input: str = Field(..., min_length=1, max_length=500)
    user_name: str = Field(..., min_length=1, max_length=50)

    @validator('user_input')
    def sanitize_input(cls, v):
        # XSS 방지: HTML 태그 제거
        import re
        return re.sub(r'<[^>]*>', '', v)
```

#### SQL Injection 방지
```python
# SQLAlchemy/Psycopg2 사용 시 자동 방어
# ❌ 절대 금지: 문자열 결합
query = f"SELECT * FROM users WHERE name = '{user_input}'"  # 위험!

# ✅ 파라미터화된 쿼리 사용
query = "SELECT * FROM users WHERE name = %s"
cursor.execute(query, (user_input,))
```

### 4.4 로깅 및 모니터링 (보안)

#### 민감 정보 로깅 금지
```python
# backend/src/core/logger.py
import logging
import re

class SanitizingFilter(logging.Filter):
    """로그에서 민감 정보 제거"""
    def filter(self, record):
        # 비밀번호, 토큰, API 키 마스킹
        if isinstance(record.msg, str):
            record.msg = re.sub(r'password["\']?\s*:\s*["\']?[^"\']+', 'password: ***', record.msg, flags=re.IGNORECASE)
            record.msg = re.sub(r'token["\']?\s*:\s*["\']?[^"\']+', 'token: ***', record.msg, flags=re.IGNORECASE)
            record.msg = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-***', record.msg)
        return True

logger = logging.getLogger(__name__)
logger.addFilter(SanitizingFilter())
```

**✅ 애플리케이션 보안 체크리스트**:
- [ ] EC2 자동 보안 업데이트 활성화
- [ ] Fail2Ban 설치 (SSH 브루트포스 방지)
- [ ] SSH 강화 (루트 로그인 금지, 비밀번호 인증 금지)
- [ ] Python/Node.js 의존성 취약점 스캔
- [ ] API Rate Limiting 설정
- [ ] CORS 특정 도메인만 허용
- [ ] 입력 검증 (XSS, SQL Injection 방지)
- [ ] 로그에서 민감 정보 마스킹

---

## 5. 모니터링 및 로깅

### 5.1 CloudTrail (AWS API 활동 로깅)

```bash
# CloudTrail 활성화 (모든 AWS API 호출 기록)
aws cloudtrail create-trail \
  --name kime-trail \
  --s3-bucket-name kime-cloudtrail-logs-2025 \
  --is-multi-region-trail \
  --enable-log-file-validation

# 로깅 시작
aws cloudtrail start-logging --name kime-trail

# S3 버킷 생성 (CloudTrail 로그 저장)
aws s3 mb s3://kime-cloudtrail-logs-2025

# 버킷 정책 설정 (CloudTrail 접근 허용)
cat > cloudtrail-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AWSCloudTrailAclCheck",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudtrail.amazonaws.com"
      },
      "Action": "s3:GetBucketAcl",
      "Resource": "arn:aws:s3:::kime-cloudtrail-logs-2025"
    },
    {
      "Sid": "AWSCloudTrailWrite",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudtrail.amazonaws.com"
      },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::kime-cloudtrail-logs-2025/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-acl": "bucket-owner-full-control"
        }
      }
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket kime-cloudtrail-logs-2025 \
  --policy file://cloudtrail-policy.json
```

**사용 사례**:
- 누가 언제 RDS 인스턴스를 삭제했는지 추적
- 보안 그룹 변경 이력 확인
- IAM 권한 변경 감사

### 5.2 AWS Config (리소스 구성 추적)

```bash
# AWS Config 활성화
aws configservice put-configuration-recorder \
  --configuration-recorder name=kime-config,roleARN=arn:aws:iam::123456789012:role/config-role \
  --recording-group allSupported=true,includeGlobalResourceTypes=true

aws configservice put-delivery-channel \
  --delivery-channel name=kime-config,s3BucketName=kime-config-logs-2025

aws configservice start-configuration-recorder \
  --configuration-recorder-name kime-config
```

**권장 Config Rules**:
- `encrypted-volumes`: EBS 볼륨이 암호화되었는지 확인
- `rds-storage-encrypted`: RDS가 암호화되었는지 확인
- `s3-bucket-public-read-prohibited`: S3 버킷이 공개되지 않았는지 확인
- `root-account-mfa-enabled`: 루트 계정 MFA 활성화 확인

### 5.3 GuardDuty (위협 탐지)

```bash
# GuardDuty 활성화
aws guardduty create-detector --enable --region ap-northeast-2

# 탐지기 ID 확인
DETECTOR_ID=$(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)

# 위협 발견 시 알림 (SNS 연동)
aws guardduty create-filter \
  --detector-id $DETECTOR_ID \
  --name high-severity-findings \
  --finding-criteria '{"Criterion":{"severity":{"Gte":7}}}' \
  --action ARCHIVE
```

**탐지 항목**:
- 비정상적인 API 호출
- 포트 스캔, 브루트포스 공격
- 암호화폐 마이닝 악성코드
- 데이터 유출 시도

### 5.4 CloudWatch Alarms (이상 탐지)

```bash
# 비정상적으로 높은 트래픽 감지
aws cloudwatch put-metric-alarm \
  --alarm-name kime-high-traffic \
  --metric-name RequestCount \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 60 \
  --threshold 10000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=LoadBalancer,Value=app/kime-alb/...

# 5XX 에러 급증
aws cloudwatch put-metric-alarm \
  --alarm-name kime-5xx-spike \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 60 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1

# Backend 인스턴스 다운 감지
aws cloudwatch put-metric-alarm \
  --alarm-name kime-backend-down \
  --metric-name UnHealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 2
```

**✅ 모니터링 체크리스트**:
- [ ] CloudTrail 활성화 (모든 API 활동 로깅)
- [ ] AWS Config 활성화 (리소스 구성 추적)
- [ ] GuardDuty 활성화 (위협 탐지)
- [ ] CloudWatch Alarms 설정 (트래픽, 에러, 다운타임)
- [ ] VPC Flow Logs 활성화
- [ ] CloudWatch Logs 보존 기간 90일 이상

---

## 6. 규정 준수

### 6.1 개인정보 보호 (GDPR, 개인정보보호법)

#### 데이터 최소화
```python
# 필요한 정보만 수집
class UserSession(BaseModel):
    session_id: UUID
    user_name: str  # 실명 불필요 시 닉네임만
    # 이메일, 전화번호 등 불필요한 정보 수집 금지
```

#### 데이터 보존 기간 설정
```sql
-- StateDB: 세션 데이터 30일 후 자동 삭제
CREATE TABLE sessions (
    ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '30 days')
);

-- 정기 삭제 작업 (Cron)
DELETE FROM sessions WHERE expires_at < NOW();
```

#### 데이터 삭제 요청 처리
```python
# GDPR 삭제권 (Right to be Forgotten) 구현
@app.delete("/api/user/{user_id}")
async def delete_user_data(user_id: str):
    # StateDB에서 삭제
    db.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
    # LogDB에서 삭제 (또는 익명화)
    db.execute("UPDATE training_logs SET user_input = '[DELETED]' WHERE session_id IN (SELECT session_id FROM sessions WHERE user_id = %s)", (user_id,))
    return {"status": "deleted"}
```

### 6.2 감사 로그 (Audit Trail)

```python
# 모든 중요 작업 로깅
import logging

audit_logger = logging.getLogger('audit')
audit_logger.info({
    "action": "session_created",
    "user_id": user_id,
    "session_id": session_id,
    "ip_address": request.client.host,
    "timestamp": datetime.now().isoformat()
})
```

**✅ 규정 준수 체크리스트**:
- [ ] 개인정보 최소 수집
- [ ] 데이터 보존 기간 설정 (30일)
- [ ] 데이터 삭제 요청 API 구현
- [ ] 감사 로그 기록
- [ ] 암호화 (저장/전송)

---

## 7. 인시던트 대응

### 7.1 인시던트 대응 절차

#### Phase 1: 탐지 (Detection)
- CloudWatch Alarms, GuardDuty 알림
- 비정상적인 트래픽, 5XX 에러, 다운타임 감지

#### Phase 2: 분석 (Analysis)
```bash
# CloudWatch Logs 확인
aws logs tail /aws/ec2/kime-backend --follow

# VPC Flow Logs 분석
aws ec2 describe-flow-logs --filter Name=resource-id,Values=vpc-XXXXXXXX

# CloudTrail 이벤트 검색
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=DeleteDBInstance \
  --start-time 2025-10-30T00:00:00Z
```

#### Phase 3: 격리 (Containment)
```bash
# 공격 IP 차단 (보안 그룹)
aws ec2 revoke-security-group-ingress \
  --group-id sg-XXXXXXXX \
  --protocol tcp \
  --port 80 \
  --cidr 123.45.67.89/32

# 또는 NACL로 차단
aws ec2 create-network-acl-entry \
  --network-acl-id acl-XXXXXXXX \
  --ingress \
  --rule-number 10 \
  --protocol tcp \
  --port-range From=80,To=80 \
  --cidr-block 123.45.67.89/32 \
  --rule-action deny

# 감염된 인스턴스 격리
aws ec2 modify-instance-attribute \
  --instance-id i-XXXXXXXX \
  --groups sg-isolated  # 아웃바운드도 차단된 보안 그룹
```

#### Phase 4: 제거 (Eradication)
```bash
# 감염된 인스턴스 종료 및 재생성
aws ec2 terminate-instances --instance-ids i-XXXXXXXX

# AMI에서 새 인스턴스 생성 (깨끗한 상태)
aws ec2 run-instances \
  --image-id ami-XXXXXXXX \
  --instance-type t3.medium \
  --key-name kime-keypair \
  --security-group-ids sg-XXXXXXXX \
  --subnet-id subnet-XXXXXXXX
```

#### Phase 5: 복구 (Recovery)
```bash
# RDS 스냅샷에서 복원 (공격 이전 시점)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier kime-db-restored \
  --db-snapshot-identifier kime-db-snapshot-20251030-02:00

# S3 버전 관리로 파일 복원
aws s3api list-object-versions --bucket kime-assets-2025 --prefix images/
aws s3api copy-object \
  --copy-source kime-assets-2025/images/logo.png?versionId=VERSION_ID \
  --bucket kime-assets-2025 \
  --key images/logo.png
```

#### Phase 6: 사후 분석 (Post-Incident Review)
- 근본 원인 분석
- 재발 방지 대책 수립
- 문서화

### 7.2 비상 연락망

```yaml
보안 담당자:
  이름: [이름]
  전화: [전화번호]
  이메일: [이메일]

시스템 관리자:
  이름: [이름]
  전화: [전화번호]
  이메일: [이메일]

AWS 기술 지원:
  전화: 1588-8186 (한국)
  이메일: aws-korea-support@amazon.com
  지원 플랜: Basic (무료) / Developer / Business
```

### 7.3 데이터 유출 시나리오

**증상**: GuardDuty에서 "Unusual data transfer to external IP" 알림

**대응**:
1. **즉시 격리**: 해당 인스턴스의 아웃바운드 차단
2. **로그 분석**: VPC Flow Logs, CloudTrail 확인
3. **데이터 확인**: 어떤 데이터가 유출되었는지 확인
4. **고객 통지**: 개인정보 유출 시 72시간 내 통지 (GDPR)
5. **보안 강화**: 유출 경로 차단, 암호화 강화

**✅ 인시던트 대응 체크리스트**:
- [ ] 인시던트 대응 절차 문서화
- [ ] 비상 연락망 구성
- [ ] 정기적인 재해 복구 훈련 (DR Drill)
- [ ] 스냅샷 백업 테스트
- [ ] 인시던트 대응 플레이북 작성

---

## 8. 보안 체크리스트

### 8.1 일일 체크리스트

- [ ] CloudWatch Alarms 확인 (에러, 다운타임)
- [ ] GuardDuty 위협 탐지 확인
- [ ] 비정상적인 트래픽 패턴 확인 (VPC Flow Logs)
- [ ] 백업 성공 여부 확인 (RDS, S3)

### 8.2 주간 체크리스트

- [ ] EC2 인스턴스 보안 패치 업데이트
- [ ] 의존성 취약점 스캔 (Python, Node.js)
- [ ] 사용하지 않는 보안 그룹 삭제
- [ ] IAM 액세스 키 사용 이력 확인 (마지막 사용일)
- [ ] CloudTrail 로그 검토 (이상 활동)

### 8.3 월간 체크리스트

- [ ] IAM 사용자 및 권한 검토 (불필요한 권한 제거)
- [ ] 액세스 키 로테이션 (90일 이상된 키)
- [ ] 보안 그룹 규칙 감사 (0.0.0.0/0 최소화)
- [ ] RDS/S3 백업 복원 테스트
- [ ] AWS Trusted Advisor 보안 권장사항 확인
- [ ] 비용 검토 (예상치 못한 비용 증가 확인)

### 8.4 분기별 체크리스트

- [ ] 재해 복구 훈련 (DR Drill)
- [ ] 인시던트 대응 절차 업데이트
- [ ] 보안 정책 문서 검토 및 업데이트
- [ ] 제3자 보안 감사 (선택 사항)
- [ ] AWS Well-Architected Review

### 8.5 프로덕션 배포 전 체크리스트

**IAM**:
- [ ] 루트 계정 MFA 활성화
- [ ] 루트 계정 액세스 키 삭제
- [ ] IAM 사용자 MFA 강제
- [ ] 최소 권한 정책 적용
- [ ] IAM Access Analyzer 활성화

**네트워크**:
- [ ] VPC Flow Logs 활성화
- [ ] 보안 그룹 0.0.0.0/0 최소화
- [ ] SSH 접근 Bastion으로만 제한
- [ ] RDS/Redis 프라이빗 서브넷 배치
- [ ] AWS WAF 설정 (Rate Limit, SQL Injection 방어)

**데이터**:
- [ ] RDS 암호화 (저장/전송)
- [ ] ElastiCache 암호화 (저장/전송)
- [ ] S3 버킷 암호화
- [ ] EBS 볼륨 암호화
- [ ] HTTPS/TLS 강제
- [ ] Secrets Manager 사용
- [ ] 자동 백업 활성화 (7일)

**애플리케이션**:
- [ ] OS 자동 보안 업데이트
- [ ] Fail2Ban 설치
- [ ] SSH 강화 (루트 로그인 금지, 비밀번호 인증 금지)
- [ ] 의존성 취약점 스캔
- [ ] API Rate Limiting
- [ ] CORS 제한
- [ ] 입력 검증 (XSS, SQL Injection)
- [ ] 로그 민감 정보 마스킹

**모니터링**:
- [ ] CloudTrail 활성화
- [ ] AWS Config 활성화
- [ ] GuardDuty 활성화
- [ ] CloudWatch Alarms 설정
- [ ] CloudWatch Logs 90일 보존

**규정 준수**:
- [ ] 개인정보 최소 수집
- [ ] 데이터 보존 기간 설정
- [ ] 데이터 삭제 API 구현
- [ ] 감사 로그 기록

**인시던트 대응**:
- [ ] 인시던트 대응 절차 문서화
- [ ] 비상 연락망 구성
- [ ] 백업 복원 테스트

---

## 추가 보안 도구 (선택 사항)

### 1. AWS Security Hub
```bash
# 통합 보안 대시보드
aws securityhub enable-security-hub --region ap-northeast-2
```
- GuardDuty, Config, IAM Access Analyzer 결과 통합
- 보안 점수 제공
- 비용: $0.0010/보안 점검/계정/리전

### 2. Amazon Macie
```bash
# S3 민감 데이터 탐지 (이메일, 신용카드 등)
aws macie2 enable-macie --region ap-northeast-2
```
- 비용: $1.25/GB (스캔)

### 3. AWS Systems Manager Session Manager
```bash
# SSH 키 없이 EC2 접속 (감사 로그 자동 기록)
aws ssm start-session --target i-XXXXXXXX
```
- 보안 강화: SSH 포트 22 완전 차단 가능

---

## 참고 자료

- [AWS Security Best Practices](https://docs.aws.amazon.com/security/)
- [AWS Well-Architected Framework - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**작성자**: Claude Code
**마지막 업데이트**: 2025-10-30
**버전**: 1.0

**⚠️ 중요**: 보안은 일회성 작업이 아닌 지속적인 프로세스입니다. 정기적으로 체크리스트를 확인하고, 새로운 위협에 대응하세요.
