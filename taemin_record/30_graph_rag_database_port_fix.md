# Graph RAG System - Database Port Configuration Fix

**Date**: 2025-10-31
**Issue**: Entity extraction working but entities not being saved
**Root Cause**: Wrong database port in `.env.local`

## Problem Summary

After implementing the complete Graph RAG system (Phase 0-8), entity extraction was working but entities were not being saved to the database. The error message was:

```
Database error: relation "statedb.entities" does not exist
LINE 2:                   INSERT INTO statedb.entities (
```

This was confusing because:
- The `statedb.entities` table clearly existed in the database
- Manual testing of `DatabaseManager.save_entity()` worked perfectly
- The search_path was configured correctly
- All migrations had run successfully

## Investigation Process

### 1. Initial Debugging
- Verified entities table exists: ✅
- Verified migrations ran: ✅
- Added search_path configuration: Still failing ❌
- Restarted server multiple times: Still failing ❌

### 2. Direct Testing
Created test script that directly instantiated `DatabaseManager` with the same parameters:
```python
db = DatabaseManager(
    host="localhost",
    port=5433,
    dbname="kimedb",
    user="kime",
    password="dev123"
)
entity_id = db.save_entity(...)  # ✅ SUCCESS!
```

This proved `DatabaseManager` was working correctly outside the server context.

### 3. Debug Logging
Added debug logging to `TrainingLogger` to print actual connection parameters:

```python
print(f"[TrainingLogger DEBUG] DB connection: {db_user}@{db_host}:{db_port}/{db_name}")
```

Output revealed:
```
[TrainingLogger DEBUG] DB connection: kime@127.0.0.1:5432/kimedb
```

**Port 5432 instead of 5433!** This was connecting to a completely different database instance.

### 4. Root Cause Found

Searched for where `DB_PORT` was defined:
```bash
$ grep -r "DB_PORT" backend/.env*
backend/.env.local:DB_PORT=5432  # ❌ WRONG PORT
```

The `.env.local` file had `DB_PORT=5432` (standard PostgreSQL port), but our Docker database was running on `DB_PORT=5433`.

## Solution

Changed [.env.local](../backend/.env.local):
```bash
# BEFORE
DB_PORT=5432  # ❌

# AFTER
DB_PORT=5433  # ✅
```

## Verification

After fixing the port and restarting the server:

1. **Entity extraction**: ✅ Working
   ```
   [TrainingLogger] Processed 3 entities for log 67
   ```

2. **Entities saved**: ✅ Working
   ```sql
   SELECT COUNT(*) FROM statedb.entities;
   -- Result: 8 entities
   ```

3. **Entity mentions created**: ✅ Working
   ```sql
   SELECT COUNT(*) FROM statedb.entity_mentions;
   -- Result: 12 mentions
   ```

4. **Training logs updated**: ✅ Working
   ```sql
   SELECT mentioned_entity_ids, embedding IS NOT NULL
   FROM training_logs
   ORDER BY id DESC LIMIT 3;

   -- Results:
   -- {1,2,3}, true
   -- {1,2,3}, true
   -- {1,2,3}, true
   ```

## Key Files Changed

1. [backend/.env.local](../backend/.env.local)
   - Changed `DB_PORT=5432` to `DB_PORT=5433`

2. [backend/src/database/db_manager.py](../backend/src/database/db_manager.py#L70-L72)
   - Already had search_path configuration (helpful but not the root cause)

3. [backend/src/tools/training_logger.py](../backend/src/tools/training_logger.py#L86-L97)
   - Removed debug logging after fix confirmed

## Lessons Learned

1. **Environment variable precedence matters**: `.env.local` was overriding expected defaults
2. **Debug logging is invaluable**: Adding connection parameter logging immediately revealed the issue
3. **Direct testing isolates problems**: Testing `DatabaseManager` directly proved it wasn't a code issue
4. **Error messages can be misleading**: "relation does not exist" didn't mean the table was missing, but that we were connected to the wrong database entirely

## Current Status

✅ **Graph RAG System Fully Operational**

- Entity extraction: Rule 60% + LLM 40%
- Relationship extraction: Co-occurrence 60% + Rule 20% + LLM 20%
- Embeddings: text-embedding-3-small (1536 dimensions)
- Vector search: IVFFlat index with cosine distance
- Graph traversal: Bidirectional relationship queries
- Auto-labeling: Ready for Rule 30% + LLM 30% + Graph 40%

All components integrated and working end-to-end.
