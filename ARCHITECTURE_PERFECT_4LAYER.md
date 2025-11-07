# 🏆 100점 만점 4계층 아키텍처 (소규모 팀 최적화)

## 목표: Lean Clean Architecture for Small Teams

---

## 📐 **1. 4계층 구조 (Presentation 제거, Application에 통합)**

```
backend/
├── src/
│   ├── core/                           # 🔵 CORE (Domain Models + Interfaces)
│   │   ├── domain/                     # 도메인 모델
│   │   │   ├── entities/               # 엔티티
│   │   │   │   ├── user.py
│   │   │   │   ├── session.py
│   │   │   │   ├── character.py
│   │   │   │   └── conversation.py
│   │   │   │
│   │   │   └── value_objects/          # 값 객체
│   │   │       ├── session_id.py
│   │   │       ├── affinity_score.py
│   │   │       └── message.py
│   │   │
│   │   ├── interfaces/                 # Port 정의
│   │   │   ├── repositories/
│   │   │   │   ├── user_repository.py
│   │   │   │   ├── session_repository.py
│   │   │   │   ├── character_repository.py
│   │   │   │   ├── conversation_repository.py
│   │   │   │   └── memory_repository.py
│   │   │   │
│   │   │   └── providers/
│   │   │       ├── llm_provider.py
│   │   │       ├── cache_provider.py
│   │   │       ├── event_bus.py
│   │   │       └── embedding_provider.py
│   │   │
│   │   ├── exceptions/                 # 예외 계층
│   │   │   ├── base.py
│   │   │   ├── domain_exceptions.py
│   │   │   ├── infrastructure_exceptions.py
│   │   │   └── validation_exceptions.py
│   │   │
│   │   ├── events/                     # 도메인 이벤트
│   │   │   ├── base_event.py
│   │   │   ├── session_events.py
│   │   │   └── message_events.py
│   │   │
│   │   └── config/
│   │       ├── settings.py             # Pydantic Settings
│   │       └── constants.py
│   │
│   ├── domain/                         # 🟢 DOMAIN (Business Logic)
│   │   ├── services/                   # 도메인 서비스
│   │   │   ├── ai/
│   │   │   │   ├── agents/             # LangGraph Agents
│   │   │   │   │   ├── orchestrator.py
│   │   │   │   │   ├── dialogue.py
│   │   │   │   │   ├── router.py
│   │   │   │   │   └── guardrail.py
│   │   │   │   │
│   │   │   │   ├── prompt_builder.py
│   │   │   │   └── response_generator.py
│   │   │   │
│   │   │   ├── game/
│   │   │   │   ├── stage_manager.py
│   │   │   │   ├── mission_evaluator.py
│   │   │   │   └── affinity_calculator.py
│   │   │   │
│   │   │   ├── narrative/
│   │   │   │   ├── scenario_loader.py
│   │   │   │   ├── scene_orchestrator.py
│   │   │   │   └── dialogue_composer.py
│   │   │   │
│   │   │   └── validation/
│   │   │       ├── intent_classifier.py
│   │   │       ├── spell_checker.py
│   │   │       └── content_filter.py
│   │   │
│   │   └── use_cases/                  # Use Cases (Application 로직)
│   │       ├── auth/
│   │       │   ├── register_user.py
│   │       │   ├── login_user.py
│   │       │   └── refresh_token.py
│   │       │
│   │       ├── chat/
│   │       │   ├── send_message.py
│   │       │   ├── stream_response.py
│   │       │   └── get_history.py
│   │       │
│   │       └── session/
│   │           ├── create_session.py
│   │           ├── resume_session.py
│   │           └── end_session.py
│   │
│   ├── infrastructure/                 # 🔴 INFRASTRUCTURE (구현체)
│   │   ├── persistence/
│   │   │   ├── postgresql/
│   │   │   │   ├── repositories/       # Repository 구현
│   │   │   │   │   ├── user_repo.py
│   │   │   │   │   ├── session_repo.py
│   │   │   │   │   ├── character_repo.py
│   │   │   │   │   ├── conversation_repo.py
│   │   │   │   │   └── memory_repo.py
│   │   │   │   │
│   │   │   │   ├── models/             # ORM Models
│   │   │   │   │   ├── user_model.py
│   │   │   │   │   └── session_model.py
│   │   │   │   │
│   │   │   │   └── connection.py
│   │   │   │
│   │   │   └── redis/
│   │   │       ├── cache_provider.py
│   │   │       └── connection.py
│   │   │
│   │   ├── external/                   # 외부 API
│   │   │   └── openai/
│   │   │       ├── llm_provider.py
│   │   │       └── embedding_provider.py
│   │   │
│   │   ├── messaging/
│   │   │   └── event_bus.py
│   │   │
│   │   └── di/                         # DI Container
│   │       └── container.py
│   │
│   └── application/                    # 🟡 APPLICATION (API + Routes)
│       ├── api/
│       │   ├── v1/
│       │   │   ├── routes/
│       │   │   │   ├── auth.py
│       │   │   │   ├── chat.py
│       │   │   │   ├── session.py
│       │   │   │   └── user.py
│       │   │   │
│       │   │   ├── schemas/            # Pydantic Schemas
│       │   │   │   ├── auth.py
│       │   │   │   ├── chat.py
│       │   │   │   └── session.py
│       │   │   │
│       │   │   └── dependencies/       # FastAPI Dependencies
│       │   │       ├── auth.py
│       │   │       └── container.py
│       │   │
│       │   └── middleware/
│       │       ├── error_handler.py
│       │       ├── rate_limiter.py
│       │       └── logging.py
│       │
│       └── server.py                   # FastAPI App
│
└── tests/                              # src 구조 미러링
    ├── unit/
    │   ├── core/
    │   ├── domain/
    │   └── infrastructure/
    ├── integration/
    └── e2e/
```

---

## 🎯 **2. 계층별 책임 (명확한 구분)**

### **Core (도메인 모델 + 인터페이스)**
```python
# 책임:
- 엔티티, 값 객체 정의
- Port 인터페이스 정의
- 도메인 예외
- 설정

# 의존성: ZERO (외부 의존 금지)

# 예시:
core/domain/entities/session.py
core/interfaces/repositories/session_repository.py
core/exceptions/domain_exceptions.py
```

### **Domain (비즈니스 로직 + Use Cases)**
```python
# 책임:
- 비즈니스 규칙 (Services)
- Use Cases (오케스트레이션)
- 도메인 이벤트 처리
- AI Agent 로직

# 의존성: Core만 의존

# 예시:
domain/services/ai/dialogue.py          # 비즈니스 로직
domain/use_cases/chat/send_message.py   # Use Case
```

### **Infrastructure (기술 구현)**
```python
# 책임:
- Repository 구현 (PostgreSQL)
- Provider 구현 (OpenAI, Redis)
- ORM 모델
- 외부 API 어댑터

# 의존성: Core 인터페이스 구현

# 예시:
infrastructure/persistence/postgresql/repositories/session_repo.py
infrastructure/external/openai/llm_provider.py
```

### **Application (API + HTTP)**
```python
# 책임:
- HTTP 요청/응답 처리
- Pydantic 스키마 (직렬화)
- 미들웨어 (인증, 로깅, Rate Limit)
- FastAPI 라우팅

# 의존성: Domain Use Cases 호출

# 예시:
application/api/v1/routes/chat.py
application/api/v1/schemas/chat.py
```

---

## 🔄 **3. 의존성 규칙 (엄격 적용)**

```
┌─────────────────────────────────────────────┐
│            APPLICATION (API)                 │  ← HTTP, Schemas, Routes
│                                              │
└──────────────────┬──────────────────────────┘
                   │ calls
                   ▼
┌─────────────────────────────────────────────┐
│    DOMAIN (Business Logic + Use Cases)      │  ← Services, Use Cases
│                                              │
└──────────────────┬──────────────────────────┘
                   │ uses interfaces
                   ▼
┌─────────────────────────────────────────────┐
│         CORE (Models + Interfaces)          │  ← Entities, Ports
│                                              │
└──────────────────▲──────────────────────────┘
                   │ implements
                   │
┌─────────────────────────────────────────────┐
│     INFRASTRUCTURE (DB, Cache, LLM)         │  ← Adapters
│                                              │
└─────────────────────────────────────────────┘
```

### **허용되는 Import:**

| 계층 | 허용 Import | 금지 Import |
|------|-------------|-------------|
| **Core** | 표준 라이브러리, pydantic, typing | ❌ 다른 모든 계층 |
| **Domain** | ✅ core.* | ❌ infrastructure.*, application.* |
| **Infrastructure** | ✅ core.interfaces.* | ❌ domain.*, application.* |
| **Application** | ✅ domain.use_cases.*, core.* | ⚠️ infrastructure.di만 (DI 주입용) |

---

## 💉 **4. 의존성 주입 (핵심 패턴)**

### **Container (DI 중앙 관리):**

```python
# infrastructure/di/container.py
from dependency_injector import containers, providers
from core.interfaces.repositories import IUserRepository, ISessionRepository
from core.interfaces.providers import ILLMProvider, ICacheProvider
from infrastructure.persistence.postgresql.repositories import UserRepo, SessionRepo
from infrastructure.external.openai import OpenAIProvider
from infrastructure.persistence.redis import RedisCacheProvider
from domain.services.ai.dialogue import DialogueService
from domain.use_cases.chat.send_message import SendMessageUseCase

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Infrastructure - Repositories
    user_repository = providers.Singleton(
        UserRepo,
        connection_string=config.database.url
    )

    session_repository = providers.Singleton(
        SessionRepo,
        connection_string=config.database.url
    )

    conversation_repository = providers.Singleton(
        ConversationRepo,
        connection_string=config.database.url
    )

    # Infrastructure - Providers
    llm_provider = providers.Singleton(
        OpenAIProvider,
        api_key=config.openai.api_key,
        model=config.openai.model
    )

    cache_provider = providers.Singleton(
        RedisCacheProvider,
        redis_url=config.redis.url
    )

    # Domain - Services (비즈니스 로직)
    dialogue_service = providers.Factory(
        DialogueService,
        llm_provider=llm_provider,
        cache_provider=cache_provider
    )

    affinity_calculator = providers.Factory(
        AffinityCalculator
    )

    # Domain - Use Cases
    send_message_use_case = providers.Factory(
        SendMessageUseCase,
        session_repo=session_repository,
        conversation_repo=conversation_repository,
        dialogue_service=dialogue_service,
        affinity_calculator=affinity_calculator
    )

    login_use_case = providers.Factory(
        LoginUseCase,
        user_repo=user_repository
    )
```

### **Application Layer 사용:**

```python
# application/api/v1/routes/chat.py
from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from infrastructure.di.container import Container
from domain.use_cases.chat.send_message import SendMessageUseCase
from application.api.v1.schemas.chat import SendMessageRequest, MessageResponse

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/message", response_model=MessageResponse)
@inject
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    use_case: SendMessageUseCase = Depends(Provide[Container.send_message_use_case])
):
    """
    채팅 메시지 전송 및 AI 응답 받기
    """
    result = await use_case.execute(
        session_id=request.session_id,
        user_id=current_user.id,
        message=request.message
    )
    return MessageResponse.from_domain(result)
```

---

## 🏗️ **5. 핵심 패턴 적용**

### **Pattern 1: Repository Pattern**

```python
# core/interfaces/repositories/session_repository.py
from abc import ABC, abstractmethod
from typing import Optional
from core.domain.entities.session import Session

class ISessionRepository(ABC):
    @abstractmethod
    def get_by_id(self, session_id: str) -> Optional[Session]:
        """세션 조회"""
        pass

    @abstractmethod
    def save(self, session: Session) -> str:
        """세션 저장"""
        pass

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """세션 삭제"""
        pass

# infrastructure/persistence/postgresql/repositories/session_repo.py
from core.interfaces.repositories.session_repository import ISessionRepository
from core.domain.entities.session import Session
from infrastructure.persistence.postgresql.models.session_model import SessionModel

class SessionRepo(ISessionRepository):
    def __init__(self, connection_string: str):
        self._engine = create_engine(connection_string)
        self._session_factory = sessionmaker(bind=self._engine)

    def get_by_id(self, session_id: str) -> Optional[Session]:
        with self._session_factory() as db:
            model = db.query(SessionModel).filter_by(id=session_id).first()
            if not model:
                return None
            return self._to_entity(model)

    def save(self, session: Session) -> str:
        with self._session_factory() as db:
            model = self._to_model(session)
            db.add(model)
            db.commit()
            return model.id

    def _to_entity(self, model: SessionModel) -> Session:
        """ORM → Entity 변환"""
        return Session(
            session_id=model.id,
            user_id=model.user_id,
            scenario_id=model.scenario_id,
            # ...
        )

    def _to_model(self, entity: Session) -> SessionModel:
        """Entity → ORM 변환"""
        return SessionModel(
            id=entity.session_id,
            user_id=entity.user_id,
            # ...
        )
```

### **Pattern 2: Use Case Pattern**

```python
# domain/use_cases/chat/send_message.py
from dataclasses import dataclass
from core.interfaces.repositories import ISessionRepository, IConversationRepository
from core.domain.entities import Message
from domain.services.ai.dialogue import DialogueService
from domain.services.game.affinity_calculator import AffinityCalculator

@dataclass
class SendMessageRequest:
    session_id: str
    user_id: str
    message: str

@dataclass
class SendMessageResponse:
    message_id: str
    ai_response: str
    affinity_changes: dict

class SendMessageUseCase:
    """
    채팅 메시지 전송 Use Case

    책임:
    1. 세션 유효성 검증
    2. 사용자 권한 확인
    3. Dialogue Service 호출
    4. Affinity 업데이트
    5. 대화 저장
    """

    def __init__(
        self,
        session_repo: ISessionRepository,
        conversation_repo: IConversationRepository,
        dialogue_service: DialogueService,
        affinity_calculator: AffinityCalculator
    ):
        self._session_repo = session_repo
        self._conversation_repo = conversation_repo
        self._dialogue_service = dialogue_service
        self._affinity_calculator = affinity_calculator

    async def execute(
        self,
        session_id: str,
        user_id: str,
        message: str
    ) -> SendMessageResponse:
        # 1. 세션 조회
        session = self._session_repo.get_by_id(session_id)
        if not session:
            raise SessionNotFoundError(session_id)

        # 2. 권한 확인
        if session.user_id != user_id:
            raise UnauthorizedError("Not your session")

        # 3. 대화 생성 (Domain Service)
        ai_response = await self._dialogue_service.generate_response(
            session=session,
            user_input=message
        )

        # 4. Affinity 업데이트
        affinity_changes = self._affinity_calculator.update(
            session=session,
            response=ai_response
        )

        # 5. 대화 저장
        message_id = self._conversation_repo.save(
            session_id=session_id,
            user_message=message,
            ai_message=ai_response.text
        )

        return SendMessageResponse(
            message_id=message_id,
            ai_response=ai_response.text,
            affinity_changes=affinity_changes
        )
```

### **Pattern 3: Factory Pattern**

```python
# domain/services/ai/agents/agent_factory.py
from core.interfaces.providers import ILLMProvider
from domain.services.ai.agents.dialogue import DialogueAgent
from domain.services.ai.agents.router import RouterAgent
from domain.services.ai.agents.guardrail import GuardrailAgent

class AgentFactory:
    """Agent 생성 팩토리"""

    @staticmethod
    def create_dialogue_agent(
        llm_provider: ILLMProvider,
        scenario_id: str
    ) -> DialogueAgent:
        return DialogueAgent(
            llm_provider=llm_provider,
            scenario_id=scenario_id
        )

    @staticmethod
    def create_router_agent(
        llm_provider: ILLMProvider
    ) -> RouterAgent:
        return RouterAgent(llm_provider=llm_provider)

    @staticmethod
    def create_guardrail_agent() -> GuardrailAgent:
        return GuardrailAgent()
```

---

## 🧪 **6. 테스트 전략 (소규모 팀 최적화)**

### **Unit Tests (계층별):**

```python
# tests/unit/domain/use_cases/test_send_message.py
import pytest
from unittest.mock import Mock
from domain.use_cases.chat.send_message import SendMessageUseCase

class TestSendMessageUseCase:
    def setup_method(self):
        # Mock dependencies
        self.session_repo = Mock()
        self.conversation_repo = Mock()
        self.dialogue_service = Mock()
        self.affinity_calculator = Mock()

        self.use_case = SendMessageUseCase(
            session_repo=self.session_repo,
            conversation_repo=self.conversation_repo,
            dialogue_service=self.dialogue_service,
            affinity_calculator=self.affinity_calculator
        )

    async def test_execute_success(self):
        # Given
        session = Mock(session_id="test", user_id="user1")
        self.session_repo.get_by_id.return_value = session
        self.dialogue_service.generate_response.return_value = Mock(text="안녕")

        # When
        result = await self.use_case.execute(
            session_id="test",
            user_id="user1",
            message="안녕하세요"
        )

        # Then
        assert result.ai_response == "안녕"
        self.conversation_repo.save.assert_called_once()

    async def test_execute_unauthorized(self):
        # Given
        session = Mock(session_id="test", user_id="user1")
        self.session_repo.get_by_id.return_value = session

        # When/Then
        with pytest.raises(UnauthorizedError):
            await self.use_case.execute(
                session_id="test",
                user_id="user2",  # 다른 유저
                message="안녕"
            )
```

### **Integration Tests:**

```python
# tests/integration/test_session_repository.py
import pytest
from infrastructure.persistence.postgresql.repositories.session_repo import SessionRepo
from core.domain.entities.session import Session

@pytest.fixture
def test_db():
    # Test DB 셋업
    db = create_test_database()
    yield db
    db.cleanup()

def test_save_and_retrieve_session(test_db):
    # Given
    repo = SessionRepo(connection_string=test_db.url)
    session = Session(
        session_id="test",
        user_id="user1",
        scenario_id="demon_slayer"
    )

    # When
    session_id = repo.save(session)
    retrieved = repo.get_by_id(session_id)

    # Then
    assert retrieved.user_id == "user1"
    assert retrieved.scenario_id == "demon_slayer"
```

### **E2E Tests (최소한으로):**

```python
# tests/e2e/test_chat_flow.py
async def test_complete_chat_flow(api_client):
    # 1. Login
    login_resp = await api_client.post("/api/v1/auth/login", json={
        "username": "test", "password": "123"
    })
    token = login_resp.json()["access_token"]

    # 2. Create Session
    session_resp = await api_client.post("/api/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"scenario_id": "demon_slayer"}
    )
    session_id = session_resp.json()["session_id"]

    # 3. Send Message
    msg_resp = await api_client.post("/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"session_id": session_id, "message": "안녕"}
    )

    assert msg_resp.status_code == 200
    assert "ai_response" in msg_resp.json()
```

---

## 📊 **7. 100점 체크리스트 (4계층 버전)**

### **아키텍처 (40점)**
- [ ] Core 계층 의존성 0개
- [ ] Domain → Infrastructure 직접 의존 0개
- [ ] 모든 Infrastructure가 Core 인터페이스 구현
- [ ] Use Case Pattern 적용
- [ ] Repository Pattern 적용
- [ ] 순환 참조 0개
- [ ] 파일 크기 < 300줄 (SRP)

### **의존성 주입 (15점)**
- [ ] DI Container 구현
- [ ] 모든 Use Case에 DI 적용
- [ ] Mock 가능한 구조
- [ ] 전역 변수 0개
- [ ] Singleton 적절히 사용

### **테스트 (20점)**
- [ ] Unit Test Coverage > 70%
- [ ] Integration Test (Repository)
- [ ] E2E Test (주요 플로우)
- [ ] 테스트 구조 = src 구조
- [ ] CI/CD 자동 테스트

### **코드 품질 (15점)**
- [ ] Type Hints 100%
- [ ] Docstring (주요 함수)
- [ ] Import linter 적용
- [ ] 명확한 에러 메시지
- [ ] 일관된 네이밍

### **문서화 (10점)**
- [ ] Architecture 문서
- [ ] API 문서 (OpenAPI)
- [ ] Onboarding 가이드
- [ ] 계층별 README
- [ ] 의존성 규칙 문서

---

## 🚀 **8. 현재 → 100점 로드맵 (소규모 팀)**

### **Sprint 1 (1주): 의존성 정리 (58 → 75점)**
```
[ ] Domain → Infrastructure 직접 import 제거 (17개 파일)
[ ] 누락 인터페이스 생성 (ISessionManager, ICharacterRepository 등)
[ ] 전역 변수 제거 (characters_repo.py 등)
[ ] DI Container에 모든 의존성 등록
```

**작업량:** 2-3명 x 1주
**예상 점수:** 75/100

---

### **Sprint 2 (1주): Repository 분할 (75 → 85점)**
```
[ ] db_manager.py (2,718줄) 분할:
    - UserRepo (200줄)
    - SessionRepo (300줄)
    - ConversationRepo (400줄)
    - CharacterRepo (150줄)
    - MemoryRepo (200줄)
[ ] 각 Repository Unit Test 작성
[ ] ORM 모델 정리
```

**작업량:** 2명 x 1주
**예상 점수:** 85/100

---

### **Sprint 3 (1주): Use Case 분리 (85 → 92점)**
```
[ ] Application routes에서 비즈니스 로직 추출
[ ] domain/use_cases/ 생성:
    - auth/register_user.py
    - auth/login_user.py
    - chat/send_message.py
    - session/create_session.py
[ ] Use Case Unit Test 작성
[ ] API routes는 Use Case만 호출하도록 수정
```

**작업량:** 1-2명 x 1주
**예상 점수:** 92/100

---

### **Sprint 4 (1주): 테스트 & 문서화 (92 → 100점)**
```
[ ] Unit Test Coverage 70% 이상 달성
[ ] Integration Test (DB, Cache, LLM)
[ ] E2E Test (주요 플로우 3개)
[ ] Architecture 문서 작성
[ ] API 문서 자동화 (OpenAPI)
[ ] Onboarding 가이드
[ ] Import linter CI/CD 적용
```

**작업량:** 전체 팀 x 1주
**예상 점수:** 100/100

---

## 💡 **핵심 원칙 (4계층)**

### **1. 의존성 규칙**
```
Core ← Domain ← Infrastructure
  ↑               ↑
  └── Application ┘
```

### **2. 파일 위치 결정 기준**

**"이 코드가 PostgreSQL을 MongoDB로 바꿔도 동작하는가?"**
- YES → Domain에 위치
- NO → Infrastructure에 위치

**"이 코드가 FastAPI를 Flask로 바꿔도 동작하는가?"**
- YES → Domain에 위치
- NO → Application에 위치

**"이 코드가 외부 의존성이 전혀 없는가?"**
- YES → Core에 위치

### **3. 테스트 가능성 우선**
- 모든 클래스는 생성자 주입
- 전역 변수 금지
- Mock 가능한 인터페이스 사용

### **4. 단일 책임**
- 파일 하나 = 책임 하나
- 300줄 넘으면 분할 검토
- God Class 금지

---

## 🎯 **예상 효과**

### **현재 (58점)**
- ❌ Domain 단위 테스트 불가능
- ❌ DB 교체 시 Domain 수정 필요
- ❌ 병합 충돌 빈번 (db_manager.py)
- ❌ 신규 개발자 온보딩 2주+

### **100점 달성 후**
- ✅ Domain 완전 독립 테스트
- ✅ DB/Cache/LLM 교체 시 Infrastructure만 수정
- ✅ 병합 충돌 최소화 (파일 분리)
- ✅ 신규 개발자 온보딩 3일

---

## 📝 **최종 권장사항**

**4주 계획으로 100점 달성 가능합니다.**

**핵심:**
1. Sprint 1에서 의존성 정리 (가장 중요)
2. Sprint 2에서 God Class 분할
3. Sprint 3에서 Use Case 분리
4. Sprint 4에서 테스트/문서

**투입 인원:** 2-3명
**예상 공수:** 80-100 man-hours

100점 아키텍처는 **"미래 변경에 대한 보험"**입니다.
