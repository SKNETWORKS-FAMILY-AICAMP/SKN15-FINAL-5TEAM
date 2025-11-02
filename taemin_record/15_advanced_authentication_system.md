# Phase 7: 고급 인증 시스템 구현 (JWT + Rate Limiting)

> **작업 날짜**: 2025-10-30
> **목표**: JWT 토큰 기반 인증 시스템 및 Rate Limiting 구현

---

## 📋 작업 개요

Phase 6에서 구현한 기본 로그인/회원가입 기능을 확장하여, 프로덕션 수준의 인증 시스템을 구축했습니다:
- JWT 토큰 기반 stateless 인증
- 액세스 토큰 + 리프레시 토큰
- Rate Limiting으로 brute-force 공격 방어
- 보호된 API 라우트

---

## 🎯 주요 작업 내용

### 1. JWT (JSON Web Tokens) 인증 시스템

#### 1.1 JWT 라이브러리 설치

```bash
pip3 install PyJWT 'python-jose[cryptography]' python-multipart
```

#### 1.2 JWT 유틸리티 함수 구현

**파일**: `backend/src/auth/jwt_utils.py`

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1시간
REFRESH_TOKEN_EXPIRE_DAYS = 7      # 7일
```

**핵심 함수**:

1. **액세스 토큰 생성**:
```python
def create_access_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

2. **리프레시 토큰 생성**:
```python
def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

3. **토큰 검증**:
```python
def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    # 토큰 타입 확인
    if payload.get("type") != token_type:
        raise HTTPException(status_code=401)

    return payload
```

4. **현재 사용자 추출**:
```python
def get_current_user(token: str) -> Dict[str, Any]:
    payload = verify_token(token, token_type="access")
    return {
        "user_id": payload.get("user_id"),
        "username": payload.get("username"),
        "display_name": payload.get("display_name")
    }
```

#### 1.3 인증 Dependency 구현

**파일**: `backend/src/auth/dependencies.py`

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    보호된 라우트에 사용되는 의존성

    Usage:
        @app.get("/protected")
        async def protected_route(user: Dict = Depends(require_auth)):
            return {"user": user}
    """
    token = credentials.credentials
    return get_current_user(token)
```

---

### 2. API 엔드포인트 업데이트

#### 2.1 로그인 API (JWT 토큰 발급)

**엔드포인트**: `POST /api/auth/login`

**요청**:
```json
{
  "username": "tanjiro",
  "password": "123"
}
```

**응답** (새로운 필드 추가):
```json
{
  "success": true,
  "message": "로그인 성공",
  "user_id": "126a8027-3c2f-4ddf-9b6e-7ec97c1684f1",
  "username": "tanjiro",
  "display_name": "탄지로",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 2.2 회원가입 API (JWT 토큰 자동 발급)

**엔드포인트**: `POST /api/auth/register`

회원가입 성공 시에도 동일하게 JWT 토큰을 자동으로 발급하여 별도의 로그인 없이 바로 사용할 수 있습니다.

#### 2.3 토큰 갱신 API

**엔드포인트**: `POST /api/auth/refresh`

**요청**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**응답**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**구현**:
```python
@app.post("/api/auth/refresh", response_model=TokenRefreshResponse)
async def refresh_token(request: TokenRefreshRequest):
    from src.auth.jwt_utils import refresh_access_token

    try:
        new_access_token = refresh_access_token(request.refresh_token)
        return TokenRefreshResponse(access_token=new_access_token)
    except HTTPException as e:
        raise e
```

#### 2.4 보호된 라우트 예제

**엔드포인트**: `GET /api/auth/me`

**요청 헤더**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**응답**:
```json
{
  "user_id": "126a8027-3c2f-4ddf-9b6e-7ec97c1684f1",
  "username": "tanjiro",
  "display_name": "탄지로"
}
```

**구현**:
```python
@app.get("/api/auth/me")
async def get_me(user: Dict = Depends(require_auth)):
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user.get("display_name")
    }
```

---

### 3. Rate Limiting 구현

#### 3.1 slowapi 라이브러리 설치

```bash
pip3 install slowapi
```

#### 3.2 Rate Limiter 설정

**파일**: `backend/src/middleware/rate_limiter.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Rate Limiter 인스턴스 생성 (IP 주소 기반)
limiter = Limiter(key_func=get_remote_address)

# Rate Limit 설정
DEFAULT_RATE_LIMIT = "100/minute"  # 일반 API: 분당 100회
AUTH_RATE_LIMIT = "5/minute"        # 로그인/회원가입: 분당 5회


def setup_rate_limiting(app):
    """FastAPI 앱에 Rate Limiting 설정"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return app
```

#### 3.3 API 엔드포인트에 Rate Limiting 적용

**로그인 API**:
```python
@app.post("/api/auth/login")
@limiter.limit(AUTH_RATE_LIMIT)  # 분당 5회 제한
async def login(req: LoginRequest, request: Request):
    # ...
```

**회원가입 API**:
```python
@app.post("/api/auth/register")
@limiter.limit(AUTH_RATE_LIMIT)  # 분당 5회 제한
async def register(req: RegisterRequest, request: Request):
    # ...
```

**Rate Limit 초과 시 응답**:
```json
{
  "error": "Rate limit exceeded: 5 per 1 minute"
}
```

HTTP 상태 코드: `429 Too Many Requests`

---

## 🔒 보안 강화 사항

### 1. JWT 토큰 보안

- **Secret Key**: 환경변수로 관리, 충분히 길고 복잡한 키 사용
- **토큰 타입 구분**: 액세스 토큰과 리프레시 토큰을 명확히 구분
- **만료 시간 설정**:
  - 액세스 토큰: 60분 (짧은 수명)
  - 리프레시 토큰: 7일 (긴 수명)
- **토큰 검증**: 만료 시간, 타입, 서명을 모두 검증

### 2. Rate Limiting 보안

- **Brute-force 공격 방지**: 로그인 시도를 분당 5회로 제한
- **DDoS 완화**: 일반 API도 분당 100회로 제한
- **IP 기반 제한**: 각 IP 주소별로 독립적인 제한 적용

### 3. HTTPS 준비

프로덕션 환경에서는 반드시 HTTPS를 사용해야 합니다:
- JWT 토큰이 HTTP 헤더로 전송되므로 암호화 필수
- 환경변수 `JWT_SECRET_KEY`를 안전하게 관리

---

## 📊 JWT 토큰 구조

### 액세스 토큰 페이로드

```json
{
  "user_id": "126a8027-3c2f-4ddf-9b6e-7ec97c1684f1",
  "username": "tanjiro",
  "display_name": "탄지로",
  "exp": 1761829287,
  "iat": 1761825687,
  "type": "access"
}
```

### 리프레시 토큰 페이로드

```json
{
  "user_id": "126a8027-3c2f-4ddf-9b6e-7ec97c1684f1",
  "exp": 1762430487,
  "iat": 1761825687,
  "type": "refresh"
}
```

**주요 필드**:
- `exp`: 만료 시간 (Unix timestamp)
- `iat`: 발급 시간 (Unix timestamp)
- `type`: 토큰 타입 (access/refresh)

---

## 🧪 테스트 시나리오

### 1. 로그인 및 JWT 토큰 발급

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tanjiro",
    "password": "123"
  }'
```

**결과**: ✅ 액세스 토큰 + 리프레시 토큰 반환

### 2. 보호된 라우트 접근

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**결과**: ✅ 사용자 정보 반환

### 3. 잘못된 토큰으로 접근

```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer invalid_token"
```

**결과**: ❌ 401 Unauthorized

### 4. 토큰 갱신

```bash
REFRESH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}"
```

**결과**: ✅ 새로운 액세스 토큰 반환

### 5. Rate Limiting 테스트

```bash
# 6번 연속 로그인 시도
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}'
  sleep 0.1
done
```

**예상 결과**:
- 1-5번 시도: ✅ 정상 응답 (실패하지만 Rate Limit은 통과)
- 6번째 시도: ❌ 429 Too Many Requests

---

## 🔧 환경 변수 설정

**`.env` 파일**:
```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production-please
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

**주의사항**:
- 프로덕션 환경에서는 `JWT_SECRET_KEY`를 반드시 변경
- 최소 32자 이상의 랜덤 문자열 사용 권장
- `.env` 파일을 `.gitignore`에 추가하여 Git에 커밋하지 않기

---

## 📁 생성된 파일 구조

```
backend/
├── src/
│   ├── auth/                      # 인증 모듈 (신규)
│   │   ├── __init__.py
│   │   ├── jwt_utils.py          # JWT 토큰 생성/검증
│   │   └── dependencies.py        # FastAPI 의존성
│   │
│   ├── middleware/                # 미들웨어 (신규)
│   │   ├── __init__.py
│   │   └── rate_limiter.py       # Rate Limiting
│   │
│   └── database/
│       └── ...
│
├── api_server.py                  # 업데이트됨
└── .env                           # JWT 설정 추가
```

---

## 🚀 프론트엔드 통합 가이드

### 1. 로그인 후 토큰 저장

```typescript
// 로그인 API 호출
const response = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});

const data = await response.json();

if (data.success) {
  // 토큰을 로컬 스토리지에 저장
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  localStorage.setItem('user', JSON.stringify({
    user_id: data.user_id,
    username: data.username,
    display_name: data.display_name
  }));
}
```

### 2. 보호된 API 호출 시 토큰 포함

```typescript
const token = localStorage.getItem('access_token');

const response = await fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({ /* ... */ })
});
```

### 3. 토큰 만료 시 자동 갱신

```typescript
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');

  const response = await fetch('http://localhost:8000/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);

  return data.access_token;
}

// Axios 인터셉터 예제
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response.status === 401) {
      const newToken = await refreshAccessToken();
      error.config.headers['Authorization'] = `Bearer ${newToken}`;
      return axios.request(error.config);
    }
    return Promise.reject(error);
  }
);
```

---

## 💡 향후 개선 사항

### 1. Token Blacklist (토큰 무효화)

로그아웃 시 토큰을 블랙리스트에 추가:

```python
# Redis를 사용한 블랙리스트
def blacklist_token(token: str):
    redis_client.setex(
        f"blacklist:{token}",
        ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "1"
    )

def is_token_blacklisted(token: str) -> bool:
    return redis_client.exists(f"blacklist:{token}")
```

### 2. 비밀번호 재설정

이메일 인증을 통한 비밀번호 재설정 기능:
- 재설정 토큰 생성 (1회용, 15분 유효)
- SMTP를 통한 이메일 전송
- 토큰 검증 후 비밀번호 변경

### 3. 소셜 로그인 (OAuth 2.0)

Google, Kakao 로그인 연동:
- OAuth 2.0 플로우 구현
- 소셜 계정과 로컬 계정 연결
- `provider` 필드 활용

### 4. 2FA (Two-Factor Authentication)

추가 보안 계층:
- TOTP (Time-based One-Time Password)
- SMS 인증
- 이메일 인증 코드

### 5. Redis 기반 Rate Limiting

현재는 메모리 기반이지만, Redis를 사용하면:
- 멀티 서버 환경에서도 작동
- 더 정확한 카운팅
- 영구 스토리지

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"  # Redis 사용
)
```

---

## 📚 참고 자료

- **JWT 공식 문서**: https://jwt.io/
- **python-jose**: https://python-jose.readthedocs.io/
- **slowapi**: https://github.com/laurentS/slowapi
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
- **OAuth 2.0**: https://oauth.net/2/

---

## 📌 체크리스트

### 완료된 작업
- [x] JWT 토큰 생성/검증 유틸리티 함수 구현
- [x] 액세스 토큰 + 리프레시 토큰 분리
- [x] 로그인 API에서 JWT 토큰 발급
- [x] 회원가입 API에서 JWT 토큰 자동 발급
- [x] 토큰 갱신 API 구현
- [x] 보호된 라우트 예제 (`/api/auth/me`)
- [x] FastAPI Dependency를 사용한 인증 미들웨어
- [x] Rate Limiting 구현 (slowapi)
- [x] 로그인/회원가입에 Rate Limiting 적용
- [x] 환경변수 설정 (JWT_SECRET_KEY 등)

### 향후 작업 (선택사항)
- [ ] Redis 기반 Token Blacklist
- [ ] 비밀번호 재설정 (이메일 인증)
- [ ] Google OAuth 2.0 연동
- [ ] Kakao 로그인 연동
- [ ] 2FA (Two-Factor Authentication)
- [ ] Redis 기반 Rate Limiting

---

## 🎓 배운 점

1. **JWT의 Stateless 특성**: 서버가 세션을 저장하지 않아도 인증 가능
2. **액세스/리프레시 토큰 분리의 중요성**: 보안과 사용자 경험의 균형
3. **Rate Limiting의 필요성**: Brute-force 공격 방어의 첫 번째 방어선
4. **FastAPI Dependency 시스템**: 코드 재사용성과 가독성 향상
5. **환경변수 관리**: 민감한 정보를 코드와 분리하는 베스트 프랙티스

---

**다음 단계**: 프론트엔드에서 JWT 토큰을 사용하도록 LoginModal 업데이트
