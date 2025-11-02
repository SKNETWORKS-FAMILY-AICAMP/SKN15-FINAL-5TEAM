# 핵심 학습 내용 및 패턴 정리

> **작성일**: 2025-11-02
> **목적**: 오늘 작업에서 배운 핵심 개념, 패턴, 코딩 기법 정리
> **대상**: 학습 자료, 복습용

---

## 📚 목차

1. [React Hooks 패턴](#react-hooks-패턴)
2. [TypeScript 타입 시스템](#typescript-타입-시스템)
3. [REST API 설계](#rest-api-설계)
4. [데이터베이스 쿼리 패턴](#데이터베이스-쿼리-패턴)
5. [인증 및 보안](#인증-및-보안)
6. [상태 관리 전략](#상태-관리-전략)
7. [에러 처리 패턴](#에러-처리-패턴)
8. [UI/UX 디자인 원칙](#uiux-디자인-원칙)

---

## React Hooks 패턴

### useState - 상태 관리의 기본

#### 기본 사용법

```typescript
// 단순 값
const [count, setCount] = useState(0);
const [isOpen, setIsOpen] = useState(false);
const [name, setName] = useState('');

// 사용
setCount(5);
setIsOpen(true);
setName('Alice');
```

#### 함수형 업데이트 (이전 값 기반)

```typescript
// ❌ 잘못된 방법 (경쟁 조건 가능)
setCount(count + 1);

// ✅ 올바른 방법
setCount(prev => prev + 1);
```

**언제 사용?**
- 이전 값을 기반으로 새 값을 계산할 때
- 여러 상태 업데이트가 동시에 발생할 수 있을 때

**실제 예시** (오늘 작업):
```typescript
// SessionResumeModal에서 사용
const [showResumeModal, setShowResumeModal] = useState(false);
const [sessionCheckDone, setSessionCheckDone] = useState(false);

// 모달 닫기
const handleClose = () => {
  setShowResumeModal(false);
};
```

#### 객체 상태 (불변성 유지)

```typescript
// ❌ 잘못된 방법 (직접 수정)
const [user, setUser] = useState({ name: '', age: 0 });
user.name = 'Alice';  // 🚫 React가 감지하지 못함

// ✅ 올바른 방법 (새 객체 생성)
setUser({ ...user, name: 'Alice' });

// ✅ 더 나은 방법 (함수형 업데이트)
setUser(prev => ({ ...prev, name: 'Alice' }));
```

**실제 예시** (오늘 작업):
```typescript
// LoginModal에서 폼 상태 초기화
const switchMode = (newMode: AuthMode) => {
  setMode(newMode);
  setUsername('');
  setPassword('');
  setPasswordConfirm('');
  setEmail('');
  setDisplayName('');
  setError('');
};
```

### useEffect - 부수 효과 처리

#### 패턴 1: 마운트 시 1회 실행

```typescript
useEffect(() => {
  console.log('컴포넌트가 마운트되었습니다');
  fetchData();
}, []);  // 빈 의존성 배열
```

**사용 사례**:
- API 초기 데이터 로딩
- 외부 라이브러리 초기화
- 이벤트 리스너 등록

#### 패턴 2: 의존성 변경 시 실행

```typescript
useEffect(() => {
  if (isLoggedIn) {
    checkSession();
  }
}, [isLoggedIn]);  // isLoggedIn 변경 시 실행
```

**실제 예시** (오늘 작업):
```typescript
// ChatPage.tsx
useEffect(() => {
  if (!isLoggedIn) {
    openLoginModal();
    setSessionCheckDone(false);
  }
}, [isLoggedIn, openLoginModal]);

useEffect(() => {
  if (isLoggedIn && characterId && !sessionCheckDone) {
    checkLastSession();
  }
}, [isLoggedIn, characterId, sessionCheckDone]);
```

**주의사항**:
- 의존성 배열에 사용하는 모든 외부 변수 포함
- ESLint의 `exhaustive-deps` 규칙 따르기

#### 패턴 3: 클린업 함수

```typescript
useEffect(() => {
  // 설정
  const timer = setInterval(() => {
    console.log('Tick');
  }, 1000);

  // 클린업 (컴포넌트 언마운트 시 실행)
  return () => {
    clearInterval(timer);
  };
}, []);
```

**사용 사례**:
- 타이머 정리 (`setInterval`, `setTimeout`)
- 이벤트 리스너 제거
- WebSocket 연결 종료
- 구독 취소

**예시**:
```typescript
useEffect(() => {
  const handleResize = () => {
    setWindowWidth(window.innerWidth);
  };

  window.addEventListener('resize', handleResize);

  return () => {
    window.removeEventListener('resize', handleResize);
  };
}, []);
```

### Hook 사용 규칙

**1. 최상위에서만 호출**
```typescript
// ❌ 잘못된 사용
function MyComponent() {
  if (condition) {
    const [state, setState] = useState(0);  // 🚫 조건문 안
  }
}

// ✅ 올바른 사용
function MyComponent() {
  const [state, setState] = useState(0);
  if (condition) {
    // state 사용
  }
}
```

**2. React 함수 컴포넌트에서만 호출**
```typescript
// ❌ 일반 함수에서 사용 불가
function regularFunction() {
  const [state, setState] = useState(0);  // 🚫
}

// ✅ 함수 컴포넌트
function MyComponent() {
  const [state, setState] = useState(0);  // ✅
}

// ✅ 커스텀 Hook
function useCustomHook() {
  const [state, setState] = useState(0);  // ✅
}
```

---

## TypeScript 타입 시스템

### Interface vs Type

#### Interface (확장 가능)

```typescript
interface User {
  id: string;
  name: string;
}

// 확장
interface AdminUser extends User {
  role: 'admin';
  permissions: string[];
}

// 병합 (동일 이름 interface는 자동으로 병합됨)
interface User {
  email: string;  // User에 email 필드 추가됨
}
```

#### Type (유연한 조합)

```typescript
type AuthMode = 'login' | 'register';  // 유니온 타입

type Success = { success: true; data: any };
type Error = { success: false; message: string };
type Result = Success | Error;  // 유니온

type UserWithTimestamp = User & { createdAt: Date };  // 인터섹션
```

#### 언제 무엇을 사용?

**Interface 사용**:
- 객체 모양 정의
- 확장 가능성이 필요할 때
- 클래스 구현 시

**Type 사용**:
- 유니온 타입 (`'a' | 'b'`)
- 튜플 타입 (`[string, number]`)
- 함수 타입
- 조건부 타입

**실제 예시** (오늘 작업):
```typescript
// Type 사용 (유니온)
type AuthMode = 'login' | 'register';

// Interface 사용 (객체 모양)
interface LastSessionInfo {
  sessionId: string;
  scenarioId: string;
  currentStage?: string;
  turnCount: number;
  createdAt?: string;
  updatedAt?: string;
  conversationSummary?: string;
}

interface SessionResumeModalProps {
  lastSession: LastSessionInfo;
  onResume: (sessionId: string) => void;
  onNewSession: () => void;
  onClose: () => void;
}
```

### Optional vs Required

```typescript
interface SignupRequest {
  username: string;        // required
  password: string;        // required
  email?: string;          // optional
  display_name?: string;   // optional
}

// 사용
const req1: SignupRequest = {
  username: 'alice',
  password: 'pass123'
  // email, display_name 생략 가능
};

const req2: SignupRequest = {
  username: 'bob',
  password: 'pass456',
  email: 'bob@example.com',
  display_name: 'Bob'
};
```

### 타입 가드

```typescript
interface Success {
  success: true;
  data: any;
}

interface Error {
  success: false;
  message: string;
}

type ApiResponse = Success | Error;

function handleResponse(response: ApiResponse) {
  if (response.success) {
    // TypeScript가 response를 Success로 좁혀줌
    console.log(response.data);
  } else {
    // TypeScript가 response를 Error로 좁혀줌
    console.log(response.message);
  }
}
```

**실제 예시** (오늘 작업):
```typescript
const response = await fetch('/api/auth/register', { ... });
const data = await response.json();

if (data.success) {
  // success일 때만 access_token 존재
  const tokens: TokenData = {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    token_type: data.token_type || 'bearer',
  };
} else {
  // 실패 시 message 표시
  setError(data.message || '회원가입 중 오류가 발생했습니다.');
}
```

---

## REST API 설계

### RESTful URL 규칙

```
리소스명은 복수형 명사 사용
동사 사용 금지 (HTTP 메서드가 동사 역할)

GET    /api/users          # 사용자 목록 조회
GET    /api/users/:id      # 특정 사용자 조회
POST   /api/users          # 사용자 생성
PUT    /api/users/:id      # 사용자 전체 수정
PATCH  /api/users/:id      # 사용자 부분 수정
DELETE /api/users/:id      # 사용자 삭제

# 중첩 리소스
GET    /api/users/:id/sessions       # 특정 사용자의 세션 목록
POST   /api/users/:id/sessions       # 특정 사용자의 세션 생성
```

**실제 예시** (오늘 작업):
```
GET    /api/session/last              # 마지막 세션 조회
GET    /api/sessions                  # 세션 목록
GET    /api/sessions/:session_id      # 세션 상세
POST   /api/auth/register             # 회원가입
POST   /api/auth/login                # 로그인
```

### HTTP 상태 코드

```
2xx: 성공
  200 OK                  # 요청 성공
  201 Created             # 리소스 생성 성공
  204 No Content          # 성공했지만 반환할 내용 없음

4xx: 클라이언트 오류
  400 Bad Request         # 잘못된 요청 (유효성 검사 실패)
  401 Unauthorized        # 인증 필요
  403 Forbidden           # 권한 없음
  404 Not Found           # 리소스 없음
  409 Conflict            # 충돌 (중복 데이터 등)
  422 Unprocessable Entity # 유효성 검사 실패

5xx: 서버 오류
  500 Internal Server Error  # 서버 내부 오류
  502 Bad Gateway            # 게이트웨이 오류
  503 Service Unavailable    # 서비스 사용 불가
```

**예시**:
```python
# 성공
return JSONResponse(
    status_code=200,
    content={"success": True, "data": ...}
)

# 중복 사용자 (409 Conflict)
return JSONResponse(
    status_code=409,
    content={"success": False, "message": "이미 존재하는 사용자명입니다."}
)

# 인증 필요 (401 Unauthorized)
raise HTTPException(
    status_code=401,
    detail="로그인이 필요합니다."
)
```

### 일관된 응답 형식

```json
// 성공 응답
{
  "success": true,
  "message": "작업이 완료되었습니다.",
  "data": {
    "user_id": "...",
    "username": "..."
  }
}

// 실패 응답
{
  "success": false,
  "message": "이미 존재하는 사용자명입니다.",
  "error_code": "DUPLICATE_USERNAME"
}

// 목록 응답 (페이지네이션)
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

**실제 예시** (오늘 작업):
```python
# GET /api/session/last
if not last_session:
    return {
        "has_session": False,
        "message": "저장된 세션이 없습니다"
    }

return {
    "has_session": True,
    "session_id": str(last_session.get("session_id")),
    "scenario_id": last_session.get("scenario_id"),
    # ...
}
```

---

## 데이터베이스 쿼리 패턴

### Parameterized Queries (SQL Injection 방지)

```python
# ❌ 위험한 방법 (SQL Injection 취약)
username = request.form['username']
query = f"SELECT * FROM users WHERE username = '{username}'"
cursor.execute(query)

# ✅ 안전한 방법 (Parameterized Query)
username = request.form['username']
cursor.execute(
    "SELECT * FROM users WHERE username = %s",
    (username,)  # 튜플로 전달
)
```

**실제 예시** (오늘 작업):
```python
def get_user_last_session(self, user_id: str, scenario_id: Optional[str] = None):
    with self.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if scenario_id:
                cur.execute("""
                    SELECT * FROM statedb.sessions
                    WHERE user_id = %s AND scenario_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (user_id, scenario_id))  # ✅ Parameterized
            else:
                cur.execute("""
                    SELECT * FROM statedb.sessions
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (user_id,))  # ✅ 단일 값도 튜플로
```

### 인덱스 활용

```sql
-- 자주 조회되는 컬럼에 인덱스 생성
CREATE INDEX idx_users_username ON statedb.users(username);
CREATE INDEX idx_users_email ON statedb.users(email);

-- 정렬 쿼리용 인덱스 (DESC 명시)
CREATE INDEX idx_sessions_updated_at ON statedb.sessions(updated_at DESC);

-- 복합 인덱스
CREATE INDEX idx_sessions_user_scenario
ON statedb.sessions(user_id, scenario_id);
```

**언제 인덱스가 필요?**
- WHERE 절에 자주 사용되는 컬럼
- ORDER BY에 사용되는 컬럼
- JOIN 조건에 사용되는 컬럼
- UNIQUE 제약조건 (자동 인덱스 생성됨)

**인덱스 단점**:
- INSERT/UPDATE/DELETE 성능 저하
- 디스크 공간 사용
- 너무 많은 인덱스는 역효과

### N+1 쿼리 문제

```python
# ❌ N+1 문제 (1 + N번의 쿼리)
users = query("SELECT * FROM users")  # 1번
for user in users:
    sessions = query(
        "SELECT * FROM sessions WHERE user_id = %s",
        (user.id,)
    )  # N번 (users 개수만큼)

# ✅ JOIN 사용 (1번의 쿼리)
result = query("""
    SELECT u.*, s.*
    FROM users u
    LEFT JOIN sessions s ON u.user_id = s.user_id
""")
```

---

## 인증 및 보안

### 비밀번호 해싱 (bcrypt)

```python
import bcrypt

# 회원가입 시 해싱
password = "user_password"
password_hash = bcrypt.hashpw(
    password.encode('utf-8'),
    bcrypt.gensalt()
).decode('utf-8')

# DB에 password_hash 저장

# 로그인 시 검증
stored_hash = get_user_password_hash(username)
if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
    # 비밀번호 일치
    return login_success()
else:
    # 비밀번호 불일치
    return login_failure()
```

**bcrypt 특징**:
- Salt 자동 생성 및 포함
- 계산 비용 조절 가능 (기본: 12 rounds)
- Rainbow Table 공격 방어
- 느린 해싱 (Brute Force 방어)

**절대 하지 말아야 할 것**:
- ❌ 비밀번호 평문 저장
- ❌ MD5, SHA1 사용 (너무 빠름)
- ❌ Salt 없이 해싱
- ❌ 비밀번호를 로그에 출력

### JWT 인증

```python
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key-keep-it-secret"

# Access Token 생성 (짧은 만료 시간)
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

# Refresh Token 생성 (긴 만료 시간)
def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

# Token 검증
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "토큰이 만료되었습니다")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "유효하지 않은 토큰입니다")
```

**JWT 구조**:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZXhwIjoxNjcwMDAwMDAwfQ.signature
└─────────── Header ───────────┘ └────────── Payload ──────────┘ └─ Signature ─┘
```

**실제 예시** (오늘 작업):
```typescript
// Frontend에서 토큰 저장
const tokens: TokenData = {
  access_token: data.access_token,
  refresh_token: data.refresh_token,
  token_type: data.token_type || 'bearer',
};
localStorage.setItem('auth_tokens', JSON.stringify(tokens));

// API 요청 시 토큰 포함
const response = await fetch('/api/protected', {
  headers: {
    'Authorization': `Bearer ${tokens.access_token}`
  }
});
```

### HTTPS의 중요성

```
HTTP (암호화 안 됨):
Client → [username: alice, password: pass123] → Server
         ↑ 중간에서 읽을 수 있음! (MITM 공격)

HTTPS (암호화됨):
Client → [암호화된 데이터] → Server
         ↑ 중간에서 읽을 수 없음!
```

**프로덕션에서 필수**:
- 비밀번호 평문 전송 방지
- JWT 토큰 탈취 방지
- MITM (Man-in-the-Middle) 공격 방지

---

## 상태 관리 전략

### Local State vs Global State

#### Local State (useState)

```typescript
function LoginModal() {
  // 이 컴포넌트에서만 사용
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  // 다른 컴포넌트는 접근 불가
}
```

**사용 시기**:
- 한 컴포넌트에서만 필요한 상태
- 폼 입력값, 모달 열림/닫힘 등

#### Global State (Context API)

```typescript
// AppContext.tsx
const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  return (
    <AppContext.Provider value={{ isLoggedIn, user, ... }}>
      {children}
    </AppContext.Provider>
  );
}

// 다른 컴포넌트에서 사용
function ChatPage() {
  const { isLoggedIn, user } = useApp();
  // ...
}
```

**사용 시기**:
- 여러 컴포넌트에서 공유해야 하는 상태
- 로그인 상태, 테마, 언어 설정 등

**실제 예시** (오늘 작업):
```typescript
// ChatPage.tsx
const { isLoggedIn, openLoginModal } = useApp();  // Global state

const [lastSession, setLastSession] = useState<LastSessionInfo | null>(null);  // Local state
const [showResumeModal, setShowResumeModal] = useState(false);  // Local state
```

### Lifting State Up (상태 끌어올리기)

```typescript
// ❌ 형제 컴포넌트 간 상태 공유 불가
function ComponentA() {
  const [data, setData] = useState(...);
  // ComponentB에서 data 사용 불가
}

function ComponentB() {
  // data에 접근할 수 없음
}

// ✅ 부모로 상태 올리기
function ParentComponent() {
  const [data, setData] = useState(...);

  return (
    <>
      <ComponentA data={data} setData={setData} />
      <ComponentB data={data} />
    </>
  );
}
```

**실제 예시** (오늘 작업):
```typescript
// ChatPage (부모)
const [resumeSessionId, setResumeSessionId] = useState<string | undefined>(undefined);

const handleResume = (sessionId: string) => {
  setResumeSessionId(sessionId);  // 부모 상태 업데이트
};

return (
  <>
    <ChatInterface initialSessionId={resumeSessionId} />  {/* 자식에게 전달 */}
    <SessionResumeModal onResume={handleResume} />  {/* 콜백 전달 */}
  </>
);
```

---

## 에러 처리 패턴

### Try-Catch 패턴

```typescript
async function fetchData() {
  try {
    const response = await fetch('/api/data');

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    return data;

  } catch (error) {
    if (error instanceof TypeError) {
      // 네트워크 오류
      console.error('네트워크 연결 실패:', error);
      showError('서버에 연결할 수 없습니다.');
    } else {
      // 기타 오류
      console.error('데이터 로딩 실패:', error);
      showError('데이터를 불러올 수 없습니다.');
    }
    throw error;  // 상위로 전파 (선택)
  }
}
```

**실제 예시** (오늘 작업):
```typescript
const handleRegister = async (e: React.FormEvent) => {
  e.preventDefault();
  setError('');

  try {
    const response = await fetch('http://localhost:8000/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, ... }),
    });

    const data = await response.json();

    if (data.success) {
      // 성공 처리
      login(email || `${username}@kimechat.com`);
      closeLoginModal();
    } else {
      // 서버 오류 (중복 사용자명 등)
      setError(data.message || '회원가입 중 오류가 발생했습니다.');
    }
  } catch (err) {
    // 네트워크 오류
    console.error('회원가입 오류:', err);
    setError('서버 연결에 실패했습니다. 나중에 다시 시도해주세요.');
  }
};
```

### 사용자 친화적 에러 메시지

```typescript
// ❌ 나쁜 예
setError('Error: ECONNREFUSED');
setError('500 Internal Server Error');

// ✅ 좋은 예
setError('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
setError('이미 존재하는 사용자명입니다. 다른 이름을 사용해주세요.');
```

### 에러 로깅

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = risky_operation()
except Exception as e:
    # 상세한 에러 로깅 (개발자용)
    logger.error(f"Failed to process: {e}", exc_info=True)

    # 간단한 메시지 (사용자용)
    return {"success": False, "message": "작업 중 오류가 발생했습니다."}
```

---

## UI/UX 디자인 원칙

### 1. 명확성 (Clarity)

**필수/선택 구분**:
```tsx
<label>
  사용자명 <span className="text-red-500">*</span>
</label>
<label>
  이메일 (선택)
</label>
```

**안내 메시지**:
```tsx
<input type="password" minLength={3} />
<p className="text-xs text-gray-500 mt-1">
  비밀번호는 최소 3자 이상이어야 합니다
</p>
```

### 2. 일관성 (Consistency)

**색상 테마 통일**:
```css
.primary-button {
  background: linear-gradient(to right, purple-600, pink-600);
}

.active-tab {
  color: purple-600;
  background: white;
}
```

**버튼 스타일 일관성**:
```tsx
{/* 주요 액션 */}
<button className="px-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white">
  이어서 하기
</button>

{/* 보조 액션 */}
<button className="px-4 py-3 bg-gray-100 text-gray-700">
  새로 시작
</button>
```

### 3. 피드백 (Feedback)

**즉시 피드백**:
```tsx
{error && (
  <div className="text-red-500 text-sm text-center bg-red-50 p-2 rounded">
    {error}
  </div>
)}

{loading && (
  <div className="text-center">
    <Spinner />
    <p>처리 중...</p>
  </div>
)}
```

**실제 예시** (오늘 작업):
```typescript
// 비밀번호 불일치 즉시 표시
if (password !== passwordConfirm) {
  setError('비밀번호가 일치하지 않습니다.');
  return;
}
```

### 4. 효율성 (Efficiency)

**자동 로그인**:
```typescript
// 회원가입 후 바로 로그인 (사용자의 추가 액션 불필요)
if (data.success) {
  setTokens(tokens);
  login(email || `${username}@kimechat.com`);
  closeLoginModal();  // 모달 자동 닫힘
}
```

**폼 자동 초기화**:
```typescript
const switchMode = (newMode: AuthMode) => {
  setMode(newMode);
  // 모든 입력 자동 리셋 (사용자가 수동으로 지울 필요 없음)
  setUsername('');
  setPassword('');
  // ...
};
```

### 5. 미적 디자인 (Aesthetics)

**그라디언트와 애니메이션**:
```css
/* SessionResumeModal */
.modal-card {
  background: linear-gradient(to bottom right, purple-50, pink-50);
  border: 1px solid purple-100;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

**시각적 계층 구조**:
```tsx
{/* 헤더 (가장 큰 텍스트) */}
<h2 className="text-2xl font-bold">
  저장된 대화가 있습니다
</h2>

{/* 부제목 */}
<p className="text-sm text-gray-500 mt-2">
  이전에 하던 대화를 이어서 하시겠습니까?
</p>

{/* 상세 정보 (작은 텍스트) */}
<p className="text-xs text-gray-500">
  마지막 대화: 10분 전
</p>
```

---

## 마무리

### 핵심 요약

1. **React Hooks**: useState, useEffect의 올바른 사용법과 의존성 관리
2. **TypeScript**: Interface vs Type, Optional 타입, 타입 가드
3. **REST API**: RESTful 규칙, HTTP 상태 코드, 일관된 응답 형식
4. **보안**: bcrypt 해싱, JWT 인증, Parameterized Query
5. **상태 관리**: Local vs Global state, Lifting State Up
6. **에러 처리**: Try-Catch, 사용자 친화적 메시지
7. **UI/UX**: 명확성, 일관성, 피드백, 효율성, 미적 디자인

### 다음 학습 주제

- **React Query**: 서버 상태 관리 라이브러리
- **Zustand/Recoil**: 더 나은 전역 상태 관리
- **React Hook Form**: 복잡한 폼 관리
- **Zod**: 런타임 타입 검증
- **Testing**: Jest, React Testing Library

---

**작성일**: 2025-11-02
**목적**: 학습 자료 및 복습용
**참고**: 실제 프로젝트 코드 기반
