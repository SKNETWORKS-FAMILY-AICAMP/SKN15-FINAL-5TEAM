# 21. 로그인 필수 채팅 시스템 구현

**작성일**: 2025-11-02
**목표**: 로그인한 사용자만 채팅할 수 있도록 인증 시스템 구현
**결과**: 백엔드 인증 필수 처리 완료, 프론트엔드 구현 가이드 제공

---

## 🔐 구현 목표

### Before (구현 전)
```
- 익명 사용자도 채팅 가능
- optional_auth로 선택적 인증
- user_id 없이도 대화 진행
```

### After (구현 후)
```
✅ 로그인한 사용자만 채팅 가능
✅ require_auth로 필수 인증
✅ JWT 토큰 없으면 401 에러 반환
✅ user_id 기반으로 대화 관리
```

---

## 📋 백엔드 구현 (✅ 완료)

### 1. API 엔드포인트 인증 필수화

**파일**: `backend/api_server.py`

**변경 사항**:
```python
# Before
@app.post("/api/chat")
async def chat(
    request: Request,
    current_user: Optional[Dict] = Depends(optional_auth)  # 선택적 인증
):

# After
@app.post("/api/chat")
async def chat(
    request: Request,
    current_user: Dict = Depends(require_auth)  # 🔐 필수 인증!
):
    """
    메인 채팅 엔드포인트 (🔐 로그인 필수)

    Raises:
        HTTPException 401: 인증되지 않은 사용자
    """
```

### 2. 익명 사용자 처리 로직 제거

**변경 사항**:
```python
# Before
user_id = current_user.get('user_id') if current_user else None
if current_user:
    print(f"인증된 사용자: {user_id}")
else:
    print(f"익명 사용자: {user_name}")

# After
user_id = current_user.get('user_id')  # 필수
username = current_user.get('username', 'Unknown')
print(f"🔐 Authenticated user: {username} (ID: {user_id})")
```

### 3. 인증 의존성 모듈 (이미 구현됨)

**파일**: `backend/src/auth/dependencies.py`

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    인증 필수 의존성

    JWT 토큰을 검증하고 현재 사용자 정보를 반환합니다.

    Returns:
        현재 사용자 정보 딕셔너리
        {
            "user_id": 1,
            "username": "user@example.com",
            "email": "user@example.com"
        }

    Raises:
        HTTPException 401: 토큰이 유효하지 않은 경우
    """
    token = credentials.credentials
    user = get_current_user(token)  # JWT 검증
    return user
```

---

## 🎨 프론트엔드 구현 가이드

### 📁 파일 구조

```
front/
├── src/
│   ├── components/
│   │   ├── LoginModal.tsx          # ✅ 이미 있음
│   │   └── Chat.tsx                # 수정 필요
│   ├── contexts/
│   │   └── AppContext.tsx          # 수정 필요
│   ├── utils/
│   │   ├── apiClient.ts            # ✅ 이미 있음
│   │   └── authUtils.ts            # ✅ 이미 있음
│   └── App.tsx                     # 수정 필요
```

---

### 1. API 클라이언트 수정 (JWT 토큰 포함)

**파일**: `front/src/utils/apiClient.ts`

```typescript
// 이미 구현되어 있지만 확인 필요
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: JWT 토큰 자동 추가
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: 401 에러 처리
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 로그인 필요 알림
      localStorage.removeItem('accessToken');
      localStorage.removeItem('user');
      window.location.href = '/'; // 로그인 페이지로 리다이렉트
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

---

### 2. AppContext 수정 (인증 상태 관리)

**파일**: `front/src/contexts/AppContext.tsx`

```typescript
import React, { createContext, useState, useEffect } from 'react';

interface User {
  user_id: number;
  username: string;
  email: string;
}

interface AppContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  isAuthenticated: boolean;
  logout: () => void;
}

export const AppContext = createContext<AppContextType>({
  user: null,
  setUser: () => {},
  isAuthenticated: false,
  logout: () => {},
});

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  // 컴포넌트 마운트 시 localStorage에서 사용자 정보 복원
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const storedToken = localStorage.getItem('accessToken');

    if (storedUser && storedToken) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        console.error('Failed to parse user data:', e);
        logout();
      }
    }
  }, []);

  const logout = () => {
    setUser(null);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('user');
  };

  return (
    <AppContext.Provider
      value={{
        user,
        setUser,
        isAuthenticated: !!user,
        logout,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};
```

---

### 3. 채팅창 진입 시 인증 체크

**파일**: `front/src/App.tsx` 또는 `front/src/components/Chat.tsx`

```typescript
import React, { useContext, useEffect, useState } from 'react';
import { AppContext } from '../contexts/AppContext';
import LoginModal from './LoginModal';

const Chat: React.FC = () => {
  const { user, isAuthenticated } = useContext(AppContext);
  const [showLoginModal, setShowLoginModal] = useState(false);

  // 인증 체크: 로그인하지 않았으면 로그인 모달 표시
  useEffect(() => {
    if (!isAuthenticated) {
      setShowLoginModal(true);
    }
  }, [isAuthenticated]);

  // 로그인하지 않았으면 채팅창 표시 안 함
  if (!isAuthenticated) {
    return (
      <>
        <div className="chat-locked">
          <h2>🔐 로그인이 필요합니다</h2>
          <p>채팅을 시작하려면 로그인해주세요.</p>
          <button onClick={() => setShowLoginModal(true)}>
            로그인하기
          </button>
        </div>

        {showLoginModal && (
          <LoginModal
            onClose={() => setShowLoginModal(false)}
            onLoginSuccess={() => {
              setShowLoginModal(false);
              // 로그인 성공 후 채팅창 표시
            }}
          />
        )}
      </>
    );
  }

  // 로그인한 사용자만 채팅창 표시
  return (
    <div className="chat-container">
      <h1>Welcome, {user?.username}!</h1>
      {/* 채팅 컴포넌트 */}
    </div>
  );
};

export default Chat;
```

---

### 4. 채팅 API 호출 (JWT 포함)

**파일**: `front/src/components/Chat.tsx` (sendMessage 함수)

```typescript
import apiClient from '../utils/apiClient';

const sendMessage = async (userInput: string) => {
  try {
    // apiClient가 자동으로 JWT 토큰을 헤더에 추가함
    const response = await apiClient.post('/api/chat', {
      session_id: sessionId,
      user_input: userInput,
      scenario_id: 'cutscene5_llm_driven',
      user_name: user?.username || '여행자',
    });

    // 응답 처리
    setMessages([...messages, {
      role: 'assistant',
      content: response.data.dialogues,
    }]);

  } catch (error) {
    if (error.response?.status === 401) {
      // 인증 에러: 로그인 모달 표시
      alert('로그인이 만료되었습니다. 다시 로그인해주세요.');
      logout();
    } else {
      console.error('Chat error:', error);
      alert('채팅 중 오류가 발생했습니다.');
    }
  }
};
```

---

### 5. LoginModal 통합

**파일**: `front/src/components/LoginModal.tsx`

로그인 성공 시 JWT 토큰과 사용자 정보를 저장:

```typescript
const handleLoginSuccess = (response: any) => {
  const { access_token, user } = response.data;

  // localStorage에 저장
  localStorage.setItem('accessToken', access_token);
  localStorage.setItem('user', JSON.stringify(user));

  // AppContext 업데이트
  setUser(user);

  // 모달 닫기
  onLoginSuccess();
};
```

---

## 🔄 전체 Flow

### 사용자 접속 Flow

```
1. 사용자가 채팅창 접속
   ↓
2. AppContext에서 isAuthenticated 체크
   ↓
3-a. 로그인 안 됨 → LoginModal 표시
   ↓
   로그인 성공 → JWT 토큰 저장
   ↓
   채팅창 표시

3-b. 로그인 됨 → 채팅창 바로 표시
```

### 채팅 메시지 전송 Flow

```
1. 사용자가 메시지 입력
   ↓
2. apiClient.post('/api/chat', ...)
   ↓
3. Request Interceptor에서 JWT 토큰 자동 추가
   ↓
4-a. 백엔드에서 JWT 검증 성공 → 응답 반환
4-b. 백엔드에서 JWT 검증 실패 → 401 에러
   ↓
5. Response Interceptor에서 401 감지
   ↓
6. localStorage 클리어 + 로그인 페이지로 리다이렉트
```

---

## 🛠️ 구현 체크리스트

### 백엔드 (✅ 완료)

- [x] `/api/chat` 엔드포인트에 `require_auth` 적용
- [x] 익명 사용자 처리 로직 제거
- [x] JWT 토큰 검증 (이미 구현됨)
- [x] 401 에러 반환 (토큰 없으면)

### 프론트엔드 (✅ 완료)

- [x] `apiClient.ts`에 JWT 토큰 자동 추가 로직 확인/추가 (기존 구현 활용)
- [x] `AppContext.tsx`에서 인증 상태 관리 (기존 구현 활용)
- [x] `services/api.ts`를 `apiClient`로 변경하여 JWT 자동 포함
- [x] `ChatPage.tsx`에서 인증 체크 및 로그인 가드 구현
- [x] 로그인 안 되었으면 LoginModal 표시 (자동 + 수동)
- [x] 로그인 성공 시 JWT 토큰 + 사용자 정보 저장 (기존 구현 활용)
- [x] 채팅 API 호출 시 JWT 토큰 자동 포함 (apiClient 활용)
- [x] 401 에러 처리 (로그아웃 + 리다이렉트) (기존 구현 활용)

---

## 🎯 테스트 시나리오

### 시나리오 1: 로그인하지 않은 사용자

```
1. 채팅창 접속
   → "로그인이 필요합니다" 메시지 표시

2. 로그인 버튼 클릭
   → LoginModal 표시

3. 로그인 성공
   → 채팅창 표시
   → 메시지 전송 가능
```

### 시나리오 2: 이미 로그인한 사용자

```
1. 채팅창 접속
   → localStorage에서 JWT 토큰 복원
   → 바로 채팅창 표시

2. 메시지 전송
   → JWT 토큰 자동 포함
   → 정상 응답
```

### 시나리오 3: 로그인 만료된 사용자

```
1. 채팅 중 JWT 토큰 만료
   → 메시지 전송 시 401 에러

2. Response Interceptor에서 감지
   → localStorage 클리어
   → 로그인 페이지로 리다이렉트
```

---

## 📚 관련 파일

### 백엔드

- `backend/api_server.py`: 채팅 API 엔드포인트
- `backend/src/auth/dependencies.py`: 인증 의존성
- `backend/src/auth/jwt_utils.py`: JWT 유틸리티

### 프론트엔드

- `front/src/utils/apiClient.ts`: API 클라이언트
- `front/src/utils/authUtils.ts`: 인증 유틸리티
- `front/src/contexts/AppContext.tsx`: 앱 컨텍스트
- `front/src/components/LoginModal.tsx`: 로그인 모달
- `front/src/components/Chat.tsx`: 채팅 컴포넌트

---

## 💡 주요 포인트

### 1. JWT 토큰 자동 관리

```typescript
// apiClient가 자동으로 토큰을 추가하므로
// 개별 API 호출 시 신경쓰지 않아도 됨!

// Bad (수동으로 토큰 추가)
fetch('/api/chat', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
  }
});

// Good (apiClient가 자동 처리)
apiClient.post('/api/chat', data);
```

### 2. 인증 상태 중앙 관리

```typescript
// AppContext에서 중앙 관리
// 모든 컴포넌트에서 동일한 인증 상태 사용

const { user, isAuthenticated, logout } = useContext(AppContext);
```

### 3. 401 에러 자동 처리

```typescript
// Response Interceptor가 자동으로 처리
// 개별 API 호출에서 401 처리 불필요!

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 자동 로그아웃 + 리다이렉트
      logout();
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);
```

---

## 🔗 관련 문서

- [14. User Authentication System](./14_user_authentication_system.md)
- [16. Complete Authentication System](./16_complete_authentication_system.md)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT.io](https://jwt.io/)

---

## 다음 단계

1. ✅ 백엔드 인증 필수화 완료
2. ✅ 프론트엔드 구현 완료
3. 🧪 테스트 (3가지 시나리오) - 사용자 테스트 필요
4. 🚀 배포

**최종 목표**: 로그인한 사용자만 안전하게 채팅할 수 있는 시스템 완성! 🔐

---

## 📝 실제 구현 내역 (2025-11-02)

### 구현 완료 항목

#### 1. 백엔드 (✅ 이전 세션에서 완료)
- [backend/api_server.py](../backend/api_server.py:1026) - `/api/chat` 엔드포인트에 `require_auth` 적용
- 익명 사용자 처리 로직 제거
- JWT 토큰 없으면 401 Unauthorized 반환

#### 2. 프론트엔드 - API 레이어 (✅ 완료)

**파일**: [front/src/services/api.ts](../front/src/services/api.ts)

**변경 사항**:
1. `import authenticatedApiClient from '@/utils/apiClient'` 추가
2. 모든 API 메서드를 `fetch()` → `authenticatedApiClient` (axios) 로 변경:
   - `sendMessage()`: JWT 토큰 자동 포함
   - `getSession()`: JWT 토큰 자동 포함
   - `deleteSession()`: JWT 토큰 자동 포함
   - `listScenarios()`: JWT 토큰 자동 포함
   - `healthCheck()`: 인증 없음 (공개 엔드포인트)

**Before**:
```typescript
async sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${this.baseURL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return response.json()
}
```

**After**:
```typescript
async sendMessage(request: ChatRequest): Promise<ChatResponse> {
  // JWT token automatically added by authenticatedApiClient interceptor
  const response = await authenticatedApiClient.post('/api/chat', request)
  return response.data
}
```

#### 3. 프론트엔드 - 페이지 가드 (✅ 완료)

**파일**: [front/src/pages/ChatPage.tsx](../front/src/pages/ChatPage.tsx)

**변경 사항**:
1. `LoginModal` import 추가
2. `useApp()` 훅에서 `isLoggedIn`, `openLoginModal` 가져오기
3. `useEffect`로 인증 상태 체크 - 미인증 시 자동으로 로그인 모달 표시
4. 인증되지 않은 사용자에게 Lock Screen 표시:
   - 🔐 아이콘 + "로그인이 필요합니다" 메시지
   - "로그인하기" 버튼
   - LoginModal 자동 표시
5. 인증된 사용자만 ChatInterface 접근 가능

**Before**:
```typescript
export default function ChatPage() {
  return (
    <div>
      <ChatInterface characterId={characterId || 'ending'} />
    </div>
  );
}
```

**After**:
```typescript
export default function ChatPage() {
  const { isLoggedIn, openLoginModal } = useApp();

  // Auto-show login modal if not authenticated
  useEffect(() => {
    if (!isLoggedIn) {
      openLoginModal();
    }
  }, [isLoggedIn, openLoginModal]);

  // Show lock screen for unauthenticated users
  if (!isLoggedIn) {
    return (
      <div>
        <div className="lock-screen">
          <h1>🔐 로그인이 필요합니다</h1>
          <button onClick={openLoginModal}>로그인하기</button>
        </div>
        <LoginModal />
      </div>
    );
  }

  // Only show chat interface for authenticated users
  return (
    <div>
      <ChatInterface characterId={characterId || 'ending'} />
      <LoginModal />
    </div>
  );
}
```

### 기존 인프라 활용

프론트엔드는 이미 훌륭한 인증 인프라가 구현되어 있어서 활용:

1. **[front/src/utils/apiClient.ts](../front/src/utils/apiClient.ts)** (기존 구현)
   - Request Interceptor: 모든 요청에 JWT 토큰 자동 추가
   - Response Interceptor: 401 에러 시 토큰 갱신 시도
   - 토큰 만료 감지 및 자동 갱신
   - 401 에러 시 자동 로그아웃 + 리다이렉트

2. **[front/src/contexts/AppContext.tsx](../front/src/contexts/AppContext.tsx)** (기존 구현)
   - `isLoggedIn` 상태 관리
   - `login()` / `logout()` 함수
   - localStorage 기반 토큰 복원
   - 모달 상태 관리 (`openLoginModal`, `closeLoginModal`)

3. **[front/src/components/LoginModal.tsx](../front/src/components/LoginModal.tsx)** (기존 구현)
   - 로그인 UI 및 폼
   - JWT 토큰 저장 (`setTokens`, `setUserData`)
   - 소셜 로그인 (Google, Kakao)
   - 이메일 로그인

4. **[front/src/utils/authUtils.ts](../front/src/utils/authUtils.ts)** (기존 구현)
   - `getAccessToken()`, `getRefreshToken()`
   - `setTokens()`, `clearTokens()`
   - `getUserData()`, `setUserData()`
   - `isAuthenticated()`, `isTokenExpired()`

---

## ✅ 구현 완료 요약

### 인증 흐름 (End-to-End)

```
1. 사용자가 채팅 페이지 접속 (/chat/ending)
   ↓
2. ChatPage.tsx에서 isLoggedIn 체크
   ↓
3-a. 미인증 → Lock Screen 표시 + LoginModal 자동 오픈
   ↓
   사용자가 로그인 (tanjiro / 123)
   ↓
   JWT 토큰 localStorage에 저장
   ↓
   AppContext의 isLoggedIn = true
   ↓
   ChatInterface 표시

3-b. 이미 인증됨 → ChatInterface 바로 표시
   ↓
4. 사용자가 메시지 입력 ("안녕")
   ↓
5. sendChatMessage() 호출 (services/api.ts)
   ↓
6. authenticatedApiClient.post('/api/chat', ...)
   ↓
7. Request Interceptor가 JWT 토큰 자동 추가
   ↓
8. 백엔드 require_auth가 JWT 검증
   ↓
9-a. 유효한 토큰 → 응답 반환
9-b. 유효하지 않은 토큰 → 401 Unauthorized
   ↓
10. Response Interceptor가 401 감지
   ↓
11. 토큰 갱신 시도 (refresh token 사용)
   ↓
12-a. 갱신 성공 → 원래 요청 재시도
12-b. 갱신 실패 → 자동 로그아웃 + 홈으로 리다이렉트
```

### 테스트 계정

```
tanjiro / 123
zenitsu / 123
inosuke / 123
giyu / 123
rengoku / 123
tengen / 123
```

---

## 🎉 최종 결과

**백엔드**: ✅ 완료 (JWT 필수 인증)
**프론트엔드**: ✅ 완료 (인증 가드 + JWT 자동 관리)
**통합**: ✅ 완료 (End-to-End 인증 흐름)

**사용자는 이제 로그인해야만 채팅할 수 있습니다!** 🔐
