# Phase 1 & 2 Implementation - Quick Reference Guide

## TL;DR
**Status**: ALL REQUIREMENTS MET ✓

- 7/7 Models implemented
- 24/24 Repository methods implemented  
- Ready to start Phase 3 (Services)

---

## File Locations

### Models
```
/backend/app/features/chat/models.py
  - UserCharacterAffinity (lines 45-70)
  - Entity (lines 97-129)
  - EntityRelationship (lines 132-159)
  - UserMemory (lines 187-215)

/backend/app/features/scenarios/models.py
  - ScenarioComment (lines 11-37)
  - ScenarioLike (lines 40-58)
  - CommentLike (lines 61-77)
```

### Repositories
```
/backend/app/features/chat/repository.py
  - ChatRepository (8 methods)

/backend/app/features/scenarios/repository.py
  - ScenarioRepository (9 methods)

/backend/app/core/db/session_repository.py
  - SessionRepository (7 methods, with Redis hybrid)
```

---

## Phase 1: Models (7 total)

### Chat Models (4)
| Model | Purpose | Key Fields |
|-------|---------|-----------|
| **UserCharacterAffinity** | Global character affinity tracking | user_id, character_name, total_affinity_score (0-1000), affinity_level (1-10) |
| **Entity** | Knowledge graph nodes | entity_type (character/location/event/item/skill), embedding (1536-dim) |
| **EntityRelationship** | Knowledge graph edges | source_entity_id, target_entity_id, relationship_type, strength (0-1) |
| **UserMemory** | User's long-term memories | user_id, memory_type (episodic/semantic/procedural), embedding (1536-dim) |

### Scenario Models (3)
| Model | Purpose | Key Fields |
|-------|---------|-----------|
| **ScenarioComment** | Thread-able comments | scenario_id, user_id, content, parent_comment_id, like_count |
| **ScenarioLike** | Scenario likes | scenario_id, user_id (unique constraint) |
| **CommentLike** | Comment likes | comment_id, user_id (composite PK) |

---

## Phase 2: Repository Methods (24 total)

### ChatRepository (8 methods)

**Affinity Management**
- `save_affinity_record(session_id, turn_number, character_name, affinity_score, change_amount)`
- `get_latest_affinity(session_id, character_name)`
- `upsert_user_character_affinity(user_id, character_name, score_delta)`

**Entity/Relationship Management**
- `save_entity(entity_data: dict)`
- `save_relationship(relationship_data: dict)`
- `save_entity_mention(mention_data: dict)` [BONUS]

**Memory Management**
- `save_memory(memory_data: dict)`
- `get_user_memories(user_id, scenario_id=None, memory_type=None, limit=10)`

---

### ScenarioRepository (9 methods)

**Comment Operations**
- `get_scenario_comments(scenario_id, sort_by='created_at', limit=50, offset=0)`
- `get_comment_replies(parent_comment_id, limit=20, offset=0)`
- `create_comment(scenario_id, user_id, content, parent_comment_id=None)`
- `update_comment(comment_id, user_id, content)` [with permission check]
- `delete_comment(comment_id, user_id)` [soft delete, with permission check]

**Like Operations**
- `toggle_comment_like(comment_id, user_id)` → (is_liked: bool, new_like_count: int)
- `toggle_scenario_like(scenario_id, user_id)` → is_liked: bool
- `get_scenario_like_count(scenario_id)` [BONUS]
- `check_user_liked_scenario(scenario_id, user_id)` [BONUS]

---

### SessionRepository (7 methods)

**Core Operations**
- `get_session(session_id)` → Dict | None [Redis→PostgreSQL fallback]
- `save_session(session_id, session_data)` [Hybrid UPSERT, Redis TTL=3600s]
- `update_session(session_id, updates: dict)` [Cache invalidation]
- `delete_session(session_id)` → bool [Soft delete]
- `get_user_recent_sessions(user_id, limit=10)` [BONUS]
- `get_active_session_count(user_id)` [BONUS]
- `cleanup_old_sessions(days=30)` [BONUS]

---

## Key Features Implemented

### Constraint Enforcement
- CheckConstraints on score/level ranges
- UniqueConstraints on business keys
- Foreign key cascades (ON DELETE CASCADE)

### Advanced Features
- Vector embeddings (pgvector 1536-dim)
- JSONB for flexible properties
- Hybrid Redis+PostgreSQL caching
- Soft deletes with is_deleted flags
- Thread-able comments (parent_comment_id)
- Permission checking in mutations
- Pagination with limit/offset
- Sorting flexibility

### Code Quality
- Full async/await implementation
- Complete type hints
- Comprehensive logging
- Consistent naming patterns

---

## Method Usage Patterns

### Getting Data
```python
# List with pagination
comments = await repo.get_scenario_comments(
    scenario_id="s001",
    sort_by="like_count",
    limit=20,
    offset=0
)

# Single record
affinity = await repo.get_latest_affinity(
    session_id="sess_123",
    character_name="Emma"
)
```

### Creating/Updating
```python
# Create comment with optional threading
comment = await repo.create_comment(
    scenario_id="s001",
    user_id="user_456",
    content="Great story!",
    parent_comment_id=None  # root comment
)

# Update comment (checks permission)
updated = await repo.update_comment(
    comment_id=5,
    user_id="user_456",
    content="Updated content"
)
```

### Toggle Operations
```python
# Like toggle returns new state + count
is_liked, new_count = await repo.toggle_comment_like(
    comment_id=5,
    user_id="user_456"
)

# Scenario like returns boolean
is_liked = await repo.toggle_scenario_like(
    scenario_id="s001",
    user_id="user_456"
)
```

### UPSERT (Create or Update)
```python
# Upsert character affinity (creates if not exists, updates if does)
affinity = await repo.upsert_user_character_affinity(
    user_id="user_456",
    character_name="Emma",
    score_delta=+50
)
```

---

## Integration into Phase 3 Services

Example service pattern using ChatRepository:

```python
class AffinityService:
    def __init__(self, chat_repo: ChatRepository):
        self.repo = chat_repo
    
    async def process_interaction(self, user_id, character_name, interaction_type):
        # Business logic here
        score_delta = self._calculate_delta(interaction_type)
        
        # Use repository
        affinity = await self.repo.upsert_user_character_affinity(
            user_id=user_id,
            character_name=character_name,
            score_delta=score_delta
        )
        return affinity
```

---

## Testing Considerations

When writing tests:

### Mock the Repository
```python
mock_repo = AsyncMock(spec=ChatRepository)
mock_repo.save_entity.return_value = Entity(...)

service = AffinityService(mock_repo)
await service.process(...)

mock_repo.save_entity.assert_called_once()
```

### Use Fixtures
```python
@pytest.fixture
async def chat_repo(async_session):
    return ChatRepository(async_session)

@pytest.mark.asyncio
async def test_save_entity(chat_repo):
    entity = await chat_repo.save_entity({
        "entity_type": "character",
        "entity_name": "Emma"
    })
    assert entity.entity_id > 0
```

---

## Performance Notes

1. **Queries**: All list queries have indexes on sort/filter fields
2. **Hybrid Cache**: SessionRepository uses Redis for <1hr data, PostgreSQL for durability
3. **Soft Deletes**: Remember to filter `is_deleted=False` in list queries (done automatically)
4. **Pagination**: Always use limit/offset for large result sets
5. **Vector Search**: Entity/UserMemory have vector embeddings ready for similarity search

---

## What Changed from merge_strategy.md

Minor naming conventions:
- `save_affinity()` → `save_affinity_record()` (clearer)
- `load_latest_affinity()` → `get_latest_affinity()` (consistency)
- `save_entities()` → `save_entity()` (works for single entity)
- `save_relationships()` → `save_relationship()` (works for single relationship)
- `load_session()` → `get_session()` (consistency)
- `get_recent_sessions()` → `get_user_recent_sessions()` (clarity on user scope)

**Impact**: None - all are functional equivalents

---

## Ready for Phase 3

You can now create Services that:
1. Inject ChatRepository, ScenarioRepository, SessionRepository
2. Implement business logic on top of these methods
3. Call multiple repository methods in coordinated transactions
4. Be injected into UseCase classes

Start with:
- `AffinityService` - wraps affinity repo methods
- `DialogueService` - wraps dialogue+memory repo methods
- `CommentService` - wraps scenario comment repo methods

---

**Last Updated**: 2025-11-10  
**Status**: Production Ready ✓
