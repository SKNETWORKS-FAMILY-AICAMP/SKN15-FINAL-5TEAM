# Phase 1.8: E2E Testing Bug Discovery

**Date**: 2025-11-02
**Status**: 🐛 **CRITICAL BUG FOUND**
**Priority**: **HIGH** - Blocks RightSidebar functionality

---

## Executive Summary

During Phase 1.8 End-to-End testing of the User Progression System, a **critical bug was discovered**: newly registered users do not have progression records initialized, causing the `/api/users/me/progression` endpoint to fail with **500 Internal Server Error**.

---

## Test Execution

### Test Script Created
- **File**: `backend/test_progression_e2e.py`
- **Purpose**: Comprehensive E2E test for progression system
- **Flow**:
  1. Register new user
  2. Login to get JWT token
  3. Call `/api/users/me/progression`
  4. Validate response schema
  5. Verify initial values

### Test Result

```
🎮 User Progression System E2E Test

======================================================================
  1️⃣  User Registration & Login
======================================================================
✅ Registration success
✅ Login success

======================================================================
  2️⃣  Get User Progression
======================================================================
❌ Request failed:
  Status: 500
  Response: Internal Server Error

❌ Test failed at get progression - aborting
```

---

## Bug Analysis

### Root Cause

**Registration Endpoint** ([api_server.py:522-603](api_server.py#L522-L603))

The `/api/auth/register` endpoint:
1. ✅ Creates user in `statedb.users` table
2. ✅ Generates JWT tokens
3. ❌ **DOES NOT initialize progression records**

```python
# Current code (api_server.py:561-566)
user_id = _hybrid_manager.db.create_user(
    username=req.username,
    password_hash=password_hash,
    email=req.email,
    display_name=req.display_name or req.username
)

# Missing: Progression initialization!
# _hybrid_manager.db.initialize_user_progression(user_id)  # <- NOT CALLED
```

### Database Impact

**Missing Records**:

When a new user registers, these tables remain empty:

| Table | Missing Record | Impact |
|-------|---------------|---------|
| `user_progression_ranks` | Initial rank (trainee, level 1, 0 XP) | User has no rank/level/XP |
| `user_progression_stats` | Initial stats (0 messages, 0 sessions) | User has no activity stats |
| `user_progression_equipment` | Initial equipment (all "waiting") | User has no equipment status |

**View Failure**:

The API endpoint queries:
```sql
SELECT * FROM statedb.v_user_progression_summary WHERE user_id = %s
```

The view `v_user_progression_summary` joins all 3 tables:
- `user_progression_ranks` (via INNER JOIN)
- `user_progression_stats` (via LEFT JOIN)
- `user_progression_equipment` (via LEFT JOIN)

**Result**: Since `user_progression_ranks` has no record, the INNER JOIN returns **NO ROWS**.

### API Endpoint Behavior

[api_server.py:733-759](api_server.py#L733-L759):

```python
@app.get("/api/users/me/progression")
async def get_user_progression(user: Dict = Depends(require_auth)):
    progression = _hybrid_manager.db.get_user_progression(user["user_id"])
    if not progression:
        raise HTTPException(status_code=404, detail="Progression data not found")
    return progression
```

**Expected**: Should return 404 if no progression data
**Actual**: Returns 500 (likely an exception in `get_user_progression`)

---

## Impact Assessment

### Critical Issues

1. **🚨 RightSidebar Cannot Load Data**
   - Frontend calls `/api/users/me/progression` when sidebar opens
   - Gets 500 error instead of data
   - User sees error message: "진행도 데이터를 불러올 수 없습니다"

2. **🚨 All New Users Affected**
   - Every user registered after Phase 1 implementation is affected
   - Existing users (if any) may already have progression records from other sources

3. **🚨 Cascading Failures**
   - `/api/users/me/progression` → 500 Error
   - `/api/users/me/equipment` → Likely fails too
   - `/api/users/me/xp-transactions` → Returns empty (no XP awarded yet)
   - `/api/leaderboard` → May exclude new users

### What Works

✅ User registration (creates user account)
✅ User login (JWT token generation)
✅ Authentication (JWT validation)
✅ Database schema (tables, views, functions exist)
✅ API endpoint routing (endpoints are defined)

### What's Broken

❌ Progression data initialization
❌ GET `/api/users/me/progression` for new users
❌ RightSidebar data loading for new users
❌ User rank/level/XP display
❌ Equipment status display

---

## Fix Required

### 1. Create DB Method: `initialize_user_progression()`

**Location**: `backend/src/database/db_manager.py`

**Method Signature**:
```python
def initialize_user_progression(self, user_id: str) -> bool:
    """신규 사용자 진행도 초기화

    Args:
        user_id: 사용자 UUID

    Returns:
        bool: 성공 여부
    """
```

**Required Inserts**:

1. **user_progression_ranks**:
```sql
INSERT INTO statedb.user_progression_ranks (user_id, rank_code, level, experience_points)
VALUES (%s, 'trainee', 1, 0);
```

2. **user_progression_stats**:
```sql
INSERT INTO statedb.user_progression_stats (user_id, total_messages, total_sessions, total_play_minutes)
VALUES (%s, 0, 0, 0);
```

3. **user_progression_equipment**:
```sql
INSERT INTO statedb.user_progression_equipment (user_id, sword_status, uniform_status, crow_status)
VALUES (%s, 'waiting', 'waiting', 'waiting');
```

### 2. Update Registration Endpoint

**Location**: [api_server.py:561-566](api_server.py#L561-L566)

**Change**:
```python
# Current
user_id = _hybrid_manager.db.create_user(
    username=req.username,
    password_hash=password_hash,
    email=req.email,
    display_name=req.display_name or req.username
)

# After Fix
user_id = _hybrid_manager.db.create_user(
    username=req.username,
    password_hash=password_hash,
    email=req.email,
    display_name=req.display_name or req.username
)

# NEW: Initialize progression for new user
if user_id:
    _hybrid_manager.db.initialize_user_progression(user_id)
```

### 3. Re-run E2E Test

After implementing the fix, re-run `test_progression_e2e.py` to verify:

**Expected Result**:
```
✅ User Registration & Login: PASSED
✅ Get Progression API: PASSED
✅ Schema Validation: PASSED
✅ Initial Values: PASSED

🎯 Integration Test Result:
  ✅ RightSidebar frontend integration ready
```

---

## Files Affected

### Modified Files (To Fix Bug)
1. **`backend/src/database/db_manager.py`**
   - Add: `initialize_user_progression()` method (~30 lines)

2. **`backend/api_server.py`**
   - Modify: Registration endpoint (add 2 lines)

### Test Files
1. **`backend/test_progression_e2e.py`** (Already created ✅)
   - Comprehensive E2E test
   - 283 lines
   - Tests registration → login → progression fetch → validation

---

## Next Steps

### Phase 1.8.1: Implement DB Method ⏳ PENDING
- [backend/src/database/db_manager.py](../backend/src/database/db_manager.py)
- Add `initialize_user_progression()` method
- Handle transaction rollback on failure

### Phase 1.8.2: Update Registration Endpoint ⏳ PENDING
- [backend/api_server.py](../backend/api_server.py#L561-L566)
- Call `initialize_user_progression()` after user creation
- Handle initialization failure gracefully

### Phase 1.8.3: Re-Run E2E Test ⏳ PENDING
- Execute `python backend/test_progression_e2e.py`
- Verify all tests pass
- Document test results

### Phase 1.9: Final Documentation ⏳ PENDING
- Complete Phase 1 summary document
- Include bug fix details
- Mark Phase 1 as COMPLETE

---

## Lessons Learned

1. **E2E Testing is Critical**: Unit tests alone don't catch integration issues
2. **Initialization Logic**: Always initialize related records when creating parent entities
3. **Database Views**: INNER JOINs require all tables to have matching records
4. **Error Handling**: 500 errors are harder to debug than explicit 404s with clear messages

---

## Related Documents

- [46_phase1_rightsidebar_backend_complete.md](46_phase1_rightsidebar_backend_complete.md) - Backend implementation
- [Database schema: 012_user_progression.sql](../backend/database/migrations/012_user_progression.sql)
- [E2E test: test_progression_e2e.py](../backend/test_progression_e2e.py)

---

**Status**: 🔧 **FIX IN PROGRESS**
**Assigned To**: Next phase (Phase 1.8.1-1.8.3)
**Priority**: **P0** (Critical - Blocks feature)
