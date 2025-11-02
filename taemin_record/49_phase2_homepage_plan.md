# Phase 2: HomePage Dynamicization - Implementation Plan

**Project**: Scenario Management System - Full-Stack Integration
**Phase**: 2 of 2 (HomePage Scenarios)
**Date**: 2025-11-02
**Status**: 📋 **PLANNING**

---

## Executive Summary

Phase 2 will transform the HomePage component from displaying hardcoded scenario data to dynamically loading scenario information from the backend API. This will enable:

- ✅ Dynamic scenario management (add/edit/remove without code changes)
- ✅ Real-time statistics (likes, comments, views)
- ✅ User-specific progress tracking per scenario
- ✅ Filtering, sorting, and search capabilities
- ✅ Scalable content management

---

## Current State Analysis

### Hardcoded Data Location

**File**: [front/src/pages/HomePage.tsx](../front/src/pages/HomePage.tsx#L30-L103)

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
  // ... 5 more scenarios (train, infinity-castle, ending, counseling, idol)
]
```

### Current CharacterCard Interface

```typescript
interface CharacterCard {
  id: string;
  title: string;
  description: string;
  image: string;
  likes: number;
  comments: number;
  views: number;
  tags: string[];
  size: 'large' | 'normal';
  link: string;
}
```

### Current Functionality

1. **Display**: 6 scenario cards in carousel/grid
2. **Search**: Filter scenarios by title/description/tags
3. **Interaction**: Like button (client-side only, not persisted)
4. **Navigation**: Click to navigate to scenario

### Problems with Current Implementation

❌ **Static Content**: Cannot add new scenarios without code deployment
❌ **Fake Stats**: likes/comments/views are hardcoded numbers
❌ **No User Data**: Cannot track which scenarios user completed
❌ **No Persistence**: Likes don't save to database
❌ **No Admin Tools**: Need developer to modify scenario list

---

## Phase 2 Goals

### Primary Objectives

1. **Database Schema**: Store scenario metadata in PostgreSQL
2. **API Endpoints**: CRUD operations for scenarios
3. **Frontend Integration**: Fetch scenarios dynamically on HomePage
4. **User Progress**: Track user completion/progress per scenario
5. **Statistics**: Real likes/comments/views from database

### Success Criteria

✅ HomePage loads scenarios from API (not hardcoded array)
✅ New scenarios can be added via database (no code change)
✅ User can see completion status per scenario
✅ Likes/views persist to database
✅ Search/filter works with API data
✅ E2E test passes

---

## Phase 2 Task Breakdown

### Phase 2.1: Database Schema Design 🗂️

**Goal**: Create tables for scenario metadata and user progress

**Tables to Create**:

1. **`scenarios`** (Main scenario metadata)
```sql
CREATE TABLE statedb.scenarios (
    scenario_id VARCHAR(50) PRIMARY KEY,  -- e.g., 'tanjiro', 'train'
    title VARCHAR(200) NOT NULL,
    description TEXT,
    image_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    tags TEXT[],  -- Array of tags
    card_size VARCHAR(20) DEFAULT 'normal',  -- 'large' or 'normal'
    route_path VARCHAR(200),  -- e.g., '/chat/tanjiro'
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

2. **`scenario_statistics`** (Aggregated stats)
```sql
CREATE TABLE statedb.scenario_statistics (
    scenario_id VARCHAR(50) PRIMARY KEY REFERENCES statedb.scenarios(scenario_id),
    total_likes INT DEFAULT 0,
    total_comments INT DEFAULT 0,
    total_views INT DEFAULT 0,
    total_completions INT DEFAULT 0,
    avg_session_duration INT DEFAULT 0,  -- minutes
    updated_at TIMESTAMP DEFAULT NOW()
);
```

3. **`user_scenario_progress`** (User-specific progress)
```sql
CREATE TABLE statedb.user_scenario_progress (
    user_id UUID REFERENCES statedb.users(user_id),
    scenario_id VARCHAR(50) REFERENCES statedb.scenarios(scenario_id),
    has_started BOOLEAN DEFAULT false,
    has_completed BOOLEAN DEFAULT false,
    completion_percentage INT DEFAULT 0,
    last_session_id VARCHAR(100),
    last_played_at TIMESTAMP,
    total_messages INT DEFAULT 0,
    total_play_time INT DEFAULT 0,  -- minutes
    is_liked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, scenario_id)
);
```

4. **`scenario_views`** (View tracking)
```sql
CREATE TABLE statedb.scenario_views (
    view_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id VARCHAR(50) REFERENCES statedb.scenarios(scenario_id),
    user_id UUID REFERENCES statedb.users(user_id),  -- NULL for anonymous
    viewed_at TIMESTAMP DEFAULT NOW()
);
```

**View**: Combine data for frontend
```sql
CREATE VIEW statedb.v_scenario_cards AS
SELECT
    s.scenario_id,
    s.title,
    s.description,
    s.image_url,
    s.tags,
    s.card_size,
    s.route_path,
    s.display_order,
    COALESCE(ss.total_likes, 0) as likes,
    COALESCE(ss.total_comments, 0) as comments,
    COALESCE(ss.total_views, 0) as views,
    s.is_active
FROM statedb.scenarios s
LEFT JOIN statedb.scenario_statistics ss ON s.scenario_id = ss.scenario_id
WHERE s.is_active = true
ORDER BY s.display_order, s.created_at DESC;
```

**Migration File**: `backend/database/migrations/013_scenarios_system.sql`

---

### Phase 2.2: Seed Existing Scenarios 🌱

**Goal**: Populate database with current 6 scenarios

**Seed Script**: `backend/scripts/seed_scenarios.py`

```python
scenarios = [
    {
        'scenario_id': 'tanjiro',
        'title': '편의점 알바생 탄지로',
        'description': '탄지로와 함께하는 편의점 일상 체험',
        'image_url': '/images/편의점탄지로.png',
        'tags': ['편의점', '일상', '탄지로'],
        'card_size': 'normal',
        'route_path': '/chat/tanjiro',
        'display_order': 1
    },
    # ... 5 more scenarios
]

# Insert into database with statistics
for scenario in scenarios:
    db.insert_scenario(scenario)
    db.initialize_scenario_statistics(scenario['scenario_id'])
```

**Initial Statistics**:
- Use current hardcoded values as baseline
- Later, real user interactions will update these

---

### Phase 2.3: DB Manager Methods 🔧

**Goal**: Add Python methods for scenario CRUD operations

**File**: `backend/src/database/db_manager.py`

**Methods to Add**:

```python
# Scenario CRUD
def get_all_scenarios(self, include_inactive: bool = False) -> List[Dict]
def get_scenario_by_id(self, scenario_id: str) -> Optional[Dict]
def create_scenario(self, scenario_data: Dict) -> bool
def update_scenario(self, scenario_id: str, updates: Dict) -> bool
def delete_scenario(self, scenario_id: str) -> bool  # Soft delete (set is_active=false)

# Statistics
def get_scenario_statistics(self, scenario_id: str) -> Dict
def increment_scenario_views(self, scenario_id: str, user_id: Optional[str] = None) -> bool
def increment_scenario_likes(self, scenario_id: str) -> bool
def decrement_scenario_likes(self, scenario_id: str) -> bool

# User Progress
def get_user_scenario_progress(self, user_id: str, scenario_id: str) -> Optional[Dict]
def get_all_user_progress(self, user_id: str) -> List[Dict]
def update_user_progress(self, user_id: str, scenario_id: str, progress_data: Dict) -> bool
def toggle_user_like(self, user_id: str, scenario_id: str) -> bool  # Like/Unlike

# Combined View
def get_scenarios_with_stats(self, user_id: Optional[str] = None) -> List[Dict]
    """
    Returns scenarios with stats, optionally including user-specific progress
    If user_id provided, includes: has_completed, is_liked, completion_percentage
    """
```

**Estimated**: ~300 lines of code

---

### Phase 2.4: API Endpoints 🌐

**Goal**: Create REST API for scenario operations

**File**: `backend/api_server.py`

**Endpoints to Add**:

```python
# Public Endpoints (no auth required)
@app.get("/api/scenarios")
async def get_scenarios(include_inactive: bool = False):
    """
    Get all scenarios with statistics
    Query params:
        - include_inactive: bool (default: false)
    Returns: List[ScenarioCard]
    """

@app.get("/api/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    """
    Get single scenario details
    Returns: ScenarioCard with full details
    """

@app.post("/api/scenarios/{scenario_id}/view")
async def record_view(scenario_id: str, user: Optional[Dict] = Depends(optional_auth)):
    """
    Record a scenario view (increments view count)
    Auth: Optional (tracks user if logged in)
    """

# Authenticated Endpoints
@app.get("/api/users/me/scenarios")
async def get_user_scenarios(user: Dict = Depends(require_auth)):
    """
    Get scenarios with user-specific progress
    Returns: List[ScenarioCard + UserProgress]
    """

@app.post("/api/users/me/scenarios/{scenario_id}/like")
async def toggle_like(scenario_id: str, user: Dict = Depends(require_auth)):
    """
    Toggle like for a scenario
    Returns: { liked: bool, new_like_count: int }
    """

@app.get("/api/users/me/scenarios/{scenario_id}/progress")
async def get_progress(scenario_id: str, user: Dict = Depends(require_auth)):
    """
    Get user progress for specific scenario
    Returns: UserScenarioProgress
    """

@app.put("/api/users/me/scenarios/{scenario_id}/progress")
async def update_progress(
    scenario_id: str,
    progress_data: Dict,
    user: Dict = Depends(require_auth)
):
    """
    Update user progress (e.g., after completing session)
    Body: { completion_percentage, has_completed, ... }
    """

# Admin Endpoints (future - Phase 2 optional)
@app.post("/api/admin/scenarios")
async def create_scenario(scenario_data: Dict, user: Dict = Depends(require_admin)):
    """Create new scenario (admin only)"""

@app.put("/api/admin/scenarios/{scenario_id}")
async def update_scenario(scenario_id: str, updates: Dict, user: Dict = Depends(require_admin)):
    """Update scenario (admin only)"""

@app.delete("/api/admin/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: str, user: Dict = Depends(require_admin)):
    """Soft delete scenario (admin only)"""
```

**Estimated**: ~250 lines of code

---

### Phase 2.5: Frontend API Client & HomePage Update 💻

**Goal**: Update frontend to use dynamic API data

#### Part A: API Client Methods

**File**: `front/src/services/api.ts`

**Interfaces**:
```typescript
export interface ScenarioCard {
  scenario_id: string
  title: string
  description: string
  image_url: string
  tags: string[]
  card_size: 'large' | 'normal'
  route_path: string
  likes: number
  comments: number
  views: number
  // User-specific (if authenticated)
  is_liked?: boolean
  has_completed?: boolean
  completion_percentage?: number
}

export interface UserScenarioProgress {
  scenario_id: string
  has_started: boolean
  has_completed: boolean
  completion_percentage: number
  last_played_at?: string
  total_messages: number
  total_play_time: number
  is_liked: boolean
}
```

**Methods**:
```typescript
async getScenarios(): Promise<ScenarioCard[]>
async getScenario(scenarioId: string): Promise<ScenarioCard>
async recordView(scenarioId: string): Promise<void>
async getUserScenarios(): Promise<ScenarioCard[]>  // With user progress
async toggleLike(scenarioId: string): Promise<{ liked: boolean, new_like_count: number }>
async getUserProgress(scenarioId: string): Promise<UserScenarioProgress>
async updateUserProgress(scenarioId: string, progress: Partial<UserScenarioProgress>): Promise<void>
```

#### Part B: HomePage Component Update

**File**: `front/src/pages/HomePage.tsx`

**Changes**:

1. **Remove Hardcoded Array** (lines 30-103)
```typescript
// BEFORE
const characters: CharacterCard[] = [ ... ]  // ❌ Delete this

// AFTER
const [scenarios, setScenarios] = useState<ScenarioCard[]>([])
const [loading, setLoading] = useState(true)
const [error, setError] = useState<string | null>(null)
```

2. **Add Data Loading**
```typescript
useEffect(() => {
  const loadScenarios = async () => {
    setLoading(true)
    try {
      const data = currentUser
        ? await apiClient.getUserScenarios()  // With progress
        : await apiClient.getScenarios()  // Public
      setScenarios(data)
    } catch (err) {
      setError('시나리오를 불러올 수 없습니다')
    } finally {
      setLoading(false)
    }
  }
  loadScenarios()
}, [currentUser])
```

3. **Update Like Handler**
```typescript
const handleLike = async (scenarioId: string) => {
  if (!currentUser) {
    // Show login modal
    return
  }

  try {
    const result = await apiClient.toggleLike(scenarioId)
    // Update local state
    setScenarios(prev => prev.map(s =>
      s.scenario_id === scenarioId
        ? { ...s, is_liked: result.liked, likes: result.new_like_count }
        : s
    ))
  } catch (err) {
    console.error('Failed to toggle like:', err)
  }
}
```

4. **Add Loading/Error States**
```tsx
if (loading) {
  return <LoadingSpinner message="시나리오 불러오는 중..." />
}

if (error) {
  return <ErrorMessage message={error} onRetry={loadScenarios} />
}
```

5. **Update Interface Mapping**
```typescript
// Map API response to component format
const characterCards: CharacterCard[] = scenarios.map(s => ({
  id: s.scenario_id,
  title: s.title,
  description: s.description,
  image: s.image_url,
  likes: s.likes,
  comments: s.comments,
  views: s.views,
  tags: s.tags.map(tag => `#${tag}`),
  size: s.card_size,
  link: s.route_path
}))
```

**Estimated**: ~150 lines changed

---

### Phase 2.6: E2E Testing 🧪

**Goal**: Comprehensive testing of scenario system

**Test File**: `backend/test_scenarios_e2e.py`

**Test Scenarios**:

1. **Public API Tests**
   - GET /api/scenarios (anonymous user)
   - GET /api/scenarios/{id}
   - POST /api/scenarios/{id}/view

2. **Authenticated API Tests**
   - GET /api/users/me/scenarios (with progress)
   - POST /api/users/me/scenarios/{id}/like
   - GET /api/users/me/scenarios/{id}/progress

3. **Frontend Integration Tests**
   - HomePage loads scenarios
   - Search/filter works
   - Like button persists
   - View count increments

4. **Data Consistency Tests**
   - Scenario statistics match database
   - User progress tracks correctly
   - Likes increment/decrement properly

**Estimated**: ~400 lines of code

---

### Phase 2.7: Documentation 📖

**Goal**: Complete documentation for Phase 2

**Documents to Create**:

1. **50_phase2_scenarios_backend_complete.md**
   - Database schema details
   - API endpoints documentation
   - DB Manager methods reference

2. **51_phase2_scenarios_frontend_complete.md**
   - Frontend integration guide
   - Component changes
   - API client usage

3. **52_phase2_complete_summary.md**
   - Full Phase 2 summary
   - Before/after comparison
   - E2E test results
   - Next steps

---

## Data Flow Architecture

### Public User (Not Logged In)

```
HomePage.tsx useEffect
       ↓
apiClient.getScenarios()
       ↓
GET /api/scenarios
       ↓
db.get_scenarios_with_stats(user_id=None)
       ↓
SELECT * FROM v_scenario_cards
       ↓
Returns: List[{ scenario_id, title, ..., likes, views }]
       ↓
HomePage displays scenario cards
```

### Authenticated User

```
HomePage.tsx useEffect
       ↓
apiClient.getUserScenarios()
       ↓
GET /api/users/me/scenarios (JWT auth)
       ↓
db.get_scenarios_with_stats(user_id=current_user)
       ↓
Joins: scenarios + statistics + user_scenario_progress
       ↓
Returns: List[{ ..., is_liked, has_completed, completion_% }]
       ↓
HomePage displays personalized cards with progress
```

### Like Action

```
User clicks Like button
       ↓
apiClient.toggleLike(scenario_id)
       ↓
POST /api/users/me/scenarios/{id}/like (JWT auth)
       ↓
db.toggle_user_like(user_id, scenario_id)
       ↓
Updates: user_scenario_progress.is_liked
Increments/Decrements: scenario_statistics.total_likes
       ↓
Returns: { liked: true, new_like_count: 122 }
       ↓
HomePage updates local state (optimistic UI)
```

---

## Migration from Hardcoded to Dynamic

### Before (Current)

```typescript
// HomePage.tsx
const characters = [
  { id: 'tanjiro', title: '...',likes: 121, ... },  // ❌ Hardcoded
  { id: 'train', title: '...', likes: 98, ... },
  // ...
]
```

**Problems**:
- Need code deployment to add scenario
- Stats (likes/views) never change
- No user-specific data

### After (Phase 2)

```typescript
// HomePage.tsx
useEffect(() => {
  const data = await apiClient.getUserScenarios()  // ✅ API call
  setScenarios(data)
}, [])

// scenarios = [
//   { scenario_id: 'tanjiro', likes: 245, is_liked: true, ... },  // ✅ Real data
//   { scenario_id: 'train', likes: 183, has_completed: true, ... },
// ]
```

**Benefits**:
- Add scenarios via database (no deployment)
- Real-time statistics
- User-specific progress tracking
- Scalable content management

---

## Timeline Estimate

| Phase | Tasks | Est. Time | Status |
|-------|-------|-----------|--------|
| 2.0 | Analysis & Planning | 1 hour | ✅ Current |
| 2.1 | Database Schema | 2 hours | ⏳ Pending |
| 2.2 | Seed Scenarios | 1 hour | ⏳ Pending |
| 2.3 | DB Manager Methods | 3 hours | ⏳ Pending |
| 2.4 | API Endpoints | 2 hours | ⏳ Pending |
| 2.5 | Frontend Integration | 2 hours | ⏳ Pending |
| 2.6 | E2E Testing | 2 hours | ⏳ Pending |
| 2.7 | Documentation | 1 hour | ⏳ Pending |
| **Total** | **8 phases** | **~14 hours** | **0% complete** |

---

## Risk Assessment

### Low Risk ✅

- Database schema (straightforward tables)
- API endpoints (similar to Phase 1)
- Frontend fetch logic (standard pattern)

### Medium Risk ⚠️

- Data migration (moving hardcoded → database)
- Statistics calculation (ensuring accuracy)
- Search functionality (must work with new API)

### Mitigation Strategies

1. **Careful Seeding**: Validate all 6 scenarios before seeding
2. **Incremental Testing**: Test each phase before moving to next
3. **Backwards Compatibility**: Keep hardcoded data until API verified
4. **E2E Coverage**: Comprehensive tests for all scenarios

---

## Success Metrics

### Phase 2 Complete When:

✅ Database has all 6 scenarios with statistics
✅ API endpoints return correct scenario data
✅ HomePage loads scenarios from API (not hardcoded)
✅ Authenticated users see personalized data
✅ Likes/views persist to database
✅ Search/filter works with API data
✅ E2E tests passing (all scenarios)
✅ Documentation complete

---

## Next Steps

**Immediate**:
- Phase 2.1: Design and create database schema
- Create migration file: `013_scenarios_system.sql`

**Following**:
- Phase 2.2: Write seed script
- Phase 2.3: Implement DB Manager methods

**User Approval Needed**:
- Review schema design
- Confirm which fields to track
- Decide on admin features (optional)

---

**Phase 2 Status**: 📋 **PLANNING COMPLETE**
**Ready to Begin**: Phase 2.1 - Database Schema
**Estimated Completion**: All phases (~14 hours total work)
