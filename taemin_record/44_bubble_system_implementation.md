# 버블(크레딧) 시스템 구현 완료

**작성일**: 2025-11-02
**상태**: ✅ 완료 (End-to-End 구현)
**관련 커밋**: 958f63a, 96b03d7, 2562655, 75c5376

## 1. 개요

사용자가 서비스를 이용하기 위해 필요한 가상 화폐인 "버블(Bubble)" 시스템을 전체 스택에 걸쳐 구현했습니다. 신규 가입 시 100버블이 자동 지급되며, 사용자는 버블을 소비하거나 충전할 수 있습니다.

### 1.1 주요 기능

- **자동 초기 버블 지급**: 신규 가입 시 100버블 자동 지급 (트리거 기반)
- **버블 조회**: 사용자의 현재 버블 잔액 및 통계 확인
- **버블 소비**: 서비스 이용 시 버블 차감 (원자적 트랜잭션)
- **버블 충전**: 구매/보너스를 통한 버블 추가 (향후 결제 시스템 연동 예정)
- **거래 내역**: 모든 버블 거래 기록 추적

### 1.2 구현 범위

| 레이어 | 구현 상태 | 파일 |
|--------|----------|------|
| Database Schema | ✅ 완료 | `backend/database/migrations/009_user_credits.sql` |
| DB Manager | ✅ 완료 | `backend/src/database/db_manager.py` |
| API Endpoints | ✅ 완료 | `backend/api_server.py` |
| Frontend API Client | ✅ 완료 | `front/src/services/api.ts` |
| Frontend State | ✅ 완료 | `front/src/contexts/AppContext.tsx` |
| UI Display | ✅ 완료 | RightSidebar.tsx (기존) |
| Payment Integration | ⏳ 예정 | 결제 시스템 연동 필요 |

---

## 2. 데이터베이스 구조

### 2.1 user_credits 테이블

사용자의 현재 버블 잔액과 통계 정보를 저장합니다.

```sql
CREATE TABLE statedb.user_credits (
    user_id UUID PRIMARY KEY
        REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    bubble_count INTEGER NOT NULL DEFAULT 100,
    total_purchased INTEGER NOT NULL DEFAULT 100,
    total_consumed INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT positive_bubble_count CHECK (bubble_count >= 0)
);
```

**컬럼 설명**:
- `bubble_count`: 현재 보유 버블 수 (≥0)
- `total_purchased`: 누적 구매/지급 버블 수
- `total_consumed`: 누적 소비 버블 수
- `last_updated`: 마지막 거래 시각
- `created_at`: 계정 생성 시각

**제약 조건**:
- `positive_bubble_count`: bubble_count는 음수 불가

### 2.2 credit_transactions 테이블

모든 버블 거래 내역을 기록합니다 (감사 로그).

```sql
CREATE TABLE statedb.credit_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_transaction_type CHECK (
        transaction_type IN ('purchase', 'consume', 'refund', 'bonus', 'initial')
    )
);
```

**거래 타입 (transaction_type)**:
- `initial`: 신규 가입 환영 버블
- `purchase`: 사용자 구매
- `consume`: 서비스 이용 소비
- `refund`: 환불
- `bonus`: 이벤트/프로모션 지급

**인덱스**:
```sql
CREATE INDEX idx_credit_transactions_user_id
    ON statedb.credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_created_at
    ON statedb.credit_transactions(created_at DESC);
```

### 2.3 자동 초기 버블 지급 트리거

신규 사용자 생성 시 자동으로 100버블을 지급합니다.

```sql
CREATE OR REPLACE FUNCTION create_initial_credits()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO statedb.user_credits
        (user_id, bubble_count, total_purchased, total_consumed)
    VALUES (NEW.user_id, 100, 100, 0);

    INSERT INTO statedb.credit_transactions
        (user_id, amount, transaction_type, balance_after, description)
    VALUES (NEW.user_id, 100, 'initial', 100, '신규 가입 환영 버블');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_initial_credits
    AFTER INSERT ON statedb.users
    FOR EACH ROW
    EXECUTE FUNCTION create_initial_credits();
```

**동작 방식**:
1. `users` 테이블에 새 행 삽입 시 트리거 발동
2. `user_credits` 테이블에 100버블 기본값 생성
3. `credit_transactions`에 'initial' 거래 기록 생성

### 2.4 기존 사용자 초기화

마이그레이션 실행 시 기존 19명의 사용자에게도 100버블을 일괄 지급했습니다.

```sql
INSERT INTO statedb.user_credits (user_id, bubble_count, total_purchased, total_consumed)
SELECT user_id, 100, 100, 0
FROM statedb.users
WHERE user_id NOT IN (SELECT user_id FROM statedb.user_credits);
```

---

## 3. 백엔드 구현

### 3.1 DB Manager 메서드 (`db_manager.py`)

#### 3.1.1 get_user_credits()

사용자의 현재 크레딧 정보를 조회합니다.

```python
def get_user_credits(self, user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 크레딧 조회

    Args:
        user_id: 사용자 UUID

    Returns:
        {
            'bubble_count': int,
            'total_purchased': int,
            'total_consumed': int,
            'last_updated': datetime
        }
    """
    query = """
    SELECT bubble_count, total_purchased, total_consumed, last_updated
    FROM statedb.user_credits
    WHERE user_id = %s
    """
    results = self.execute_query(query, (user_id,))
    return results[0] if results else None
```

**사용 예시**:
```python
credits = db_manager.get_user_credits("58dc2ed8-f31b-4960-b74b-69f191a1b057")
# {'bubble_count': 87, 'total_purchased': 100, 'total_consumed': 13, ...}
```

#### 3.1.2 consume_credits()

버블을 소비하고 거래 내역을 기록합니다 (원자적 트랜잭션).

```python
def consume_credits(self, user_id: str, amount: int, description: str) -> bool:
    """크레딧 소비 (원자적 트랜잭션)

    Args:
        user_id: 사용자 UUID
        amount: 소비할 버블 수 (양수)
        description: 거래 설명

    Returns:
        True: 소비 성공
        False: 잔액 부족으로 실패
    """
    query = """
    WITH updated AS (
      UPDATE statedb.user_credits
      SET bubble_count = bubble_count - %s,
          total_consumed = total_consumed + %s,
          last_updated = NOW()
      WHERE user_id = %s AND bubble_count >= %s
      RETURNING user_id, bubble_count
    )
    INSERT INTO statedb.credit_transactions
      (user_id, amount, transaction_type, balance_after, description)
    SELECT user_id, -%s, 'consume', bubble_count, %s
    FROM updated
    RETURNING transaction_id;
    """
    results = self.execute_query(
        query,
        (amount, amount, user_id, amount, amount, description)
    )
    return len(results) > 0
```

**트랜잭션 보장**:
- `WITH...RETURNING` 패턴으로 UPDATE와 INSERT를 원자적으로 처리
- 잔액 부족 시 (`bubble_count < amount`) 아무것도 업데이트되지 않음
- 데이터베이스 수준에서 동시성 제어 보장

**사용 예시**:
```python
success = db_manager.consume_credits(
    user_id="58dc2ed8-...",
    amount=5,
    description="시나리오 실행: 기차역"
)
if success:
    print("5버블 소비 완료")
else:
    print("잔액 부족")
```

#### 3.1.3 add_credits()

버블을 추가하고 거래 내역을 기록합니다.

```python
def add_credits(
    self,
    user_id: str,
    amount: int,
    transaction_type: str,
    description: str
) -> bool:
    """크레딧 추가 (구매/보너스/환불)

    Args:
        user_id: 사용자 UUID
        amount: 추가할 버블 수 (양수)
        transaction_type: 'purchase', 'bonus', 'refund' 중 하나
        description: 거래 설명

    Returns:
        True: 추가 성공
        False: 실패
    """
    query = """
    WITH updated AS (
      UPDATE statedb.user_credits
      SET bubble_count = bubble_count + %s,
          total_purchased = total_purchased + %s,
          last_updated = NOW()
      WHERE user_id = %s
      RETURNING user_id, bubble_count
    )
    INSERT INTO statedb.credit_transactions
      (user_id, amount, transaction_type, balance_after, description)
    SELECT user_id, %s, %s, bubble_count, %s
    FROM updated
    RETURNING transaction_id;
    """
    results = self.execute_query(
        query,
        (amount, amount, user_id, amount, transaction_type, description)
    )
    return len(results) > 0
```

**사용 예시**:
```python
# 결제 완료 후
success = db_manager.add_credits(
    user_id="58dc2ed8-...",
    amount=1000,
    transaction_type="purchase",
    description="1000버블 패키지 구매"
)

# 프로모션 이벤트
success = db_manager.add_credits(
    user_id="58dc2ed8-...",
    amount=50,
    transaction_type="bonus",
    description="출석 이벤트 보너스"
)
```

### 3.2 API 엔드포인트 (`api_server.py`)

#### 3.2.1 GET /api/users/me/credits

현재 로그인한 사용자의 크레딧 정보를 조회합니다.

```python
@app.get("/api/users/me/credits")
async def get_user_credits(user: Dict = Depends(require_auth)):
    """사용자 크레딧(버블) 조회

    Returns:
        {
            "bubble_count": 87,
            "total_purchased": 100,
            "total_consumed": 13,
            "last_updated": "2025-11-02T10:30:00"
        }

    Raises:
        404: 크레딧 정보를 찾을 수 없음 (데이터 불일치)
    """
    credits = _hybrid_manager.db.get_user_credits(user["user_id"])
    if not credits:
        raise HTTPException(
            status_code=404,
            detail="크레딧 정보를 찾을 수 없습니다"
        )
    return credits
```

**cURL 예시**:
```bash
curl -X GET http://localhost:8000/api/users/me/credits \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**응답 예시**:
```json
{
  "bubble_count": 87,
  "total_purchased": 100,
  "total_consumed": 13,
  "last_updated": "2025-11-02T10:30:00.123456"
}
```

#### 3.2.2 POST /api/users/me/credits/consume

버블을 소비합니다 (서비스 이용 시 호출).

```python
class ConsumeCreditsRequest(BaseModel):
    amount: int
    description: str

@app.post("/api/users/me/credits/consume")
async def consume_user_credits(
    req: ConsumeCreditsRequest,
    user: Dict = Depends(require_auth)
):
    """사용자 크레딧(버블) 소비

    Request Body:
        {
            "amount": 5,
            "description": "시나리오 실행: 기차역"
        }

    Returns:
        {
            "success": true,
            "message": "5 버블이 차감되었습니다"
        }

    Raises:
        400: 크레딧 잔액 부족
    """
    success = _hybrid_manager.db.consume_credits(
        user["user_id"],
        req.amount,
        req.description
    )
    if not success:
        raise HTTPException(
            status_code=400,
            detail="크레딧 잔액이 부족합니다"
        )
    return {
        "success": True,
        "message": f"{req.amount} 버블이 차감되었습니다"
    }
```

**cURL 예시**:
```bash
curl -X POST http://localhost:8000/api/users/me/credits/consume \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5,
    "description": "시나리오 실행: 기차역"
  }'
```

**성공 응답**:
```json
{
  "success": true,
  "message": "5 버블이 차감되었습니다"
}
```

**실패 응답 (잔액 부족)**:
```json
{
  "detail": "크레딧 잔액이 부족합니다"
}
```

---

## 4. 프론트엔드 구현

### 4.1 API Client (`front/src/services/api.ts`)

#### 4.1.1 UserCredits 인터페이스

```typescript
export interface UserCredits {
  bubble_count: number
  total_purchased: number
  total_consumed: number
  last_updated?: string
}
```

#### 4.1.2 getUserCredits()

사용자 크레딧 정보를 가져옵니다.

```typescript
async getUserCredits(): Promise<UserCredits> {
  try {
    const response = await authenticatedApiClient.get('/api/users/me/credits')
    return response.data
  } catch (error) {
    console.error('Error getting user credits:', error)
    throw error
  }
}
```

**사용 예시**:
```typescript
const credits = await apiClient.getUserCredits()
console.log(`현재 버블: ${credits.bubble_count}`)
```

#### 4.1.3 consumeCredits()

버블을 소비합니다.

```typescript
async consumeCredits(
  amount: number,
  description: string
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await authenticatedApiClient.post(
      '/api/users/me/credits/consume',
      { amount, description }
    )
    return response.data
  } catch (error) {
    console.error('Error consuming credits:', error)
    throw error
  }
}
```

**사용 예시**:
```typescript
try {
  const result = await apiClient.consumeCredits(5, "시나리오 실행")
  alert(result.message) // "5 버블이 차감되었습니다"
} catch (error) {
  alert("잔액이 부족합니다")
}
```

### 4.2 AppContext 통합 (`front/src/contexts/AppContext.tsx`)

#### 4.2.1 State 및 타입

```typescript
interface AppContextType {
  currentBubbles: number;
  updateBubbles: (count: number) => void;
  consumeBubbles: (amount: number) => boolean;
  // ... 기타 프로퍼티
}
```

#### 4.2.2 초기 로딩 시 크레딧 조회

로그인 상태 확인 시 자동으로 버블 카운트를 로드합니다.

```typescript
useEffect(() => {
  const validateToken = async () => {
    if (isAuthenticated()) {
      try {
        // 1. 토큰 유효성 검증
        const userInfo = await apiClient.getCurrentUser();
        setIsLoggedIn(true);
        setUserEmail(userInfo.display_name || userInfo.username);

        // 2. 크레딧 로딩 (신규 추가)
        try {
          const credits = await apiClient.getUserCredits();
          setCurrentBubbles(credits.bubble_count);
        } catch (error) {
          console.error('Failed to load credits:', error);
          setCurrentBubbles(0);
        }
      } catch (error) {
        // 토큰 무효 시
        clearTokens();
        setIsLoggedIn(false);
      }
    }
    setIsAuthLoading(false);
  };

  validateToken();
}, []);
```

**동작 흐름**:
1. 앱 초기화 시 토큰 존재 확인
2. `/api/auth/me` 호출하여 토큰 유효성 검증
3. 토큰 유효 시 `/api/users/me/credits` 호출
4. 버블 카운트를 Context 상태에 저장
5. 실패 시 0으로 설정 (에러 처리)

#### 4.2.3 버블 소비 함수 (기존)

```typescript
const consumeBubbles = (amount: number) => {
  if (currentBubbles >= amount) {
    setCurrentBubbles(prev => prev - amount);
    return true;
  }
  return false;
};
```

**주의**: 이 함수는 **UI 상태만 업데이트**합니다. 실제 서버 소비는 별도로 `apiClient.consumeCredits()`를 호출해야 합니다.

**올바른 사용 예시**:
```typescript
// 1. 서버에 소비 요청
const result = await apiClient.consumeCredits(5, "시나리오 실행");

// 2. 성공 시 로컬 상태 업데이트
if (result.success) {
  consumeBubbles(5);
}
```

### 4.3 UI 표시 (`RightSidebar.tsx`)

기존 RightSidebar에서 `currentBubbles` 상태를 표시합니다.

```typescript
const { currentBubbles } = useApp();

return (
  <div>
    <div>버블 {currentBubbles}개</div>
  </div>
);
```

---

## 5. 트랜잭션 흐름

### 5.1 신규 가입 시 (자동)

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant DB as PostgreSQL

    Client->>API: POST /api/auth/signup
    API->>DB: INSERT INTO users
    DB->>DB: TRIGGER create_initial_credits()
    DB->>DB: INSERT INTO user_credits (100 bubbles)
    DB->>DB: INSERT INTO credit_transactions ('initial')
    DB-->>API: Success
    API-->>Client: 201 Created
```

### 5.2 버블 조회

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant DB as PostgreSQL

    Client->>API: GET /api/users/me/credits
    Note over API: JWT 인증 (require_auth)
    API->>DB: SELECT FROM user_credits WHERE user_id=?
    DB-->>API: {bubble_count: 87, ...}
    API-->>Client: 200 OK {bubble_count: 87}
```

### 5.3 버블 소비

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant DB as PostgreSQL

    Client->>API: POST /api/users/me/credits/consume<br/>{amount: 5, description: "..."}
    Note over API: JWT 인증
    API->>DB: BEGIN TRANSACTION
    DB->>DB: UPDATE user_credits<br/>SET bubble_count -= 5<br/>WHERE bubble_count >= 5
    alt 잔액 충분
        DB->>DB: INSERT INTO credit_transactions<br/>('consume', -5, ...)
        DB->>DB: COMMIT
        DB-->>API: transaction_id (success)
        API-->>Client: 200 OK {success: true}
    else 잔액 부족
        DB->>DB: ROLLBACK (nothing updated)
        DB-->>API: No rows affected
        API-->>Client: 400 Bad Request
    end
```

### 5.4 버블 충전 (향후)

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Payment as 결제 시스템
    participant DB as PostgreSQL

    Client->>API: POST /api/payments/purchase<br/>{package: "1000 bubbles"}
    API->>Payment: 결제 요청
    Payment-->>API: 결제 완료
    API->>DB: add_credits(1000, 'purchase', '...')
    DB->>DB: UPDATE user_credits += 1000
    DB->>DB: INSERT credit_transactions
    DB-->>API: Success
    API-->>Client: 200 OK {new_balance: 1087}
```

---

## 6. 테스트

### 6.1 데이터베이스 테스트

#### 신규 가입 시 자동 지급 확인

```sql
-- 1. 테스트 사용자 생성
INSERT INTO statedb.users (user_id, username, email, display_name, password_hash)
VALUES (
    'test-user-uuid',
    'testuser',
    'test@example.com',
    'Test User',
    '$2b$12$...'
);

-- 2. user_credits 테이블 확인
SELECT * FROM statedb.user_credits WHERE user_id = 'test-user-uuid';
-- 기대 결과: bubble_count=100, total_purchased=100, total_consumed=0

-- 3. credit_transactions 테이블 확인
SELECT * FROM statedb.credit_transactions WHERE user_id = 'test-user-uuid';
-- 기대 결과: transaction_type='initial', amount=100, description='신규 가입 환영 버블'
```

#### 버블 소비 테스트

```sql
-- 1. 초기 상태 확인
SELECT bubble_count FROM statedb.user_credits WHERE user_id = 'test-user-uuid';
-- 100

-- 2. db_manager.consume_credits() 호출 (Python)
-- consume_credits('test-user-uuid', 30, '테스트 시나리오 실행')

-- 3. 결과 확인
SELECT bubble_count, total_consumed FROM statedb.user_credits
WHERE user_id = 'test-user-uuid';
-- 기대 결과: bubble_count=70, total_consumed=30

-- 4. 거래 내역 확인
SELECT amount, transaction_type, balance_after, description
FROM statedb.credit_transactions
WHERE user_id = 'test-user-uuid' AND transaction_type = 'consume'
ORDER BY created_at DESC LIMIT 1;
-- 기대 결과: amount=-30, balance_after=70
```

#### 잔액 부족 테스트

```python
# Python에서 테스트
success = db_manager.consume_credits('test-user-uuid', 1000, '너무 비싼 시나리오')
print(success)  # False

# DB 상태 확인 - 아무것도 변경되지 않아야 함
SELECT bubble_count FROM statedb.user_credits WHERE user_id = 'test-user-uuid';
# 여전히 70
```

### 6.2 API 테스트

#### 크레딧 조회 API

```bash
# 1. 로그인하여 토큰 획득
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}' \
  | jq -r '.access_token')

# 2. 크레딧 조회
curl -X GET http://localhost:8000/api/users/me/credits \
  -H "Authorization: Bearer $TOKEN" \
  | jq

# 기대 응답:
# {
#   "bubble_count": 100,
#   "total_purchased": 100,
#   "total_consumed": 0,
#   "last_updated": "2025-11-02T10:30:00"
# }
```

#### 크레딧 소비 API (성공 케이스)

```bash
curl -X POST http://localhost:8000/api/users/me/credits/consume \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10,
    "description": "시나리오 실행: 기차역"
  }' \
  | jq

# 기대 응답:
# {
#   "success": true,
#   "message": "10 버블이 차감되었습니다"
# }

# 다시 조회하면 90으로 감소
curl -X GET http://localhost:8000/api/users/me/credits \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.bubble_count'
# 90
```

#### 크레딧 소비 API (실패 케이스)

```bash
# 잔액보다 많은 금액 소비 시도
curl -X POST http://localhost:8000/api/users/me/credits/consume \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10000,
    "description": "너무 비싼 시나리오"
  }' \
  | jq

# 기대 응답 (HTTP 400):
# {
#   "detail": "크레딧 잔액이 부족합니다"
# }
```

### 6.3 프론트엔드 테스트

#### 브라우저 콘솔 테스트

```javascript
// 1. apiClient import (React DevTools에서)
import { apiClient } from '@/services/api';

// 2. 크레딧 조회
const credits = await apiClient.getUserCredits();
console.log('현재 버블:', credits.bubble_count);

// 3. 크레딧 소비
const result = await apiClient.consumeCredits(5, '테스트 소비');
console.log(result.message); // "5 버블이 차감되었습니다"

// 4. 다시 조회하여 확인
const updated = await apiClient.getUserCredits();
console.log('남은 버블:', updated.bubble_count); // 5 감소
```

#### E2E 테스트 시나리오

1. **신규 회원가입**
   - 회원가입 완료
   - 우측 사이드바에 "버블 100개" 표시 확인

2. **시나리오 실행**
   - 시나리오 시작 버튼 클릭
   - 버블 5개 차감
   - 우측 사이드바에 "버블 95개" 표시 확인

3. **잔액 부족**
   - 버블이 3개 남은 상태에서
   - 5버블이 필요한 시나리오 실행 시도
   - "잔액이 부족합니다" 에러 메시지 확인

---

## 7. 주요 커밋

| 커밋 해시 | 커밋 메시지 | 변경 사항 |
|----------|------------|-----------|
| `958f63a` | feat(backend): Add bubble system database migration | DB 스키마 생성 (009_user_credits.sql) |
| `96b03d7` | feat(backend): Add credit management methods to DBManager | DB Manager 메서드 추가 |
| `2562655` | feat(backend): Add user credits API endpoints | FastAPI 엔드포인트 추가 |
| `75c5376` | feat(frontend): Complete bubble system integration | Frontend API Client + AppContext 통합 |

---

## 8. 향후 개선 사항

### 8.1 결제 시스템 연동 (High Priority)

현재 버블 충전 기능은 DB와 API는 구현되었으나, 실제 결제 시스템과의 연동이 필요합니다.

**필요 작업**:
- [ ] 결제 API 연동 (토스페이먼츠, 카카오페이 등)
- [ ] PaymentModal.tsx 동적화 (현재 하드코딩된 가격)
- [ ] POST `/api/payments/purchase` 엔드포인트 구현
- [ ] 결제 완료 콜백 처리
- [ ] 결제 실패 시 롤백 로직
- [ ] 결제 내역 관리 (payment_history 테이블)

### 8.2 거래 내역 조회 UI

사용자가 자신의 버블 사용 내역을 확인할 수 있는 UI가 필요합니다.

**필요 작업**:
- [ ] GET `/api/users/me/credits/transactions` API 구현 (페이지네이션)
- [ ] 거래 내역 모달/페이지 UI 구현
- [ ] 필터링 (transaction_type별)
- [ ] 날짜별 정렬

### 8.3 버블 소비 자동화

현재는 수동으로 `consumeCredits()`를 호출해야 하지만, 시나리오 실행 시 자동 차감이 필요합니다.

**필요 작업**:
- [ ] 시나리오 실행 시작 시점에 버블 소비 로직 추가
- [ ] 실행 실패 시 버블 환불 로직 (refund)
- [ ] 버블 부족 시 사전 경고 UI

### 8.4 프로모션 시스템

이벤트나 프로모션을 위한 버블 지급 시스템이 필요합니다.

**필요 작업**:
- [ ] 관리자 API (POST `/api/admin/credits/bonus`)
- [ ] 일일 출석 체크 보너스
- [ ] 추천인 시스템 (referral bonus)
- [ ] 특정 이벤트 완료 시 보너스

### 8.5 통계 및 모니터링

버블 경제 생태계 모니터링을 위한 대시보드가 필요합니다.

**필요 작업**:
- [ ] 관리자 대시보드 (전체 버블 유통량)
- [ ] 일별 버블 소비/충전 통계
- [ ] 사용자별 평균 버블 사용량
- [ ] 이상 거래 탐지 (fraud detection)

### 8.6 성능 최적화

대규모 트래픽 대비 성능 최적화가 필요합니다.

**필요 작업**:
- [ ] Redis 캐싱 (현재 버블 카운트)
- [ ] 버블 소비 요청 중복 방지 (idempotency key)
- [ ] 대량 거래 내역 아카이빙
- [ ] 읽기 복제본 활용

---

## 9. 문제 해결 가이드

### 9.1 버블이 표시되지 않음

**증상**: 로그인 후 우측 사이드바에 버블이 0으로 표시됨

**원인 및 해결**:

1. **DB에 user_credits 레코드가 없음**
   ```sql
   -- 확인
   SELECT * FROM statedb.user_credits WHERE user_id = '<user_id>';

   -- 수동 생성
   INSERT INTO statedb.user_credits (user_id, bubble_count, total_purchased)
   VALUES ('<user_id>', 100, 100);
   ```

2. **API 요청 실패**
   - 브라우저 DevTools > Network 탭 확인
   - `/api/users/me/credits` 요청이 401/404 반환 시 토큰 문제

3. **트리거 미작동**
   ```sql
   -- 트리거 존재 확인
   SELECT * FROM pg_trigger WHERE tgname = 'trigger_create_initial_credits';

   -- 재생성
   DROP TRIGGER IF EXISTS trigger_create_initial_credits ON statedb.users;
   -- (009_user_credits.sql 다시 실행)
   ```

### 9.2 버블 소비가 작동하지 않음

**증상**: `consumeCredits()` 호출 시 항상 400 에러

**원인 및 해결**:

1. **잔액 실제 부족**
   ```sql
   SELECT bubble_count FROM statedb.user_credits WHERE user_id = '<user_id>';
   ```

2. **트랜잭션 실패**
   ```python
   # 백엔드 로그 확인
   # execute_query() 내부 에러 로그 출력
   ```

3. **JWT 토큰 만료**
   - 재로그인하여 새 토큰 발급

### 9.3 기존 사용자에게 버블이 없음

**증상**: 마이그레이션 전 가입한 사용자는 버블이 0

**해결**:
```sql
-- 009_user_credits.sql의 기존 사용자 초기화 쿼리 실행
INSERT INTO statedb.user_credits (user_id, bubble_count, total_purchased, total_consumed)
SELECT user_id, 100, 100, 0
FROM statedb.users
WHERE user_id NOT IN (SELECT user_id FROM statedb.user_credits);

-- 거래 내역도 추가
INSERT INTO statedb.credit_transactions (user_id, amount, transaction_type, balance_after, description)
SELECT user_id, 100, 'initial', 100, '신규 가입 환영 버블'
FROM statedb.users
WHERE user_id NOT IN (
    SELECT DISTINCT user_id FROM statedb.credit_transactions WHERE transaction_type = 'initial'
);
```

---

## 10. 결론

버블 시스템이 데이터베이스부터 프론트엔드까지 완전히 구현되었습니다. 주요 성과는 다음과 같습니다:

### 10.1 완료된 작업

✅ **Database Layer**
- user_credits 테이블 (잔액 및 통계)
- credit_transactions 테이블 (거래 내역)
- 자동 초기 버블 지급 트리거
- 기존 19명 사용자 초기화 완료

✅ **Backend Layer**
- DB Manager: `get_user_credits()`, `consume_credits()`, `add_credits()`
- API Endpoints: GET/POST `/api/users/me/credits`
- JWT 인증 통합
- 원자적 트랜잭션 보장

✅ **Frontend Layer**
- TypeScript 타입 정의 (UserCredits)
- API Client 메서드
- AppContext 통합 (자동 로딩)
- UI 표시 (RightSidebar)

### 10.2 다음 단계

1. **결제 시스템 연동** (결제 API → 버블 충전)
2. **거래 내역 UI** (사용자가 내역 확인 가능)
3. **자동 버블 소비** (시나리오 실행 시 자동 차감)
4. **프로모션 시스템** (이벤트 보너스, 출석 체크)

### 10.3 시스템 안정성

- ✅ 동시성 제어 (DB 트랜잭션)
- ✅ 잔액 부족 처리 (원자적 검증)
- ✅ 에러 핸들링 (try-catch, HTTP 상태 코드)
- ✅ 거래 내역 추적 (감사 로그)
- ⏳ 중복 요청 방지 (idempotency - 향후 구현)

---

**문서 작성**: Claude
**검토 필요**: 결제 시스템 연동 시 이 문서를 참고하여 구현
**관련 이슈**: #6 (High Priority - Bubble Count Loading)
