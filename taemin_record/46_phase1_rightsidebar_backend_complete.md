# Phase 1: RightSidebar Backend 구현 완료

**작성일**: 2025-11-02
**커밋**: ed04a83
**상태**: ✅ Backend 완료 (Frontend 진행 중)
**소요 시간**: 약 2시간

---

## 1. 작업 개요

**목표**: RightSidebar의 하드코딩된 사용자 통계/계급/장비 데이터를 동적 API 기반으로 전환

**현재 상황 (Before)**:
```typescript
// RightSidebar.tsx (하드코딩)
<div>계급: 귀살대 대원</div>
<div>경험치: 150/500</div>
<div>총 메시지: 47개</div>
<div>일륜도: 양호</div>
```

**목표 상황 (After - Frontend 완료 후)**:
```typescript
// RightSidebar.tsx (동적)
const progression = await apiClient.getUserProgression()
<div>계급: {progression.rank_name_ko}</div>
<div>경험치: {progression.experience_points}/{progression.next_rank_xp}</div>
<div>총 메시지: {progression.total_messages}개</div>
<div>일륜도: {equipment.sword_status}</div>
```

---

## 2. 완료된 작업

### 2.1 Phase 1.1: Database Schema 생성 ✅

**파일**: [backend/database/migrations/012_user_progression.sql](../backend/database/migrations/012_user_progression.sql) (244줄)

#### 생성된 테이블

##### rank_definitions (계급 정의)
```sql
CREATE TABLE statedb.rank_definitions (
    rank_code VARCHAR(50) PRIMARY KEY,
    rank_name_ko VARCHAR(100) NOT NULL,
    rank_name_en VARCHAR(100),
    rank_name_ja VARCHAR(100),
    min_xp INTEGER NOT NULL,  -- 최소 경험치
    level_range_start INTEGER NOT NULL,
    level_range_end INTEGER NOT NULL,
    icon_emoji VARCHAR(10)
);
```

**초기 데이터 (5개 계급)**:
| 계급 코드 | 한글명 | 최소 XP | 레벨 범위 | 아이콘 |
|----------|--------|---------|----------|--------|
| novice | 견습생 | 0 | 1-5 | 🌱 |
| member | 귀살대 대원 | 500 | 6-15 | ⚔️ |
| elite | 정예 대원 | 2,000 | 16-30 | 🏅 |
| pillar_candidate | 주 후보 | 5,000 | 31-50 | 🌟 |
| hashira | 주 (柱) | 10,000 | 51-99 | 💎 |

##### user_progression (사용자 진행도)
```sql
CREATE TABLE statedb.user_progression (
    user_id UUID PRIMARY KEY,
    rank_code VARCHAR(50) REFERENCES rank_definitions(rank_code),
    experience_points INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    total_messages INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    total_play_minutes INTEGER DEFAULT 0,
    scenarios_completed INTEGER DEFAULT 0,
    achievements_count INTEGER DEFAULT 0
);
```

##### user_equipment (장비 상태)
```sql
CREATE TABLE statedb.user_equipment (
    user_id UUID PRIMARY KEY,
    sword_status VARCHAR(50) DEFAULT 'good',  -- excellent, good, fair, poor, broken
    uniform_status VARCHAR(50) DEFAULT 'worn', -- pristine, worn, equipped, damaged, torn
    crow_status VARCHAR(50) DEFAULT 'waiting', -- waiting, active, resting, absent
    sword_type VARCHAR(100),
    uniform_color VARCHAR(50),
    crow_name VARCHAR(100)
);
```

##### xp_transactions (경험치 거래 내역)
```sql
CREATE TABLE statedb.xp_transactions (
    transaction_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    xp_amount INTEGER NOT NULL,
    xp_type VARCHAR(50) NOT NULL,  -- message, session_complete, scenario_complete, etc.
    xp_balance_after INTEGER NOT NULL,
    level_before INTEGER,
    level_after INTEGER,
    did_level_up BOOLEAN DEFAULT FALSE,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**경험치 타입 (xp_type)**:
- `message`: 메시지 전송
- `session_complete`: 세션 완료
- `scenario_complete`: 시나리오 완료
- `achievement`: 업적 달성
- `daily_bonus`: 일일 보너스
- `event`: 이벤트 보상

#### 유틸리티

**View: v_user_progression_summary**
```sql
CREATE VIEW statedb.v_user_progression_summary AS
SELECT
    up.*,
    rd.rank_name_ko,
    rd.icon_emoji AS rank_icon,
    (SELECT min_xp FROM rank_definitions
     WHERE min_xp > up.experience_points
     ORDER BY min_xp LIMIT 1) AS next_rank_xp,
    ue.sword_status,
    ue.uniform_status,
    ue.crow_status
FROM user_progression up
LEFT JOIN rank_definitions rd ON ...
LEFT JOIN user_equipment ue ON ...
```

**Trigger: 신규 사용자 자동 초기화**
```sql
CREATE OR REPLACE FUNCTION create_user_progression()
RETURNS TRIGGER AS $$
BEGIN
    -- user_progression 초기화 (rank=novice, level=1, xp=0)
    INSERT INTO user_progression ...;

    -- user_equipment 초기화 (sword=good, uniform=worn, crow=waiting)
    INSERT INTO user_equipment ...;

    -- xp_transactions 초기 기록
    INSERT INTO xp_transactions ...;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

#### Migration 실행 결과

```bash
$ PGPASSWORD=dev123 psql -h localhost -p 5433 -U kime -d kimedb \
  -f backend/database/migrations/012_user_progression.sql

CREATE TABLE
INSERT 0 5  # 5개 계급 정의
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TRIGGER
INSERT 0 19  # 19명 기존 사용자 user_progression 초기화
INSERT 0 19  # 19명 기존 사용자 user_equipment 초기화
INSERT 0 19  # 19명 기존 사용자 xp_transactions 초기 기록
CREATE VIEW
NOTICE: ✅ Migration 012_user_progression.sql 완료
NOTICE: 👥 기존 사용자 19개 초기화 완료
```

---

### 2.2 Phase 1.3: DB Manager 메서드 추가 ✅

**파일**: [backend/src/database/db_manager.py](../backend/src/database/db_manager.py) (Lines 1622-1854, 234줄 추가)

#### 메서드 목록

##### 1. get_user_progression()
```python
def get_user_progression(self, user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 진행도 조회 (v_user_progression_summary 뷰 사용)

    Returns:
        {
            'user_id': str,
            'rank_code': str,
            'rank_name_ko': str,
            'rank_icon': str (emoji),
            'experience_points': int,
            'level': int,
            'next_rank_xp': int,
            'total_messages': int,
            'total_sessions': int,
            'total_play_minutes': int,
            'scenarios_completed': int,
            'achievements_count': int,
            'sword_status': str,
            'uniform_status': str,
            'crow_status': str,
            'updated_at': datetime
        }
    """
```

**사용 예시**:
```python
progression = db_manager.get_user_progression("58dc2ed8-f31b-4960-b74b-69f191a1b057")
print(f"계급: {progression['rank_name_ko']}")  # 견습생
print(f"레벨: {progression['level']}")  # 1
print(f"경험치: {progression['experience_points']}")  # 0
```

##### 2. get_user_equipment()
```python
def get_user_equipment(self, user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 장비 상태 조회

    Returns:
        {
            'sword_status': str,
            'uniform_status': str,
            'crow_status': str,
            'sword_type': str,
            'uniform_color': str,
            'crow_name': str
        }
    """
```

##### 3. award_experience()
```python
def award_experience(
    self,
    user_id: str,
    xp_amount: int,
    xp_type: str,
    description: str = None,
    metadata: Dict = None
) -> Optional[Dict[str, Any]]:
    """경험치 지급 및 자동 레벨업 처리

    레벨 계산 공식: level = FLOOR(SQRT(xp) / 10) + 1

    Returns:
        {
            'user_id': str,
            'experience_points': int,
            'level': int,
            'level_before': int,
            'level_after': int,
            'did_level_up': bool
        }
    """
```

**사용 예시**:
```python
# 메시지 전송 시 10XP 지급
result = db_manager.award_experience(
    user_id="58dc2ed8-...",
    xp_amount=10,
    xp_type="message",
    description="메시지 전송",
    metadata={"message_id": "msg_123"}
)

if result['did_level_up']:
    print(f"🎉 레벨 업! {result['level_before']} → {result['level_after']}")
```

**레벨 계산 예시**:
| XP | 레벨 | 비고 |
|----|------|------|
| 0 | 1 | 시작 |
| 100 | 2 | FLOOR(SQRT(100)/10) + 1 = 2 |
| 400 | 3 | FLOOR(SQRT(400)/10) + 1 = 3 |
| 900 | 4 | FLOOR(SQRT(900)/10) + 1 = 4 |
| 2,500 | 6 | FLOOR(SQRT(2500)/10) + 1 = 6 |

##### 4. increment_user_stat()
```python
def increment_user_stat(
    self,
    user_id: str,
    stat_name: str,
    increment_by: int = 1
) -> bool:
    """사용자 통계 증가

    Valid stat_name:
    - 'total_messages'
    - 'total_sessions'
    - 'total_play_minutes'
    - 'scenarios_completed'
    - 'achievements_count'
    """
```

**사용 예시**:
```python
# 메시지 전송 시
db_manager.increment_user_stat(user_id, "total_messages")

# 세션 종료 시
db_manager.increment_user_stat(user_id, "total_sessions")

# 플레이 시간 30분 추가
db_manager.increment_user_stat(user_id, "total_play_minutes", 30)
```

##### 5. update_user_equipment()
```python
def update_user_equipment(
    self,
    user_id: str,
    equipment_updates: Dict[str, str]
) -> bool:
    """사용자 장비 상태 업데이트

    Valid fields:
    - sword_status, uniform_status, crow_status
    - sword_type, uniform_color, crow_name
    """
```

**사용 예시**:
```python
# 일륜도 업그레이드
db_manager.update_user_equipment(user_id, {
    "sword_status": "excellent",
    "sword_type": "물의 호흡"
})
```

##### 6. get_xp_transactions()
```python
def get_xp_transactions(
    self,
    user_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """사용자 경험치 거래 내역 조회 (페이지네이션)"""
```

##### 7. get_rank_leaderboard()
```python
def get_rank_leaderboard(
    self,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """경험치 기준 리더보드 조회 (ROW_NUMBER 사용)

    Returns:
        [
            {
                'rank': 1,
                'user_id': str,
                'username': str,
                'display_name': str,
                'rank_code': str,
                'rank_name_ko': str,
                'rank_icon': str,
                'experience_points': int,
                'level': int,
                'total_messages': int,
                'scenarios_completed': int
            },
            ...
        ]
    """
```

---

### 2.3 Phase 1.4: API Endpoints 추가 ✅

**파일**: [backend/api_server.py](../backend/api_server.py) (Lines 729-929, 202줄 추가)

#### Endpoint 목록

##### 1. GET /api/users/me/progression
```python
@app.get("/api/users/me/progression")
async def get_user_progression(user: Dict = Depends(require_auth)):
    """현재 사용자의 진행도 조회 (JWT 필수)"""
```

**응답 예시**:
```json
{
  "user_id": "58dc2ed8-f31b-4960-b74b-69f191a1b057",
  "rank_code": "novice",
  "rank_name_ko": "견습생",
  "rank_icon": "🌱",
  "experience_points": 0,
  "level": 1,
  "next_rank_xp": 500,
  "total_messages": 0,
  "total_sessions": 0,
  "total_play_minutes": 0,
  "scenarios_completed": 0,
  "achievements_count": 0,
  "sword_status": "good",
  "uniform_status": "worn",
  "crow_status": "waiting",
  "updated_at": "2025-11-02T15:30:00"
}
```

##### 2. GET /api/users/me/equipment
```python
@app.get("/api/users/me/equipment")
async def get_user_equipment(user: Dict = Depends(require_auth)):
    """현재 사용자의 장비 상태 조회 (JWT 필수)"""
```

**응답 예시**:
```json
{
  "sword_status": "good",
  "uniform_status": "worn",
  "crow_status": "waiting",
  "sword_type": null,
  "uniform_color": null,
  "crow_name": null
}
```

##### 3. POST /api/users/me/progression/award-xp
```python
class AwardXPRequest(BaseModel):
    xp_amount: int
    xp_type: str
    description: str = None
    metadata: Dict = None

@app.post("/api/users/me/progression/award-xp")
async def award_user_experience(req: AwardXPRequest, user: Dict = Depends(require_auth)):
    """사용자에게 경험치 지급 (내부 API, JWT 필수)"""
```

**요청 예시**:
```bash
curl -X POST http://localhost:8000/api/users/me/progression/award-xp \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -H "Content-Type: application/json" \
  -d '{
    "xp_amount": 10,
    "xp_type": "message",
    "description": "메시지 전송"
  }'
```

**응답 예시**:
```json
{
  "user_id": "58dc2ed8-...",
  "experience_points": 10,
  "level": 1,
  "level_before": 1,
  "level_after": 1,
  "did_level_up": false
}
```

##### 4. PUT /api/users/me/equipment
```python
class UpdateEquipmentRequest(BaseModel):
    equipment_updates: Dict[str, str]

@app.put("/api/users/me/equipment")
async def update_user_equipment(req: UpdateEquipmentRequest, user: Dict = Depends(require_auth)):
    """사용자 장비 상태 업데이트 (JWT 필수)"""
```

**요청 예시**:
```bash
curl -X PUT http://localhost:8000/api/users/me/equipment \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_updates": {
      "sword_status": "excellent",
      "uniform_status": "equipped"
    }
  }'
```

##### 5. GET /api/users/me/xp-transactions
```python
@app.get("/api/users/me/xp-transactions")
async def get_user_xp_transactions(
    user: Dict = Depends(require_auth),
    limit: int = 50,
    offset: int = 0
):
    """사용자 경험치 거래 내역 조회 (페이지네이션, JWT 필수)

    Query Parameters:
        limit: 조회 개수 (기본 50, 최대 100)
        offset: 오프셋
    """
```

**응답 예시**:
```json
[
  {
    "transaction_id": "trans_123",
    "xp_amount": 10,
    "xp_type": "message",
    "xp_balance_after": 10,
    "level_before": 1,
    "level_after": 1,
    "did_level_up": false,
    "description": "메시지 전송",
    "created_at": "2025-11-02T15:30:00"
  }
]
```

##### 6. GET /api/leaderboard
```python
@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 100):
    """경험치 기준 리더보드 조회 (공개 API, JWT 불필요)

    Query Parameters:
        limit: 조회 개수 (기본 100, 최대 500)
    """
```

**응답 예시**:
```json
[
  {
    "rank": 1,
    "user_id": "user_456",
    "username": "zenitsu",
    "display_name": "아가츠마 젠이츠",
    "rank_code": "member",
    "rank_name_ko": "귀살대 대원",
    "rank_icon": "⚔️",
    "experience_points": 1250,
    "level": 12,
    "total_messages": 89,
    "scenarios_completed": 3
  },
  ...
]
```

---

## 3. 데이터 흐름

### 3.1 신규 사용자 가입 플로우

```
1. POST /api/auth/signup (회원가입 API 호출)
   ↓
2. INSERT INTO users (새 사용자 생성)
   ↓
3. TRIGGER create_user_progression() 자동 실행
   ↓
4. INSERT INTO user_progression (rank=novice, level=1, xp=0)
   INSERT INTO user_equipment (sword=good, uniform=worn, crow=waiting)
   INSERT INTO xp_transactions (xp_type='event', description='귀살대 입문')
   ↓
5. 사용자 생성 완료 (초기 진행도 자동 설정)
```

### 3.2 메시지 전송 시 XP 지급 플로우

```
1. 사용자가 메시지 전송
   ↓
2. 메시지 저장 후, 백엔드에서 내부적으로:
   POST /api/users/me/progression/award-xp
   {
     "xp_amount": 10,
     "xp_type": "message",
     "description": "메시지 전송"
   }
   ↓
3. award_experience() 메서드 실행
   - UPDATE user_progression SET xp += 10, level = FLOOR(SQRT(xp)/10)+1
   - INSERT INTO xp_transactions (기록)
   ↓
4. 레벨업 여부 확인
   - did_level_up = true 이면 알림 (향후 구현)
   ↓
5. increment_user_stat('total_messages') 호출
   ↓
6. 완료
```

### 3.3 RightSidebar 데이터 로딩 플로우 (향후)

```
1. RightSidebar 열림
   ↓
2. GET /api/users/me/progression (JWT 포함)
   ↓
3. get_user_progression() 메서드 실행
   - v_user_progression_summary 뷰 조회 (JOIN)
   ↓
4. 응답 데이터로 UI 렌더링
   - 계급: {rank_name_ko} {rank_icon}
   - 레벨: {level}
   - 경험치: {experience_points} / {next_rank_xp}
   - 총 메시지: {total_messages}
   - 일륜도: {sword_status}
   - 복장: {uniform_status}
   - 까마귀: {crow_status}
```

---

## 4. 테스트 가이드

### 4.1 Database 테스트

#### 신규 사용자 생성 시 자동 초기화 확인
```sql
-- 1. 테스트 사용자 생성
INSERT INTO statedb.users (user_id, username, email, display_name, password_hash)
VALUES (
    'test-user-uuid-progression',
    'testprogression',
    'test.progression@example.com',
    'Test Progression',
    '$2b$12$test...'
);

-- 2. user_progression 확인
SELECT * FROM statedb.user_progression
WHERE user_id = 'test-user-uuid-progression';
-- 기대: rank_code=novice, level=1, xp=0

-- 3. user_equipment 확인
SELECT * FROM statedb.user_equipment
WHERE user_id = 'test-user-uuid-progression';
-- 기대: sword_status=good, uniform_status=worn, crow_status=waiting

-- 4. xp_transactions 확인
SELECT * FROM statedb.xp_transactions
WHERE user_id = 'test-user-uuid-progression';
-- 기대: xp_type='event', description='귀살대 입문'
```

#### 경험치 지급 및 레벨업 테스트
```sql
-- 1. 초기 상태 확인
SELECT level, experience_points FROM statedb.user_progression
WHERE user_id = 'test-user-uuid-progression';
-- level=1, xp=0

-- 2. Python에서 경험치 지급 (100XP)
-- db_manager.award_experience('test-user-uuid-progression', 100, 'event', 'Test 100XP')

-- 3. 레벨업 확인
SELECT level, experience_points FROM statedb.user_progression
WHERE user_id = 'test-user-uuid-progression';
-- 기대: level=2, xp=100 (FLOOR(SQRT(100)/10)+1 = 2)

-- 4. 거래 내역 확인
SELECT xp_amount, level_before, level_after, did_level_up
FROM statedb.xp_transactions
WHERE user_id = 'test-user-uuid-progression'
ORDER BY created_at DESC LIMIT 1;
-- 기대: xp_amount=100, level_before=1, level_after=2, did_level_up=true
```

### 4.2 API 테스트

#### 1. 진행도 조회
```bash
# 1. 로그인하여 토큰 획득
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testprogression","password":"test123"}' \
  | jq -r '.access_token')

# 2. 진행도 조회
curl -X GET http://localhost:8000/api/users/me/progression \
  -H "Authorization: Bearer $TOKEN" \
  | jq

# 기대 응답:
# {
#   "rank_code": "novice",
#   "rank_name_ko": "견습생",
#   "rank_icon": "🌱",
#   "level": 1,
#   "experience_points": 0,
#   ...
# }
```

#### 2. 경험치 지급
```bash
curl -X POST http://localhost:8000/api/users/me/progression/award-xp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "xp_amount": 50,
    "xp_type": "message",
    "description": "Test XP award"
  }' \
  | jq

# 기대 응답:
# {
#   "user_id": "...",
#   "experience_points": 50,
#   "level": 1,
#   "level_before": 1,
#   "level_after": 1,
#   "did_level_up": false
# }
```

#### 3. 장비 업데이트
```bash
curl -X PUT http://localhost:8000/api/users/me/equipment \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_updates": {
      "sword_status": "excellent",
      "sword_type": "물의 호흡"
    }
  }' \
  | jq

# 기대 응답:
# {"success": true}
```

#### 4. 리더보드 조회
```bash
curl -X GET http://localhost:8000/api/leaderboard?limit=10 | jq

# 기대 응답:
# [
#   {"rank": 1, "username": "...", "experience_points": 1250, ...},
#   ...
# ]
```

---

## 5. 다음 단계 (Phase 1.5-1.9)

### Phase 1.6: Frontend API Client ⏳
**파일**: `front/src/services/api.ts`

**추가할 인터페이스**:
```typescript
export interface UserProgression {
  user_id: string
  rank_code: string
  rank_name_ko: string
  rank_icon: string
  experience_points: number
  level: number
  next_rank_xp: number
  total_messages: number
  total_sessions: number
  total_play_minutes: number
  scenarios_completed: number
  achievements_count: number
  sword_status: string
  uniform_status: string
  crow_status: string
}

export interface UserEquipment {
  sword_status: string
  uniform_status: string
  crow_status: string
  sword_type?: string
  uniform_color?: string
  crow_name?: string
}
```

**추가할 메서드**:
```typescript
async getUserProgression(): Promise<UserProgression>
async getUserEquipment(): Promise<UserEquipment>
async awardXP(xpAmount: number, xpType: string, description?: string): Promise<any>
async updateEquipment(updates: Record<string, string>): Promise<any>
async getXPTransactions(limit?: number, offset?: number): Promise<any[]>
```

### Phase 1.7: RightSidebar 리팩토링 ⏳
**파일**: `front/src/components/RightSidebar.tsx`

**변경 사항**:
```typescript
// BEFORE (하드코딩)
<div>계급: 귀살대 대원</div>
<div>경험치: 150/500</div>

// AFTER (동적)
const [progression, setProgression] = useState<UserProgression | null>(null)

useEffect(() => {
  if (isOpen && currentUser) {
    const loadProgression = async () => {
      const data = await apiClient.getUserProgression()
      setProgression(data)
    }
    loadProgression()
  }
}, [isOpen, currentUser])

<div>계급: {progression?.rank_name_ko} {progression?.rank_icon}</div>
<div>경험치: {progression?.experience_points}/{progression?.next_rank_xp}</div>
```

### Phase 1.8: End-to-End 테스트 ⏳
1. 로그인
2. RightSidebar 열기
3. 실제 데이터 확인 (rank, level, XP, stats)
4. 메시지 전송 → XP 증가 확인
5. RightSidebar 다시 열기 → 업데이트된 데이터 확인

### Phase 1.9: 최종 문서화 ⏳
- Phase 1 전체 구현 가이드
- 스크린샷 추가
- 문제 해결 가이드

---

## 6. 성과 요약

### 코드 통계
- **SQL**: 244줄 (012_user_progression.sql)
- **Python**: 234줄 (db_manager.py)
- **Python**: 202줄 (api_server.py)
- **총계**: 680줄

### 생성된 리소스
- **테이블**: 4개 (rank_definitions, user_progression, user_equipment, xp_transactions)
- **뷰**: 1개 (v_user_progression_summary)
- **트리거**: 1개 (create_user_progression)
- **DB 메서드**: 8개
- **API 엔드포인트**: 6개

### 마이그레이션 결과
- ✅ 19명 기존 사용자 초기화 완료
- ✅ 5개 계급 정의 생성
- ✅ 신규 사용자 자동 초기화 트리거 설정

---

## 7. 관련 문서

- [45_hardcoded_data_analysis_medium_priority.md](./45_hardcoded_data_analysis_medium_priority.md) - 하드코딩 데이터 분석
- [44_bubble_system_implementation.md](./44_bubble_system_implementation.md) - 버블 시스템 구현 (참고 자료)

---

**다음 작업**: Phase 1.6 (Frontend API Client) → Phase 1.7 (RightSidebar 통합) → Phase 1.8 (테스트)
