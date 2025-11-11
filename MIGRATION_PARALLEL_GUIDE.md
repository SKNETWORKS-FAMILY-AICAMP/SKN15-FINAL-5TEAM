# 병렬 마이그레이션 가이드 (4개 Claude 창)

> 파일 충돌 없이 안전하게 병렬 작업하기
> 각 창은 독립적인 파일/디렉토리 작업
> 작성일: 2025-11-11

---

## 🎯 전체 개요

### 작업 분리 전략
```
창 1 → chat/agent/ + chat/agents/        (agent 통합)
창 2 → entities/ + chat/models/entity*    (entities 통합)
창 3 → progression/ + memories/ + users/  (progression + memories 통합)
창 4 → chat/services/ + logging/          (services 추가 + logging 완성)
```

### ⚠️ 중요: 작업 순서
1. **창 1, 2, 3, 4 병렬 실행** (파일 충돌 없음)
2. **모든 창 완료 후** → 창 5: chat/repositories 분리 (선택)
3. **마지막** → import 경로 일괄 수정

---

## 창 1: agent vs agents 통합 🔥

**담당 파일:**
- `backend/app/features/chat/agent/`
- `backend/app/features/chat/agents/`

**목표:**
- LangGraph 기반 단일 agent 디렉토리 구성
- nodes, guards, handlers로 구조화

### STEP 1-1: 디렉토리 생성

```bash
cd /Users/jtm427/Desktop/workspace

# nodes, guards, handlers 디렉토리 생성
mkdir -p backend/app/features/chat/agent/nodes
mkdir -p backend/app/features/chat/agent/guards
mkdir -p backend/app/features/chat/agent/handlers
```

### STEP 1-2: 핵심 파일 이동 (LangGraph)

```bash
# graph_state.py, workflow.py는 최상위에 유지
cp backend/app/features/chat/agents/graph_state.py backend/app/features/chat/agent/
cp backend/app/features/chat/agents/workflow.py backend/app/features/chat/agent/

# 백업 (혹시 몰라서)
cp backend/app/features/chat/agents/graph_state.py backend/app/features/chat/agent/graph_state.py.backup
```

### STEP 1-3: 에이전트 → nodes/

```bash
# Parent Agent
cat > backend/app/features/chat/agent/nodes/parent.py << 'EOF'
"""
Parent Agent - 세션 검증 및 컨텍스트 준비
"""
from typing import Dict, Any
from ..graph_state import GraphState
from app.core.logging import get_service_logger

logger = get_service_logger("ParentAgent")


class ParentAgent:
    """Parent Agent - 전체 워크플로우 조율"""

    def execute(self, state: GraphState) -> GraphState:
        """Parent Agent 실행"""
        logger.info("execute", "Parent agent started")

        # 세션 검증
        required = ["session_id", "user_id", "scenario_id", "user_input"]
        for field in required:
            if not state.get(field):
                state["error"] = f"Missing: {field}"
                return state

        # 기본값 설정
        if "turn_count" not in state:
            state["turn_count"] = 0
        if "current_stage" not in state:
            state["current_stage"] = "intro"
        if "stage_type" not in state:
            state["stage_type"] = "open_narrative"

        return state
EOF

# Dialogue Agent
cp backend/app/features/chat/agents/dialogue_agent.py backend/app/features/chat/agent/nodes/dialogue.py

# Router Agent
cp backend/app/features/chat/agents/router_agent.py backend/app/features/chat/agent/nodes/router.py

# Children Agent
cp backend/app/features/chat/agents/children_agent.py backend/app/features/chat/agent/nodes/children.py
```

### STEP 1-4: 가드레일 → guards/

```bash
# Guardrail Agent
cp backend/app/features/chat/agents/guardrail_agent.py backend/app/features/chat/agent/guards/guardrail.py

# should_route 조건부 엣지 함수 생성
cat > backend/app/features/chat/agent/guards/should_route.py << 'EOF'
"""
조건부 엣지 함수들
"""
from ..graph_state import GraphState


def should_route(state: GraphState) -> str:
    """
    라우팅 필요 여부 결정

    Returns:
        "route" - RouterAgent로 이동
        "dialogue" - DialogueAgent로 이동
        "end" - 종료 (가드레일 실패)
    """
    # 가드레일 실패 시 종료
    if not state.get("is_safe", True):
        return "end"

    # router 타입 스테이지인 경우 라우팅
    if state.get("stage_type") == "router":
        return "route"

    # 그 외는 대화 생성
    return "dialogue"


def check_safety(state: GraphState) -> str:
    """
    출력 안전성 확인

    Returns:
        "safe" - 안전, 종료
        "unsafe" - 불안전, 재생성
    """
    if state.get("is_safe", True):
        return "safe"
    else:
        return "unsafe"
EOF
```

### STEP 1-5: 스테이지 핸들러 → handlers/

```bash
# agents/stage_handlers/ 내용을 handlers/로 복사
cp backend/app/features/chat/agents/stage_handlers/scene_handler.py backend/app/features/chat/agent/handlers/scene.py
cp backend/app/features/chat/agents/stage_handlers/mission_handler.py backend/app/features/chat/agent/handlers/mission.py
cp backend/app/features/chat/agents/stage_handlers/router_handler.py backend/app/features/chat/agent/handlers/router.py
cp backend/app/features/chat/agents/stage_handlers/free_intent_handler.py backend/app/features/chat/agent/handlers/free_intent.py
cp backend/app/features/chat/agents/stage_handlers/open_narrative_handler.py backend/app/features/chat/agent/handlers/open_narrative.py

# __init__.py 생성
cat > backend/app/features/chat/agent/handlers/__init__.py << 'EOF'
"""
Stage Handlers - 스테이지 타입별 대화 생성
"""
from .scene import SceneStageHandler
from .mission import MissionStageHandler
from .router import RouterStageHandler
from .free_intent import FreeIntentStageHandler
from .open_narrative import OpenNarrativeStageHandler

__all__ = [
    "SceneStageHandler",
    "MissionStageHandler",
    "RouterStageHandler",
    "FreeIntentStageHandler",
    "OpenNarrativeStageHandler",
]
EOF
```

### STEP 1-6: __init__.py 업데이트

```bash
cat > backend/app/features/chat/agent/__init__.py << 'EOF'
"""
Chat Feature - Agent Layer (LangGraph)

Architecture:
- graph_state.py: TypedDict 상태 정의
- workflow.py: StateGraph 워크플로우
- nodes/: 에이전트 (상태 변환)
- guards/: 검증 및 라우팅
- handlers/: 스테이지별 대화 생성
"""

from .graph_state import GraphState, AgentDecision
from .workflow import ChatWorkflow, get_workflow

from .nodes.parent import ParentAgent
from .nodes.dialogue import DialogueAgent
from .nodes.router import RouterAgent
from .nodes.children import ChildrenAgent

from .guards.guardrail import GuardrailAgent
from .guards.should_route import should_route, check_safety

from .handlers import (
    SceneStageHandler,
    MissionStageHandler,
    RouterStageHandler,
    FreeIntentStageHandler,
    OpenNarrativeStageHandler,
)

__all__ = [
    # State
    "GraphState",
    "AgentDecision",
    # Workflow
    "ChatWorkflow",
    "get_workflow",
    # Nodes
    "ParentAgent",
    "DialogueAgent",
    "RouterAgent",
    "ChildrenAgent",
    # Guards
    "GuardrailAgent",
    "should_route",
    "check_safety",
    # Handlers
    "SceneStageHandler",
    "MissionStageHandler",
    "RouterStageHandler",
    "FreeIntentStageHandler",
    "OpenNarrativeStageHandler",
]
EOF

# nodes/__init__.py
cat > backend/app/features/chat/agent/nodes/__init__.py << 'EOF'
"""
Agent Nodes - 상태 변환 에이전트
"""
from .parent import ParentAgent
from .dialogue import DialogueAgent
from .router import RouterAgent
from .children import ChildrenAgent

__all__ = ["ParentAgent", "DialogueAgent", "RouterAgent", "ChildrenAgent"]
EOF

# guards/__init__.py
cat > backend/app/features/chat/agent/guards/__init__.py << 'EOF'
"""
Guards - 검증 및 라우팅
"""
from .guardrail import GuardrailAgent
from .should_route import should_route, check_safety

__all__ = ["GuardrailAgent", "should_route", "check_safety"]
EOF
```

### STEP 1-7: workflow.py import 수정

```bash
# workflow.py에서 import 경로 수정
# 원본 백업
cp backend/app/features/chat/agent/workflow.py backend/app/features/chat/agent/workflow.py.backup

# 수정 (sed 사용)
# macOS sed는 -i '' 필요
sed -i '' 's/from \.parent_agent import ParentAgent/from .nodes.parent import ParentAgent/g' backend/app/features/chat/agent/workflow.py
sed -i '' 's/from \.dialogue_agent import DialogueAgent/from .nodes.dialogue import DialogueAgent/g' backend/app/features/chat/agent/workflow.py
sed -i '' 's/from \.router_agent import RouterAgent/from .nodes.router import RouterAgent/g' backend/app/features/chat/agent/workflow.py
sed -i '' 's/from \.guardrail_agent import GuardrailAgent/from .guards.guardrail import GuardrailAgent/g' backend/app/features/chat/agent/workflow.py
```

### STEP 1-8: 기존 agents/ 디렉토리 제거

```bash
# ⚠️ 백업 후 제거
mv backend/app/features/chat/agents backend/app/features/chat/agents.backup

# 확인
ls -la backend/app/features/chat/agent/
# nodes/, guards/, handlers/ 존재 확인
```

### ✅ 창 1 완료 체크리스트

- [ ] nodes/ 디렉토리 생성 완료
- [ ] guards/ 디렉토리 생성 완료
- [ ] handlers/ 디렉토리 생성 완료
- [ ] ParentAgent → nodes/parent.py 이동
- [ ] DialogueAgent → nodes/dialogue.py 이동
- [ ] RouterAgent → nodes/router.py 이동
- [ ] ChildrenAgent → nodes/children.py 이동
- [ ] GuardrailAgent → guards/guardrail.py 이동
- [ ] should_route 함수 생성
- [ ] 5개 스테이지 핸들러 이동
- [ ] __init__.py 모두 생성
- [ ] workflow.py import 수정
- [ ] agents.backup 폴더 생성 (원본 보존)

---

## 창 2: entities → chat 통합 🔥

**담당 파일:**
- `backend/app/features/entities/`
- `backend/app/features/chat/models/`
- `backend/app/features/chat/repositories/`

**목표:**
- entities를 chat의 일부로 통합
- Graph RAG는 대화 컨텍스트

### STEP 2-1: chat/models/ 디렉토리 생성

```bash
cd /Users/jtm427/Desktop/workspace

# models 디렉토리 생성
mkdir -p backend/app/features/chat/models
mkdir -p backend/app/features/chat/repositories
```

### STEP 2-2: models.py → models/*.py 분리

```bash
# 기존 models.py 백업
cp backend/app/features/chat/models.py backend/app/features/chat/models.py.backup

# DialogueTurn 모델
cat > backend/app/features/chat/models/dialogue_turn.py << 'EOF'
"""
DialogueTurn 모델
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.db.models import Base
import uuid
from datetime import datetime


class DialogueTurn(Base):
    """대화 턴"""
    __tablename__ = "dialogue_turns"

    turn_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("game_sessions.session_id"), nullable=False)
    turn_number = Column(Integer, nullable=False)

    user_input = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    speaker = Column(String(100))
    emotion = Column(String(50))

    stage_id = Column(String(100))
    stage_type = Column(String(50))

    image_url = Column(Text)
    thumbnail_url = Column(Text)

    affinity_change = Column(Float, default=0.0)
    xp_earned = Column(Integer, default=0)

    metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    session = relationship("GameSession", back_populates="dialogue_turns")
EOF

# ConversationSummary 모델
cat > backend/app/features/chat/models/conversation_summary.py << 'EOF'
"""
ConversationSummary 모델
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.core.db.models import Base
import uuid
from datetime import datetime


class ConversationSummary(Base):
    """대화 요약"""
    __tablename__ = "conversation_summaries"

    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("game_sessions.session_id"), nullable=False)

    summary_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))

    message_count = Column(Integer, default=0)
    last_turn_number = Column(Integer, default=0)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session = relationship("GameSession")
EOF
```

### STEP 2-3: entities 모델 이동

```bash
# Entity 모델
cat > backend/app/features/chat/models/entity.py << 'EOF'
"""
Entity 모델 (Graph RAG)
"""
from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.core.db.models import Base
import uuid
from datetime import datetime


class Entity(Base):
    """엔티티 (인물, 장소, 사물, 개념)"""
    __tablename__ = "entities"

    entity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(String(100), nullable=False)

    entity_type = Column(String(50), nullable=False)  # person, place, thing, concept
    entity_name = Column(String(255), nullable=False)
    description = Column(Text)

    properties = Column(JSONB, default={})
    embedding = Column(Vector(1536))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    mentions = relationship("EntityMention", back_populates="entity", cascade="all, delete-orphan")
    source_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan"
    )
    target_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan"
    )
EOF

# Relationship 모델
cat > backend/app/features/chat/models/relationship.py << 'EOF'
"""
Relationship 모델 (엔티티 간 관계)
"""
from sqlalchemy import Column, String, Float, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.db.models import Base
import uuid
from datetime import datetime


class Relationship(Base):
    """엔티티 간 관계"""
    __tablename__ = "relationships"

    relationship_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=False)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=False)

    relationship_type = Column(String(100), nullable=False)  # knows, located_in, owns, etc.
    description = Column(String(500))
    strength = Column(Float, default=1.0)

    metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source_entity = relationship("Entity", foreign_keys=[source_entity_id], back_populates="source_relationships")
    target_entity = relationship("Entity", foreign_keys=[target_entity_id], back_populates="target_relationships")
EOF

# EntityMention 모델
cat > backend/app/features/chat/models/entity_mention.py << 'EOF'
"""
EntityMention 모델 (대화 턴에서 엔티티 언급)
"""
from sqlalchemy import Column, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.db.models import Base
import uuid
from datetime import datetime


class EntityMention(Base):
    """엔티티 언급 (대화 턴에서)"""
    __tablename__ = "entity_mentions"

    mention_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=False)
    dialogue_turn_id = Column(UUID(as_uuid=True), ForeignKey("dialogue_turns.turn_id"), nullable=False)

    mention_text = Column(Text, nullable=False)
    context = Column(Text)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="mentions")
    dialogue_turn = relationship("DialogueTurn")
EOF
```

### STEP 2-4: models/__init__.py 생성

```bash
cat > backend/app/features/chat/models/__init__.py << 'EOF'
"""
Chat Models
"""
from .dialogue_turn import DialogueTurn
from .conversation_summary import ConversationSummary
from .entity import Entity
from .relationship import Relationship
from .entity_mention import EntityMention

__all__ = [
    "DialogueTurn",
    "ConversationSummary",
    "Entity",
    "Relationship",
    "EntityMention",
]
EOF
```

### STEP 2-5: EntityRepository 이동

```bash
# entities/repository.py → chat/repositories/entity_repository.py
cp backend/app/features/entities/repository.py backend/app/features/chat/repositories/entity_repository.py

# import 경로 수정
sed -i '' 's/from \.schemas import/from ..models.entity import Entity\nfrom ..models.relationship import Relationship\nfrom ..models.entity_mention import EntityMention\n# from .schemas import/g' backend/app/features/chat/repositories/entity_repository.py
```

### STEP 2-6: repositories/__init__.py

```bash
cat > backend/app/features/chat/repositories/__init__.py << 'EOF'
"""
Chat Repositories
"""
from .entity_repository import EntityRepository

__all__ = ["EntityRepository"]
EOF
```

### STEP 2-7: entities/ 백업 및 제거

```bash
# 백업
mv backend/app/features/entities backend/app/features/entities.backup

# 확인
ls -la backend/app/features/chat/models/
ls -la backend/app/features/chat/repositories/
```

### ✅ 창 2 완료 체크리스트

- [ ] chat/models/ 디렉토리 생성
- [ ] chat/repositories/ 디렉토리 생성
- [ ] DialogueTurn → models/dialogue_turn.py
- [ ] ConversationSummary → models/conversation_summary.py
- [ ] Entity → models/entity.py
- [ ] Relationship → models/relationship.py
- [ ] EntityMention → models/entity_mention.py
- [ ] models/__init__.py 생성
- [ ] EntityRepository 이동
- [ ] repositories/__init__.py 생성
- [ ] entities.backup 폴더 생성

---

## 창 3: progression + memories 통합 🔥

**담당 파일:**
- `backend/app/features/progression/`
- `backend/app/features/memories/`
- `backend/app/features/users/models/`
- `backend/app/features/chat/models/`

**목표:**
- progression → users (XP는 사용자 속성)
- memories → chat (메모리는 대화 컨텍스트)

### STEP 3-1: users/models/ 디렉토리 생성

```bash
cd /Users/jtm427/Desktop/workspace

mkdir -p backend/app/features/users/models
```

### STEP 3-2: XPTransaction 이동

```bash
# progression/models.py → users/models/xp_transaction.py
cat > backend/app/features/users/models/xp_transaction.py << 'EOF'
"""
XPTransaction 모델
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.db.models import Base
import uuid
from datetime import datetime


class XPTransaction(Base):
    """XP 트랜잭션 로그"""
    __tablename__ = "xp_transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("game_sessions.session_id"))

    xp_amount = Column(Integer, nullable=False)  # 양수: 획득, 음수: 소비
    xp_type = Column(String(50), nullable=False)  # message, scenario_complete, achievement, etc.

    xp_balance_after = Column(Integer, nullable=False)
    level_before = Column(Integer)
    level_after = Column(Integer)
    did_level_up = Column(Boolean, default=False)

    extra_metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="xp_transactions")
    session = relationship("GameSession")
EOF

# users/models/__init__.py
cat > backend/app/features/users/models/__init__.py << 'EOF'
"""
User Models
"""
from .xp_transaction import XPTransaction

__all__ = ["XPTransaction"]
EOF
```

### STEP 3-3: UserMemory 이동

```bash
# memories/models.py → chat/models/user_memory.py
cat > backend/app/features/chat/models/user_memory.py << 'EOF'
"""
UserMemory 모델
"""
from sqlalchemy import Column, String, Text, Float, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.core.db.models import Base
import uuid
from datetime import datetime


class UserMemory(Base):
    """사용자 메모리 (장기 기억)"""
    __tablename__ = "user_memories"

    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("game_sessions.session_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    memory_text = Column(Text, nullable=False)
    memory_type = Column(String(50))  # preference, fact, goal, etc.
    importance = Column(Float, default=0.5)

    embedding = Column(Vector(1536))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_accessed = Column(TIMESTAMP, default=datetime.utcnow)
    access_count = Column(Integer, default=0)

    # Relationships
    session = relationship("GameSession")
    user = relationship("User")
EOF

# chat/models/__init__.py 업데이트
cat > backend/app/features/chat/models/__init__.py << 'EOF'
"""
Chat Models
"""
from .dialogue_turn import DialogueTurn
from .conversation_summary import ConversationSummary
from .user_memory import UserMemory
from .entity import Entity
from .relationship import Relationship
from .entity_mention import EntityMention

__all__ = [
    "DialogueTurn",
    "ConversationSummary",
    "UserMemory",
    "Entity",
    "Relationship",
    "EntityMention",
]
EOF
```

### STEP 3-4: MemoryRepository 이동

```bash
# memories/repository.py → chat/repositories/memory_repository.py
cp backend/app/features/memories/repository.py backend/app/features/chat/repositories/memory_repository.py

# import 수정
sed -i '' 's/from \.models import UserMemory/from ..models.user_memory import UserMemory/g' backend/app/features/chat/repositories/memory_repository.py

# chat/repositories/__init__.py 업데이트
cat > backend/app/features/chat/repositories/__init__.py << 'EOF'
"""
Chat Repositories
"""
from .entity_repository import EntityRepository
from .memory_repository import MemoryRepository

__all__ = ["EntityRepository", "MemoryRepository"]
EOF
```

### STEP 3-5: ProgressionRepository → UserRepository 통합

```bash
# users/repository.py에 XP 메서드 추가
# 기존 repository.py 읽기
cat backend/app/features/users/repository.py

# XP 메서드 추가 (기존 파일에 append)
cat >> backend/app/features/users/repository.py << 'EOF'

    # ========================================
    # XP 관련 메서드 (progression에서 이동)
    # ========================================

    async def add_xp(
        self,
        user_id: str,
        xp_amount: int,
        xp_type: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> XPTransaction:
        """
        XP 추가 + 트랜잭션 로그

        Args:
            user_id: 사용자 ID
            xp_amount: XP 양 (양수: 획득, 음수: 소비)
            xp_type: XP 타입 (message, scenario_complete, achievement)
            session_id: 세션 ID (선택)
            metadata: 추가 메타데이터

        Returns:
            XPTransaction 인스턴스
        """
        from app.features.users.models.xp_transaction import XPTransaction

        # 사용자 조회
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # 레벨 계산 (현재)
        level_before = self._calculate_level(user.total_xp)

        # XP 업데이트
        new_xp = user.total_xp + xp_amount
        user.total_xp = new_xp

        # 레벨 계산 (업데이트 후)
        level_after = self._calculate_level(new_xp)
        did_level_up = level_after > level_before

        # 트랜잭션 로그 생성
        transaction = XPTransaction(
            user_id=user_id,
            session_id=session_id,
            xp_amount=xp_amount,
            xp_type=xp_type,
            xp_balance_after=new_xp,
            level_before=level_before,
            level_after=level_after,
            did_level_up=did_level_up,
            extra_metadata=metadata or {}
        )

        self.db.add(transaction)
        await self.db.flush()

        return transaction

    def _calculate_level(self, xp: int) -> int:
        """XP로부터 레벨 계산"""
        import math
        return math.floor(math.sqrt(xp / 100))

    async def get_xp_transactions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[XPTransaction]:
        """XP 트랜잭션 조회"""
        from app.features.users.models.xp_transaction import XPTransaction
        from sqlalchemy import select

        result = await self.db.execute(
            select(XPTransaction)
            .where(XPTransaction.user_id == user_id)
            .order_by(XPTransaction.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
EOF
```

### STEP 3-6: 백업 및 제거

```bash
# progression/ 백업
mv backend/app/features/progression backend/app/features/progression.backup

# memories/ 백업
mv backend/app/features/memories backend/app/features/memories.backup

# 확인
ls -la backend/app/features/users/models/
ls -la backend/app/features/chat/models/
```

### ✅ 창 3 완료 체크리스트

- [ ] users/models/ 디렉토리 생성
- [ ] XPTransaction → users/models/xp_transaction.py
- [ ] users/models/__init__.py 생성
- [ ] UserMemory → chat/models/user_memory.py
- [ ] chat/models/__init__.py 업데이트
- [ ] MemoryRepository 이동
- [ ] UserRepository에 XP 메서드 추가
- [ ] progression.backup 생성
- [ ] memories.backup 생성

---

## 창 4: services 추가 + logging 완성 🔥

**담당 파일:**
- `backend/app/features/chat/services/`
- `backend/app/features/logging/`

**목표:**
- progression_service.py 추가 (XP 계산)
- image_mapping_service.py 추가
- logging/repository.py 추가

### STEP 4-1: ProgressionService 생성

```bash
cd /Users/jtm427/Desktop/workspace

cat > backend/app/features/chat/services/progression_service.py << 'EOF'
"""
ProgressionService - XP 진행도 계산
"""


class ProgressionService:
    """
    XP 진행도 계산 서비스 (Stateless)

    역할:
    - XP 계산 로직 (DB 접근 없음)
    - 레벨 계산
    """

    def calculate_message_xp(self, message_length: int) -> int:
        """
        메시지 길이 기반 XP 계산

        Args:
            message_length: 메시지 길이

        Returns:
            XP 양
        """
        base_xp = 5

        # 길이에 따른 보너스
        if message_length > 50:
            base_xp += 5
        if message_length > 100:
            base_xp += 5
        if message_length > 200:
            base_xp += 10

        return base_xp

    def calculate_scenario_complete_xp(self, difficulty: str) -> int:
        """
        시나리오 완료 XP

        Args:
            difficulty: 난이도 (easy, normal, hard)

        Returns:
            XP 양
        """
        xp_map = {
            "easy": 100,
            "normal": 200,
            "hard": 300,
        }
        return xp_map.get(difficulty, 100)

    def calculate_level_from_xp(self, xp: int) -> int:
        """
        XP로부터 레벨 계산

        공식: level = floor(sqrt(XP / 100))

        Args:
            xp: 총 XP

        Returns:
            레벨
        """
        import math
        return math.floor(math.sqrt(xp / 100))

    def get_xp_for_next_level(self, current_level: int) -> int:
        """
        다음 레벨까지 필요한 총 XP

        Args:
            current_level: 현재 레벨

        Returns:
            다음 레벨까지 필요한 총 XP
        """
        next_level = current_level + 1
        return (next_level ** 2) * 100

    def get_xp_progress_to_next_level(
        self,
        current_xp: int,
        current_level: int
    ) -> dict:
        """
        다음 레벨까지 진행도

        Args:
            current_xp: 현재 XP
            current_level: 현재 레벨

        Returns:
            {
                "current_level": int,
                "next_level": int,
                "current_xp": int,
                "xp_for_current_level": int,
                "xp_for_next_level": int,
                "xp_needed": int,
                "progress_percentage": float
            }
        """
        xp_for_current = (current_level ** 2) * 100
        xp_for_next = ((current_level + 1) ** 2) * 100
        xp_needed = xp_for_next - current_xp

        xp_in_current_level = current_xp - xp_for_current
        xp_range = xp_for_next - xp_for_current
        progress = (xp_in_current_level / xp_range) * 100 if xp_range > 0 else 0

        return {
            "current_level": current_level,
            "next_level": current_level + 1,
            "current_xp": current_xp,
            "xp_for_current_level": xp_for_current,
            "xp_for_next_level": xp_for_next,
            "xp_needed": xp_needed,
            "progress_percentage": round(progress, 2)
        }


# 싱글톤
_progression_service = None


def get_progression_service() -> ProgressionService:
    """ProgressionService 싱글톤"""
    global _progression_service
    if _progression_service is None:
        _progression_service = ProgressionService()
    return _progression_service
EOF
```

### STEP 4-2: ImageMappingService 생성

```bash
cat > backend/app/features/chat/services/image_mapping_service.py << 'EOF'
"""
ImageMappingService - 이미지 매핑 우선순위 처리
"""
from typing import Optional
from app.features.scenarios.repository import ScenarioRepository


class ImageMappingService:
    """
    이미지 매핑 우선순위 처리

    우선순위:
    1. 스테이지 직접 할당 (ScenarioStageImage)
    2. 매핑 규칙 (ImageMappingRule)
    3. 시나리오 기본 이미지 (ScenarioDefaultImage)
    """

    def __init__(self, scenario_repo: ScenarioRepository):
        self.scenario_repo = scenario_repo

    async def resolve_image(
        self,
        scenario_id: str,
        stage_id: str,
        image_type: str = "background"
    ) -> Optional[str]:
        """
        이미지 URL 결정 (우선순위 기반)

        Args:
            scenario_id: 시나리오 ID
            stage_id: 스테이지 ID
            image_type: 이미지 타입 (background, character_sprite, thumbnail)

        Returns:
            이미지 URL 또는 None
        """
        # 1. 스테이지 직접 할당
        stage_image = await self.scenario_repo.get_stage_image(
            scenario_id, stage_id, image_type
        )
        if stage_image:
            return stage_image.image_url

        # 2. 매핑 규칙
        stage = await self.scenario_repo.get_stage(stage_id)
        if stage:
            mapping = await self.scenario_repo.get_image_mapping(
                scenario_id, stage.stage_type, image_type
            )
            if mapping:
                return mapping.image_url

        # 3. 시나리오 기본 이미지
        default = await self.scenario_repo.get_default_image(
            scenario_id, image_type
        )
        if default:
            return default.image_url

        return None

    async def resolve_all_images(
        self,
        scenario_id: str,
        stage_id: str
    ) -> dict:
        """
        모든 이미지 타입 한 번에 결정

        Args:
            scenario_id: 시나리오 ID
            stage_id: 스테이지 ID

        Returns:
            {
                "background": str | None,
                "character_sprite": str | None,
                "thumbnail": str | None
            }
        """
        return {
            "background": await self.resolve_image(scenario_id, stage_id, "background"),
            "character_sprite": await self.resolve_image(scenario_id, stage_id, "character_sprite"),
            "thumbnail": await self.resolve_image(scenario_id, stage_id, "thumbnail"),
        }
EOF
```

### STEP 4-3: services/__init__.py 업데이트

```bash
# 기존 __init__.py에 추가
cat >> backend/app/features/chat/services/__init__.py << 'EOF'

from .progression_service import ProgressionService, get_progression_service
from .image_mapping_service import ImageMappingService

__all__ = [
    # ... 기존 exports
    "ProgressionService",
    "get_progression_service",
    "ImageMappingService",
]
EOF
```

### STEP 4-4: logging/repository.py 생성

```bash
cat > backend/app/features/logging/repository.py << 'EOF'
"""
LoggingRepository - 시스템 로그 저장/조회
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import SystemLog


class LoggingRepository:
    """시스템 로그 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(
        self,
        log_level: str,
        message: str,
        logger_name: str,
        module: Optional[str] = None,
        function: Optional[str] = None,
        line_number: Optional[int] = None,
        extra_data: Optional[dict] = None
    ) -> SystemLog:
        """로그 생성"""
        log = SystemLog(
            log_level=log_level,
            message=message,
            logger_name=logger_name,
            module=module,
            function=function,
            line_number=line_number,
            extra_data=extra_data or {}
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_logs(
        self,
        log_level: Optional[str] = None,
        limit: int = 100
    ) -> List[SystemLog]:
        """로그 조회"""
        query = select(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit)

        if log_level:
            query = query.where(SystemLog.log_level == log_level)

        result = await self.db.execute(query)
        return result.scalars().all()
EOF
```

### STEP 4-5: logging/__init__.py 업데이트

```bash
cat > backend/app/features/logging/__init__.py << 'EOF'
"""
Logging Feature
"""
from .models import SystemLog
from .repository import LoggingRepository

__all__ = ["SystemLog", "LoggingRepository"]
EOF
```

### ✅ 창 4 완료 체크리스트

- [ ] progression_service.py 생성
- [ ] image_mapping_service.py 생성
- [ ] services/__init__.py 업데이트
- [ ] logging/repository.py 생성
- [ ] logging/__init__.py 업데이트

---

## 🔄 모든 창 완료 후: Import 경로 수정

**모든 창(1, 2, 3, 4)이 완료된 후** 실행하세요.

### STEP 5-1: chat/usecase.py import 수정

```bash
cd /Users/jtm427/Desktop/workspace

# 백업
cp backend/app/features/chat/usecase.py backend/app/features/chat/usecase.py.backup

# agents → agent
sed -i '' 's/from \.agents\.workflow/from .agent.workflow/g' backend/app/features/chat/usecase.py

# entities
sed -i '' 's/from app\.features\.entities/from .repositories.entity_repository/g' backend/app/features/chat/usecase.py

# progression
sed -i '' 's/from app\.features\.progression/from app.features.users/g' backend/app/features/chat/usecase.py

# memories
sed -i '' 's/from app\.features\.memories/from .repositories.memory_repository/g' backend/app/features/chat/usecase.py
```

### STEP 5-2: 서비스 파일들 import 수정

```bash
# extractors/entity_extractor.py
sed -i '' 's/from app\.features\.entities/from ..repositories.entity_repository/g' backend/app/features/chat/services/extractors/entity_extractor.py

# memory_service.py
sed -i '' 's/from app\.features\.memories/from ..repositories.memory_repository/g' backend/app/features/chat/services/memory_service.py
```

### STEP 5-3: main.py 라우터 수정

```bash
# entities 라우터 제거
# main.py 열어서 수동 수정

# 주석 처리:
# from app.features.entities.controller import router as entities_router
# app.include_router(entities_router, prefix="/api/entities", tags=["entities"])
```

### STEP 5-4: 전체 테스트

```bash
# 백엔드 재시작
cd backend
docker-compose restart backend

# 로그 확인
docker-compose logs backend -f

# API 테스트
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "scenario_id": "example-advanced",
    "user_input": "안녕하세요",
    "user_name": "테스터"
  }'
```

---

## ✅ 최종 검증 체크리스트

### 구조 검증
- [ ] `chat/agent/` 존재 (nodes, guards, handlers)
- [ ] `chat/agents.backup/` 존재
- [ ] `chat/models/` 존재 (dialogue_turn, entity, user_memory, etc.)
- [ ] `chat/repositories/` 존재 (entity, memory)
- [ ] `users/models/xp_transaction.py` 존재
- [ ] `chat/services/progression_service.py` 존재
- [ ] `chat/services/image_mapping_service.py` 존재
- [ ] `logging/repository.py` 존재
- [ ] `entities.backup/` 존재
- [ ] `progression.backup/` 존재
- [ ] `memories.backup/` 존재

### 기능 검증
- [ ] 백엔드 정상 시작
- [ ] `/api/chat` 정상 작동
- [ ] 엔티티 추출 정상
- [ ] XP 부여 정상
- [ ] 메모리 저장 정상

### Import 검증
```bash
# Python import 체크
cd backend
python -c "from app.features.chat.agent.workflow import get_workflow; print('OK')"
python -c "from app.features.chat.models import Entity; print('OK')"
python -c "from app.features.users.models import XPTransaction; print('OK')"
python -c "from app.features.chat.services.progression_service import get_progression_service; print('OK')"
```

---

## 🎯 요약

### 창 1 - agent 통합
- agent vs agents 중복 제거
- nodes, guards, handlers로 구조화
- **소요 시간: 15-20분**

### 창 2 - entities 통합
- entities → chat/models
- EntityRepository → chat/repositories
- **소요 시간: 10-15분**

### 창 3 - progression + memories 통합
- progression → users/models
- memories → chat/models
- UserRepository에 XP 메서드 추가
- **소요 시간: 15-20분**

### 창 4 - services 추가
- progression_service.py
- image_mapping_service.py
- logging/repository.py
- **소요 시간: 10분**

### 총 예상 시간
**병렬 작업: 20-25분** (가장 긴 창 기준)
**순차 작업: 50-65분**

---

**작성자:** Claude (Sonnet 4.5)
**마지막 업데이트:** 2025-11-11
