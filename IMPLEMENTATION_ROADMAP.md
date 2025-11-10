# Phase 3-4 Implementation Roadmap

## Overview
- **Current Completion**: 47.7% (10.5/22 components)
- **Estimated Timeline**: 3-4 weeks
- **Blocking Issues**: None - can proceed with all missing components in parallel

---

## PHASE 3 - SERVICES LAYER (6 Required)

### 1. MemoryService (Consolidation Task - Easiest)
**Effort**: 2-3 hours | **Complexity**: Low | **Dependencies**: Existing extractors
**File**: `/Users/jtm427/Desktop/workspace/backend/app/features/chat/services/memory_service.py`

**Task**:
- Create wrapper service around EntityExtractor, RelationshipExtractor, MemoryExtractor
- Expose unified interface: `extract_entities()`, `extract_relationships()`, `extract_memories()`
- Keep individual extractors for internal use
- Update `services/__init__.py` to export MemoryService

**Status**: Ready to implement - extractors already complete

---

### 2. AffinityService (Core Feature)
**Effort**: 1-2 days | **Complexity**: Medium | **Dependencies**: ChatRepository, UserCharacterAffinity model

**File**: `/Users/jtm427/Desktop/workspace/backend/app/features/chat/services/affinity_service.py`

**Required Methods**:
```python
class AffinityService:
    def __init__(self, repository: ChatRepository):
        self.repository = repository
    
    async def update_affinity(
        self,
        session_id: str,
        user_id: str,
        character_name: str,
        interaction_type: str,
        sentiment: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update character affinity for user
        Returns: Updated affinity record
        """
        # 1. Classify interaction using LLM
        classification = await self._classify_interaction_with_llm(interaction_type, context)
        
        # 2. Calculate affinity delta
        delta = self._calculate_affinity_delta(classification, sentiment)
        
        # 3. Update user-character affinity
        affinity_record = await self.repository.upsert_character_affinity(
            user_id=user_id,
            character_name=character_name,
            score_delta=delta
        )
        
        # 4. Save to affinity_records table
        await self.repository.save_affinity(session_id, affinity_record.to_dict())
        
        return affinity_record.to_dict()
    
    async def _classify_interaction_with_llm(
        self,
        interaction_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify interaction type and sentiment using LLM"""
        # Use LLMClient to classify
        # Return: {affinity_impact: float, emotion: str, ...}
```

**Source Code** (migrate from):
- `backend/src/services/affinity_service.py`

**Integration Points**:
- Called from ParentAgent.execute() after dialogue generation
- Updates UserCharacterAffinity and AffinityRecord models
- Uses LLMClient for classification

---

### 3. DialogueService (Complex Pipeline)
**Effort**: 2-3 days | **Complexity**: High | **Dependencies**: LLMService, ScenarioService

**File**: `/Users/jtm427/Desktop/workspace/backend/app/features/chat/services/dialogue_service.py`

**Required Methods**:
```python
class DialogueService:
    async def validate_dialogue(self, dialogue: str, context: Dict) -> Dict[str, Any]:
        """Validate dialogue against scenario rules & guidelines"""
        # Check content appropriateness, length, character consistency
        
    async def correct_dialogue(self, dialogue: str, errors: List[str]) -> str:
        """Fix grammar, punctuation, character voice consistency"""
        
    async def format_dialogue(self, dialogue: str, speaker: str) -> ChatMessage:
        """Format into ChatMessage with metadata"""
        
    async def detect_events(self, dialogue: str, state: Dict) -> List[Dict]:
        """Detect story events, achievements, milestone triggers"""
        
    async def select_image(self, dialogue: str, context: Dict) -> Optional[str]:
        """Select appropriate image asset for dialogue"""
```

**Consolidates**:
- dialogue_validation_service.py → `validate_dialogue()`
- dialogue_correction_service.py → `correct_dialogue()`
- dialogue_formatter_service.py → `format_dialogue()`
- dialogue_event_detector_service.py → `detect_events()`
- dialogue_image_service.py → `select_image()`

**Pipeline Flow**:
```
Input → Validate → Correct → Format → Detect Events → Select Image → Output
```

**Integration Points**:
- Called from DialogueAgent or ParentAgent.execute()
- Works with LLMService for validation/correction
- Uses ScenarioService for image mapping data

---

### 4. MissionService (Game Logic)
**Effort**: 1-2 days | **Complexity**: Medium | **Dependencies**: ChatRepository, StageService

**File**: `/Users/jtm427/Desktop/workspace/backend/app/features/chat/services/mission_service.py`

**Required Methods**:
```python
class MissionService:
    async def check_mission_completion(
        self,
        session_id: str,
        mission_id: str,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if mission objectives are complete"""
        # Evaluate completion criteria
        # Return: {completed: bool, progress: float, ...}
    
    async def generate_feedback(
        self,
        mission_id: str,
        completion_status: Dict
    ) -> str:
        """Generate feedback message for mission result"""
        # Use LLM to create feedback
    
    async def record_mission_result(
        self,
        user_id: str,
        session_id: str,
        mission_id: str,
        result: Dict
    ) -> None:
        """Record mission result to database"""
        # Save mission_records entry
```

**Consolidates**:
- mission_logic_service.py → `check_mission_completion()`
- mission_feedback_service.py → `generate_feedback()`
- mission_record_service.py → `record_mission_result()`

**Integration Points**:
- Called from stage handlers (mission_stage.py)
- Updates MissionRecord model
- Works with ChatRepository for persistence

---

### 5. ContextService (Context Building)
**Effort**: 1-2 days | **Complexity**: Medium | **Dependencies**: ScenarioService, EntityExtractor

**File**: `/Users/jtm427/Desktop/workspace/backend/app/features/chat/services/context_service.py`

**Required Methods**:
```python
class ContextService:
    async def build_children_context(
        self,
        user_id: str,
        scenario_id: str,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build context for children (age-appropriate filtering, preferences)"""
        # Load scenario context
        # Filter by age appropriateness
        # Include user preferences from memory
        # Return structured context
    
    async def generate_beats(
        self,
        scenario_id: str,
        stage_id: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate beat sequences for current stage"""
        # Load beats from ScenarioService
        # Filter/adapt based on context
        # Return beat list for dialogue generation
```

**Consolidates**:
- context_builder_service.py → `build_children_context()`
- beats_generator_service.py → `generate_beats()`

**Integration Points**:
- Called from LLMService for beat-based dialogue generation
- Works with ScenarioService for beat data
- Uses EntityExtractor for entity context
- Respects user memory from MemoryService

---

### 6. RouterService (Already Partially Done)
**Effort**: 1 hour (verification) | **Complexity**: Low | **Status**: ✓ Mostly complete

**Current Status**:
- RouterAgent exists in `app/features/chat/agent/guards/router.py`
- All required methods implemented:
  - ✓ `classify()` - Topic classification
  - ✓ `_classify_by_embedding()` - Semantic classification
  - ✓ `_classify_by_keywords()` - Keyword fallback
  - ✓ `get_response_strategy()` - Strategy selection

**Decision**:
- **Option A** (Recommended): Keep as RouterAgent in guards layer
  - Works well in pipeline
  - Clear separation of concerns
  - No changes needed
  
- **Option B**: Move to services/router_service.py
  - Would need to move file
  - Would require updating imports in ParentAgent

**Recommendation**: Keep as-is, no action needed

---

## PHASE 4 - AGENTS LAYER (4+ Required)

### 1. MemoryService Export (Quick Fix)
**Effort**: 30 min | **Complexity**: Trivial | **Dependencies**: None

**Task**:
- Add MemoryService export to `app/features/chat/services/__init__.py`
- Make available to agents for extraction calls

---

### 2. DialogueAgent (Wrapper Agent)
**Effort**: 1-2 hours | **Complexity**: Low | **Dependencies**: DialogueService

**File**: `/Users/jtm427/Desktop/workspace/backend/app/features/chat/agent/dialogue.py`

**Implementation**:
```python
class DialogueAgent:
    """
    [Layer 3] Dialogue Processing Agent
    
    Responsibility: Apply dialogue pipeline transformations
    Pipeline: Validate → Correct → Format → Detect Events → Select Image
    """
    
    def __init__(self, dialogue_service: DialogueService):
        self.dialogue_service = dialogue_service
    
    async def validate_and_correct(
        self,
        dialogue: str,
        context: Dict[str, Any]
    ) -> ChatMessage:
        """
        Process dialogue through validation & correction pipeline
        
        Args:
            dialogue: Raw dialogue text
            context: Context dict (state, scenario, etc.)
        
        Returns:
            Processed ChatMessage
        """
        # 1. Validate dialogue
        validation = await self.dialogue_service.validate_dialogue(dialogue, context)
        if not validation['is_valid']:
            raise ValueError(f"Dialogue validation failed: {validation['errors']}")
        
        # 2. Correct dialogue
        corrected = await self.dialogue_service.correct_dialogue(dialogue, validation['suggestions'])
        
        # 3. Format dialogue
        formatted_msg = await self.dialogue_service.format_dialogue(corrected, context['speaker'])
        
        # 4. Detect events
        events = await self.dialogue_service.detect_events(dialogue, context['state'])
        formatted_msg.events = events
        
        # 5. Select image
        image = await self.dialogue_service.select_image(dialogue, context)
        formatted_msg.image_url = image
        
        return formatted_msg
```

**Integration**: Called from ParentAgent.execute() after LLM generation

---

### 3. StageHandlers Directory (5 Files - Complex)
**Effort**: 3-4 days | **Complexity**: High | **Dependencies**: All services + LLMService

**Directory Structure**:
```
app/features/chat/agent/stage_handlers/
├── __init__.py
├── mission_stage.py
├── free_intent_stage.py
├── router_stage.py
├── scene_stage.py
└── open_narrative_stage.py
```

#### 3.1 Base Handler Interface
**File**: `stage_handlers/__init__.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class StageHandler(ABC):
    """Base class for stage-specific handling"""
    
    @abstractmethod
    async def handle(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute stage logic and return updated state"""
        pass
    
    @abstractmethod
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this handler applies to current state"""
        pass
```

#### 3.2 MissionStageHandler
**File**: `stage_handlers/mission_stage.py`

**Responsibilities**:
- Check mission completion
- Generate mission feedback
- Record mission results
- Trigger next stage progression

**Methods**:
```python
class MissionStageHandler(StageHandler):
    def __init__(self, mission_service: MissionService):
        self.mission_service = mission_service
    
    async def handle(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        1. Check mission completion
        2. Generate feedback if complete
        3. Record result
        4. Update state for next stage
        """
```

**Integration**: Called when `current_stage == 'mission'`

#### 3.3 FreeIntentStageHandler
**File**: `stage_handlers/free_intent_stage.py`

**Responsibilities**:
- Handle free-form user responses
- Apply no specific mission constraints
- Standard dialogue generation

#### 3.4 RouterStageHandler
**File**: `stage_handlers/router_stage.py`

**Responsibilities**:
- Use RouterAgent to classify user intent
- Route to appropriate next stage based on classification
- Apply response strategy

#### 3.5 SceneStageHandler
**File**: `stage_handlers/scene_stage.py`

**Responsibilities**:
- Handle scene/narrative stage progression
- Load scene context and beats
- Generate beat-based dialogue
- Manage scene transitions

#### 3.6 OpenNarrativeStageHandler
**File**: `stage_handlers/open_narrative_stage.py`

**Responsibilities**:
- Handle open-ended narrative
- Generate dynamic story content
- Manage narrative consistency

**Integration Pattern** (from ParentAgent):
```python
async def execute(self, ...):
    # ... existing code ...
    
    # NEW: Stage handler routing
    current_stage = state.get('current_stage')
    handler = self._get_stage_handler(current_stage)
    if handler:
        state = await handler.handle(state)
    
    # ... rest of code ...

def _get_stage_handler(self, stage_type: str) -> Optional[StageHandler]:
    handlers = {
        'mission': MissionStageHandler(self.mission_service),
        'free_intent': FreeIntentStageHandler(),
        'router': RouterStageHandler(self.router_agent),
        'scene': SceneStageHandler(self.scenario_service),
        'open_narrative': OpenNarrativeStageHandler(),
    }
    return handlers.get(stage_type)
```

---

### 4. ChildrenAgent (Verify Integration Status)
**Effort**: 1-2 hours (investigation) | **Complexity**: Low | **Blocking**: Need to check

**Tasks**:
1. Check if children-specific logic is in LLMService
2. Check if src/agents/children_agent.py exists and what it does
3. Decide: Keep integrated in LLMService or create separate agent?

**Current Finding**: Likely already integrated into LLMService
- Age-appropriate filtering happens in dialogue generation
- Can verify by checking LLMService implementation

---

### 5. Update ParentAgent (Integration Task)
**Effort**: 1-2 days | **Complexity**: Medium | **Status**: Partially complete

**Current Implementation**: ✓ Core pipeline exists
**Missing Integrations**:

1. **Add DialogueAgent pipeline** (after LLM generation)
```python
dialogue_agent = DialogueAgent(self.dialogue_service)
validated_msg = await dialogue_agent.validate_and_correct(raw_dialogue, context)
```

2. **Add AffinityService update** (after dialogue generation)
```python
await self.affinity_service.update_affinity(
    session_id=session_id,
    user_id=user_id,
    character_name=character_name,
    interaction_type=route_result.topic,
    sentiment=self._extract_sentiment(user_message),
    context=state
)
```

3. **Add StageHandlers routing** (based on stage type)
```python
handler = self._get_stage_handler(state.get('current_stage'))
if handler and handler.should_handle(state):
    state = await handler.handle(state)
```

4. **Add MemoryService integration** (optional, after each turn)
```python
entities = await self.memory_service.extract_entities(dialogue_text)
relationships = await self.memory_service.extract_relationships(dialogue_text)
memories = await self.memory_service.extract_memories(summary)
```

**File**: `/Users/jtm427/Desktop/workspace/backend/app/features/chat/agent/parent.py`

---

## Implementation Order

### Week 1
- [ ] **Day 1**: MemoryService wrapper + DialogueAgent
- [ ] **Day 2**: AffinityService implementation
- [ ] **Day 3-4**: DialogueService (complex)
- [ ] **Day 5**: MissionService + ContextService

### Week 2
- [ ] **Day 1-2**: StageHandlers (5 files) - Start with base, then each handler
- [ ] **Day 3-4**: Update ParentAgent with all integrations
- [ ] **Day 5**: Testing and integration validation

### Week 3
- [ ] **Days 1-2**: Fix bugs, refine implementations
- [ ] **Days 3-5**: E2E testing, edge case handling

---

## Testing Strategy

### Unit Tests
- [ ] Each Service has 70%+ method coverage
- [ ] Each Agent has 50%+ method coverage
- [ ] Mock Repository calls

### Integration Tests
- [ ] ParentAgent full pipeline
- [ ] StageHandlers with real state transitions
- [ ] Service chains (DialogueService → MissionService)

### E2E Tests
- [ ] Full chat flow from start to finish
- [ ] Affinity updates across multiple turns
- [ ] Stage progression completeness

---

## Dependencies & Imports

### MemoryService
```python
from .extractors import EntityExtractor, RelationshipExtractor, MemoryExtractor
```

### AffinityService
```python
from ..repository import ChatRepository
from ..models import UserCharacterAffinity, AffinityRecord
from app.core.llm import LLMClient
```

### DialogueService
```python
from .llm_service import LLMService
from .scenario_service import ScenarioService
from app.core.llm import LLMClient
```

### MissionService
```python
from ..repository import ChatRepository
from ..models import MissionRecord
```

### ContextService
```python
from .scenario_service import ScenarioService
from .extractors import EntityExtractor
```

### DialogueAgent
```python
from .dialogue_service import DialogueService
from ..models import ChatMessage
```

### StageHandlers
```python
from ..services import MissionService, ScenarioService, ContextService
from .guards import RouterAgent
from .parent import ChatParent  # For parent reference
```

---

## Success Criteria

- All 13 missing files/components implemented
- All 22 Phase 3-4 components fully integrated
- ParentAgent.execute() pipeline complete
- 100% backward compatibility with existing code
- All unit tests passing
- E2E chat flow working end-to-end

