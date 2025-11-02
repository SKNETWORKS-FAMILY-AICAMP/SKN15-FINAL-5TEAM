# 환경 변수 관리 가이드

## 📋 목차
1. [환경 변수란?](#환경 변수란)
2. [프론트엔드 환경 변수](#프론트엔드-환경-변수)
3. [백엔드 환경 변수](#백엔드-환경-변수)
4. [환경별 전환](#환경별-전환)
5. [보안 주의사항](#보안-주의사항)

---

## 환경 변수란?

### 정의
실행 환경에 따라 다른 값을 사용할 수 있게 하는 변수

### 필요한 이유
```typescript
// ❌ 나쁜 예: 하드코딩
const API_URL = "http://localhost:8000";  // 프로덕션에서 작동 안 함!

// ✅ 좋은 예: 환경 변수 사용
const API_URL = import.meta.env.VITE_API_URL;
// 개발: http://localhost:8000
// 프로덕션: http://kime-alb-xxxxx.elb.amazonaws.com
```

### 장점
1. **환경 분리**: 개발/프로덕션 설정 독립적 관리
2. **보안**: 민감한 정보 코드에서 분리
3. **유연성**: 재빌드 없이 설정 변경 가능
4. **협업**: 각자 로컬 설정 사용

---

## 프론트엔드 환경 변수

### 파일 구조
```
front/
├── .env                    # 로컬 개발 (gitignore)
├── .env.production         # AWS 프로덕션 (gitignore)
├── .env.example            # 예제 (git 커밋)
└── src/
    └── vite-env.d.ts       # TypeScript 타입 정의
```

### .env (로컬 개발)
```bash
# API 엔드포인트
VITE_API_URL=http://localhost:8000

# CDN URL (로컬 이미지)
VITE_CDN_URL=/images

# 환경 구분
VITE_ENVIRONMENT=development
```

### .env.production (AWS 프로덕션)
```bash
# API 엔드포인트 (ALB)
VITE_API_URL=http://kime-alb-xxxxx.ap-northeast-2.elb.amazonaws.com

# CDN URL (CloudFront)
VITE_CDN_URL=https://d1a2b3c4d5e6f7.cloudfront.net

# 환경 구분
VITE_ENVIRONMENT=production
```

### .env.example (공개 가능)
```bash
# API 엔드포인트
VITE_API_URL=http://localhost:8000

# CDN URL
VITE_CDN_URL=/images

# 환경 구분
VITE_ENVIRONMENT=development
```

### 사용 방법

#### 1. TypeScript 타입 정의
`front/src/vite-env.d.ts`:
```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_CDN_URL: string
  readonly VITE_ENVIRONMENT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

#### 2. 코드에서 사용
```typescript
// 환경 변수 읽기
const API_URL = import.meta.env.VITE_API_URL;
const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';  // 기본값 제공

// API 호출
async function fetchData() {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

// 이미지 경로
const imagePath = `${CDN_URL}/프로필_탄지로.png`;
```

### Vite 환경 변수 규칙

| 규칙 | 설명 | 예시 |
|------|------|------|
| `VITE_` 접두사 필수 | 클라이언트 노출 | `VITE_API_URL` ✅ |
| 접두사 없으면 노출 안 됨 | 서버 전용 | `API_KEY` ❌ |
| 빌드 타임 주입 | 코드에 하드코딩됨 | - |
| 런타임 변경 불가 | 재빌드 필요 | - |

⚠️ **주의:** API Key 같은 민감한 정보는 환경 변수에 두지 말고, 백엔드에서 관리!

---

## 백엔드 환경 변수

### 파일 구조
```
backend/
├── .env.local              # 로컬 개발 (gitignore)
├── .env.production         # AWS 프로덕션 (gitignore)
└── .env.example            # 예제 (git 커밋)
```

### .env.local (로컬 개발)
```bash
# PostgreSQL (Docker)
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=dev123

# Redis (Docker)
REDIS_HOST=localhost
REDIS_PORT=6379
SESSION_TTL=3600

# OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 환경
ENVIRONMENT=development
```

### .env.production (AWS 프로덕션)
```bash
# PostgreSQL (RDS)
DB_HOST=kime-db.xxxxx.ap-northeast-2.rds.amazonaws.com
DB_PORT=5432
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=[보안된 패스워드]

# Redis (ElastiCache)
REDIS_HOST=kime-redis.xxxxx.cache.amazonaws.com
REDIS_PORT=6379
SESSION_TTL=3600

# OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 환경
ENVIRONMENT=production
```

### 사용 방법

#### 1. python-dotenv 설치
```bash
pip install python-dotenv
```

#### 2. 코드에서 로드
```python
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv('.env.local')  # 로컬 개발
# 또는
load_dotenv('.env.production')  # 프로덕션

# 환경 변수 읽기
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 사용
db_config = {
    "host": DB_HOST,
    "port": DB_PORT,
    "database": os.getenv('DB_NAME'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD')
}
```

---

## 환경별 전환

### 로컬 개발 → AWS 프로덕션

#### 프론트엔드
```bash
# 로컬 개발
npm run dev  # .env 사용

# 프로덕션 빌드
npm run build  # .env.production 사용
```

#### 백엔드
```python
# api_server.py
import os

# 환경 자동 감지
ENV = os.getenv('ENVIRONMENT', 'development')

if ENV == 'production':
    load_dotenv('.env.production')
else:
    load_dotenv('.env.local')
```

### 환경 확인 방법

#### 프론트엔드
```typescript
console.log('Environment:', import.meta.env.VITE_ENVIRONMENT);
console.log('API URL:', import.meta.env.VITE_API_URL);
console.log('CDN URL:', import.meta.env.VITE_CDN_URL);
```

#### 백엔드
```python
print(f"Environment: {os.getenv('ENVIRONMENT')}")
print(f"DB Host: {os.getenv('DB_HOST')}")
print(f"Redis Host: {os.getenv('REDIS_HOST')}")
```

---

## 보안 주의사항

### ✅ 안전한 사용

```bash
# .gitignore에 추가 (필수!)
.env
.env.local
.env.production
```

```bash
# Git에 커밋하기 전 확인
git status
# .env 파일이 목록에 없는지 확인!
```

### ❌ 절대 하지 말 것

1. **환경 변수 파일 커밋 금지**
   - `.env`, `.env.production` → Git에 추가하지 마세요!

2. **API Key를 프론트엔드에 노출 금지**
   ```typescript
   // ❌ 절대 하지 마세요!
   const OPENAI_API_KEY = import.meta.env.VITE_OPENAI_API_KEY;
   // 클라이언트 코드에 그대로 노출됩니다!
   ```

3. **민감한 정보는 백엔드에서만**
   - API Key, DB 패스워드 → 백엔드 환경 변수
   - API URL, CDN URL → 프론트엔드 환경 변수 OK

### 🔒 민감한 정보 관리

#### AWS Secrets Manager (추천)
```python
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='ap-northeast-2')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise e

# 사용
OPENAI_API_KEY = get_secret('kime/openai-api-key')
```

---

## 체크리스트

### 로컬 개발 시작 전
- [ ] `front/.env` 파일 생성
- [ ] `backend/.env.local` 파일 생성
- [ ] `.gitignore`에 환경 변수 파일 추가 확인
- [ ] `front/src/vite-env.d.ts` 타입 정의 확인

### AWS 배포 전
- [ ] `front/.env.production` 파일 생성
- [ ] ALB URL, CloudFront URL 정확히 입력
- [ ] `backend/.env.production` 파일 생성
- [ ] RDS, ElastiCache 엔드포인트 정확히 입력
- [ ] 민감한 정보 커밋 안 했는지 확인
- [ ] 프로덕션 빌드 테스트

---

## 관련 문서
- [02_image_cdn_migration.md](02_image_cdn_migration.md) - CDN URL 설정
- [03_aws_deployment_guide.md](03_aws_deployment_guide.md) - AWS 엔드포인트 확인
- [05_troubleshooting.md](05_troubleshooting.md) - 환경 변수 에러 해결

---
작성일: 2025-10-30
