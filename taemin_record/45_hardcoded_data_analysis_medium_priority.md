# 하드코딩 데이터 분석 및 동적화 계획 (Medium Priority)

**작성일**: 2025-11-02
**분석 범위**: Frontend 하드코딩 데이터 전수 조사
**우선순위**: Medium (Critical/High 완료 후 진행)

---

## 1. 분석 요약

Frontend의 3개 주요 컴포넌트에서 **대량의 하드코딩 데이터**를 발견했습니다:

| 컴포넌트 | 하드코딩 데이터 | 동적화 필요성 | 백엔드 지원 | 예상 작업 시간 |
|---------|----------------|--------------|------------|--------------|
| **PaymentModal** | 결제 패키지 3개<br/>결제 수단 4개 | **HIGH** 🔴 | ❌ 없음 | 8-10시간 |
| **HomePage** | 시나리오 카드 6개 | **MEDIUM** 🟡 | ⚠️ 부분적 | 6-8시간 |
| **RightSidebar** | 사용자 통계/장비 | **MEDIUM** 🟡 | ❌ 없음 | 4-6시간 |
| **총계** | **13개 데이터 엔티티** | | | **18-24시간** |

---

## 2. PaymentModal 분석

### 2.1 현재 상태

**파일**: [front/src/components/PaymentModal.tsx](../front/src/components/PaymentModal.tsx) (Lines 23-78)

#### 하드코딩된 버블 패키지 (Lines 23-71)

```typescript
const bubblePacks: BubblePack[] = [
  {
    id: 'small',
    name: '물의 호흡',
    bubbles: 1000,
    price: '₩2,900',
    features: [
      '🫧 호흡 버블 1,000개',
      '⏰ 즉시 충전',
      '💬 약 20회 대화 가능'
    ]
  },
  {
    id: 'medium',
    name: '뇌의 호흡',
    bubbles: 5000,
    price: '₩9,900',
    originalPrice: '₩14,500',
    features: [...],
    isPopular: true,
    savings: '32% 할인',
    bonus: 500  // 보너스 버블
  },
  {
    id: 'large',
    name: '일의 호흡',
    bubbles: 12000,
    price: '₩19,900',
    originalPrice: '₩34,800',
    features: [...],
    savings: '43% 할인',
    bonus: 3000
  }
];
```

#### 하드코딩된 결제 수단 (Lines 73-78)

```typescript
const paymentMethods = [
  { id: 'card', name: '신용카드', icon: '💳' },
  { id: 'kakao', name: '카카오페이', icon: '🟡' },
  { id: 'toss', name: '토스페이', icon: '🔵' },
  { id: 'paypal', name: 'PayPal', icon: '🅿️' }
];
```

### 2.2 문제점

1. **가격 정책 변경 시 재배포 필요**
   - 할인율 변경, 신규 패키지 추가 시 프론트엔드 빌드/배포 필요
   - 관리자가 실시간으로 가격/패키지 조정 불가능

2. **결제 게이트웨이 통합 부재**
   - 실제 결제 API 연동 없음 (Line 112-134: 시뮬레이션만 존재)
   - 구매 내역 데이터베이스 저장 안 됨

3. **프로모션/이벤트 대응 불가**
   - 특정 기간 한정 할인 불가능
   - A/B 테스트 불가능

### 2.3 필요한 작업

#### Phase 1: Database Schema (2시간)

```sql
-- 010_payment_packages.sql

CREATE TABLE statedb.payment_packages (
    package_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_code VARCHAR(50) UNIQUE NOT NULL,  -- 'small', 'medium', 'large'
    name_ko VARCHAR(100) NOT NULL,
    bubble_amount INTEGER NOT NULL,
    bonus_bubbles INTEGER DEFAULT 0,
    price_krw INTEGER NOT NULL,              -- 원화 가격 (센트 단위)
    original_price_krw INTEGER,              -- 정가 (할인 표시용)
    discount_rate INTEGER,                   -- 할인율 (%)
    is_popular BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    features JSONB,                          -- Feature 리스트
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE statedb.payment_methods (
    method_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    method_code VARCHAR(50) UNIQUE NOT NULL,  -- 'card', 'kakao', 'toss', 'paypal'
    name_ko VARCHAR(100) NOT NULL,
    icon_emoji VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0
);

CREATE TABLE statedb.payment_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES statedb.users(user_id),
    package_id UUID NOT NULL REFERENCES statedb.payment_packages(package_id),
    method_code VARCHAR(50) NOT NULL,
    amount_krw INTEGER NOT NULL,
    bubble_amount INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'pending', 'completed', 'failed', 'refunded'
    payment_gateway_id VARCHAR(200),  -- 외부 PG사 거래 ID
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Phase 2: Backend API (3시간)

```python
# db_manager.py 추가 메서드

def get_payment_packages(self):
    """활성 결제 패키지 목록 조회"""
    query = """
    SELECT package_id, package_code, name_ko, bubble_amount, bonus_bubbles,
           price_krw, original_price_krw, discount_rate, is_popular, features
    FROM statedb.payment_packages
    WHERE is_active = TRUE
    ORDER BY display_order, price_krw
    """
    return self.execute_query(query)

def get_payment_methods(self):
    """활성 결제 수단 목록 조회"""
    query = """
    SELECT method_code, name_ko, icon_emoji
    FROM statedb.payment_methods
    WHERE is_active = TRUE
    ORDER BY display_order
    """
    return self.execute_query(query)

def create_payment_transaction(self, user_id, package_id, method_code, amount_krw, bubble_amount):
    """결제 트랜잭션 생성"""
    query = """
    INSERT INTO statedb.payment_transactions
      (user_id, package_id, method_code, amount_krw, bubble_amount, status)
    VALUES (%s, %s, %s, %s, %s, 'pending')
    RETURNING transaction_id
    """
    results = self.execute_query(query, (user_id, package_id, method_code, amount_krw, bubble_amount))
    return results[0]['transaction_id'] if results else None

def complete_payment(self, transaction_id, payment_gateway_id):
    """결제 완료 처리"""
    query = """
    UPDATE statedb.payment_transactions
    SET status = 'completed', payment_gateway_id = %s, paid_at = NOW()
    WHERE transaction_id = %s
    RETURNING user_id, bubble_amount
    """
    results = self.execute_query(query, (payment_gateway_id, transaction_id))
    if results:
        user_id = results[0]['user_id']
        bubble_amount = results[0]['bubble_amount']
        # 버블 추가
        self.add_credits(user_id, bubble_amount, 'purchase', f'결제 완료: {transaction_id}')
        return True
    return False
```

```python
# api_server.py 엔드포인트 추가

@app.get("/api/payments/packages")
async def get_payment_packages():
    """결제 패키지 목록 조회"""
    packages = _hybrid_manager.db.get_payment_packages()
    return {"packages": packages}

@app.get("/api/payments/methods")
async def get_payment_methods():
    """결제 수단 목록 조회"""
    methods = _hybrid_manager.db.get_payment_methods()
    return {"methods": methods}

class InitiatePaymentRequest(BaseModel):
    package_id: str
    method_code: str

@app.post("/api/payments/initiate")
async def initiate_payment(req: InitiatePaymentRequest, user: Dict = Depends(require_auth)):
    """결제 시작"""
    # 1. Package 정보 조회
    # 2. Transaction 생성
    # 3. PG사 API 호출 (토스페이먼츠, 카카오페이 등)
    # 4. 결제 URL 반환
    transaction_id = _hybrid_manager.db.create_payment_transaction(...)
    return {"transaction_id": transaction_id, "redirect_url": "..."}

@app.post("/api/payments/callback")
async def payment_callback(transaction_id: str, pg_id: str):
    """PG사 콜백 처리"""
    success = _hybrid_manager.db.complete_payment(transaction_id, pg_id)
    if success:
        return {"success": True}
    raise HTTPException(status_code=400, detail="Payment completion failed")
```

#### Phase 3: Frontend 리팩토링 (2-3시간)

```typescript
// front/src/services/api.ts

export interface PaymentPackage {
  package_id: string
  package_code: string
  name_ko: string
  bubble_amount: number
  bonus_bubbles: number
  price_krw: number
  original_price_krw?: number
  discount_rate?: number
  is_popular: boolean
  features: string[]
}

export interface PaymentMethod {
  method_code: string
  name_ko: string
  icon_emoji: string
}

async getPaymentPackages(): Promise<PaymentPackage[]>
async getPaymentMethods(): Promise<PaymentMethod[]>
async initiatePayment(packageId: string, methodCode: string): Promise<{transaction_id: string, redirect_url: string}>
```

```typescript
// front/src/components/PaymentModal.tsx

// BEFORE: const bubblePacks = [...하드코딩...]

// AFTER:
const [bubblePacks, setBubblePacks] = useState<PaymentPackage[]>([])
const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([])

useEffect(() => {
  const loadPaymentData = async () => {
    const [packages, methods] = await Promise.all([
      apiClient.getPaymentPackages(),
      apiClient.getPaymentMethods()
    ])
    setBubblePacks(packages)
    setPaymentMethods(methods)
  }
  if (isOpen) {
    loadPaymentData()
  }
}, [isOpen])
```

#### Phase 4: 실제 결제 게이트웨이 연동 (4-5시간)

**옵션 A: 토스페이먼츠**
- 국내 점유율 1위
- API 문서 우수
- 테스트 환경 제공

**옵션 B: 카카오페이**
- 카카오톡 연동
- 간편 결제

**옵션 C: PayPal**
- 해외 사용자 대응
- 환율 자동 처리

**통합 전략**:
1. 토스페이먼츠를 주 결제 수단으로 (Phase 4-1)
2. 카카오페이 추가 (Phase 4-2, optional)
3. PayPal 국제화 시점에 추가 (Phase 4-3, 나중에)

---

## 3. HomePage 분석

### 3.1 현재 상태

**파일**: [front/src/pages/HomePage.tsx](../front/src/pages/HomePage.tsx) (Lines 30-108)

#### 하드코딩된 시나리오 카드 (6개)

```typescript
const characters: CharacterCard[] = [
  {
    id: 'tanjiro',
    title: '편의점 알바생 탄지로',
    description: '탄지로와 함께하는 편의점 일상 체험',
    image: `${CDN_URL}/편의점탄지로.png`,
    likes: 121,
    comments: 45,
    views: 1200,
    tags: ['#편의점', '#일상', '#탄지로'],
    size: 'normal',
    link: '/chat/tanjiro'
  },
  {
    id: 'train',
    title: '무한열차',
    description: '열차 안에서 벌어지는 사건...',
    likes: 98,
    comments: 32,
    views: 890,
    tags: ['#무한열차', '#꿈속전투', '#엔무'],
    size: 'normal',
    link: '/character/train'
  },
  // ... 4개 더
];
```

### 3.2 백엔드 현황

**✅ 존재하는 것**:
- `GET /api/scenarios` 엔드포인트 ([api_server.py:1829](../backend/api_server.py))
- `backend/data/scenarios/` 폴더의 시나리오 JSON 파일들
- `scenario_loader.py` 유틸리티

**❌ 부족한 것**:
- **메타데이터 부재**: 현재 API는 scenario ID만 반환
- **Engagement 데이터 없음**: likes, comments, views 등 사용자 참여 데이터 없음
- **Tags/카테고리 시스템 없음**: 필터링/검색 불가능

**현재 API 응답**:
```json
{
  "scenarios": [
    {"id": "cutscene5_llm_driven"}
  ]
}
```

**필요한 응답**:
```json
{
  "scenarios": [
    {
      "id": "tanjiro",
      "title": "편의점 알바생 탄지로",
      "description": "...",
      "thumbnail_url": "https://cdn.../편의점탄지로.png",
      "tags": ["편의점", "일상", "탄지로"],
      "difficulty": "easy",
      "estimated_duration": "15분",
      "likes_count": 121,
      "comments_count": 45,
      "views_count": 1200,
      "is_featured": false,
      "created_at": "2025-10-15T10:00:00Z"
    }
  ]
}
```

### 3.3 필요한 작업

#### Phase 1: Database Schema (2시간)

```sql
-- 011_scenario_metadata.sql

CREATE TABLE statedb.scenario_metadata (
    scenario_id VARCHAR(100) PRIMARY KEY,  -- 시나리오 파일명 (예: 'tanjiro')
    title_ko VARCHAR(200) NOT NULL,
    title_en VARCHAR(200),
    description_ko TEXT NOT NULL,
    description_en TEXT,
    thumbnail_url VARCHAR(500),
    difficulty VARCHAR(20),  -- 'easy', 'medium', 'hard'
    estimated_duration_minutes INTEGER,
    card_size VARCHAR(20) DEFAULT 'normal',  -- 'large', 'normal'
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE statedb.scenario_tags (
    scenario_id VARCHAR(100) REFERENCES statedb.scenario_metadata(scenario_id),
    tag VARCHAR(50) NOT NULL,
    PRIMARY KEY (scenario_id, tag)
);

CREATE INDEX idx_scenario_tags_tag ON statedb.scenario_tags(tag);

CREATE TABLE statedb.scenario_engagement (
    scenario_id VARCHAR(100) REFERENCES statedb.scenario_metadata(scenario_id),
    user_id UUID REFERENCES statedb.users(user_id),
    engagement_type VARCHAR(20) NOT NULL,  -- 'view', 'like', 'comment'
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (scenario_id, user_id, engagement_type, created_at)
);

CREATE INDEX idx_scenario_engagement_scenario ON statedb.scenario_engagement(scenario_id, engagement_type);
```

#### Phase 2: Backend API Enhancement (2-3시간)

```python
# db_manager.py

def get_scenarios_with_metadata(self, user_id=None):
    """시나리오 메타데이터 + 통계 조회"""
    query = """
    WITH engagement_stats AS (
      SELECT
        scenario_id,
        COUNT(*) FILTER (WHERE engagement_type = 'like') AS likes_count,
        COUNT(*) FILTER (WHERE engagement_type = 'comment') AS comments_count,
        COUNT(DISTINCT user_id) FILTER (WHERE engagement_type = 'view') AS views_count
      FROM statedb.scenario_engagement
      GROUP BY scenario_id
    ),
    user_likes AS (
      SELECT scenario_id
      FROM statedb.scenario_engagement
      WHERE user_id = %s AND engagement_type = 'like'
    )
    SELECT
      sm.scenario_id, sm.title_ko, sm.description_ko, sm.thumbnail_url,
      sm.difficulty, sm.estimated_duration_minutes, sm.card_size,
      sm.is_featured,
      COALESCE(es.likes_count, 0) AS likes_count,
      COALESCE(es.comments_count, 0) AS comments_count,
      COALESCE(es.views_count, 0) AS views_count,
      ARRAY_AGG(st.tag) FILTER (WHERE st.tag IS NOT NULL) AS tags,
      CASE WHEN ul.scenario_id IS NOT NULL THEN TRUE ELSE FALSE END AS user_has_liked
    FROM statedb.scenario_metadata sm
    LEFT JOIN engagement_stats es ON sm.scenario_id = es.scenario_id
    LEFT JOIN statedb.scenario_tags st ON sm.scenario_id = st.scenario_id
    LEFT JOIN user_likes ul ON sm.scenario_id = ul.scenario_id
    WHERE sm.is_active = TRUE
    GROUP BY sm.scenario_id, es.likes_count, es.comments_count, es.views_count, ul.scenario_id
    ORDER BY sm.display_order, sm.created_at DESC
    """
    return self.execute_query(query, (user_id,))

def record_scenario_engagement(self, scenario_id, user_id, engagement_type):
    """시나리오 참여 기록 (view, like, comment)"""
    query = """
    INSERT INTO statedb.scenario_engagement (scenario_id, user_id, engagement_type)
    VALUES (%s, %s, %s)
    ON CONFLICT (scenario_id, user_id, engagement_type, created_at) DO NOTHING
    """
    self.execute_query(query, (scenario_id, user_id, engagement_type))
```

```python
# api_server.py

@app.get("/api/scenarios")
async def list_scenarios(user: Dict = Depends(optional_auth)):
    """시나리오 목록 조회 (메타데이터 + 통계 포함)"""
    user_id = user.get('user_id') if user else None
    scenarios = _hybrid_manager.db.get_scenarios_with_metadata(user_id)
    return {"scenarios": scenarios}

@app.post("/api/scenarios/{scenario_id}/like")
async def like_scenario(scenario_id: str, user: Dict = Depends(require_auth)):
    """시나리오 좋아요"""
    _hybrid_manager.db.record_scenario_engagement(scenario_id, user['user_id'], 'like')
    return {"success": True}

@app.post("/api/scenarios/{scenario_id}/view")
async def view_scenario(scenario_id: str, user: Dict = Depends(require_auth)):
    """시나리오 조회수 증가"""
    _hybrid_manager.db.record_scenario_engagement(scenario_id, user['user_id'], 'view')
    return {"success": True}
```

#### Phase 3: Frontend 리팩토링 (2-3시간)

```typescript
// front/src/pages/HomePage.tsx

// BEFORE: const characters: CharacterCard[] = [...하드코딩...]

// AFTER:
const [characters, setCharacters] = useState<CharacterCard[]>([])
const [loading, setLoading] = useState(true)

useEffect(() => {
  const loadScenarios = async () => {
    try {
      const response = await apiClient.getScenarios()
      setCharacters(response.scenarios.map(s => ({
        id: s.scenario_id,
        title: s.title_ko,
        description: s.description_ko,
        image: s.thumbnail_url,
        likes: s.likes_count,
        comments: s.comments_count,
        views: s.views_count,
        tags: s.tags,
        size: s.card_size,
        link: `/chat/${s.scenario_id}`
      })))
    } catch (error) {
      console.error('Failed to load scenarios:', error)
    } finally {
      setLoading(false)
    }
  }
  loadScenarios()
}, [])

const handleLike = async (scenarioId: string) => {
  await apiClient.likeScenario(scenarioId)
  // UI 업데이트
}
```

#### Phase 4: Initial Data Seeding (1시간)

기존 하드코딩 데이터를 데이터베이스에 마이그레이션:

```sql
INSERT INTO statedb.scenario_metadata (scenario_id, title_ko, description_ko, thumbnail_url, difficulty, estimated_duration_minutes, card_size, display_order)
VALUES
  ('tanjiro', '편의점 알바생 탄지로', '탄지로와 함께하는 편의점 일상 체험', 'https://cdn.../편의점탄지로.png', 'easy', 15, 'normal', 1),
  ('train', '무한열차', '열차 안에서 벌어지는 사건에 휘말려...', 'https://cdn.../무한열차.jpeg', 'hard', 45, 'normal', 2),
  ('infinity-castle', '무한성', '최종 결전을 배경으로...', 'https://cdn.../무한성.webp', 'hard', 60, 'large', 3),
  ('ending', '엔딩 이후', '최종 결전 후 동료들과...', 'https://cdn.../엔딩이후.png', 'easy', 20, 'normal', 4),
  ('counseling', '귀칼 상담소 AU', '캐릭터들이 상담사가 되어...', 'https://cdn.../귀칼상담소.png', 'medium', 30, 'normal', 5),
  ('idol', '아이돌/밴드 AU', '귀멸 캐릭터들이 아이돌 그룹으로...', 'https://cdn.../아이돌밴드.png', 'medium', 40, 'normal', 6);

INSERT INTO statedb.scenario_tags (scenario_id, tag)
VALUES
  ('tanjiro', '편의점'), ('tanjiro', '일상'), ('tanjiro', '탄지로'),
  ('train', '무한열차'), ('train', '꿈속전투'), ('train', '엔무'),
  ('infinity-castle', '최종결전'), ('infinity-castle', '귀살대'), ('infinity-castle', '무잔전'),
  ('ending', '엔딩이후'), ('ending', '일상'), ('ending', '평화'), ('ending', '동료애'),
  ('counseling', '상담소'), ('counseling', '힐링AU'), ('counseling', '감정공감'),
  ('idol', '아이돌AU'), ('idol', '밴드AU'), ('idol', '팬심폭발');
```

---

## 4. RightSidebar 분석

### 4.1 현재 상태

**파일**: [front/src/components/RightSidebar.tsx](../front/src/components/RightSidebar.tsx)

#### Info Tab - 하드코딩된 데이터 (Lines 99-131)

```typescript
<div className="bg-blue-50 rounded-lg p-4">
  <h3>🎖️ 계급 정보</h3>
  <div>계급: 귀살대 대원</div>        {/* 하드코딩 */}
  <div>경험치: 150/500</div>          {/* 하드코딩 */}
  <div style={{ width: '30%' }}></div> {/* 하드코딩 */}
</div>

<div className="bg-green-50 rounded-lg p-4">
  <h3>⚔️ 장비 상태</h3>
  <div>일륜도: 양호</div>            {/* 하드코딩 */}
  <div>귀살대 복장: 착용중</div>      {/* 하드코딩 */}
  <div>까마귀: 대기중</div>           {/* 하드코딩 */}
</div>
```

#### Stats Tab - 하드코딩된 데이터 (Lines 135-144)

```typescript
<div className="bg-yellow-50 rounded-lg p-4">
  <h3>📊 채팅 통계</h3>
  <div>총 메시지: 47개</div>        {/* 하드코딩 */}
  {/* 더 많은 통계 데이터 예상 */}
</div>
```

### 4.2 필요한 데이터

1. **User Rank/Level System**:
   - 계급 (Rank): Bronze, Silver, Gold, Platinum, Diamond 등
   - 경험치 (XP): 현재/다음 레벨까지 필요 XP
   - 레벨업 보상 시스템

2. **Equipment/Inventory System**:
   - 일륜도 (Sword) 상태
   - 복장 (Uniform) 상태
   - 까마귀 (Crow) 상태
   - 향후 확장: 아이템 인벤토리

3. **User Statistics**:
   - 총 메시지 수
   - 총 대화 세션 수
   - 총 플레이 시간
   - 완료한 시나리오 수
   - 획득한 업적 수

### 4.3 필요한 작업

#### Phase 1: Database Schema (2시간)

```sql
-- 012_user_progression.sql

CREATE TABLE statedb.user_progression (
    user_id UUID PRIMARY KEY REFERENCES statedb.users(user_id),
    rank_code VARCHAR(50) DEFAULT 'novice',  -- 'novice', 'member', 'hashira', etc.
    experience_points INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    total_messages INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    total_play_minutes INTEGER DEFAULT 0,
    scenarios_completed INTEGER DEFAULT 0,
    achievements_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE statedb.rank_definitions (
    rank_code VARCHAR(50) PRIMARY KEY,
    rank_name_ko VARCHAR(100) NOT NULL,
    rank_name_en VARCHAR(100),
    min_xp INTEGER NOT NULL,
    level_range_start INTEGER NOT NULL,
    level_range_end INTEGER NOT NULL,
    icon_emoji VARCHAR(10)
);

INSERT INTO statedb.rank_definitions (rank_code, rank_name_ko, min_xp, level_range_start, level_range_end, icon_emoji)
VALUES
  ('novice', '견습생', 0, 1, 5, '🌱'),
  ('member', '귀살대 대원', 500, 6, 15, '⚔️'),
  ('elite', '정예 대원', 2000, 16, 30, '🏅'),
  ('pillar_candidate', '주 후보', 5000, 31, 50, '🌟'),
  ('hashira', '주 (柱)', 10000, 51, 99, '💎');

CREATE TABLE statedb.user_equipment (
    user_id UUID PRIMARY KEY REFERENCES statedb.users(user_id),
    sword_status VARCHAR(50) DEFAULT 'good',     -- 'excellent', 'good', 'fair', 'poor'
    uniform_status VARCHAR(50) DEFAULT 'worn',   -- 'worn', 'equipped', 'damaged'
    crow_status VARCHAR(50) DEFAULT 'waiting',   -- 'waiting', 'active', 'absent'
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Phase 2: XP 자동 증가 시스템 (2시간)

```python
# db_manager.py

def award_experience(self, user_id, xp_amount, reason):
    """경험치 지급 및 레벨업 처리"""
    query = """
    WITH updated AS (
      UPDATE statedb.user_progression
      SET experience_points = experience_points + %s,
          level = FLOOR(SQRT(experience_points + %s) / 10) + 1,
          updated_at = NOW()
      WHERE user_id = %s
      RETURNING user_id, experience_points, level
    )
    SELECT * FROM updated
    """
    results = self.execute_query(query, (xp_amount, xp_amount, user_id))
    if results:
        # 레벨업 확인 및 보상 지급 로직
        return results[0]
    return None

def increment_user_stats(self, user_id, stat_name):
    """사용자 통계 증가 (메시지 수, 세션 수 등)"""
    valid_stats = ['total_messages', 'total_sessions', 'total_play_minutes', 'scenarios_completed']
    if stat_name not in valid_stats:
        raise ValueError(f"Invalid stat name: {stat_name}")

    query = f"""
    UPDATE statedb.user_progression
    SET {stat_name} = {stat_name} + 1,
        updated_at = NOW()
    WHERE user_id = %s
    """
    self.execute_query(query, (user_id,))

def get_user_progression(self, user_id):
    """사용자 진행도 조회"""
    query = """
    SELECT
      up.*,
      rd.rank_name_ko,
      rd.icon_emoji AS rank_icon,
      (SELECT min_xp FROM statedb.rank_definitions WHERE min_xp > up.experience_points ORDER BY min_xp LIMIT 1) AS next_rank_xp
    FROM statedb.user_progression up
    LEFT JOIN statedb.rank_definitions rd ON
      up.experience_points >= rd.min_xp AND
      up.level BETWEEN rd.level_range_start AND rd.level_range_end
    WHERE up.user_id = %s
    """
    results = self.execute_query(query, (user_id,))
    return results[0] if results else None
```

#### Phase 3: API 엔드포인트 (1시간)

```python
# api_server.py

@app.get("/api/users/me/progression")
async def get_user_progression(user: Dict = Depends(require_auth)):
    """사용자 진행도/통계 조회"""
    progression = _hybrid_manager.db.get_user_progression(user["user_id"])
    if not progression:
        raise HTTPException(status_code=404, detail="Progression data not found")
    return progression

@app.get("/api/users/me/equipment")
async def get_user_equipment(user: Dict = Depends(require_auth)):
    """사용자 장비 상태 조회"""
    query = "SELECT * FROM statedb.user_equipment WHERE user_id = %s"
    results = _hybrid_manager.db.execute_query(query, (user["user_id"],))
    return results[0] if results else {"sword_status": "good", "uniform_status": "worn", "crow_status": "waiting"}
```

#### Phase 4: Frontend 리팩토링 (1-2시간)

```typescript
// front/src/components/RightSidebar.tsx

const [progression, setProgression] = useState(null)
const [equipment, setEquipment] = useState(null)

useEffect(() => {
  if (isOpen && currentUser) {
    const loadUserData = async () => {
      const [prog, equip] = await Promise.all([
        apiClient.getUserProgression(),
        apiClient.getUserEquipment()
      ])
      setProgression(prog)
      setEquipment(equip)
    }
    loadUserData()
  }
}, [isOpen, currentUser])

// BEFORE: <div>계급: 귀살대 대원</div>
// AFTER:
<div>계급: {progression?.rank_name_ko || '견습생'}</div>
<div>경험치: {progression?.experience_points || 0}/{progression?.next_rank_xp || 500}</div>

// BEFORE: <div>일륜도: 양호</div>
// AFTER:
<div>일륜도: {equipment?.sword_status || '양호'}</div>
```

---

## 5. 우선순위 및 구현 순서 제안

### 5.1 Phase별 작업 계획

#### Phase 1: RightSidebar 동적화 (4-6시간) - **최우선**

**이유**:
- 사용자 경험에 가장 직접적인 영향
- 백엔드 작업량이 상대적으로 적음
- 게임화(Gamification) 요소 추가로 리텐션 향상
- 다른 기능과 독립적 (블로킹 없음)

**작업 순서**:
1. Database schema (012_user_progression.sql)
2. DB Manager 메서드 (get_user_progression, increment_user_stats)
3. API 엔드포인트 (/api/users/me/progression, /api/users/me/equipment)
4. Frontend 리팩토링 (RightSidebar.tsx)
5. 기존 사용자 초기 데이터 생성

**완료 조건**:
- ✅ 사용자별 고유한 계급/경험치 표시
- ✅ 메시지 전송 시 XP 자동 증가
- ✅ 실시간 통계 업데이트

---

#### Phase 2: HomePage 동적화 (6-8시간)

**이유**:
- 첫 인상을 결정하는 랜딩 페이지
- 시나리오 추가/수정이 용이해짐
- 사용자 참여 데이터 수집 시작 (likes, views)
- SEO 개선 가능 (메타데이터 활용)

**작업 순서**:
1. Database schema (011_scenario_metadata.sql)
2. 기존 하드코딩 데이터 마이그레이션 (Initial seeding)
3. DB Manager 메서드 (get_scenarios_with_metadata, record_engagement)
4. API 엔드포인트 개선 (GET /api/scenarios, POST /api/scenarios/{id}/like)
5. Frontend 리팩토링 (HomePage.tsx)

**완료 조건**:
- ✅ 시나리오 카드 동적 로딩
- ✅ 좋아요/조회수 실시간 업데이트
- ✅ 관리자가 DB에서 시나리오 추가/수정 가능

---

#### Phase 3: PaymentModal 동적화 (8-10시간) - **가장 복잡**

**이유**:
- 실제 수익 창출과 직결
- 결제 게이트웨이 연동 필요 (외부 의존성)
- 보안/법적 고려사항 많음
- 가장 많은 테스트 필요

**작업 순서**:
1. Database schema (010_payment_packages.sql)
2. 결제 패키지 초기 데이터 생성
3. DB Manager 메서드 (결제 트랜잭션 관리)
4. API 엔드포인트 (패키지 조회, 결제 시작, 콜백)
5. **토스페이먼츠 연동** (PG사 API)
6. Frontend 리팩토링 (PaymentModal.tsx)
7. 통합 테스트 (테스트 결제 → 버블 지급 → 사용)

**완료 조건**:
- ✅ 결제 패키지 동적 로딩
- ✅ 실제 결제 처리 (테스트 환경)
- ✅ 결제 완료 시 자동 버블 지급
- ✅ 결제 내역 저장

**주의사항**:
- PG사 심사 필요 (영업일 기준 3-5일)
- 사업자 등록 필요
- 통신판매업 신고 필요

---

### 5.2 전체 타임라인 (순차 진행 시)

```
Week 1:
├─ Day 1-2: RightSidebar (Phase 1) ✅
├─ Day 3-4: HomePage (Phase 2) ✅
└─ Day 5:   Documentation & Testing

Week 2:
├─ Day 1-2: PaymentModal Backend (Phase 3-1)
├─ Day 3:   PG Integration (Phase 3-2)
├─ Day 4:   Frontend Refactoring (Phase 3-3)
└─ Day 5:   Testing & Deployment
```

**병렬 진행 가능성**:
- Phase 1 (RightSidebar)과 Phase 2 (HomePage)는 독립적 → 병렬 가능
- Phase 3 (PaymentModal)는 PG사 심사 대기 기간 활용 가능

---

## 6. 즉시 시작 가능한 Quick Win

### Option A: RightSidebar만 먼저 완료 (1-2일)

**장점**:
- 즉각적인 UX 개선
- 게임화 요소로 재방문율 증가
- 다른 작업과 독립적

**구현 범위**:
- 사용자별 계급/XP 시스템
- 메시지 통계 (총 메시지 수, 세션 수)
- 장비 상태 (향후 확장 가능하도록 설계)

---

### Option B: HomePage + RightSidebar 동시 진행 (3-4일)

**장점**:
- 사용자 가시적 변화 극대화
- 시나리오 관리 용이
- 참여 데이터 수집 시작

**구현 범위**:
- Option A의 모든 항목
- 시나리오 메타데이터 시스템
- 좋아요/조회수 기능

---

### Option C: 전체 동적화 (2주)

**장점**:
- 완전한 데이터 중심 아키텍처로 전환
- 관리자 패널 구축 가능
- 실제 수익 창출 시작

**구현 범위**:
- Option B의 모든 항목
- 결제 시스템 완전 통합
- Payment Gateway 연동

---

## 7. 다음 단계 (Next Steps)

현재 버블 시스템 구현 및 문서화가 완료되었습니다. 다음 작업을 진행하기 전에 **사용자(개발자)의 의사 결정**이 필요합니다:

### 결정 사항

1. **우선순위 선택**:
   - [ ] Option A: RightSidebar만 (1-2일)
   - [ ] Option B: HomePage + RightSidebar (3-4일)
   - [ ] Option C: 전체 동적화 (2주)

2. **결제 시스템 시작 시기**:
   - [ ] 지금 당장 (사업자 등록 진행 중이라면)
   - [ ] 1-2주 후 (다른 기능 완성 후)
   - [ ] 나중에 (MVP 검증 후)

3. **PG사 선택** (Phase 3 진행 시):
   - [ ] 토스페이먼츠 (추천)
   - [ ] 카카오페이
   - [ ] PayPal
   - [ ] 여러 개 통합 (시간 더 소요)

4. **작업 방식**:
   - [ ] 순차 진행 (안정적, 느림)
   - [ ] 병렬 진행 (빠름, 리스크 높음)

---

## 8. 예상 비용 및 리소스

### 개발 시간

| Phase | 작업 | 시간 | 비고 |
|-------|------|------|------|
| Phase 1 | RightSidebar | 4-6시간 | 1명 개발자 기준 |
| Phase 2 | HomePage | 6-8시간 | 1명 개발자 기준 |
| Phase 3 | PaymentModal | 8-10시간 | + PG 심사 대기 |
| **총계** | | **18-24시간** | **약 3-4 작업일** |

### 인프라 비용 (Phase 3 진행 시)

- 토스페이먼츠 수수료: 3.3% (일반 신용카드)
- SSL 인증서: 무료 (Let's Encrypt) 또는 월 $10 (유료)
- 사업자 등록: 일회성 비용
- 통신판매업 신고: 일회성 비용

---

## 9. 리스크 및 대응 방안

### Risk #1: PG사 심사 지연

**리스크**: 토스페이먼츠 심사에 1-2주 소요 가능
**대응**: Phase 1, 2를 먼저 완료하고 대기
**완화**: 테스트 환경으로 먼저 구현 완료

### Risk #2: 기존 사용자 데이터 마이그레이션

**리스크**: 19명 기존 사용자의 초기 데이터 생성
**대응**: 마이그레이션 스크립트 사전 작성 및 테스트
**완화**: 롤백 계획 수립

### Risk #3: 결제 오류 시 버블 지급 누락

**리스크**: 결제는 완료되었으나 버블 지급 실패
**대응**: 트랜잭션 로그 기반 수동 복구 프로세스
**완화**: Idempotency key 사용 (중복 방지)

---

## 10. 결론

하드코딩된 데이터를 동적화하면:

**단기 효과**:
- ✅ 관리 효율성 증가 (코드 수정 없이 데이터 변경)
- ✅ 사용자 경험 개선 (개인화된 통계 표시)
- ✅ 개발 속도 향상 (신규 시나리오 추가 용이)

**장기 효과**:
- ✅ 수익 창출 시작 (결제 시스템)
- ✅ 데이터 기반 의사결정 (사용자 참여 분석)
- ✅ 관리자 패널 구축 기반 마련

**권장 사항**: **Option B (HomePage + RightSidebar)**를 먼저 완료하여 즉각적인 사용자 가치를 제공하고, 사업자 등록 진행 상황에 맞춰 Phase 3 (PaymentModal)를 순차적으로 진행하는 것을 추천합니다.

---

**다음 문서**: 선택된 Phase의 상세 구현 가이드 작성 예정
**관련 문서**:
- [44_bubble_system_implementation.md](./44_bubble_system_implementation.md)
- [43_issue_resolution_session_summary.md](./43_issue_resolution_session_summary.md)
