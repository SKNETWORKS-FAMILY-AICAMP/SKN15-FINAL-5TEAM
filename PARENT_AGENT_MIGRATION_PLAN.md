# Parent Agent 마이그레이션 계획

## 현재 상황 분석

### 기존 src/ 구조
```
src/
├── domain/
│   ├── agents/          # ParentAgent, GuardrailAgent, RouterAgent 등
│   ├── handlers/        # MissionHandler, SceneHandler 등
│   ├── services/        # 158개 Python 파일
│   │   ├── orchestration/   # state_tools, scene_tools, scenario_loader
│   │   ├── generation/      # children_agent, fallback_llm
│   │   ├── classification/  # intent_detector, entity_extractor
│   │   ├── evaluation/      # affinity_calculator, memory_extractor
│   │   └── validation/      # spell_checker
│   └── models/          # 데이터 모델들
├── core/
│   ├── utils/           # llm_client, logger
│   └── config/          # config_loader
└── infrastructure/      # DB, Redis 등
```

### 의존성 문제
1. **복잡한 Import 체인**
   - ParentAgent → Handlers → Services → Core Utils
   - 순환 참조 가능성
   - 158개 파일의 복잡한 의존성

2. **누락된 패키지**
   - `pydantic_settings` 등 일부 의존성 누락
   - 직접 import 시도 시 ModuleNotFoundError 발생

3. **설정 시스템 차이**
   - 기존: `src.core.config.config_loader` (YAML 기반)
   - 신규: `app.core.config` (Pydantic Settings 기반)

## 마이그레이션 전략

### 옵션 1: 점진적 마이그레이션 (권장)
**단계별 접근으로 안정성 확보**

#### Phase 1: 핵심 서비스만 먼저 마이그레이션
1. **ChildrenAgent 마이그레이션**
   - LLM 대사 생성 로직
   - 의존성: LLMClient, tone_profile_loader
   - 목표: `app/features/chat/services/llm_service.py`

2. **간단한 Guardrail/Router**
   - 입력 검증, 토픽 분류
   - 목표: `app/features/chat/services/guardrail_service.py`

3. **State Management**
   - state_tools, scene_tools 단순화
   - 목표: `app/features/chat/services/state_service.py`

#### Phase 2: Handler 통합
1. **Handler 패턴 단순화**
   - 기존: MissionHandler, SceneHandler, NarrativeHandler 등 5개
   - 신규: 통합된 StageHandler 하나로 단순화
   - 목표: `app/features/chat/agent/stage_handler.py`

#### Phase 3: Parent Agent 완성
1. **Parent Agent 실제 구현**
   - Phase 1, 2의 서비스 활용
   - 스테이지 라우팅 로직
   - 목표: `app/features/chat/agent/parent.py` 업데이트

### 옵션 2: 하이브리드 접근 (임시)
**필요한 부분만 src/에서 import**

```python
# app/features/chat/agent/parent.py
try:
    from src.domain.agents.parent_agent import ParentAgent as LegacyParent
    LEGACY_AVAILABLE = True
except ImportError:
    LEGACY_AVAILABLE = False

class ChatParent:
    def __init__(self):
        self.legacy = LegacyParent() if LEGACY_AVAILABLE else None

    async def execute(...):
        if self.legacy:
            # Legacy 코드 사용
            return await self._execute_legacy(...)
        else:
            # Dummy 응답
            return self._dummy_response(...)
```

**문제점:**
- src/ 의존성 전체를 유지해야 함
- 두 시스템 병행 유지의 복잡도
- 향후 정리 어려움

### 옵션 3: 완전 재작성 (장기)
**새로운 아키텍처로 처음부터 구현**

**장점:**
- 깨끗한 설계
- 4-Layer 아키텍처 완전 준수
- 불필요한 레거시 코드 제거

**단점:**
- 시간 소요 큼
- 기존 로직 재현 필요
- 테스트 부담

## 권장 실행 계획

### 🎯 Phase 1: LLM Service 마이그레이션 (우선)

#### 1.1 LLMClient 재구현
```
app/core/llm/
├── __init__.py
├── client.py          # LLMClient 재구현 (OpenAI/Anthropic)
└── prompts.py         # 프롬프트 템플릿 관리
```

#### 1.2 ChildrenAgent → LLMService
```
app/features/chat/services/
├── __init__.py
└── llm_service.py     # 대사 생성 로직
```

**마이그레이션 범위:**
- `src/domain/services/generation/children_agent.py` 로직
- Beat 기반 대사 생성
- LLM 응답 정규화

#### 1.3 통합 테스트
- 더미 시나리오로 대사 생성 테스트
- Frontend 연동 확인

### 🎯 Phase 2: State & Stage Management

#### 2.1 State Service
```
app/features/chat/services/
├── state_service.py   # 세션 상태 관리
└── stage_service.py   # 스테이지 진행 관리
```

#### 2.2 Stage Handler 통합
```
app/features/chat/agent/
└── stage_handler.py   # 통합 스테이지 처리
```

### 🎯 Phase 3: Parent Agent 완성

```python
# app/features/chat/agent/parent.py

from ..services.llm_service import LLMService
from ..services.state_service import StateService
from ..services.stage_service import StageService
from .stage_handler import StageHandler

class ChatParent:
    def __init__(self):
        self.llm = LLMService()
        self.state = StateService()
        self.stage = StageService()
        self.handler = StageHandler()

    async def execute(self, user_message, session_state, scenario_id):
        # 1. State 준비
        state = await self.state.prepare(session_state, scenario_id)

        # 2. Stage 결정
        current_stage = await self.stage.resolve(state)

        # 3. Handler 실행
        result = await self.handler.handle(current_stage, state, user_message)

        # 4. LLM 대사 생성
        dialogues = await self.llm.generate_dialogues(result.beats, state)

        # 5. State 업데이트
        updated_state = await self.state.update(state, result)

        return DialogueResult(
            dialogues=dialogues,
            next_stage=result.next_stage,
            stage_complete=result.stage_complete,
            updated_state=updated_state,
            affinity_delta=result.affinity_delta
        )
```

## 다음 즉시 실행할 작업

1. **LLMClient 재구현** (`app/core/llm/client.py`)
   - OpenAI API 호출
   - 에러 핸들링
   - 프롬프트 템플릿 시스템

2. **간단한 대사 생성 테스트**
   - 하드코딩된 시나리오로 테스트
   - Frontend 연동 확인

3. **점진적 확장**
   - State 관리 추가
   - Stage 라우팅 추가
   - Handler 로직 추가

## 파일 정리 계획

### 단계별 정리
1. **Phase 1 완료 후**: src/domain/services/generation/ 일부 제거
2. **Phase 2 완료 후**: src/domain/handlers/ 제거
3. **Phase 3 완료 후**: src/domain/agents/ 제거
4. **최종**: src/ 전체 제거 또는 참고용 보관

## 타임라인 예상

- **Phase 1 (LLM Service)**: 2-3시간
- **Phase 2 (State/Stage)**: 3-4시간
- **Phase 3 (Parent 완성)**: 2-3시간
- **테스트 & 버그 수정**: 2-3시간

**총 예상 시간**: 9-13시간 (1-2일)

## 결론

**권장 접근**: 옵션 1 (점진적 마이그레이션)
- Phase 1부터 시작하여 단계별 검증
- 각 단계마다 Git 커밋
- Frontend-Backend 연동 지속 확인
