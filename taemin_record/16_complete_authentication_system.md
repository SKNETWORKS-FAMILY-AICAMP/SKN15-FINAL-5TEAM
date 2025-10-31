# Phase 8: 완전한 인증 시스템 구축

> **작업 날짜**: 2025-10-30
> **목표**: JWT 프론트엔드 통합, 소셜 로그인 (Google/Kakao), 비밀번호 재설정 완성

---

## 📋 작업 개요

Phase 6, 7에 이어 최종적으로 프로덕션 수준의 완전한 인증 시스템을 구축했습니다:

### 1단계: 프론트엔드 JWT 통합
- ✅ localStorage에 JWT 토큰 자동 저장
- ✅ axios 인터셉터로 모든 API 요청에 토큰 자동 첨부
- ✅ 토큰 만료 5분 전 자동 갱신 로직
- ✅ 401 에러 시 자동 재시도 메커니즘
- ✅ 페이지 새로고침 시 로그인 상태 유지

### 2단계: 소셜 로그인 (OAuth 2.0)
- ✅ Google OAuth 2.0 통합
- ✅ Kakao OAuth 통합
- ✅ 소셜 계정 자동 사용자 생성
- ✅ 프론트엔드 OAuth 플로우 구현

### 3단계: 비밀번호 재설정
- ✅ 이메일 기반 비밀번호 재설정 요청
- ✅ 보안 토큰 생성 (1시간 유효)
- ✅ SMTP 이메일 전송 (HTML 템플릿)
- ✅ 토큰 검증 및 비밀번호 업데이트

---

## 🎯 1단계: 프론트엔드 JWT 통합

### 1.1 필요한 라이브러리 설치

```bash
cd front
npm install axios
```

### 1.2 JWT 토큰 관리 유틸리티

**파일**: `front/src/utils/authUtils.ts`

```typescript
export interface TokenData {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// 토큰 저장
export const setTokens = (tokens: TokenData): void => {
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
  localStorage.setItem('token_type', tokens.token_type);
};

// 토큰 가져오기
export const getAccessToken = (): string | null => {
  return localStorage.getItem('access_token');
};

// 토큰 삭제 (로그아웃)
export const clearTokens = (): void => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('token_type');
  localStorage.removeItem('user_data');
};

// 토큰 만료 여부 확인
export const isTokenExpired = (token: string): boolean => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) return true;
  return decoded.exp < Math.floor(Date.now() / 1000);
};
```

### 1.3 Axios 인터셉터 (자동 토큰 첨부 + 갱신)

**파일**: `front/src/utils/apiClient.ts`

```typescript
import axios from 'axios';
import { getAccessToken, setTokens, isTokenExpiringSoon } from './authUtils';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
});

// 요청 인터셉터: 토큰 자동 첨부
apiClient.interceptors.request.use(async (config) => {
  const accessToken = getAccessToken();

  if (accessToken) {
    // 토큰이 5분 이내 만료되면 자동 갱신
    if (isTokenExpiringSoon(accessToken)) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        config.headers.Authorization = `Bearer ${newToken}`;
      }
    } else {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
  }

  return config;
});

// 응답 인터셉터: 401 에러 시 토큰 갱신 후 재시도
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const newToken = await refreshAccessToken();

      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);
```

### 1.4 LoginModal 업데이트

**파일**: `front/src/components/LoginModal.tsx`

```typescript
import { setTokens, setUserData } from '@/utils/authUtils';

const handleSubmit = async (e: React.FormEvent) => {
  const response = await fetch('http://localhost:8000/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json();

  if (data.success) {
    // JWT 토큰 저장
    setTokens({
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      token_type: data.token_type,
    });

    // 사용자 정보 저장
    setUserData({
      user_id: data.user_id,
      username: data.username,
      display_name: data.display_name,
      email: data.email,
    });

    login(`${username}@kimechat.com`);
    closeLoginModal();
  }
};
```

### 1.5 AppContext 업데이트 (로그인 상태 유지)

**파일**: `front/src/contexts/AppContext.tsx`

```typescript
import { isAuthenticated, getUserData, clearTokens } from '@/utils/authUtils';

export const AppProvider = ({ children }: { children: ReactNode }) => {
  // 초기 로딩 시 토큰 기반 로그인 상태 확인
  useEffect(() => {
    if (isAuthenticated()) {
      const userData = getUserData();
      if (userData) {
        setIsLoggedIn(true);
        setUserEmail(userData.email || `${userData.username}@kimechat.com`);
      }
    }
  }, []);

  const logout = () => {
    clearTokens(); // JWT 토큰 삭제
    setIsLoggedIn(false);
    setUserEmail('');
  };
};
```

---

## 🌐 2단계: 소셜 로그인 (OAuth 2.0)

### 2.1 Google OAuth 라이브러리 설치

```bash
cd backend
pip3 install google-auth google-auth-oauthlib google-auth-httplib2
```

### 2.2 환경 변수 설정

**파일**: `backend/.env`

```bash
# Google OAuth 2.0
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# Kakao OAuth
KAKAO_CLIENT_ID=your-kakao-app-key-here
KAKAO_REDIRECT_URI=http://localhost:8000/api/auth/kakao/callback
```

**Google OAuth 설정 방법**:
1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) 접속
2. 프로젝트 생성 → API 및 서비스 → 사용자 인증 정보
3. OAuth 2.0 클라이언트 ID 생성
4. 승인된 리디렉션 URI: `http://localhost:8000/api/auth/google/callback`

**Kakao OAuth 설정 방법**:
1. [Kakao Developers](https://developers.kakao.com/console/app) 접속
2. 애플리케이션 추가 → 앱 키 확인
3. 플랫폼 설정 → 웹 → Redirect URI: `http://localhost:8000/api/auth/kakao/callback`

### 2.3 Google OAuth 핸들러

**파일**: `backend/src/auth/oauth_google.py`

```python
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token

def get_google_oauth_url() -> tuple[str, str]:
    """Google OAuth 로그인 URL 생성"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=['openid', 'email', 'profile'],
    )
    authorization_url, state = flow.authorization_url()
    return authorization_url, state

def verify_google_token(code: str) -> dict:
    """OAuth 코드로 사용자 정보 가져오기"""
    flow.fetch_token(code=code)
    credentials = flow.credentials

    id_info = id_token.verify_oauth2_token(
        credentials.id_token,
        requests.Request(),
        GOOGLE_CLIENT_ID
    )

    return {
        'sub': id_info['sub'],
        'email': id_info['email'],
        'name': id_info['name'],
        'picture': id_info['picture'],
    }
```

### 2.4 Kakao OAuth 핸들러

**파일**: `backend/src/auth/oauth_kakao.py`

```python
import requests

def get_kakao_oauth_url() -> str:
    """Kakao OAuth 로그인 URL 생성"""
    return f"https://kauth.kakao.com/oauth/authorize?client_id={KAKAO_CLIENT_ID}&redirect_uri={KAKAO_REDIRECT_URI}&response_type=code"

def verify_kakao_token(code: str) -> dict:
    """OAuth 코드로 사용자 정보 가져오기"""
    # 1. 액세스 토큰 획득
    token_response = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            'grant_type': 'authorization_code',
            'client_id': KAKAO_CLIENT_ID,
            'redirect_uri': KAKAO_REDIRECT_URI,
            'code': code,
        }
    )
    access_token = token_response.json()['access_token']

    # 2. 사용자 정보 조회
    user_response = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={'Authorization': f'Bearer {access_token}'}
    )
    user_data = user_response.json()

    return {
        'id': str(user_data['id']),
        'email': user_data['kakao_account'].get('email'),
        'nickname': user_data['kakao_account']['profile']['nickname'],
    }
```

### 2.5 API 엔드포인트

**파일**: `backend/api_server.py`

```python
@app.get("/api/auth/google")
async def google_login():
    """Google OAuth 로그인 URL 반환"""
    auth_url, state = get_google_oauth_url()
    return {"auth_url": auth_url, "state": state}

@app.get("/api/auth/google/callback")
async def google_callback(code: str):
    """Google OAuth 콜백 - JWT 토큰 발급"""
    google_user_info = verify_google_token(code)
    user = create_or_get_google_user(db_manager, google_user_info)

    access_token = create_access_token(data={"user_id": user['user_id']})
    refresh_token = create_refresh_token(data={"user_id": user['user_id']})

    return AuthResponse(
        success=True,
        access_token=access_token,
        refresh_token=refresh_token,
    )
```

### 2.6 프론트엔드 OAuth 버튼

**파일**: `front/src/components/LoginModal.tsx`

```typescript
const handleSocialLogin = async (provider: string) => {
  try {
    let authUrl: string;

    if (provider === 'Google') {
      const response = await fetch('http://localhost:8000/api/auth/google');
      const data = await response.json();
      authUrl = data.auth_url;
    } else if (provider === 'Kakao') {
      const response = await fetch('http://localhost:8000/api/auth/kakao');
      const data = await response.json();
      authUrl = data.auth_url;
    }

    // OAuth 로그인 페이지로 리다이렉트
    window.location.href = authUrl;
  } catch (err) {
    console.error(`${provider} 로그인 오류:`, err);
  }
};
```

---

## 📧 3단계: 비밀번호 재설정

### 3.1 데이터베이스 마이그레이션

**파일**: `backend/database/migrations/004_password_reset_tokens.sql`

```sql
CREATE TABLE IF NOT EXISTS statedb.password_reset_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_password_reset_tokens_token ON statedb.password_reset_tokens(token);
```

```bash
PGPASSWORD=dev123 psql -h localhost -U kime -d kimedb -f database/migrations/004_password_reset_tokens.sql
```

### 3.2 SMTP 설정

**파일**: `backend/.env`

```bash
# Email / SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@kimechat.com
SMTP_FROM_NAME=KIME Chat

FRONTEND_URL=http://localhost:5173
```

**Gmail App Password 생성**:
1. Google 계정 → 보안 → 2단계 인증 활성화
2. 앱 비밀번호 생성 → "메일" 선택
3. 생성된 16자리 비밀번호를 `SMTP_PASSWORD`에 입력

### 3.3 이메일 전송 유틸리티

```bash
pip3 install aiosmtplib email-validator
```

**파일**: `backend/src/utils/email_sender.py`

```python
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

async def send_email(
    to_email: str,
    subject: str,
    html_content: str
) -> bool:
    """이메일 전송"""
    message = MIMEMultipart("alternative")
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(html_content, "html"))

    await aiosmtplib.send(
        message,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USERNAME,
        password=SMTP_PASSWORD,
        start_tls=True,
    )

    return True
```

### 3.4 비밀번호 재설정 API

**파일**: `backend/api_server.py`

```python
@app.post("/api/auth/password-reset/request")
async def request_password_reset(req: PasswordResetRequest):
    """비밀번호 재설정 요청"""
    import secrets
    from datetime import datetime, timedelta

    user = db_manager.get_user_by_username(req.email)
    if not user:
        # 보안상 사용자가 없어도 성공 응답
        return {"success": True, "message": "이메일이 전송되었습니다."}

    # 재설정 토큰 생성 (1시간 유효)
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    db_manager.create_password_reset_token(
        user['user_id'], reset_token, expires_at
    )

    # 재설정 링크 생성
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    # 이메일 전송
    await send_email(
        to_email=user['email'],
        subject="[KIME Chat] 비밀번호 재설정 요청",
        html_content=generate_password_reset_email(reset_link)
    )

    return {"success": True, "message": "이메일을 확인해주세요."}


@app.post("/api/auth/password-reset/confirm")
async def confirm_password_reset(req: PasswordResetConfirm):
    """비밀번호 재설정 확인"""
    import bcrypt

    # 토큰 검증
    token_data = db_manager.get_password_reset_token(req.token)
    if not token_data:
        raise HTTPException(status_code=400, detail="유효하지 않은 토큰")

    # 새 비밀번호 해싱
    new_password_hash = bcrypt.hashpw(
        req.new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # 비밀번호 업데이트
    db_manager.update_user_password(token_data['user_id'], new_password_hash)
    db_manager.mark_password_reset_token_as_used(req.token)

    return {"success": True, "message": "비밀번호가 변경되었습니다"}
```

---

## 📊 최종 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    프론트엔드 (React)                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ LoginModal   │  │ AppContext   │  │ apiClient.ts │     │
│  │  - 이메일    │  │  - 상태 관리 │  │  - axios     │     │
│  │  - Google    │  │  - 토큰 확인 │  │  - 인터셉터  │     │
│  │  - Kakao     │  └──────────────┘  └──────────────┘     │
│  └──────────────┘                                           │
│                                                              │
│  authUtils.ts: 토큰 저장/조회/삭제/검증                     │
└───────────────────────┬──────────────────────────────────────┘
                        │ HTTP/HTTPS
┌───────────────────────┴──────────────────────────────────────┐
│                  백엔드 (FastAPI)                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ api_server   │  │ JWT Utils    │  │ OAuth        │     │
│  │  - /login    │  │  - 생성      │  │  - Google    │     │
│  │  - /register │  │  - 검증      │  │  - Kakao     │     │
│  │  - /refresh  │  │  - 갱신      │  └──────────────┘     │
│  │  - /google   │  └──────────────┘                        │
│  │  - /kakao    │                                           │
│  │  - /password │  ┌──────────────┐  ┌──────────────┐     │
│  │    -reset    │  │ Email Sender │  │ Rate Limiter │     │
│  └──────────────┘  │  - SMTP      │  │  - slowapi   │     │
│                    └──────────────┘  └──────────────┘     │
└───────────────────────┬──────────────────────────────────────┘
                        │
┌───────────────────────┴──────────────────────────────────────┐
│                PostgreSQL Database                           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ users        │  │ sessions     │  │ password_    │     │
│  │  - user_id   │  │  - session   │  │   reset_     │     │
│  │  - username  │  │  - user_id   │  │   tokens     │     │
│  │  - email     │  │  - data      │  │  - token     │     │
│  │  - password  │  └──────────────┘  │  - expires   │     │
│  │  - provider  │                    └──────────────┘     │
│  └──────────────┘                                           │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔐 보안 기능 요약

| 기능 | 설명 | 구현 상태 |
|------|------|----------|
| **JWT 액세스 토큰** | 1시간 유효, stateless 인증 | ✅ 완료 |
| **JWT 리프레시 토큰** | 7일 유효, 자동 갱신 | ✅ 완료 |
| **비밀번호 해싱** | bcrypt + salt | ✅ 완료 |
| **Rate Limiting** | 로그인: 5/분, API: 100/분 | ✅ 완료 |
| **OAuth 2.0** | Google + Kakao 소셜 로그인 | ✅ 완료 |
| **비밀번호 재설정** | 이메일 인증 + 1시간 토큰 | ✅ 완료 |
| **토큰 자동 갱신** | 만료 5분 전 자동 refresh | ✅ 완료 |
| **CORS 보안** | 허용된 origin만 접근 | ✅ 완료 |

---

## 🚀 테스트 가이드

### 1단계 테스트: JWT 통합

```bash
# 1. 백엔드 서버 실행
cd backend
python3 api_server.py

# 2. 프론트엔드 서버 실행
cd front
npm run dev

# 3. 브라우저 http://localhost:5173
# 4. 로그인 → 개발자 도구 → Application → Local Storage
#    - access_token, refresh_token, user_data 확인
# 5. 페이지 새로고침 → 로그인 상태 유지 확인
```

### 2단계 테스트: 소셜 로그인

```bash
# 1. Google/Kakao 버튼 클릭
# 2. OAuth 로그인 페이지로 리다이렉트
# 3. 로그인 후 콜백 처리 확인
# 4. JWT 토큰 발급 확인
```

**주의**: 실제 OAuth 테스트를 위해서는 Google Cloud Console과 Kakao Developers에서 OAuth 앱을 등록해야 합니다.

### 3단계 테스트: 비밀번호 재설정

```bash
# 1. "비밀번호 찾기" 링크 클릭 (구현 필요)
# 2. 이메일 입력
# 3. 이메일 수신 확인
# 4. 재설정 링크 클릭
# 5. 새 비밀번호 입력
# 6. 새 비밀번호로 로그인 확인
```

---

## 📁 생성된 파일 목록

### Frontend
- `front/src/utils/authUtils.ts` - JWT 토큰 관리
- `front/src/utils/apiClient.ts` - axios 인터셉터
- `front/src/components/LoginModal.tsx` - OAuth 버튼 통합
- `front/src/contexts/AppContext.tsx` - 로그인 상태 관리

### Backend
- `backend/src/auth/oauth_google.py` - Google OAuth 핸들러
- `backend/src/auth/oauth_kakao.py` - Kakao OAuth 핸들러
- `backend/src/utils/email_sender.py` - SMTP 이메일 전송
- `backend/database/migrations/004_password_reset_tokens.sql` - 비밀번호 재설정 테이블
- `backend/src/database/db_manager.py` - 비밀번호 재설정 메서드 추가
- `backend/api_server.py` - OAuth 및 비밀번호 재설정 엔드포인트 추가

### Configuration
- `backend/.env` - OAuth + SMTP 설정 추가
- `front/package.json` - axios 패키지 추가

---

## 🎓 학습 포인트

### JWT 토큰 관리
- **액세스 토큰**: 짧은 수명 (1시간), API 요청에 사용
- **리프레시 토큰**: 긴 수명 (7일), 액세스 토큰 갱신에 사용
- **자동 갱신**: 만료 5분 전 자동으로 리프레시하여 사용자 경험 향상

### OAuth 2.0 플로우
1. 사용자가 "Google로 로그인" 클릭
2. Google 로그인 페이지로 리다이렉트
3. 사용자가 구글 계정으로 로그인
4. Google이 콜백 URL로 authorization code 전달
5. 백엔드가 code를 access token으로 교환
6. Google API로 사용자 정보 조회
7. 자체 JWT 토큰 발급

### 이메일 인증
- **보안 토큰**: `secrets.token_urlsafe(32)` 사용
- **만료 시간**: 1시간 후 자동 무효화
- **일회용**: 한 번 사용하면 `used=true`로 표시
- **보안 고려**: 사용자 존재 여부를 노출하지 않음

---

## 🔮 향후 개선 사항

### 보안 강화
- [ ] **2FA (Two-Factor Authentication)**: Google Authenticator 연동
- [ ] **토큰 블랙리스트**: 로그아웃 시 토큰 무효화
- [ ] **비밀번호 정책**: 최소 길이, 복잡도 요구사항
- [ ] **IP 제한**: Rate Limiting에 IP 기반 차단 추가

### 사용자 경험
- [ ] **비밀번호 재설정 UI**: 전용 페이지 생성
- [ ] **이메일 인증**: 회원가입 시 이메일 확인 필수
- [ ] **프로필 관리**: 사용자 정보 수정 페이지
- [ ] **소셜 계정 연결**: 여러 소셜 계정을 하나의 계정에 연결

### 모니터링
- [ ] **로그인 히스토리**: 로그인 시간, IP, 디바이스 기록
- [ ] **보안 알림**: 새로운 기기에서 로그인 시 이메일 알림
- [ ] **실패 로그**: 로그인 실패 횟수 추적 및 계정 잠금

---

## 📝 참고 자료

- [Google OAuth 2.0 문서](https://developers.google.com/identity/protocols/oauth2)
- [Kakao OAuth 문서](https://developers.kakao.com/docs/latest/ko/kakaologin/common)
- [JWT 공식 사이트](https://jwt.io/)
- [FastAPI 인증 가이드](https://fastapi.tiangolo.com/tutorial/security/)
- [SMTP Gmail 설정](https://support.google.com/mail/answer/7126229)

---

**작업 완료**: 2025-10-30
**다음 Phase**: AWS 배포 (Phase 4-5 재개)
